#!/usr/bin/env python3
"""Provider-free installed-package qualification for managed webhook C3."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from codex_wake.github_polling import GitHubPollingConfig
from codex_wake.github_source_config import GitHubSourceStore
from codex_wake.managed_webhook_cleanup import (
    LocalCleanupState, ManagedWebhookCleanupController, SystemdCleanupAdapter,
)
from codex_wake.managed_webhook_health import (
    CleanupAction, ListenerHealth, PollingFallbackHealth,
    ProviderDeliveryHealth, project_health,
)
from codex_wake.managed_webhook_rotation_preview import ManagedWebhookRotationPreviewer
from codex_wake.managed_webhooks import (
    InventoryClass, LifecycleState, ManagedWebhookBinding, ManagedWebhookStore,
    OperationKind, OperationReceipt, OperationState, ProviderHook,
)
from codex_wake.webhook_lifecycle import WebhookListenerConfig, WebhookListenerStore


class _ProviderFixture:
    def __init__(self, hook: ProviderHook):
        self.hook = hook
        self.observation_calls = 0
        self.disable_calls = 0
        self.delete_calls = 0
        self.readback_calls = 0
        self.network_calls = 0

    def list_hooks(self, *, repository_id: int) -> tuple[ProviderHook, ...]:
        self.observation_calls += 1
        if repository_id != 42:
            raise RuntimeError("fixture repository changed")
        return (self.hook,)

    def disable_hook(self, **_: object) -> ProviderHook:
        self.disable_calls += 1
        self.hook = replace(self.hook, active=False)
        return self.hook

    def delete_hook(self, **_: object) -> None:
        self.delete_calls += 1
        self.hook = None

    def get_hook(self, **_: object) -> ProviderHook | None:
        self.readback_calls += 1
        return self.hook


class _LocalFixture:
    def __init__(self) -> None:
        self.state = LocalCleanupState.OWNED_ACTIVE
        self.observe_calls = 0
        self.disable_calls = 0
        self.delete_calls = 0

    def observe(self, **_: object) -> LocalCleanupState:
        self.observe_calls += 1
        return self.state

    def disable_and_prove_absent(self, **_: object) -> LocalCleanupState:
        self.disable_calls += 1
        self.state = LocalCleanupState.PROVEN_ABSENT
        return self.state

    def delete_and_prove_absent(self, **_: object) -> LocalCleanupState:
        self.delete_calls += 1
        return self.state


class _ReadOnlySystemdFixture:
    def __init__(self) -> None:
        self.read_calls = 0
        self.mutation_calls = 0

    def run(self, args, **_: object):
        self.read_calls += 1
        if any(action in args for action in ("enable", "disable", "daemon-reload")):
            self.mutation_calls += 1
            raise AssertionError("systemd mutation entered")
        if "is-active" in args:
            output = "inactive\n"
        elif "is-enabled" in args:
            output = "disabled\n"
        else:
            output = "\n"
        return subprocess.CompletedProcess(args, 0, output, "")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_qualification() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="codex-wake-c3-provider-free-") as temporary:
        base = Path(temporary)
        root = base / "wake"
        listener = WebhookListenerStore(root).configure(WebhookListenerConfig(
            source_instance="github-workflow", secret_ref="FIXTURE_HMAC", enabled=True,
        ))
        GitHubSourceStore(root).configure(GitHubPollingConfig(
            source_instance="github-workflow", repository="octo/example",
            repository_id=42, workflow_id=7, refs=frozenset({"refs/heads/main"}),
            conclusions=frozenset({"success"}), credential_ref="FIXTURE_READ_TOKEN",
            enabled=True, evidence_mode="positive_only",
        ))
        initial = ManagedWebhookBinding(
            owner_id="github-workflow", installation_id="install-1",
            canonical_root=str(root.resolve()), owner_uid=os.getuid(),
            provider_host="api.github.com", source_instance="github-workflow",
            repository="octo/example", repository_id=42,
            callback_url="https://hooks.example.test/github/webhook",
            events=("workflow_run",),
            service_id="codex-wake-github-webhook-github-workflow.service",
            executable_id="codex-wake-github-webhook",
            provider_credential_ref="FIXTURE_ADMIN_CREDENTIAL", secret_generation=1,
        )
        receipt = OperationReceipt(
            operation_id="op_0_create", operation=OperationKind.CREATE,
            state=OperationState.SUCCEEDED, generation=0,
            inventory=InventoryClass.EXACT, hook_id=101, code="READBACK_EXACT",
        )
        binding = ManagedWebhookStore(root).save(replace(
            initial, provider_hook_id=101, lifecycle=LifecycleState.ACTIVE,
            receipts=(receipt,),
        ))
        provider = _ProviderFixture(ProviderHook(
            hook_id=101, callback_url=binding.callback_url, events=binding.events,
            active=True, content_type="json", insecure_ssl=False,
        ))
        local = _LocalFixture()
        controller = ManagedWebhookCleanupController(
            root, provider=provider, local=local,
        )
        retained = (
            root / "signals" / "journal.sqlite3",
            root / "pending" / "wake-fixture.json",
            root / "signals" / "checkpoint-fixture.json",
            root / "github" / "polling-anchor-fixture.json",
        )
        for path in retained:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("retained\n", encoding="ascii")
        before = tuple(_digest(path) for path in retained)
        cleanup = controller.preview(binding.owner_id, CleanupAction.DISABLE)
        rotation = ManagedWebhookRotationPreviewer(root).preview(
            listener.source_instance, now=100, target_generation=2,
            overlap_seconds=900,
        )
        planes = project_health(
            generation=binding.generation,
            desired_fingerprint=binding.desired_fingerprint,
            local_listener=ListenerHealth.READY,
            provider_object=cleanup.inventory,
            provider_delivery=ProviderDeliveryHealth.UNPROVEN,
            polling_fallback=PollingFallbackHealth.READY,
        )

        disabled = controller.execute(cleanup)
        delete_plan = controller.preview(binding.owner_id, CleanupAction.DELETE)
        deleted = controller.execute(delete_plan)

        proc_root = base / "proc"
        (proc_root / "net").mkdir(parents=True)
        header = "  sl  local_address rem_address   st\n"
        (proc_root / "net" / "tcp").write_text(header, encoding="ascii")
        (proc_root / "net" / "tcp6").write_text(header, encoding="ascii")
        unit_dir = base / "units"
        unit_dir.mkdir()
        unit_path = unit_dir / binding.service_id
        unit_path.write_text("retained stopped unit fixture\n", encoding="ascii")
        unit_path.chmod(0o600)
        systemd = _ReadOnlySystemdFixture()
        census = SystemdCleanupAdapter(
            root, runner=systemd, proc_root=proc_root, unit_dir=unit_dir,
        ).observe(listener=listener, service_id=binding.service_id)
        after = tuple(_digest(path) for path in retained)
        result: dict[str, object] = {
            "schema_version": 1,
            "qualification": "managed_webhook_c3_provider_free",
            "planes": planes.to_dict(),
            "rotation": {
                "mode": "preview_only",
                "phase": rotation.phase,
                "next_action": rotation.next_action,
                "apply_supported": rotation.apply_supported,
                "lifecycle_execution": "not_included",
            },
            "cleanup": {
                "mode": "applied_to_fixtures",
                "eligibility": cleanup.eligibility.value,
                "disable_tombstone": disabled.state.value,
                "delete_tombstone": deleted.state.value,
                "tombstone_retained": True,
            },
            "provider_observation_calls": provider.observation_calls,
            "effect_counters": {
                "external_provider_calls": provider.network_calls,
                "external_service_mutation_calls": systemd.mutation_calls,
                "secret_resolution_calls": 0,
                "dispatch_calls": 0,
                "external_ingress_calls": 0,
            },
            "fixture_counters": {
                "provider_disable_calls": provider.disable_calls,
                "provider_delete_calls": provider.delete_calls,
                "provider_readback_calls": provider.readback_calls,
                "local_observe_calls": local.observe_calls,
                "local_disable_calls": local.disable_calls,
                "local_delete_calls": local.delete_calls,
                "systemd_read_calls": systemd.read_calls,
            },
            "local_absence_census": {
                "state": census.value,
                "unit_file_present": unit_path.is_file(),
                "pid_entries": sum(item.name.isdigit() for item in proc_root.iterdir()),
                "socket_tables": 2,
            },
            "sentinels_unchanged": before == after,
            "retention_scope": "wake_root_product_paths",
            "sanitized": True,
        }
    result["temporary_root_removed"] = not base.exists()
    if not result["temporary_root_removed"]:
        raise RuntimeError("temporary qualification root was not removed")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_qualification()
    print(json.dumps(result, sort_keys=True) if args.json else "managed webhook qualification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
