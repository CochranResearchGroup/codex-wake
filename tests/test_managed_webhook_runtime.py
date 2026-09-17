from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import unittest
from datetime import timedelta
from unittest.mock import patch

from codex_wake.github_polling import GitHubPollingAdapter
from codex_wake.github_source_config import GitHubSourceStore
from codex_wake.managed_webhook_rotation import (
    ManagedWebhookRotationCoordinator, ManagedWebhookRotationStore, Observation,
    RotationRecord, RuntimeProof,
)
from codex_wake.managed_webhook_runtime import (
    runtime_attestation_path, verify_runtime_attestation, write_runtime_attestation,
)
from codex_wake.managed_webhooks import ManagedWebhookBinding, ManagedWebhookStore
from codex_wake.signal_records import signal_journal_path
from codex_wake.signals import ArmContext, WakeId
from codex_wake.webhook_lifecycle import WebhookListenerConfig, WebhookListenerStore, WebhookServiceConfig
from codex_wake.webhook_listener import build_webhook_runtime
from tests.test_github_polling import NOW, FixtureClient, config as github_config, run
from tests.test_github_webhook_runtime import SECRET, exchange, signed_body
from tests.test_signal_store import make_module
from tests.test_signals import make_intent


BOOT_ID = "12345678-1234-4234-9234-123456789abc"


def binding(root: Path, **changes: object) -> ManagedWebhookBinding:
    values: dict[str, object] = {
        "owner_id": "wake-owner-1", "installation_id": "wake-install-1",
        "canonical_root": str(root.resolve()), "owner_uid": os.getuid(),
        "provider_host": "api.github.com", "source_instance": "github-workflow",
        "repository": "octo/example", "repository_id": 42,
        "callback_url": "https://hooks.example.test/github/webhook",
        "events": ("workflow_run",),
        "service_id": "codex-wake-github-webhook-github-workflow.service",
        "executable_id": "codex-wake-github-webhook",
        "provider_credential_ref": "CODEX_WAKE_GITHUB_ADMIN_TOKEN",
        "secret_generation": 7, "generation": 0,
    }
    values.update(changes)
    return ManagedWebhookBinding(**values)


def rotation(root: Path, **changes: object) -> RotationRecord:
    values: dict[str, object] = {
        "owner_id": "wake-owner-1", "canonical_root": str(root.resolve()),
        "owner_uid": os.getuid(), "source_instance": "github-workflow",
        "service_id": "codex-wake-github-webhook-github-workflow.service",
        "binding_revision": 0, "previous_generation": 7, "target_generation": 8,
        "overlap_deadline": 2_000_000_000,
    }
    values.update(changes)
    return RotationRecord(**values)


class Runner:
    def __init__(self, pid: int):
        self.pid = pid

    def run(self, args, *, check=True):
        output = f"{self.pid}\n" if "--property=MainPID" in args else ""
        return subprocess.CompletedProcess(args, 0, output, "")


class ManagedWebhookRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "wake"
        self.proc = Path(self.temporary.name) / "proc"
        self.pid = 4321
        (self.proc / "sys" / "kernel" / "random").mkdir(parents=True)
        (self.proc / "sys" / "kernel" / "random" / "boot_id").write_text(BOOT_ID + "\n")
        (self.proc / "stat").write_text("cpu 0 0 0 0\nbtime 1700000000\n")
        (self.proc / str(self.pid)).mkdir(parents=True)
        tail = ["S"] + ["0"] * 18 + ["250"]
        (self.proc / str(self.pid) / "stat").write_text(
            f"{self.pid} (webhook worker) " + " ".join(tail) + "\n"
        )
        self.listener = WebhookListenerConfig(
            "github-workflow", secret_ref="TARGET_SECRET", previous_secret_ref="PREVIOUS_SECRET",
            current_generation=8, previous_generation=7, enabled=True,
        )
        self.binding = binding(self.root)
        self.rotation = rotation(self.root)
        self.config = WebhookServiceConfig(
            self.rotation.service_id, self.root, self.listener.source_instance, None,
            Path(self.temporary.name) / "unit", Path(self.temporary.name) / "log",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_owner_only_attestation_projects_verified_process_clock_and_generations(self) -> None:
        written = write_runtime_attestation(
            wake_root=self.root, listener=self.listener, binding=self.binding,
            rotation=self.rotation, process_id=self.pid, proc_root=self.proc,
        )
        path = runtime_attestation_path(self.root, self.listener.source_instance)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(written.loaded_generations, (7, 8))
        with patch("codex_wake.managed_webhook_runtime.os.sysconf", return_value=100):
            proof = verify_runtime_attestation(
                config=self.config, listener=self.listener, binding=self.binding,
                rotation=self.rotation, runner=Runner(self.pid), proc_root=self.proc,
                bind_probe=lambda: True,
            )
        self.assertEqual(proof.process_id, self.pid)
        self.assertEqual(proof.process_started_at, 1_700_000_002)
        self.assertEqual(proof.authority_revision, 0)
        self.assertEqual(proof.loaded_generations, (7, 8))
        self.assertEqual(proof.evidence_locator, "runtime-attestation")

    def test_verification_rejects_foreign_mode_pid_boot_process_and_socket(self) -> None:
        write_runtime_attestation(
            wake_root=self.root, listener=self.listener, binding=self.binding,
            rotation=self.rotation, process_id=self.pid, proc_root=self.proc,
        )
        path = runtime_attestation_path(self.root, self.listener.source_instance)
        cases = ("mode", "pid", "boot", "ticks", "socket", "pid-reuse-during-probe")
        for case in cases:
            with self.subTest(case=case):
                path.chmod(0o600)
                (self.proc / "sys" / "kernel" / "random" / "boot_id").write_text(BOOT_ID + "\n")
                tail = ["S"] + ["0"] * 18 + ["250"]
                (self.proc / str(self.pid) / "stat").write_text(
                    f"{self.pid} (webhook worker) " + " ".join(tail) + "\n"
                )
                runner = Runner(self.pid)
                probe = lambda: True
                if case == "mode":
                    path.chmod(0o644)
                elif case == "pid":
                    runner = Runner(self.pid + 1)
                elif case == "boot":
                    (self.proc / "sys" / "kernel" / "random" / "boot_id").write_text(
                        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa\n"
                    )
                elif case == "ticks":
                    tail[-1] = "251"
                    (self.proc / str(self.pid) / "stat").write_text(
                        f"{self.pid} (webhook worker) " + " ".join(tail) + "\n"
                    )
                elif case == "socket":
                    probe = lambda: False
                else:
                    def replace_same_pid() -> bool:
                        replaced = ["S"] + ["0"] * 18 + ["251"]
                        (self.proc / str(self.pid) / "stat").write_text(
                            f"{self.pid} (replacement worker) " + " ".join(replaced) + "\n"
                        )
                        return True
                    probe = replace_same_pid
                with self.assertRaisesRegex(ValueError, "managed webhook runtime"):
                    verify_runtime_attestation(
                        config=self.config, listener=self.listener, binding=self.binding,
                        rotation=self.rotation, runner=runner, proc_root=self.proc,
                        bind_probe=probe,
                    )

    def test_write_rejects_cross_owner_or_binding_authority(self) -> None:
        for changed in (
            binding(self.root, owner_id="other-owner"),
            binding(self.root, source_instance="other-source"),
            binding(self.root, service_id="other.service"),
            binding(self.root, generation=1),
        ):
            with self.subTest(binding=changed), self.assertRaisesRegex(ValueError, "authority is invalid"):
                write_runtime_attestation(
                    wake_root=self.root, listener=self.listener, binding=changed,
                    rotation=self.rotation, process_id=self.pid, proc_root=self.proc,
                )

    def test_product_runtime_admits_and_records_only_the_target_generation(self) -> None:
        source = github_config(evidence_mode="positive_only")
        GitHubSourceStore(self.root).configure(source)
        module = make_module(signal_journal_path(self.root))
        adapter = GitHubPollingAdapter(source, FixtureClient([]))
        spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
        module.arm(
            WakeId("rotation-product"), spec,
            ArmContext("rotation-product", "rotation-product", NOW, None, make_intent().resume, adapter),
        )
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        listener = WebhookListenerConfig(
            source.source_instance, port=port, secret_ref="TARGET_SECRET",
            previous_secret_ref="PREVIOUS_SECRET", current_generation=8,
            previous_generation=7, enabled=True,
        )
        WebhookListenerStore(self.root).configure(listener)
        service_id = f"codex-wake-github-webhook-{source.source_instance}.service"
        managed_binding = ManagedWebhookStore(self.root).save(binding(
            self.root, source_instance=source.source_instance, service_id=service_id,
            repository=source.repository, repository_id=source.repository_id,
        ))
        observed_at = int((NOW + timedelta(seconds=2)).timestamp())
        coordinator = ManagedWebhookRotationCoordinator(ManagedWebhookRotationStore(self.root))
        current = coordinator.begin(rotation(
            self.root, source_instance=source.source_instance, service_id=service_id,
            binding_revision=managed_binding.generation, overlap_deadline=observed_at + 60,
        ), now=observed_at - 4)
        current = coordinator.intend_dual_restart(
            current.owner_id, expected_revision=current.revision, now=observed_at - 3,
        )
        current = coordinator.observe_dual_restart(
            current.owner_id, expected_revision=current.revision,
            proof=RuntimeProof(
                process_id=123, process_started_at=observed_at - 3,
                authority_revision=managed_binding.generation, loaded_generations=(7, 8),
                evidence_locator="fixture-runtime",
            ), now=observed_at - 2,
        )
        current = coordinator.intend_provider_update(
            current.owner_id, expected_revision=current.revision, now=observed_at - 1,
        )
        current = coordinator.observe_provider_update(
            current.owner_id, expected_revision=current.revision,
            observation=Observation.PROVED, now=observed_at,
        )
        runtime = build_webhook_runtime(
            wake_root=self.root, listener=listener,
            environment={
                "TARGET_SECRET": SECRET.decode(),
                "PREVIOUS_SECRET": "prior-fixture-only-webhook-secret",
                source.credential_ref: "fixture-provider-token",
            },
            attempt_client_factory=lambda deadline: FixtureClient([
                replace(
                    run(), completed_at=None, terminal_proof_at=run().completed_at,
                    time_provenance="github_attempt_started_or_job_completed_lower_bound",
                )
            ]),
            now=lambda: NOW + timedelta(seconds=2),
            runtime_proof_verifier=lambda: current.runtime_proof,
        )
        body, signature = signed_body()
        result = []

        def deliver() -> None:
            result.append(exchange(runtime.address, body, signature))
            result.append(exchange(runtime.address, body, signature))
            runtime.shutdown()

        client = threading.Thread(target=deliver)
        client.start()
        runtime.serve()
        client.join(2)
        self.assertFalse(client.is_alive())
        self.assertEqual(result, [(200, "COMMITTED"), (200, "DUPLICATE")])
        persisted = ManagedWebhookRotationStore(self.root).load("wake-owner-1")
        self.assertEqual(persisted.phase.value, "AWAITING_DELIVERY")
        self.assertIsNotNone(persisted.delivery_locator)
        self.assertTrue(runtime_attestation_path(self.root, source.source_instance).is_file())

        pending_target = coordinator.intend_target_restart(
            persisted.owner_id, expected_revision=persisted.revision, now=observed_at + 1,
        )
        target_listener = replace(
            listener, previous_secret_ref=None, previous_generation=None,
        )
        WebhookListenerStore(self.root).transition_rotation_secrets(
            expected=listener, replacement=target_listener,
            rotation=pending_target, binding=managed_binding,
        )
        target_proof = RuntimeProof(
            process_id=999, process_started_at=observed_at + 1,
            authority_revision=managed_binding.generation, loaded_generations=(8,),
            evidence_locator="target-runtime",
        )
        current = coordinator.observe_target_restart(
            persisted.owner_id, expected_revision=pending_target.revision,
            proof=target_proof, now=observed_at + 2,
        )
        current = coordinator.intend_retirement(
            current.owner_id, expected_revision=current.revision, now=observed_at + 3,
        )
        complete = coordinator.observe_retirement(
            current.owner_id, expected_revision=current.revision,
            observation=Observation.PROVED, now=observed_at + 4,
        )
        restarted = build_webhook_runtime(
            wake_root=self.root, listener=target_listener,
            environment={
                "TARGET_SECRET": SECRET.decode(),
                source.credential_ref: "fixture-provider-token",
            },
            attempt_client_factory=lambda deadline: FixtureClient([
                replace(
                    run(), completed_at=None, terminal_proof_at=run().completed_at,
                    time_provenance="github_attempt_started_or_job_completed_lower_bound",
                )
            ]),
            now=lambda: NOW + timedelta(seconds=6),
            runtime_proof_verifier=lambda: RuntimeProof(
                process_id=1000, process_started_at=observed_at + 5,
                authority_revision=managed_binding.generation, loaded_generations=(8,),
                evidence_locator="new-runtime",
            ),
        )
        restarted_result = []

        def deliver_restarted() -> None:
            restarted_result.append(exchange(
                restarted.address, body, signature,
                delivery="11111111-2222-3333-4444-555555555555",
            ))
            restarted.shutdown()

        restarted_client = threading.Thread(target=deliver_restarted)
        restarted_client.start()
        restarted.serve()
        restarted_client.join(2)
        self.assertEqual(complete.phase.value, "COMPLETE")
        self.assertEqual(restarted_result, [(200, "DUPLICATE")])

    def test_rotation_runtime_requires_all_distinct_secrets_before_attesting(self) -> None:
        source = github_config(evidence_mode="positive_only")
        GitHubSourceStore(self.root).configure(source)
        make_module(signal_journal_path(self.root))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        listener = WebhookListenerConfig(
            source.source_instance, port=port, secret_ref="TARGET_SECRET",
            previous_secret_ref="PREVIOUS_SECRET", current_generation=8,
            previous_generation=7, enabled=True,
        )
        WebhookListenerStore(self.root).configure(listener)
        for environment in (
            {"TARGET_SECRET": SECRET.decode()},
            {"TARGET_SECRET": SECRET.decode(), "PREVIOUS_SECRET": SECRET.decode()},
        ):
            with self.subTest(keys=tuple(environment)), self.assertRaisesRegex(
                Exception, "secret generation set is unavailable",
            ):
                build_webhook_runtime(
                    wake_root=self.root, listener=listener, environment=environment,
                    attempt_client_factory=lambda deadline: FixtureClient([run()]),
                    now=lambda: NOW + timedelta(seconds=2),
                )
        self.assertFalse(runtime_attestation_path(self.root, source.source_instance).exists())

    def test_pre_rotation_runtime_is_revoked_when_rotation_authority_appears(self) -> None:
        source = github_config(evidence_mode="positive_only")
        GitHubSourceStore(self.root).configure(source)
        make_module(signal_journal_path(self.root))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        listener = WebhookListenerConfig(
            source.source_instance, port=port, secret_ref="CURRENT_SECRET",
            current_generation=7, enabled=True,
        )
        WebhookListenerStore(self.root).configure(listener)
        runtime = build_webhook_runtime(
            wake_root=self.root, listener=listener,
            environment={"CURRENT_SECRET": SECRET.decode()},
            attempt_client_factory=lambda deadline: FixtureClient([run()]),
            now=lambda: NOW + timedelta(seconds=2),
        )
        service_id = f"codex-wake-github-webhook-{source.source_instance}.service"
        managed_binding = ManagedWebhookStore(self.root).save(binding(
            self.root, source_instance=source.source_instance, service_id=service_id,
            repository=source.repository, repository_id=source.repository_id,
        ))
        ManagedWebhookRotationStore(self.root).save(rotation(
            self.root, source_instance=source.source_instance, service_id=service_id,
            binding_revision=managed_binding.generation,
            overlap_deadline=int((NOW + timedelta(minutes=1)).timestamp()),
        ))
        body, signature = signed_body()
        result = []

        def deliver() -> None:
            result.append(exchange(runtime.address, body, signature))
            runtime.shutdown()

        client = threading.Thread(target=deliver)
        client.start()
        runtime.serve()
        client.join(2)
        self.assertEqual(result, [(503, "SECRET_UNAVAILABLE")])

    def test_rotation_runtime_rejects_foreign_binding_repository(self) -> None:
        source = github_config(evidence_mode="positive_only")
        GitHubSourceStore(self.root).configure(source)
        make_module(signal_journal_path(self.root))
        listener = WebhookListenerConfig(
            source.source_instance, secret_ref="CURRENT_SECRET", current_generation=7, enabled=True,
        )
        WebhookListenerStore(self.root).configure(listener)
        service_id = f"codex-wake-github-webhook-{source.source_instance}.service"
        managed_binding = ManagedWebhookStore(self.root).save(binding(
            self.root, source_instance=source.source_instance, service_id=service_id,
            repository="foreign/repository", repository_id=999,
        ))
        ManagedWebhookRotationStore(self.root).save(rotation(
            self.root, source_instance=source.source_instance, service_id=service_id,
            binding_revision=managed_binding.generation,
            overlap_deadline=int((NOW + timedelta(minutes=1)).timestamp()),
        ))
        with self.assertRaisesRegex(Exception, "rotation authority is unavailable"):
            build_webhook_runtime(
                wake_root=self.root, listener=listener,
                environment={"CURRENT_SECRET": SECRET.decode()},
                attempt_client_factory=lambda deadline: FixtureClient([run()]),
                now=lambda: NOW + timedelta(seconds=2),
            )


if __name__ == "__main__":
    unittest.main()
