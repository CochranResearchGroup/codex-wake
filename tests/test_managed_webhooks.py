from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest

from codex_wake.managed_webhooks import (
    InventoryClass,
    LifecycleState,
    ManagedWebhookBinding,
    ManagedWebhookReconciler,
    ManagedWebhookStore,
    OperationKind,
    OperationReceipt,
    OperationState,
    PlanAction,
    ProviderHook,
)


def binding(**changes: object) -> ManagedWebhookBinding:
    values: dict[str, object] = {
        "owner_id": "wake-owner-1",
        "installation_id": "wake-install-1",
        "canonical_root": "/var/lib/codex-wake",
        "owner_uid": os.getuid(),
        "provider_host": "api.github.com",
        "source_instance": "github-workflow",
        "repository": "octo/example",
        "repository_id": 42,
        "callback_url": "https://hooks.example.test/github/webhook",
        "events": ("workflow_run",),
        "service_id": "codex-wake-github-webhook-github-workflow.service",
        "executable_id": "codex-wake-github-webhook",
        "provider_credential_ref": "CODEX_WAKE_GITHUB_ADMIN_TOKEN",
        "secret_generation": 1,
    }
    values.update(changes)
    return ManagedWebhookBinding(**values)


class FakeProvider:
    def __init__(self, hooks: tuple[ProviderHook, ...] = ()) -> None:
        self.hooks = list(hooks)
        self.calls: list[tuple[str, int | None]] = []
        self.fail_write = False
        self.fail_readback = False

    def list_hooks(self, *, repository_id: int) -> tuple[ProviderHook, ...]:
        self.calls.append(("list", repository_id))
        return tuple(self.hooks)

    def create_hook(self, binding: ManagedWebhookBinding) -> ProviderHook:
        self.calls.append(("create", None))
        if self.fail_write:
            raise RuntimeError("provider result uncertain: token=never-recorded")
        hook = hook_for(binding, 101)
        self.hooks.append(hook)
        return hook

    def update_hook(self, *, hook_id: int, binding: ManagedWebhookBinding) -> ProviderHook:
        self.calls.append(("update", hook_id))
        if self.fail_write:
            raise RuntimeError("provider result uncertain")
        hook = hook_for(binding, hook_id)
        self.hooks = [hook if item.hook_id == hook_id else item for item in self.hooks]
        return hook

    def get_hook(self, *, repository_id: int, hook_id: int) -> ProviderHook | None:
        self.calls.append(("get", hook_id))
        if self.fail_readback:
            raise RuntimeError("provider readback unavailable")
        return next((item for item in self.hooks if item.hook_id == hook_id), None)


def hook_for(item: ManagedWebhookBinding, hook_id: int, **changes: object) -> ProviderHook:
    values: dict[str, object] = {
        "hook_id": hook_id,
        "callback_url": item.callback_url,
        "events": item.events,
        "active": True,
        "content_type": "json",
        "insecure_ssl": False,
    }
    values.update(changes)
    return ProviderHook(**values)


def attributed(item: ManagedWebhookBinding, hook_id: int, *, state: OperationState = OperationState.SUCCEEDED) -> ManagedWebhookBinding:
    receipt = OperationReceipt(
        operation_id=f"op_{item.generation}_create", operation=OperationKind.CREATE,
        state=state, generation=item.generation, inventory=InventoryClass.EXACT,
        hook_id=hook_id, code="READBACK_EXACT" if state is OperationState.SUCCEEDED else "WRITE_OR_READBACK_UNRESOLVED",
    )
    return replace(item, provider_hook_id=hook_id, receipts=item.receipts + (receipt,))


