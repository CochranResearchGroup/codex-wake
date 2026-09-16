from __future__ import annotations

import hashlib
import hmac
import importlib.util
import io
import json
import os
import runpy
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
import zipfile
from contextlib import contextmanager
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from codex_wake.github_polling import (
    GitHubPollingAdapter,
    GitHubPollingConfig,
    RunPage,
    WorkflowRun,
)
from codex_wake.github_webhook_runtime import GitHubWebhookRuntime
from codex_wake.github_webhooks import WebhookConfig
from codex_wake.signals import ArmContext, EvaluationLimits, Ingested, Matched, WakeId
from codex_wake.webhook_http import WebhookHTTPConfig
from tests.test_signal_store import make_module
from tests.test_signals import make_intent


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/webhook_installed_smoke.py"
SPEC = importlib.util.spec_from_file_location("webhook_installed_smoke", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
smoke = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = smoke
SPEC.loader.exec_module(smoke)


def context(base: Path, *, manager: Path | None = None) -> smoke.ExecutionContext:
    return smoke.ExecutionContext(
        root=base,
        artifact_dir=base / "evidence",
        wake_root=base / "wake",
        manager_unit_dir=manager or base / "manager",
        fixture_dir=base / "fixture",
        installed_cli=base / "venv/bin/codex-wake",
        installed_listener=base / "venv/bin/codex-wake-github-webhook",
        installed_python=Path(sys.executable).resolve(),
    )


def fixture_at(when: datetime) -> smoke.Fixture:
    value = smoke.make_fixture()
    workflow = dict(value.workflow)
    workflow["terminal_proof_at"] = when.isoformat()
    body = json.loads(value.body)
    body["workflow_run"]["updated_at"] = when.isoformat()
    return replace(
        value,
        body=json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        workflow=workflow,
    )


class InstalledWebhookSmokeTests(unittest.TestCase):
    def test_default_refuses_without_execution(self) -> None:
        stderr = io.StringIO()
        with patch.object(smoke, "execute", side_effect=AssertionError("must not execute")):
            with redirect_stderr(stderr):
                result = smoke.main([])
        self.assertEqual(result, 2)
        self.assertIn("refuses", stderr.getvalue())
        self.assertIn("--execute", stderr.getvalue())

    def test_receipt_redacts_keys_values_and_stages_owner_only(self) -> None:
        secret = "never-publish-this-value"
        receipt = {
            "token": secret,
            "nested": {"webhook_secret": secret},
            "payload": '{"private":"body"}',
            "environment_file": f"KEY={secret}",
            "safe": f"COMMITTED {secret}",
        }
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "receipt.json"
            smoke.stage_receipt(
                receipt, destination=destination, secret_values=(secret,),
            )
            rendered = destination.read_text(encoding="utf-8")
            mode = destination.stat().st_mode & 0o777
        self.assertNotIn(secret, rendered)
        self.assertNotIn("private", rendered)
        self.assertIn("COMMITTED [redacted]", rendered)
        self.assertEqual(mode, 0o600)

    def test_command_runner_is_bounded_and_never_uses_a_shell(self) -> None:
        calls = []

        def fake_run(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, "ok", "")

        with tempfile.TemporaryDirectory() as tmp, patch.object(
            smoke.subprocess, "run", side_effect=fake_run,
        ):
            smoke.run_command(
                ["/installed/codex-wake", "status"],
                artifact_dir=Path(tmp), name="status", timeout=30,
            )
        self.assertEqual(calls[0][0], ["/installed/codex-wake", "status"])
        self.assertFalse(calls[0][1].get("shell", False))
        self.assertEqual(calls[0][1]["timeout"], 30)
        with self.assertRaisesRegex(ValueError, "timeout"):
            smoke.run_command(
                ["command"], artifact_dir=Path("/tmp"), name="bad", timeout=61,
            )

    def test_managed_reader_is_no_dispatch_isolated_and_stopped(self) -> None:
        class FakeProcess:
            pid = 4321

            def __init__(self) -> None:
                self.returncode = None
                self.terminated = False

            def poll(self):
                return self.returncode

            def terminate(self) -> None:
                self.terminated = True
                self.returncode = 0

            def wait(self, timeout=None):
                return self.returncode

            def kill(self) -> None:
                self.returncode = -9

        process = FakeProcess()
        checkpoints = []
        readiness = {
            "monitor_ready": True,
            "monitor_source": "codex-waked",
            "health": {
                "pid": process.pid,
                "mode": "loop",
                "recent": True,
                "persistent": True,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context(Path(tmp))
            env = smoke.installed_env(ctx)
            with patch.object(
                smoke.subprocess, "Popen", return_value=process,
            ) as popen, patch.object(
                smoke, "json_command", return_value=readiness,
            ), patch.object(
                smoke, "_process_start_identity", return_value="9876",
            ):
                tracked = []
                with smoke.managed_reader(
                    ctx, env, checkpoint=lambda stage, value: checkpoints.append(
                        (stage, dict(value))
                    ), tracked_identities=tracked,
                ) as evidence:
                    self.assertEqual(evidence["pid"], process.pid)
                    self.assertIsNone(process.poll())

            argv = popen.call_args.args[0]
            self.assertEqual(argv[:2], [
                str(ctx.installed_python), str(ctx.reader_bootstrap_path),
            ])
            self.assertIn("--no-dispatch", argv)
            self.assertEqual(env["XDG_STATE_HOME"], str(ctx.root / "state"))
            self.assertEqual(tracked, [(process.pid, "9876")])
            self.assertTrue(process.terminated)
            self.assertEqual([stage for stage, _ in checkpoints], [
                "managed_reader_ready", "managed_reader_stopped",
            ])
            self.assertTrue(checkpoints[-1][1]["stopped"])

    def test_managed_reader_bootstrap_blocks_signal_sources_before_daemon_main(self) -> None:
        from codex_wake import daemon

        with tempfile.TemporaryDirectory() as tmp:
            ctx = context(Path(tmp))
            path = smoke.write_managed_reader_bootstrap(ctx)
            observed = []
            original = daemon.default_signal_runners

            def fake_main(argv=None):
                observed.append((argv, daemon.default_signal_runners(None, None)))
                return 0

            try:
                with patch.object(daemon, "main", side_effect=fake_main), patch.object(
                    sys, "argv", [str(path), "--no-dispatch"],
                ), self.assertRaises(SystemExit) as stopped:
                    runpy.run_path(str(path), run_name="__main__")
            finally:
                daemon.default_signal_runners = original

        self.assertEqual(stopped.exception.code, 0)
        self.assertEqual(observed, [(["--no-dispatch"], ())])

    def test_arm_runs_only_while_no_dispatch_reader_is_active(self) -> None:
        events = []
        commands = {}

        @contextmanager
        def fake_reader(_context, _env, **kwargs):
            events.append("reader-enter")
            kwargs["checkpoint"]("managed_reader_ready", {"pid": 4321})
            try:
                yield {"pid": 4321, "dispatch": "disabled"}
            finally:
                kwargs["checkpoint"](
                    "managed_reader_stopped", {"pid": 4321, "stopped": True},
                )
                events.append("reader-exit")

        def fake_run(argv, **kwargs):
            name = kwargs["name"]
            events.append(name)
            commands[name] = argv
            stdout = "wake_qualified /tmp/pending/wake_qualified.json\n" if name == "arm" else ""
            return subprocess.CompletedProcess(argv, 0, stdout, "")

        with tempfile.TemporaryDirectory() as tmp:
            ctx = context(Path(tmp))
            with patch.object(smoke, "managed_reader", side_effect=fake_reader), patch.object(
                smoke, "run_command", side_effect=fake_run,
            ):
                wake_id, reader = smoke.configure_and_arm(
                    ctx, smoke.installed_env(ctx),
                    checkpoint=lambda stage, value: events.append(
                        f"checkpoint-{stage}-{value.get('wake_id', '')}"
                    ),
                )

        self.assertEqual(wake_id, "wake_qualified")
        self.assertEqual(reader["dispatch"], "disabled")
        self.assertEqual(events, [
            "configure-source-disabled", "reader-enter",
            "checkpoint-managed_reader_ready-", "enable-source",
            "arm", "checkpoint-armed-wake_qualified",
            "checkpoint-managed_reader_stopped-", "reader-exit",
            "configure-webhook",
        ])
        self.assertIn("--disabled", commands["configure-source-disabled"])
        self.assertIn("--enabled", commands["enable-source"])

    def test_manager_preflight_accepts_only_running_or_degraded_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context(Path(tmp))
            degraded = subprocess.CompletedProcess([], 1, "degraded\n", "")
            with patch.object(smoke, "run_command", return_value=degraded), patch.object(
                smoke, "manager_failed_units", return_value=("preexisting.service",),
            ):
                self.assertEqual(
                    smoke.manager_preflight(ctx),
                    ("degraded", ("preexisting.service",)),
                )
            unreachable = subprocess.CompletedProcess([], 1, "offline\n", "")
            with patch.object(smoke, "run_command", return_value=unreachable):
                with self.assertRaisesRegex(RuntimeError, "unreachable"):
                    smoke.manager_preflight(ctx)

    def test_manager_namespace_is_real_while_application_state_is_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            ctx = context(base, manager=base / "real-manager")
            with patch.dict(os.environ, {
                "XDG_CONFIG_HOME": str(base / "real-xdg"),
                "XDG_STATE_HOME": str(base / "host-state"),
            }, clear=False):
                env = smoke.installed_env(ctx)
            self.assertEqual(env["XDG_CONFIG_HOME"], str(base / "real-xdg"))
            self.assertEqual(env["XDG_STATE_HOME"], str(base / "state"))
            self.assertEqual(env["PYTHONPATH"], str(ctx.fixture_dir))
            calls = []

            def fake_run(argv, **kwargs):
                calls.append(argv)
                return subprocess.CompletedProcess(argv, 0, "", "")

            with patch.object(smoke, "run_command", side_effect=fake_run):
                for action in ("install", "start", "stop", "uninstall"):
                    smoke.service_command(
                        ctx, action, env=env, name=action,
                        executable_path=ctx.bootstrap_path if action == "install" else None,
                    )
            for argv in calls:
                position = argv.index("--unit-dir")
                self.assertEqual(argv[position + 1], str(ctx.manager_unit_dir))
                log_position = argv.index("--log-path")
                self.assertEqual(argv[log_position + 1], str(ctx.log_path))
                self.assertIn(str(ctx.wake_root), argv)

    def test_fixture_uses_one_valid_protocol_identity_and_secret_encoding(self) -> None:
        fixture = smoke.make_fixture()
        self.assertGreaterEqual(len(fixture.secret.encode("utf-8")), 16)
        uuid.UUID(fixture.delivery_id)
        uuid.UUID(fixture.restart_delivery_id)
        self.assertNotEqual(fixture.delivery_id, fixture.restart_delivery_id)
        signature = hmac.new(
            fixture.secret.encode("utf-8"), fixture.body, hashlib.sha256,
        ).hexdigest()
        self.assertEqual(len(signature), 64)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context(Path(tmp))
            path = smoke.write_service_environment(ctx, fixture)
            text = path.read_text(encoding="utf-8")
        self.assertIn(f"CODEX_WAKE_WEBHOOK_SECRET={fixture.secret}\n", text)
        self.assertEqual(json.loads(fixture.body)["workflow_run"]["updated_at"],
                         fixture.workflow["terminal_proof_at"])

    def test_failed_explicit_bootstrap_cannot_reach_installed_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            ctx = context(base)
            ctx.installed_listener.parent.mkdir(parents=True)
            provider_tripwire = base / "provider-reached"
            ctx.installed_listener.write_text(
                "#!/usr/bin/env python3\nfrom pathlib import Path\n"
                f"Path({str(provider_tripwire)!r}).write_text('reached')\n",
                encoding="utf-8",
            )
            smoke.write_fixture_bootstrap(ctx, smoke.make_fixture())
            (ctx.fixture_dir / "webhook_fixture_bootstrap.py").write_text(
                "raise RuntimeError('broken fixture')\n", encoding="utf-8",
            )
            result = subprocess.run(
                [str(ctx.bootstrap_path), "--wake-root", str(ctx.wake_root),
                 "--source", smoke.SOURCE],
                env=smoke.installed_env(ctx), text=True, capture_output=True,
                check=False, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(provider_tripwire.exists())

    def test_clean_candidate_rejects_any_dirty_or_untracked_input(self) -> None:
        dirty = subprocess.CompletedProcess([], 0, "?? src/new.py\n", "")
        with patch.object(smoke, "run_command", return_value=dirty):
            with self.assertRaisesRegex(RuntimeError, "not clean"):
                smoke.clean_candidate(Path("/repo"), Path("/evidence"))

    def test_build_uses_export_cwd_and_rejects_runner_in_wheel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            export = base / "export"
            export.mkdir()
            wheel_dir = base / "wheel"
            calls = []

            def fake_run(argv, **kwargs):
                calls.append((argv, kwargs))
                wheel = Path(argv[argv.index("--out-dir") + 1]) / "codex_wake-1.whl"
                with zipfile.ZipFile(wheel, "w") as archive:
                    archive.writestr("codex_wake/__init__.py", "")
                return subprocess.CompletedProcess(argv, 0, "", "")

            with patch.object(smoke.shutil, "which", return_value="/usr/bin/uv"), patch.object(
                smoke, "run_command", side_effect=fake_run,
            ):
                wheel = smoke.build_wheel(export, wheel_dir, base / "evidence")
            self.assertTrue(wheel.is_file())
            self.assertEqual(calls[0][1]["cwd"], export)

    def test_build_environment_excludes_python_import_injection(self) -> None:
        with patch.dict(os.environ, {
            "PYTHONPATH": "/untrusted/source",
            "PYTHONHOME": "/untrusted/home",
            "P53_PRESERVED": "yes",
        }, clear=False):
            env = smoke.isolated_build_env()
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("PYTHONHOME", env)
        self.assertEqual(env["P53_PRESERVED"], "yes")

    def test_process_identity_requires_exact_pid_executable_start_and_socket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            proc = base / "proc"
            pid = 123
            process = proc / str(pid)
            (process / "fd").mkdir(parents=True)
            (proc / "net").mkdir()
            ctx = replace(
                context(base), installed_python=base / "venv/bin/python",
            )
            ctx.installed_python.parent.mkdir(parents=True)
            ctx.installed_python.write_text("python", encoding="utf-8")
            (process / "exe").symlink_to(ctx.installed_python)
            (process / "fd/7").symlink_to("socket:[456]")
            (proc / "net/tcp").write_text(
                "header\n 0: 0100007F:2274 00000000:0000 0A 0 0 0 0 0 456\n",
                encoding="utf-8",
            )
            (proc / "net/tcp6").write_text("header\n", encoding="utf-8")
            arguments = [str(ctx.installed_python), str(ctx.bootstrap_path),
                         "--wake-root", str(ctx.wake_root), "--source", smoke.SOURCE]
            (process / "cmdline").write_bytes(b"\0".join(
                value.encode("utf-8") for value in arguments
            ) + b"\0")
            (process / "stat").write_text(
                " ".join([str(pid), "(listener)"] + ["0"] * 19 + ["999"]),
                encoding="ascii",
            )
            values = iter(["active", "enabled", str(pid), "999", "exec", "0"])
            with patch.object(smoke, "systemctl_value", side_effect=lambda *a, **k: next(values)):
                identity = smoke.service_identity(ctx, proc_root=proc)
            self.assertEqual(identity["pid"], str(pid))
            self.assertEqual(identity["process_start_ticks"], "999")
            self.assertEqual(identity["socket"]["socket_inode"], "456")

    def test_process_census_matches_exact_bootstrap_argv_and_tracked_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            proc = base / "proc"
            proc.mkdir()
            ctx = context(base)

            def process(pid, arguments, start):
                directory = proc / str(pid)
                directory.mkdir()
                (directory / "cmdline").write_bytes(
                    b"\0".join(value.encode() for value in arguments) + b"\0"
                )
                (directory / "stat").write_text(
                    " ".join([str(pid), "(listener)"] + ["0"] * 19 + [str(start)]),
                    encoding="ascii",
                )

            exact = [str(ctx.installed_python), str(ctx.bootstrap_path),
                     "--wake-root", str(ctx.wake_root), "--source", smoke.SOURCE]
            process(101, exact, 1001)
            process(102, ["codex-wake-github-webhook", "--wake-root", "/other",
                          "--source", smoke.SOURCE], 1002)
            process(103, ["renamed-process"], 1003)
            reader = [str(ctx.installed_python), str(ctx.reader_bootstrap_path),
                      "--wake-root", str(ctx.wake_root), "--no-dispatch"]
            process(104, reader, 1004)
            matches = smoke.matching_processes(
                ctx, tracked_identities=((103, "1003"),), proc_root=proc,
            )
            self.assertEqual([item["pid"] for item in matches], ["101", "103", "104"])
            self.assertEqual(matches[0]["reason"], "exact_bootstrap_argv")
            self.assertEqual(matches[1]["reason"], "tracked_pid_start")
            self.assertEqual(matches[2]["reason"], "exact_reader_argv")
            with self.assertRaisesRegex(RuntimeError, "census"):
                smoke.matching_processes(ctx, proc_root=base / "missing-proc")

    def test_socket_identity_rejects_any_additional_owned_listener(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            pid = 123
            (proc / str(pid) / "fd").mkdir(parents=True)
            (proc / "net").mkdir()
            (proc / str(pid) / "fd/7").symlink_to("socket:[456]")
            (proc / str(pid) / "fd/8").symlink_to("socket:[789]")
            (proc / "net/tcp").write_text(
                "header\n"
                " 0: 0100007F:2274 00000000:0000 0A 0 0 0 0 0 456\n"
                " 1: 00000000:2275 00000000:0000 0A 0 0 0 0 0 789\n",
                encoding="utf-8",
            )
            (proc / "net/tcp6").write_text("header\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "exactly"):
                smoke._socket_identity(pid, proc_root=proc)

    def test_poll_convergence_rejects_weak_activity_summary(self) -> None:
        weak = {
            "before": {"receipts": 1, "arms": 1, "matches": 0, "statuses": {}},
            "after": {"receipts": 1, "arms": 1, "matches": 1, "statuses": {}},
            "poll": {"dispatched": 0, "fired": 2, "failed": 1,
                     "signal_sources": []},
        }
        with self.assertRaisesRegex(RuntimeError, "logical wake"):
            smoke.assert_poll_convergence(weak)

    def test_failed_uninstall_preserves_unit_wake_fixture_and_recovery_root(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            root = Path(outer) / "recovery"
            root.mkdir()
            ctx = context(root)
            ctx.unit_path.parent.mkdir(parents=True)
            ctx.unit_path.write_text("owned unit", encoding="utf-8")
            ctx.wake_root.mkdir()
            ctx.fixture_dir.mkdir()
            (ctx.fixture_dir / "sidecar").write_text("fixture", encoding="utf-8")
            failed = subprocess.CompletedProcess([], 1, "", "")
            with patch.object(smoke, "service_command", return_value=failed), patch.object(
                smoke, "inactive_service_state",
                return_value={"active": "active", "enabled": "enabled",
                              "enabled_observed": "enabled", "pid": "12"},
            ), patch.object(smoke, "manager_failed_units", return_value=("old.service",)), patch.object(
                smoke, "matching_processes", return_value=("12 listener",),
            ), patch.object(smoke, "port_is_free", return_value=False):
                receipt = smoke.cleanup(
                    ctx, env={}, service_attempted=True,
                    failed_units_before=("old.service",),
                )
            self.assertFalse(receipt["safe"])
            self.assertTrue(root.exists())
            self.assertTrue(ctx.unit_path.exists())
            self.assertTrue(ctx.wake_root.exists())
            self.assertTrue((ctx.fixture_dir / "sidecar").exists())
            self.assertEqual(receipt["recovery_root"], str(root))

    def test_cleanup_success_requires_complete_terminal_readback_and_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            root = Path(outer) / "packet"
            root.mkdir()
            ctx = context(root)
            ctx.unit_path.parent.mkdir(parents=True)
            ctx.unit_path.write_text("owned", encoding="utf-8")

            def uninstall(*args, **kwargs):
                ctx.unit_path.unlink()
                return subprocess.CompletedProcess([], 0, "", "")

            with patch.object(smoke, "service_command", side_effect=uninstall), patch.object(
                smoke, "inactive_service_state",
                return_value={"active": "inactive", "enabled": "disabled",
                              "enabled_observed": "not-found", "pid": "0"},
            ), patch.object(smoke, "manager_failed_units", return_value=("old.service",)), patch.object(
                smoke, "matching_processes", return_value=(),
            ), patch.object(smoke, "port_is_free", return_value=True):
                receipt = smoke.cleanup(
                    ctx, env={}, service_attempted=True,
                    failed_units_before=("old.service",),
                )
            self.assertTrue(receipt["safe"])
            self.assertTrue(receipt["temporary_roots_removed"])
            self.assertEqual(receipt["failed_units_delta"], [])
            self.assertFalse(root.exists())

    def test_cleanup_preserves_recovery_on_matching_bootstrap_or_census_failure(self) -> None:
        for mode in ("match", "failure"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as outer:
                root = Path(outer) / "packet"
                root.mkdir()
                ctx = context(root)
                ctx.unit_path.parent.mkdir(parents=True)
                ctx.unit_path.write_text("owned", encoding="utf-8")

                def uninstall(*args, **kwargs):
                    ctx.unit_path.unlink()
                    return subprocess.CompletedProcess([], 0, "", "")

                census = (
                    RuntimeError("census unavailable")
                    if mode == "failure"
                    else ({"pid": "12", "process_start_ticks": "34",
                           "reason": "exact_bootstrap_argv"},)
                )
                with patch.object(smoke, "service_command", side_effect=uninstall), patch.object(
                    smoke, "inactive_service_state",
                    return_value={"active": "inactive", "enabled": "disabled",
                                  "enabled_observed": "not-found", "pid": "0"},
                ), patch.object(smoke, "manager_failed_units", return_value=("old.service",)), patch.object(
                    smoke, "matching_processes",
                    side_effect=census if isinstance(census, Exception) else None,
                    return_value=() if isinstance(census, Exception) else census,
                ), patch.object(smoke, "port_is_free", return_value=True):
                    receipt = smoke.cleanup(
                        ctx, env={}, service_attempted=True,
                        failed_units_before=("old.service",),
                        tracked_identities=((12, "34"),),
                    )
                self.assertFalse(receipt["safe"])
                self.assertEqual(receipt["recovery_root"], str(root))
                self.assertTrue(root.exists())

    def test_pre_service_cleanup_preserves_root_for_surviving_reader(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            root = Path(outer) / "packet"
            root.mkdir()
            ctx = context(root)
            proc = Path(outer) / "proc"
            process = proc / "4321"
            process.mkdir(parents=True)
            arguments = [
                str(ctx.installed_python), str(ctx.reader_bootstrap_path),
                "--wake-root", str(ctx.wake_root), "--no-dispatch",
            ]
            (process / "cmdline").write_bytes(
                b"\0".join(value.encode() for value in arguments) + b"\0"
            )
            (process / "stat").write_text(
                " ".join(["4321", "(reader)"] + ["0"] * 19 + ["9876"]),
                encoding="ascii",
            )
            census = smoke.matching_processes

            def synthetic_census(context, *, tracked_identities=()):
                return census(
                    context, tracked_identities=tracked_identities, proc_root=proc,
                )

            with patch.object(
                smoke, "matching_processes", side_effect=synthetic_census,
            ), patch.object(smoke, "port_is_free", return_value=True):
                receipt = smoke.cleanup(
                    ctx, env={}, service_attempted=False,
                    failed_units_before=None, tracked_identities=((4321, "9876"),),
                )

            self.assertFalse(receipt["safe"])
            self.assertFalse(receipt["no_matching_process"])
            self.assertEqual(receipt["recovery_root"], str(root))
            self.assertTrue(root.exists())

    def test_polling_failure_retains_every_completed_stage_after_safe_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            receipt_path = base / "external-receipt.json"
            wheel = base / "candidate.whl"
            wheel.write_bytes(b"wheel")
            staged_before_failure = {}
            identities = iter((
                ({"status": "ready"}, {"active": "active"},
                 {"webhook_listener": {"status": "ready"}},
                 {"pid": "101", "process_start_ticks": "1001"}),
                ({"status": "ready"}, {"active": "active"},
                 {"webhook_listener": {"status": "ready"}},
                 {"pid": "102", "process_start_ticks": "1002"}),
            ))
            deliveries = iter(((200, "COMMITTED"), (200, "DUPLICATE"),
                               (200, "DUPLICATE")))

            def fake_run(argv, **kwargs):
                if argv[1:3] == ["-m", "venv"]:
                    venv = Path(argv[3])
                    (venv / "bin").mkdir(parents=True)
                    for name in ("python", "codex-wake", "codex-wake-github-webhook"):
                        (venv / "bin" / name).write_text(name, encoding="utf-8")
                return subprocess.CompletedProcess(argv, 0, "", "")

            def fake_bootstrap(ctx, fixture):
                ctx.bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
                ctx.bootstrap_path.write_text("bootstrap", encoding="utf-8")
                return ctx.bootstrap_path

            def fake_service(ctx, action, **kwargs):
                if action == "install":
                    ctx.unit_path.parent.mkdir(parents=True, exist_ok=True)
                    ctx.unit_path.write_text("owned unit", encoding="utf-8")
                return subprocess.CompletedProcess([], 0, "", "")

            def fake_configure(ctx, env, *, checkpoint, tracked_identities):
                checkpoint("managed_reader_ready", {
                    "pid": 4321, "process_start_ticks": "9876",
                    "dispatch": "disabled", "signal_sources": "blocked",
                })
                checkpoint("armed", {
                    "wake_id": "wake_stage", "configuration": "armed",
                })
                checkpoint("managed_reader_stopped", {
                    "pid": 4321, "process_start_ticks": "9876",
                    "dispatch": "disabled", "signal_sources": "blocked",
                    "stopped": True,
                })
                return "wake_stage", {"pid": 4321, "stopped": True}

            def fail_poll(*args, **kwargs):
                staged_before_failure.update(json.loads(
                    receipt_path.read_text(encoding="utf-8")
                ))
                raise RuntimeError("poll failed")

            with patch.object(smoke, "manager_unit_dir", return_value=base / "manager"), patch.object(
                smoke, "manager_preflight", return_value=("degraded", ("old.service",)),
            ), patch.object(smoke, "port_is_free", return_value=True), patch.object(
                smoke, "matching_processes", return_value=(),
            ), patch.object(smoke, "clean_candidate", return_value={
                "commit": "a" * 40, "tree": "b" * 40,
            }), patch.object(smoke, "export_clean_tree"), patch.object(
                smoke, "build_wheel", return_value=wheel,
            ), patch.object(smoke, "run_command", side_effect=fake_run), patch.object(
                smoke, "installed_provenance", return_value={
                    "module": "/isolated/codex_wake/__init__.py",
                    "module_sha256": "c" * 64, "version": "0.5.2",
                    "interpreter": "/isolated/python",
                },
            ), patch.object(smoke, "configure_and_arm", side_effect=fake_configure), patch.object(
                smoke, "write_fixture_bootstrap", side_effect=fake_bootstrap,
            ), patch.object(smoke, "fixture_preflight"), patch.object(
                smoke, "service_command", side_effect=fake_service,
            ), patch.object(smoke, "wait_ready", side_effect=lambda *a, **k: next(identities)), patch.object(
                smoke, "signed_loopback_delivery", side_effect=lambda *a, **k: next(deliveries),
            ), patch.object(smoke, "provider_free_poll", side_effect=fail_poll), patch.object(
                smoke, "cleanup", return_value={"safe": True, "temporary_roots_removed": True},
            ):
                with redirect_stdout(io.StringIO()):
                    result = smoke.execute(receipt_path=receipt_path)

            self.assertEqual(result, 1)
            self.assertEqual(
                [item["code"] for item in staged_before_failure["deliveries"]],
                ["COMMITTED", "DUPLICATE", "DUPLICATE"],
            )
            self.assertEqual(staged_before_failure["initial_service"]["pid"], "101")
            self.assertEqual(staged_before_failure["restarted_service"]["pid"], "102")
            self.assertEqual(staged_before_failure["wake_id"], "wake_stage")
            self.assertTrue(staged_before_failure["managed_reader"]["stopped"])
            final = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(final["overall"], "failed")
            self.assertEqual(final["error"], "RuntimeError")
            self.assertTrue(final["cleanup"]["safe"])

    def test_in_process_ingress_restart_and_poll_share_one_frozen_occurrence(self) -> None:
        registered = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
        fixture = fixture_at(registered + timedelta(seconds=1))
        workflow = fixture.workflow
        run = WorkflowRun(
            str(workflow["repository"]), int(workflow["repository_id"]),
            int(workflow["workflow_id"]), int(workflow["run_id"]),
            int(workflow["run_attempt"]), str(workflow["ref"]),
            str(workflow["head_sha"]), str(workflow["status"]),
            str(workflow["conclusion"]), None,
            datetime.fromisoformat(str(workflow["terminal_proof_at"])),
            "github_attempt_started_or_job_completed_lower_bound",
        )

        class Client:
            def list_runs(self, query):
                return RunPage((run,), None, None, None)

            def get_run_attempt(self, repository, run_id, run_attempt):
                self.assert_identity = (repository, run_id, run_attempt)
                return run

        config = GitHubPollingConfig(
            source_instance=smoke.SOURCE, repository=smoke.REPOSITORY,
            repository_id=1, workflow_id=1,
            refs=frozenset({"refs/heads/main"}),
            conclusions=frozenset({"success"}), credential_ref="TOKEN",
            evidence_mode="positive_only",
        )

        def exchange(address, delivery_id):
            signature = hmac.new(
                fixture.secret.encode(), fixture.body, hashlib.sha256,
            ).hexdigest()
            request = (
                b"POST /github/webhook HTTP/1.1\r\nHost: localhost\r\n"
                b"Content-Type: application/json\r\n"
                + f"Content-Length: {len(fixture.body)}\r\n".encode()
                + f"X-Hub-Signature-256: sha256={signature}\r\n".encode()
                + b"X-GitHub-Event: workflow_run\r\n"
                + f"X-GitHub-Delivery: {delivery_id}\r\n\r\n".encode()
                + fixture.body
            )
            with smoke.socket.create_connection(address, timeout=2) as connection:
                connection.sendall(request)
                response = connection.makefile("rb").read()
            head, body = response.split(b"\r\n\r\n", 1)
            return int(head.split(b" ", 2)[1]), json.loads(body)["code"]

        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            module = make_module(database)
            adapter = GitHubPollingAdapter(config, Client())
            request = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(
                WakeId("wake_installed_contract"), request,
                ArmContext("key", "fingerprint", registered, None,
                           make_intent().resume, adapter),
            )

            def runtime(store):
                return GitHubWebhookRuntime(
                    WebhookHTTPConfig(host="127.0.0.1", port=0,
                                      request_timeout=2, shutdown_timeout=1),
                    adapter=adapter, module=store, checkpoints=store,
                    anchor=armed.anchor,
                    webhook_config=WebhookConfig(secret_refs=("SECRET",)),
                    resolve_secret=lambda ref: fixture.secret.encode(),
                    attempt_client_factory=lambda deadline: Client(),
                    operation_timeout=1,
                    now=lambda: datetime.fromisoformat(
                        str(workflow["terminal_proof_at"])
                    ),
                )

            first_runtime = runtime(module)
            first_results = []

            def first_deliveries():
                first_results.append(exchange(first_runtime.address, fixture.delivery_id))
                first_results.append(exchange(first_runtime.address, fixture.delivery_id))
                first_runtime.shutdown()

            thread = threading.Thread(target=first_deliveries)
            thread.start()
            first_runtime.serve()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(first_results, [(200, "COMMITTED"), (200, "DUPLICATE")])

            reopened = make_module(database)
            restarted = runtime(reopened)
            restart_results = []

            def restart_delivery():
                restart_results.append(
                    exchange(restarted.address, fixture.restart_delivery_id)
                )
                restarted.shutdown()

            thread = threading.Thread(target=restart_delivery)
            thread.start()
            restarted.serve()
            thread.join(2)
            self.assertEqual(restart_results, [(200, "DUPLICATE")])
            polled = adapter.poll_into(
                reopened, armed.anchor, checkpoints=reopened,
                now=registered + timedelta(seconds=2),
            )
            self.assertIsInstance(polled, Ingested)
            self.assertTrue(polled.receipts[0].duplicate)
            matched = reopened.evaluate(
                armed.wake_id, armed, registered + timedelta(seconds=2),
                EvaluationLimits(10),
            )
            self.assertIsInstance(matched, Matched)
            with sqlite3.connect(database) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM receipts WHERE source='github' AND source_instance=?",
                    (smoke.SOURCE,),
                ).fetchone()[0]
            self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
