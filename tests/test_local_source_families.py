from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from codex_wake.filesystem_signals import FilesystemSignalRunner
from codex_wake.local_source_families import (
    filesystem_family,
    local_source_registrations,
    process_exit_family,
    user_systemd_family,
)
from codex_wake.records import WakePath
from codex_wake.signals import ArmId, ArmedSignal, SignalRequest, SourceAnchor, WakeId
from codex_wake.source_registry import (
    BuiltinSourceRegistry,
    ReconstructionCandidate,
    ReconstructionContext,
)
from codex_wake.systemd_signals import SystemdSignalRunner
from codex_wake.systemd_source_config import SystemdSourceConfig, SystemdSourceStore


NOW = datetime(2026, 9, 15, tzinfo=UTC)


def candidate(
    wake_id: str,
    *,
    source: str,
    kind: str,
    source_instance: str,
    cwd: Path,
    subject: str,
) -> ReconstructionCandidate:
    armed = ArmedSignal(
        WakeId(wake_id),
        ArmId(f"arm_{wake_id}"),
        SignalRequest(
            1, source, source_instance, "state", kind, subject, "becomes",
        ),
        SourceAnchor(0, "fixture:0", {}, "state_recheck"),
        NOW,
        None,
    )
    return ReconstructionCandidate(
        WakePath(
            cwd / "pending" / f"{wake_id}.json",
            {
                "cwd": str(cwd),
                "predicate": {
                    "source": source,
                    "source_instance": source_instance,
                    "subject": subject,
                },
            },
        ),
        armed,
    )


class LocalSourceFamilyTests(unittest.TestCase):
    def context(self, root: Path) -> ReconstructionContext:
        return ReconstructionContext(root, Mock(), initial_reason="startup")

    def test_filesystem_family_preserves_pending_arm_and_adapter_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = (
                candidate(
                    "wake_z", source="filesystem", kind="file.created",
                    source_instance="z", cwd=root, subject="path:z.txt",
                ),
                candidate(
                    "wake_a", source="filesystem", kind="file.exists",
                    source_instance="a", cwd=root, subject="path:a.txt",
                ),
                candidate(
                    "wake_z_second", source="filesystem", kind="file.changed",
                    source_instance="z", cwd=root, subject="path:z.txt",
                ),
            )

            runners = filesystem_family(self.context(root), candidates)

            self.assertEqual(len(runners), 1)
            runner = runners[0]
            self.assertIsInstance(runner, FilesystemSignalRunner)
            self.assertEqual(tuple(runner._adapters), ("z", "a"))
            self.assertEqual(
                tuple(armed.wake_id for armed in runner._armed_signals),
                ("wake_z", "wake_a", "wake_z_second"),
            )
            self.assertEqual(runner._reason, "startup")

    def test_process_family_sorts_runners_and_retains_anchor_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = (
                candidate(
                    "wake_z", source="runtime", kind="process.exit",
                    source_instance="z", cwd=root, subject="process:z",
                ),
                candidate(
                    "wake_bad", source="runtime", kind="process.exit",
                    source_instance="bad", cwd=root, subject="process:bad",
                ),
                candidate(
                    "wake_a", source="runtime", kind="process.exit",
                    source_instance="a", cwd=root, subject="process:a",
                ),
            )

            def restored(armed):
                if armed.wake_id == "wake_bad":
                    raise ValueError("invalid anchor")
                adapter = Mock()
                adapter.descriptor = armed.spec.source_instance
                adapter.runner.return_value = f"runner:{armed.spec.source_instance}"
                return adapter

            with patch(
                "codex_wake.process_signals.restore_production_process_exit_adapter",
                side_effect=restored,
            ):
                runners = process_exit_family(self.context(root), candidates)

            self.assertEqual(runners[:2], ("runner:a", "runner:z"))
            self.assertEqual(
                (runners[2].source, runners[2].source_instance, runners[2].health_code),
                ("runtime", "bad", "RUNTIME_ANCHOR_INVALID"),
            )

    def test_user_systemd_family_sorts_configured_instances_and_uses_injected_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SystemdSourceStore(root)
            store.configure(SystemdSourceConfig(
                "a", "a.service", os.geteuid(), frozenset({"active"}),
            ))
            store.configure(SystemdSourceConfig(
                "z", "z.service", os.geteuid(), frozenset({"active"}),
            ))
            candidates = (
                candidate(
                    "wake_z", source="systemd", kind="unit.active_state",
                    source_instance="z", cwd=root, subject="unit:z.service",
                ),
                candidate(
                    "wake_a", source="systemd", kind="unit.active_state",
                    source_instance="a", cwd=root, subject="unit:a.service",
                ),
            )
            backend_factory = Mock(return_value=Mock())

            runners = user_systemd_family(
                self.context(root), candidates, systemd_backend_factory=backend_factory,
            )

            self.assertEqual(len(runners), 1)
            runner = runners[0]
            self.assertIsInstance(runner, SystemdSignalRunner)
            self.assertEqual(tuple(runner._adapters), ("a", "z"))
            self.assertEqual(
                tuple(armed.wake_id for armed in runner._armed_signals), ("wake_a", "wake_z"),
            )
            self.assertEqual(
                [call.args[0].source_instance for call in backend_factory.call_args_list],
                ["a", "z"],
            )
            backend_factory.return_value.resolve_unit.assert_not_called()
            backend_factory.return_value.read_unit.assert_not_called()

    def test_user_systemd_family_reports_unconfigured_instances_without_backend_use(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = (
                candidate(
                    "wake_z", source="systemd", kind="unit.active_state",
                    source_instance="z", cwd=root, subject="unit:z.service",
                ),
                candidate(
                    "wake_a", source="systemd", kind="unit.active_state",
                    source_instance="a", cwd=root, subject="unit:a.service",
                ),
            )
            backend_factory = Mock()

            runners = user_systemd_family(
                self.context(root), candidates, systemd_backend_factory=backend_factory,
            )

            self.assertEqual(
                [(runner.source, runner.source_instance, runner.health_code) for runner in runners],
                [
                    ("systemd", "a", "SYSTEMD_SOURCE_UNSUPPORTED"),
                    ("systemd", "z", "SYSTEMD_SOURCE_UNSUPPORTED"),
                ],
            )
            backend_factory.assert_not_called()

    def test_local_source_registrations_are_closed_and_nonconstructing(self) -> None:
        registrations = local_source_registrations()

        self.assertEqual(BuiltinSourceRegistry(registrations).registrations, registrations)
        self.assertEqual(
            [registration.registration_id for registration in registrations],
            ["local-filesystem", "local-process-exit", "local-user-systemd"],
        )
        self.assertEqual(
            registrations[0].ownership,
            frozenset({
                ("filesystem", "file.created"),
                ("filesystem", "file.exists"),
                ("filesystem", "file.changed"),
            }),
        )
        self.assertEqual(registrations[1].ownership, frozenset({("runtime", "process.exit")}))
        self.assertEqual(registrations[2].ownership, frozenset({("systemd", "unit.active_state")}))
