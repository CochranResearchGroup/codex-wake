from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.github_source_config import GitHubSourceStore
from codex_wake.managed_webhook_cleanup import (
    CleanupPhase, CleanupRecord, LocalCleanupState, ManagedWebhookCleanupController,
    ManagedWebhookCleanupStore, SystemdCleanupAdapter,
)
from codex_wake.managed_webhook_health import (
    CleanupAction, CleanupEligibility, CleanupHistory, CleanupHistoryEvent,
    CleanupHistoryPhase, CleanupIntent, ProviderObjectHealth,
)
from codex_wake.managed_webhook_rotation import (
    ManagedWebhookRotationCoordinator, ManagedWebhookRotationStore, RotationRecord,
)
from codex_wake.managed_webhooks import (
    InventoryClass, LifecycleState, ManagedWebhookBinding, ManagedWebhookStore,
    ManagedWebhookReconciler, OperationKind, OperationReceipt, OperationState,
    ProviderHook,
)
from codex_wake.webhook_lifecycle import WebhookListenerConfig, WebhookListenerStore
from tests.test_github_polling import config as github_config


class FakeProvider:
    def __init__(self, hooks: tuple[ProviderHook, ...]) -> None:
        self.hooks = list(hooks)
        self.calls: list[tuple[str, int]] = []
        self.fail_disable = False

    def list_hooks(self, *, repository_id: int) -> tuple[ProviderHook, ...]:
        self.calls.append(("list", repository_id))
        return tuple(self.hooks)

    def disable_hook(self, *, repository_id: int, hook_id: int) -> ProviderHook:
        self.calls.append(("disable", hook_id))
        if self.fail_disable:
            raise RuntimeError("provider result uncertain: token=never-recorded")
        selected = next(item for item in self.hooks if item.hook_id == hook_id)
        disabled = replace(selected, active=False)
        self.hooks = [disabled if item.hook_id == hook_id else item for item in self.hooks]
        return disabled

    def get_hook(self, *, repository_id: int, hook_id: int) -> ProviderHook | None:
        self.calls.append(("get", hook_id))
        return next((item for item in self.hooks if item.hook_id == hook_id), None)

    def delete_hook(self, *, repository_id: int, hook_id: int) -> None:
        self.calls.append(("delete", hook_id))
        self.hooks = [item for item in self.hooks if item.hook_id != hook_id]


class FakeLocal:
    def __init__(self, state: LocalCleanupState) -> None:
        self.state = state
        self.calls: list[str] = []

    def observe(self, *, listener, service_id: str) -> LocalCleanupState:
        self.calls.append("observe")
        return self.state

    def disable_and_prove_absent(
        self, *, listener, service_id: str,
    ) -> LocalCleanupState:
        self.calls.append("disable")
        self.state = LocalCleanupState.PROVEN_ABSENT
        return self.state

    def delete_and_prove_absent(
        self, *, listener, service_id: str,
    ) -> LocalCleanupState:
        self.calls.append("delete")
        self.state = LocalCleanupState.PROVEN_ABSENT
        return self.state


class ManagedWebhookCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "wake"
        WebhookListenerStore(self.root).configure(WebhookListenerConfig(
            source_instance="github-workflow", secret_ref="WEBHOOK_SECRET_VALUE", enabled=True,
        ))
        GitHubSourceStore(self.root).configure(github_config(
            source_instance="github-workflow", repository="octo/example",
            repository_id=42, evidence_mode="positive_only",
        ))
        initial = ManagedWebhookBinding(
            owner_id="github-workflow", installation_id="install-1",
            canonical_root=str(self.root.resolve()), owner_uid=os.getuid(),
            provider_host="api.github.com", source_instance="github-workflow",
            repository="octo/example", repository_id=42,
            callback_url="https://hooks.example.test/github/webhook",
            events=("workflow_run",),
            service_id="codex-wake-github-webhook-github-workflow.service",
            executable_id="codex-wake-github-webhook",
            provider_credential_ref="GITHUB_ADMIN_TOKEN_VALUE", secret_generation=1,
        )
        receipt = OperationReceipt(
            operation_id="op_0_create", operation=OperationKind.CREATE,
            state=OperationState.SUCCEEDED, generation=0,
            inventory=InventoryClass.EXACT, hook_id=101, code="READBACK_EXACT",
        )
        self.binding = ManagedWebhookStore(self.root).save(replace(
            initial, provider_hook_id=101, lifecycle=LifecycleState.ACTIVE,
            receipts=(receipt,),
        ))
        self.hook = ProviderHook(
            hook_id=101, callback_url=self.binding.callback_url,
            events=self.binding.events, active=True, content_type="json",
            insecure_ssl=False,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_disable_preview_is_effect_free_and_requires_exact_provider_and_local_ownership(self) -> None:
        provider = FakeProvider((self.hook,))
        local = FakeLocal(LocalCleanupState.OWNED_ACTIVE)
        plan = ManagedWebhookCleanupController(
            self.root, provider=provider, local=local,
        ).preview("github-workflow", CleanupAction.DISABLE)

        self.assertEqual(plan.inventory, ProviderObjectHealth.EXACT)
        self.assertEqual(plan.eligibility, CleanupEligibility.ELIGIBLE_FOR_EXPLICIT_PLAN)
        self.assertEqual(plan.intent.hook_id, 101)
        self.assertEqual(provider.calls, [("list", 42)])
        self.assertEqual(local.calls, ["observe"])

    def test_explicit_disable_records_intent_before_one_effect_and_retains_tombstone(self) -> None:
        provider = FakeProvider((self.hook,))
        local = FakeLocal(LocalCleanupState.OWNED_ACTIVE)
        controller = ManagedWebhookCleanupController(
            self.root, provider=provider, local=local,
        )
        plan = controller.preview("github-workflow", CleanupAction.DISABLE)
        tombstone = controller.execute(plan)

        self.assertEqual(tombstone.state.value, "DISABLED_PROVEN")
        record = ManagedWebhookCleanupStore(self.root).load("github-workflow")
        self.assertEqual(record.phase, CleanupPhase.DISABLED_PROVEN)
        self.assertEqual(record.resulting_binding_generation, self.binding.generation + 1)
        self.assertEqual(record.tombstone, tombstone)
        self.assertEqual(
            provider.calls,
            [("list", 42), ("list", 42), ("disable", 101), ("get", 101)],
        )
        self.assertEqual(local.calls, ["observe", "observe", "disable"])
        self.assertEqual(
            ManagedWebhookStore(self.root).load("github-workflow").lifecycle,
            LifecycleState.DISABLED,
        )
        self.assertFalse(WebhookListenerStore(self.root).select("github-workflow").enabled)

    def test_uncertain_disable_is_durable_and_never_becomes_retry_permission(self) -> None:
        provider = FakeProvider((self.hook,))
        provider.fail_disable = True
        local = FakeLocal(LocalCleanupState.OWNED_ACTIVE)
        controller = ManagedWebhookCleanupController(
            self.root, provider=provider, local=local,
        )
        plan = controller.preview("github-workflow", CleanupAction.DISABLE)
        with self.assertRaisesRegex(ValueError, "outcome is unknown") as raised:
            controller.execute(plan)
        self.assertNotIn("never-recorded", str(raised.exception))
        record = ManagedWebhookCleanupStore(self.root).load("github-workflow")
        self.assertEqual(record.phase, CleanupPhase.UNKNOWN)
        self.assertEqual(
            ManagedWebhookStore(self.root).load("github-workflow").lifecycle,
            LifecycleState.UNKNOWN,
        )

        second = controller.preview("github-workflow", CleanupAction.DISABLE)
        self.assertEqual(second.eligibility, CleanupEligibility.NOT_AUTHORIZED)
        with self.assertRaisesRegex(ValueError, "not executable"):
            controller.execute(second)
        self.assertEqual(
            [call for call in provider.calls if call[0] == "disable"],
            [("disable", 101)],
        )

    def test_delete_requires_disabled_tombstone_and_fresh_absence_then_deletes_once(self) -> None:
        provider = FakeProvider((self.hook,))
        local = FakeLocal(LocalCleanupState.OWNED_ACTIVE)
        controller = ManagedWebhookCleanupController(
            self.root, provider=provider, local=local,
        )
        controller.execute(controller.preview("github-workflow", CleanupAction.DISABLE))
        delete_plan = controller.preview("github-workflow", CleanupAction.DELETE)
        self.assertEqual(
            delete_plan.eligibility, CleanupEligibility.ELIGIBLE_FOR_EXPLICIT_PLAN,
        )
        deleted = controller.execute(delete_plan)

        self.assertEqual(deleted.state.value, "DELETED_PROVEN")
        record = ManagedWebhookCleanupStore(self.root).load("github-workflow")
        self.assertEqual(record.phase, CleanupPhase.DELETED_PROVEN)
        self.assertEqual(record.disabled_tombstone.state.value, "DISABLED_PROVEN")
        self.assertEqual(record.tombstone, deleted)
        self.assertEqual(
            ManagedWebhookStore(self.root).load("github-workflow").lifecycle,
            LifecycleState.DELETED,
        )
        self.assertEqual(
            [call for call in provider.calls if call[0] in {"disable", "delete"}],
            [("disable", 101), ("delete", 101)],
        )
        self.assertEqual(local.calls[-2:], ["observe", "delete"])

    def test_cleanup_authority_fences_reenable_reconcile_and_new_rotation(self) -> None:
        provider = FakeProvider((self.hook,))
        local = FakeLocal(LocalCleanupState.OWNED_ACTIVE)
        controller = ManagedWebhookCleanupController(
            self.root, provider=provider, local=local,
        )
        controller.execute(controller.preview("github-workflow", CleanupAction.DISABLE))

        listener_store = WebhookListenerStore(self.root)
        with self.assertRaisesRegex(ValueError, "cleanup authority exists"):
            listener_store.configure(replace(
                listener_store.select("github-workflow"), enabled=True,
            ))

        binding = ManagedWebhookStore(self.root).load("github-workflow")
        reconciliation = ManagedWebhookReconciler(
            ManagedWebhookStore(self.root), provider,
        ).preview(binding.owner_id)
        with self.assertRaisesRegex(ValueError, "cleanup authority exists"):
            ManagedWebhookReconciler(
                ManagedWebhookStore(self.root), provider,
            ).execute(reconciliation)

        rotation = RotationRecord(
            owner_id=binding.owner_id, canonical_root=str(self.root.resolve()),
            owner_uid=os.getuid(), source_instance=binding.source_instance,
            service_id=binding.service_id, binding_revision=binding.generation,
            previous_generation=1, target_generation=2, overlap_deadline=200,
        )
        with self.assertRaisesRegex(ValueError, "cleanup authority exists"):
            ManagedWebhookRotationCoordinator(
                ManagedWebhookRotationStore(self.root),
            ).begin(rotation, now=100)

    def test_cleanup_authority_is_scoped_to_owner_not_the_whole_root(self) -> None:
        other_intent = CleanupIntent.create(
            owner_id="other-owner", repository_id=77, hook_id=88,
            service_id="codex-wake-github-webhook-other-owner.service",
            generation=0, desired_fingerprint="b" * 64,
            action=CleanupAction.DISABLE,
        )
        other_history = CleanupHistory(
            owner_id=other_intent.owner_id,
            repository_id=other_intent.repository_id,
            hook_id=other_intent.hook_id, service_id=other_intent.service_id,
            generation=other_intent.generation,
            desired_fingerprint=other_intent.desired_fingerprint,
            entries=(CleanupHistoryEvent.from_intent(
                0, other_intent, CleanupHistoryPhase.INTENT_RECORDED,
            ),),
        )
        cleanup_store = ManagedWebhookCleanupStore(self.root)
        with cleanup_store.locked():
            cleanup_store._save_unlocked(CleanupRecord(
                canonical_root=str(self.root.resolve()), owner_uid=os.getuid(),
                source_instance="other-owner", revision=0,
                phase=CleanupPhase.PREPARED, intent=other_intent,
                history=other_history,
            ), expected_revision=None)
        provider = FakeProvider((self.hook,))
        controller = ManagedWebhookCleanupController(
            self.root, provider=provider,
            local=FakeLocal(LocalCleanupState.OWNED_ACTIVE),
        )

        tombstone = controller.execute(
            controller.preview("github-workflow", CleanupAction.DISABLE)
        )

        self.assertEqual(tombstone.state.value, "DISABLED_PROVEN")
        self.assertEqual(cleanup_store.load("other-owner").phase, CleanupPhase.PREPARED)

    def test_local_absence_requires_empty_cgroup_and_no_ipv4_or_ipv6_listener(self) -> None:
        unit_dir = Path(self.temporary.name) / "units"
        unit_dir.mkdir()
        proc = Path(self.temporary.name) / "proc"
        (proc / "net").mkdir(parents=True)
        header = "  sl  local_address rem_address   st\n"
        (proc / "net" / "tcp").write_text(header, encoding="ascii")
        (proc / "net" / "tcp6").write_text(header, encoding="ascii")
        cgroups = Path(self.temporary.name) / "cgroup"
        group = cgroups / "user.slice" / "cleanup"
        group.mkdir(parents=True)
        (group / "cgroup.procs").write_text("", encoding="ascii")
        service_id = "codex-wake-github-webhook-github-workflow.service"
        unit_path = unit_dir / service_id
        unit_path.write_text(
            "EnvironmentFile=" + str(self.root.resolve() / "github" / "webhook.env") + "\n"
            "ExecStart=/usr/bin/codex-wake-github-webhook --wake-root \""
            + str(self.root.resolve()) + "\" --source github-workflow\n"
            "Restart=on-failure\nTimeoutStopSec=15\n",
            encoding="utf-8",
        )
        unit_path.chmod(0o600)

        class Runner:
            control_group = "/user.slice/cleanup\n"

            def run(self, args, **kwargs):
                if "is-active" in args:
                    output = "inactive\n"
                elif "is-enabled" in args:
                    output = "disabled\n"
                elif "--property=ControlGroup" in args:
                    output = self.control_group
                else:
                    output = "0\n"
                return subprocess.CompletedProcess(args, 0, output, "")

        adapter = SystemdCleanupAdapter(
            self.root, runner=Runner(), proc_root=proc,
            cgroup_root=cgroups, unit_dir=unit_dir,
        )
        self.assertEqual(
            adapter.observe(
                listener=WebhookListenerStore(self.root).select("github-workflow"),
                service_id=service_id,
            ),
            LocalCleanupState.PROVEN_ABSENT,
        )
        process = proc / "123"
        process.mkdir()
        adapter.runner.control_group = ""
        root_bytes = str(self.root.resolve()).encode("utf-8")
        for cmdline in (
            b"codex-wake-github-webhook\0--wake-root=" + root_bytes
            + b"\0--source=github-workflow\0",
            b"python\0-m\0codex_wake.webhook_listener\0--wake-root\0"
            + root_bytes + b"\0--source\0github-workflow\0",
        ):
            with self.subTest(cmdline=cmdline):
                (process / "cmdline").write_bytes(cmdline)
                self.assertEqual(
                    adapter.observe(
                        listener=WebhookListenerStore(self.root).select("github-workflow"),
                        service_id=service_id,
                    ),
                    LocalCleanupState.UNKNOWN,
                )
        (process / "cmdline").unlink()
        process.rmdir()
        (proc / "net" / "tcp").write_text(
            header + "   0: 00000000:2274 00000000:0000 0A 0 0 0 0 0 0\n",
            encoding="ascii",
        )
        self.assertEqual(
            adapter.observe(
                listener=WebhookListenerStore(self.root).select("github-workflow"),
                service_id=service_id,
            ),
            LocalCleanupState.UNKNOWN,
        )

    def test_active_systemd_observation_uses_frozen_listener_without_store_reentry(self) -> None:
        unit_dir = Path(self.temporary.name) / "active-units"
        unit_dir.mkdir()
        proc = Path(self.temporary.name) / "active-proc"
        (proc / "net").mkdir(parents=True)
        process = proc / "123" / "fd"
        process.mkdir(parents=True)
        os.symlink("socket:[999]", process / "3")
        header = "  sl  local_address rem_address   st tx rx tr tm retr uid timeout inode\n"
        (proc / "net" / "tcp").write_text(
            header + "0: 0100007F:2274 00000000:0000 0A 0 0 0 0 0 999\n",
            encoding="ascii",
        )
        (proc / "net" / "tcp6").write_text(header, encoding="ascii")
        service_id = "codex-wake-github-webhook-github-workflow.service"
        unit_path = unit_dir / service_id
        unit_path.write_text(
            "EnvironmentFile=" + str(self.root.resolve() / "github" / "webhook.env") + "\n"
            "ExecStart=/usr/bin/codex-wake-github-webhook --wake-root \""
            + str(self.root.resolve()) + "\" --source github-workflow\n"
            "Restart=on-failure\nTimeoutStopSec=15\n",
            encoding="utf-8",
        )
        unit_path.chmod(0o600)

        class ActiveRunner:
            def run(self, args, **kwargs):
                if "is-active" in args:
                    output = "active\n"
                elif "is-enabled" in args:
                    output = "enabled\n"
                elif "--property=MainPID" in args:
                    output = "123\n"
                else:
                    output = "0\n"
                return subprocess.CompletedProcess(args, 0, output, "")

        listener = WebhookListenerStore(self.root).select("github-workflow")
        adapter = SystemdCleanupAdapter(
            self.root, runner=ActiveRunner(), proc_root=proc,
            unit_dir=unit_dir,
        )
        with patch.object(
            WebhookListenerStore, "select",
            side_effect=AssertionError("listener store re-entered"),
        ):
            self.assertEqual(
                adapter.observe(listener=listener, service_id=service_id),
                LocalCleanupState.OWNED_ACTIVE,
            )


if __name__ == "__main__":
    unittest.main()
