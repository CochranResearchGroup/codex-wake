from __future__ import annotations

import os
import multiprocessing
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from codex_wake.managed_webhook_health import (
    PollingFallbackHealth, ProviderDeliveryHealth,
)
from codex_wake.managed_webhook_health_evidence import ManagedWebhookHealthEvidenceStore
from codex_wake.managed_webhooks import ManagedWebhookBinding


def binding(root: Path) -> ManagedWebhookBinding:
    return ManagedWebhookBinding(
        owner_id="health-owner", installation_id="health-install",
        canonical_root=str(root.resolve()), owner_uid=os.getuid(),
        provider_host="api.github.com", source_instance="github-ci",
        repository="example/project", repository_id=42,
        callback_url="https://hooks.example.test/github/webhook", events=("workflow_run",),
        service_id="codex-wake-github-webhook-github-ci.service",
        executable_id="codex-wake-github-webhook",
        provider_credential_ref="GITHUB_ADMIN_TOKEN", secret_generation=1,
    )


def project_fifo(root: str, result: multiprocessing.queues.Queue) -> None:
    store = ManagedWebhookHealthEvidenceStore(Path(root))
    delivery, polling = store.project(binding(Path(root)), now=1)
    result.put((delivery.value, polling.value))


class ManagedWebhookHealthEvidenceStoreTests(unittest.TestCase):
    def test_recording_rejects_a_symlinked_lock_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookHealthEvidenceStore(root)
            store.lock_path.parent.mkdir(parents=True)
            target = Path(temporary) / "outside-lock"
            target.touch()
            store.lock_path.symlink_to(target)

            with self.assertRaisesRegex(ValueError, "health evidence"):
                store.record_polling(binding(root), observed_at=1)

    def test_exact_binding_generation_successor_starts_fresh_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookHealthEvidenceStore(root)
            initial = binding(root)
            store.record_polling(initial, observed_at=10)
            successor = replace(initial, generation=initial.generation + 1)

            self.assertEqual(
                store.project(successor, now=11),
                (ProviderDeliveryHealth.UNPROVEN, PollingFallbackHealth.UNOBSERVED),
            )
            store.record_polling(successor, observed_at=11)
            self.assertEqual(
                store.project(successor, now=11),
                (ProviderDeliveryHealth.UNPROVEN, PollingFallbackHealth.READY),
            )

    def test_later_exact_delivery_replaces_the_prior_locator_but_not_the_clock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookHealthEvidenceStore(root)
            current = binding(root)
            store.record_delivery(
                current, generation=current.secret_generation,
                journal_locator="event_000000000001", observed_at=10,
            )

            latest = store.record_delivery(
                current, generation=current.secret_generation,
                journal_locator="event_000000000002", observed_at=11,
            )
            self.assertEqual(
                (latest.delivery_locator, latest.delivery_observed_at),
                ("event_000000000002", 11),
            )
            with self.assertRaisesRegex(ValueError, "clock moved backwards"):
                store.record_delivery(
                    current, generation=current.secret_generation,
                    journal_locator="event_000000000003", observed_at=9,
                )

    def test_world_writable_evidence_file_projects_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookHealthEvidenceStore(root)
            current = binding(root)
            store.record_polling(current, observed_at=1)
            store.path.chmod(0o666)

            self.assertEqual(
                store.project(current, now=2),
                (ProviderDeliveryHealth.UNKNOWN, PollingFallbackHealth.UNKNOWN),
            )

    def test_cross_root_or_owner_binding_cannot_record_or_project_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookHealthEvidenceStore(root)
            for foreign in (
                binding(Path(temporary) / "other-wake"),
                replace(binding(root), owner_uid=os.getuid() + 1, desired_fingerprint=""),
            ):
                with self.subTest(foreign=foreign.canonical_root, uid=foreign.owner_uid):
                    with self.assertRaisesRegex(ValueError, "health evidence"):
                        store.record_polling(foreign, observed_at=1)
                    self.assertEqual(
                        store.project(foreign, now=1),
                        (ProviderDeliveryHealth.UNKNOWN, PollingFallbackHealth.UNKNOWN),
                    )

    def test_fifo_evidence_file_does_not_block_health_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookHealthEvidenceStore(root)
            store.path.parent.mkdir(parents=True)
            os.mkfifo(store.path, 0o600)
            context = multiprocessing.get_context()
            result = context.Queue()
            child = context.Process(target=project_fifo, args=(str(root), result))
            child.start()
            child.join(1)
            if child.is_alive():
                child.terminate()
                child.join(1)
                self.fail("FIFO-backed health projection blocked")
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(
                result.get(timeout=1),
                (ProviderDeliveryHealth.UNKNOWN.value, PollingFallbackHealth.UNKNOWN.value),
            )


if __name__ == "__main__":
    unittest.main()