class ManagedWebhookBindingTests(unittest.TestCase):
    def test_fingerprint_is_deterministic_and_rejects_supplied_mismatch(self) -> None:
        first = binding()
        self.assertEqual(first.desired_fingerprint, binding().desired_fingerprint)
        self.assertNotEqual(first.desired_fingerprint, binding(callback_url="https://hooks.example.test/other").desired_fingerprint)
        self.assertNotEqual(first.desired_fingerprint, binding(canonical_root="/srv/codex-wake").desired_fingerprint)
        with self.assertRaisesRegex(ValueError, "binding is invalid"):
            binding(desired_fingerprint="0" * 64)
        with self.assertRaisesRegex(ValueError, "binding is invalid"):
            binding(provider_credential_ref="actual-secret-value")
        with self.assertRaisesRegex(ValueError, "binding is invalid"):
            binding(callback_url="https:///missing-host", provider_hook_id=7)
        with self.assertRaisesRegex(ValueError, "binding is invalid"):
            replace(attributed(binding(), 7), receipts=())

    def test_store_is_owner_scoped_atomic_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookStore(root)
            saved = store.save(binding(canonical_root=str(root.resolve())))
            self.assertEqual(store.load("wake-owner-1"), saved)
            rendered = store.path.read_text(encoding="utf-8")
            self.assertNotIn("actual-secret-value", rendered)
            self.assertIn("CODEX_WAKE_GITHUB_ADMIN_TOKEN", rendered)
            payload = json.loads(rendered)
            self.assertEqual(payload["schema_version"], 1)
            with self.assertRaisesRegex(ValueError, "owner"):
                store.load("another-owner")

    def test_inventory_classes_are_deterministic(self) -> None:
        item = binding()
        reconciler = ManagedWebhookReconciler(ManagedWebhookStore(Path(tempfile.gettempdir()) / "unused-managed-webhooks"), FakeProvider())
        self.assertEqual(reconciler.classify(item, ()), InventoryClass.ABSENT)
        self.assertEqual(reconciler.classify(item, (hook_for(item, 1),)), InventoryClass.COLLISION)
        owned = attributed(item, 1)
        self.assertEqual(reconciler.classify(owned, (hook_for(owned, 1),)), InventoryClass.EXACT)
        self.assertEqual(reconciler.classify(owned, (hook_for(owned, 1), hook_for(owned, 2))), InventoryClass.DUPLICATE)
        self.assertEqual(reconciler.classify(owned, (hook_for(owned, 1, active=False),)), InventoryClass.DRIFTED)
        self.assertEqual(reconciler.classify(owned, ()), InventoryClass.MISSING)


class ManagedWebhookReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ManagedWebhookStore(Path(self.temporary.name) / "wake")
        self.item = self.store.save(binding(canonical_root=str(self.store.wake_root)))
        self.provider = FakeProvider()
        self.reconciler = ManagedWebhookReconciler(self.store, self.provider)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_preview_is_read_only_and_absence_plans_one_create(self) -> None:
        plan = self.reconciler.preview("wake-owner-1")
        self.assertEqual((plan.inventory, plan.action, plan.operation), (InventoryClass.ABSENT, PlanAction.WRITE, OperationKind.CREATE))
        self.assertEqual(self.provider.calls, [("list", 42)])

    def test_execute_records_intent_writes_once_then_readbacks(self) -> None:
        plan = self.reconciler.preview("wake-owner-1")
        receipt = self.reconciler.execute(plan)
        self.assertEqual(receipt.state.value, "SUCCEEDED")
        self.assertEqual([name for name, _ in self.provider.calls], ["list", "create", "get"])
        saved = self.store.load("wake-owner-1")
        self.assertEqual(saved.lifecycle, LifecycleState.ACTIVE)
        self.assertEqual(saved.provider_hook_id, 101)
        self.assertNotIn("token=", json.dumps(saved.to_dict()))

    def test_exact_inventory_is_a_no_write_convergence(self) -> None:
        owned = self.store.save(attributed(self.item, 9), expected_generation=self.item.generation)
        self.provider.hooks = [hook_for(owned, 9)]
        plan = self.reconciler.preview("wake-owner-1")
        self.assertEqual((plan.inventory, plan.action), (InventoryClass.EXACT, PlanAction.NOOP))
        receipt = self.reconciler.execute(plan)
        self.assertEqual(receipt.operation, OperationKind.OBSERVE)
        self.assertEqual([name for name, _ in self.provider.calls], ["list"])

    def test_drift_updates_exact_owned_id_once(self) -> None:
        owned = self.store.save(attributed(self.item, 9), expected_generation=self.item.generation)
        self.provider.hooks = [hook_for(owned, 9, active=False)]
        plan = self.reconciler.preview("wake-owner-1")
        self.assertEqual((plan.inventory, plan.operation), (InventoryClass.DRIFTED, OperationKind.UPDATE))
        self.reconciler.execute(plan)
        self.assertEqual([name for name, _ in self.provider.calls], ["list", "update", "get"])

    def test_ambiguous_write_enters_unknown_and_rejects_second_write(self) -> None:
        self.provider.fail_write = True
        receipt = self.reconciler.execute(self.reconciler.preview("wake-owner-1"))
        self.assertEqual(receipt.state.value, "UNKNOWN")
        self.assertEqual(self.store.load("wake-owner-1").lifecycle, LifecycleState.UNKNOWN)
        self.provider.calls.clear()
        plan = self.reconciler.preview("wake-owner-1")
        self.assertEqual((plan.action, plan.operation), (PlanAction.READ_ONLY, OperationKind.OBSERVE))
        self.reconciler.execute(plan)
        self.assertEqual([name for name, _ in self.provider.calls], ["list"])

    def test_pending_intent_crash_recovery_is_read_only_then_unknown(self) -> None:
        plan = self.reconciler.preview("wake-owner-1")
        intent = replace(self.item, lifecycle=LifecycleState.CREATING)
        self.store.save(intent, expected_generation=plan.generation)
        self.provider.calls.clear()
        recovered = self.reconciler.preview("wake-owner-1")
        self.assertEqual((recovered.action, recovered.operation), (PlanAction.READ_ONLY, OperationKind.OBSERVE))
        receipt = self.reconciler.execute(recovered)
        self.assertEqual(receipt.state.value, "UNKNOWN")
        self.assertEqual([name for name, _ in self.provider.calls], ["list"])

    def test_disabled_binding_is_never_recreated(self) -> None:
        self.store.save(replace(self.item, lifecycle=LifecycleState.DISABLED), expected_generation=self.item.generation)
        plan = self.reconciler.preview("wake-owner-1")
        self.assertEqual((plan.inventory, plan.action), (InventoryClass.ABSENT, PlanAction.READ_ONLY))

    def test_stale_preview_is_rejected_before_write(self) -> None:
        plan = self.reconciler.preview("wake-owner-1")
        self.store.save(replace(self.store.load("wake-owner-1"), lifecycle=LifecycleState.DISABLED), expected_generation=self.item.generation)
        with self.assertRaisesRegex(ValueError, "stale"):
            self.reconciler.execute(plan)
        self.assertEqual([name for name, _ in self.provider.calls], ["list"])

    def test_unbound_matching_target_is_collision_and_never_adopted(self) -> None:
        self.provider.hooks = [hook_for(self.item, 1)]
        plan = self.reconciler.preview("wake-owner-1")
        self.assertEqual((plan.inventory, plan.action), (InventoryClass.COLLISION, PlanAction.READ_ONLY))

    def test_duplicate_and_missing_bound_id_never_plan_provider_writes(self) -> None:
        owned = self.store.save(attributed(self.item, 1), expected_generation=self.item.generation)
        for hooks, expected in (
            ([hook_for(owned, 1), hook_for(owned, 2)], InventoryClass.DUPLICATE),
            ([hook_for(owned, 2)], InventoryClass.MISSING),
        ):
            with self.subTest(expected=expected):
                self.provider.hooks = hooks
                plan = self.reconciler.preview("wake-owner-1")
                self.assertEqual((plan.inventory, plan.action), (expected, PlanAction.READ_ONLY))

    def test_ownership_ambiguity_is_recorded_as_unknown(self) -> None:
        active = self.store.save(replace(attributed(self.item, 9), lifecycle=LifecycleState.ACTIVE), expected_generation=self.item.generation)
        self.provider.hooks = [hook_for(active, 10)]
        receipt = self.reconciler.execute(self.reconciler.preview("wake-owner-1"))
        self.assertEqual(receipt.state.value, "UNKNOWN")
        self.assertEqual(self.store.load("wake-owner-1").lifecycle, LifecycleState.UNKNOWN)

    def test_create_result_id_survives_failed_readback_for_exact_id_recovery(self) -> None:
        self.provider.fail_readback = True
        receipt = self.reconciler.execute(self.reconciler.preview("wake-owner-1"))
        self.assertEqual((receipt.state, receipt.hook_id), (OperationState.UNKNOWN, 101))
        unresolved = self.store.load("wake-owner-1")
        self.assertEqual((unresolved.lifecycle, unresolved.provider_hook_id), (LifecycleState.UNKNOWN, 101))
        self.provider.fail_readback = False
        recovered = self.reconciler.preview("wake-owner-1")
        self.assertEqual((recovered.inventory, recovered.action), (InventoryClass.EXACT, PlanAction.READ_ONLY))
        self.reconciler.execute(recovered)
        self.assertEqual(self.store.load("wake-owner-1").lifecycle, LifecycleState.ACTIVE)


if __name__ == "__main__":
    unittest.main()
