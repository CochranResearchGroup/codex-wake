from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/webhook_live_github_qualification.py"
SPEC = importlib.util.spec_from_file_location("webhook_live_github_qualification", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


@contextmanager
def private_packet() -> tuple[Path, Path, dict[str, str]]:
    """A hermetic filesystem packet; the production temporary-root guard is mocked."""
    with tempfile.TemporaryDirectory() as tmp, patch.object(runner, "_is_temporary", return_value=False):
        base = Path(tmp)
        env = {"XDG_STATE_HOME": str(base / "state"), runner.TOKEN_REF: "token-private"}
        root = runner.create_private_root(env=env, armed=True)
        receipt = base / "receipt.json"
        yield root, receipt, env


def hook_response(hook_id: int = 456) -> dict:
    return {
        "id": hook_id, "active": True, "events": ["workflow_run"],
        "config": {"url": runner.CALLBACK_URL, "content_type": "json", "insecure_ssl": "0"},
    }


def effectors(calls: list[str], *, bad_census: bool = False, bad_query: bool = False,
              bad_wheel: bool = False) -> runner.RuntimeEffectors:
    def effect(name, value):
        def call(*_args):
            calls.append(name)
            return value
        return call

    def build_wheel(_root, candidate):
        calls.append("wheel")
        return {
            "wheel_path": "/private/p53-c6-live-github-test/wheel/codex_wake.whl",
            "wheel_sha256": "c" * 64,
            "archive_ref": candidate["canonical_ref"],
            "archive_commit": candidate["commit"],
            "archive_tree": candidate["tree"],
            "build_commit": "f" * 40 if bad_wheel else candidate["commit"],
        }

    return runner.RuntimeEffectors(
        canonical_candidate=effect("candidate", {"clean": True, "canonical_ref": "refs/remotes/origin/main",
                                                  "commit": "a" * 40, "tree": "b" * 40}),
        build_wheel=build_wheel,
        create_venv=effect("venv", {"isolated": True}),
        install_wheel=effect("install", {"global_install_mutations": 0}),
        configure_source=effect("source", {"source": runner.SOURCE, "enabled": False}),
        initialize_daemon=effect("daemon", {"dispatch_enabled": False, "anchor": "anchor-p53-c6",
                                              "source_enabled": True, "wake_id": "wake_p53_c6"}),
        configure_listener=effect("listener", {"source": runner.SOURCE, "address": "127.0.0.1", "port": 8820}),
        install_service=effect("service", {"unit": runner.UNIT}),
        readiness=effect("readiness", {"ready": True, "source": runner.SOURCE, "dispatch_enabled": False}),
        uninstall_service=effect("uninstall", {"unit": runner.UNIT, "uninstalled": True}),
        runtime_census=effect("census", {
            "unit_absent": True, "active": "inactive", "enabled": "disabled", "pid": 0,
            "matching_processes": 0, "port_8820_released": not bad_census,
            "unit_query": {"ok": not bad_query, "returncode": 1 if bad_query else 0,
                           "bus_error": "failed to connect" if bad_query else None},
            "failed_units_query": {"ok": not bad_query, "returncode": 1 if bad_query else 0,
                                   "bus_error": "failed to connect" if bad_query else None},
        }),
        unrelated_state=effect("unrelated", {"failed_units_delta": [], "route_hash": "retained"}),
    )


class LiveGitHubQualificationTests(unittest.TestCase):
    def test_frozen_identity_and_create_request_are_exact(self) -> None:
        identity = runner.frozen_identity()
        self.assertEqual((identity.github_host, identity.actor, identity.repository_id, identity.workflow_id),
                         ("github.com", "ecochran76", 1242753508, 279450573))
        self.assertEqual((identity.callback_url, identity.source_instance, identity.listener),
                         ("https://codex-wake.ecochran.dyndns.org/github/webhook",
                          "p53-c6-live-github", "127.0.0.1:8820"))
        request = runner.build_provider_request("create", secret="very-private")
        self.assertEqual((request.method, request.path), ("POST", "/repos/CochranResearchGroup/codex-wake/hooks"))
        self.assertEqual(request.body["events"], ["workflow_run"])
        self.assertEqual(request.body["config"], {
            "url": runner.CALLBACK_URL, "content_type": "json", "insecure_ssl": "0", "secret": "very-private",
        })

    def test_provider_request_and_staged_receipt_redact_recursive_secret_values(self) -> None:
        request = runner.build_provider_request("create", secret="very-private")
        rendered = json.dumps(runner.sanitized_request_summary(request, secrets=("very-private",)), sort_keys=True)
        self.assertNotIn("very-private", rendered)
        self.assertIn("request_sha256", rendered)
        with private_packet() as (root, receipt, _):
            runner.stage_receipt({"nested": ["very-private", {"note": "very-private"}],
                                  "secret_ref": runner.SECRET_REF}, receipt, root=root, secrets=("very-private",))
            staged = receipt.read_text(encoding="utf-8")
            self.assertNotIn("very-private", staged)
            self.assertIn(runner.SECRET_REF, staged)
            with self.assertRaisesRegex(RuntimeError, "outside"):
                runner.stage_receipt({}, root / "inside.json", root=root)

    def test_governed_private_root_rejects_temporary_and_non_child_paths(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "temporary"):
            runner.qualification_directory({"XDG_STATE_HOME": "/tmp/nope"})
        with private_packet() as (root, _, env):
            self.assertEqual(root.parent, runner.qualification_directory(env))
            impostor = root.parent.parent / "p53-c6-live-github-impostor"
            impostor.mkdir(mode=0o700)
            with self.assertRaisesRegex(RuntimeError, "governed"):
                runner.exact_private_root(impostor, env=env)

    def test_injected_runtime_preparation_is_bounded_and_does_not_expose_secret(self) -> None:
        with private_packet() as (root, receipt, env):
            runner.prepare_local(root, receipt, env=env, armed=True)
            calls: list[str] = []
            result = runner.prepare_runtime(
                root, env=env, effectors=effectors(calls), secret_factory=lambda: "s" * 32, armed=True,
            )
            self.assertEqual(calls, ["candidate", "wheel", "venv", "install", "source", "daemon", "listener", "service", "readiness"])
            self.assertEqual(result["phase"], "runtime_ready")
            self.assertEqual(result["runtime_counters"], {
                "establish": 1, "cleanup": 0, "secret_provision": 1, "secret_retirement": 0, "observation": 0,
            })
            self.assertEqual(result["wheel"], {
                "archive_ref": "refs/remotes/origin/main", "archive_commit": "a" * 40,
                "archive_tree": "b" * 40, "build_commit": "a" * 40,
                "wheel_sha256": "c" * 64,
            })
            self.assertEqual(
                runner.load_private_state(root, env=env)["wheel"]["wheel_path"],
                "/private/p53-c6-live-github-test/wheel/codex_wake.whl",
            )
            environment = runner.environment_path(root)
            provider_payload = runner.provider_payload_path(root)
            self.assertEqual(environment.stat().st_mode & 0o777, 0o600)
            self.assertEqual(provider_payload.stat().st_mode & 0o777, 0o600)
            self.assertIn("s" * 32, environment.read_text(encoding="utf-8"))
            self.assertIn("s" * 32, provider_payload.read_text(encoding="utf-8"))
            staged = receipt.read_text(encoding="utf-8")
            self.assertNotIn("s" * 32, staged)
            self.assertNotIn("token-private", staged)
            self.assertIn(runner.SECRET_REF, staged)
            self.assertNotIn("wheel_path", staged)

    def test_prepare_refuses_existing_state_or_packet_material(self) -> None:
        with private_packet() as (root, receipt, env):
            runner.prepare_local(root, receipt, env=env, armed=True)
            with self.assertRaisesRegex(RuntimeError, "existing lifecycle"):
                runner.prepare_local(root, receipt, env=env, armed=True)
        with private_packet() as (root, receipt, env):
            (root / "orphaned-packet-material").write_text("present", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "existing lifecycle"):
                runner.prepare_local(root, receipt, env=env, armed=True)

    def test_secret_provision_is_persisted_before_partial_write_and_cleanup_removes_present_artifacts(self) -> None:
        with private_packet() as (root, receipt, env):
            runner.prepare_local(root, receipt, env=env, armed=True)
            calls: list[str] = []
            with patch.object(runner, "write_provider_payload", side_effect=RuntimeError("payload write failed")):
                with self.assertRaisesRegex(RuntimeError, "payload write failed"):
                    runner.prepare_runtime(root, env=env, effectors=effectors(calls),
                                           secret_factory=lambda: "s" * 32, armed=True)
            state = runner.load_private_state(root, env=env)
            self.assertEqual(state["phase"], "runtime_prepare_uncertain")
            self.assertEqual(state["runtime_counters"]["secret_provision"], 1)
            self.assertEqual(state["secret_material"]["created"], ["webhook_env"])
            self.assertTrue(runner.environment_path(root).exists())
            self.assertFalse(runner.provider_payload_path(root).exists())
            runner.cleanup_runtime(root, env=env, effectors=effectors(calls), armed=True)
            self.assertFalse(runner.environment_path(root).exists())
            self.assertFalse(runner.provider_payload_path(root).exists())
            self.assertEqual(runner.load_private_state(root, env=env)["runtime_counters"]["secret_retirement"], 1)

    def test_cleanup_retires_secret_before_missing_unrelated_state_baseline(self) -> None:
        with private_packet() as (root, receipt, env):
            runner.prepare_local(root, receipt, env=env, armed=True)
            calls: list[str] = []
            runner.prepare_runtime(root, env=env, effectors=effectors(calls), secret_factory=lambda: "s" * 32, armed=True)
            adapter = effectors(calls)
            adapter = runner.RuntimeEffectors(
                **{**adapter.__dict__, "unrelated_state": lambda *_args: (_ for _ in ()).throw(RuntimeError("baseline missing"))}
            )
            with self.assertRaisesRegex(RuntimeError, "baseline missing"):
                runner.cleanup_runtime(root, env=env, effectors=adapter, armed=True)
            state = runner.load_private_state(root, env=env)
            self.assertTrue(state["secret_retired"])
            self.assertEqual(state["runtime_counters"]["secret_retirement"], 1)
            self.assertFalse(runner.environment_path(root).exists())
            self.assertFalse(runner.provider_payload_path(root).exists())

    def test_wheel_must_bind_the_validated_candidate_not_mutable_head(self) -> None:
        with private_packet() as (root, receipt, env):
            runner.prepare_local(root, receipt, env=env, armed=True)
            calls: list[str] = []
            with self.assertRaisesRegex(RuntimeError, "wheel archive"):
                runner.prepare_runtime(root, env=env, effectors=effectors(calls, bad_wheel=True),
                                       secret_factory=lambda: "s" * 32, armed=True)
            state = runner.load_private_state(root, env=env)
            self.assertEqual(state["candidate"]["commit"], "a" * 40)
            self.assertEqual(state["runtime_counters"]["establish"], 1)

    def test_runtime_requires_environment_token_and_fakes_all_effectors(self) -> None:
        with private_packet() as (root, receipt, env):
            with self.assertRaisesRegex(RuntimeError, "execution arm"):
                runner.prepare_local(root, receipt, env=env)
            runner.prepare_local(root, receipt, env=env, armed=True)
            env.pop(runner.TOKEN_REF)
            calls: list[str] = []
            with self.assertRaisesRegex(RuntimeError, "environment"):
                runner.prepare_runtime(root, env=env, effectors=effectors(calls), secret_factory=lambda: "s" * 32, armed=True)
            self.assertEqual(calls, [])

    def test_runner_has_no_direct_provider_network_subprocess_or_service_path(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("import subprocess", "import socket", "import requests", "http.client", "urllib.request"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_counters_are_separate_and_ambiguous_writes_reconcile_without_retry(self) -> None:
        state = runner.new_state(Path("/private/p53-c6-live-github-test"), Path("/receipt.json"))
        state = runner.record_attempt(state, "create")
        uncertain = runner.record_provider_result(state, "create", response=None, ambiguous=True)
        with self.assertRaisesRegex(RuntimeError, "ambiguous"):
            runner.record_attempt(uncertain, "create")
        reconciled = runner.reconcile_ambiguous_write(uncertain, "create", (hook_response(),))
        self.assertEqual(reconciled["counters"], {
            "create": 1, "trigger": 0, "delete": 0, "redelivery": 0, "dispatch": 0,
        })
        state = runner.record_attempt(reconciled, "trigger")
        state = runner.record_attempt(state, "delete")
        self.assertEqual(state["counters"], {
            "create": 1, "trigger": 1, "delete": 1, "redelivery": 0, "dispatch": 0,
        })
        for forbidden in ("redelivery", "dispatch"):
            with self.subTest(action=forbidden), self.assertRaisesRegex(RuntimeError, "forbidden"):
                runner.record_attempt(state, forbidden)
        delete_ambiguous = runner.record_provider_result(state, "delete", response=None, ambiguous=True)
        deleted = runner.reconcile_ambiguous_write(
            delete_ambiguous, "delete", ({"hook_id": 456, "absent": True},),
        )
        self.assertTrue(deleted["delete_readback_absent"])
        self.assertEqual(deleted["counters"]["delete"], 1)

    def test_delivery_and_poll_convergence_require_one_exact_post_anchor_occurrence(self) -> None:
        state = runner.new_state(Path("/private/p53-c6-live-github-test"), Path("/receipt.json"))
        state = runner.record_attempt(state, "create")
        state = runner.record_provider_result(state, "create", response=hook_response())
        state = runner.record_attempt(state, "trigger")
        state = runner.freeze_trigger(state, {
            "pr_number": 88, "head_sha": "d" * 40, "base_ref": runner.REF,
            "docs_only": True, "green": True, "merge_method": "squash",
        })
        state = runner.record_trigger_result(state, merge_sha="e" * 40)
        deliveries = (
            {"delivery_id": "ping", "event": "ping", "action": "created", "status_code": 200},
            {"delivery_id": "qualified", "event": "workflow_run", "action": "completed",
             "authenticated": True, "status_code": 200, "repository": runner.REPOSITORY,
             "repository_id": runner.REPOSITORY_ID, "workflow_id": runner.WORKFLOW_ID,
             "ref": runner.REF, "conclusion": runner.CONCLUSION, "head_sha": "e" * 40, "hook_id": 456,
             "terminal_after_anchor": True,
             "run": {"status": "completed", "event": "push", "run_id": 701, "run_attempt": 2}},
        )
        delivery = runner.validate_delivery_window(deliveries, trigger=state["trigger"])
        self.assertEqual(
            delivery["occurrence"],
            "github:repository:1242753508:run:701:attempt:2",
        )
        state = runner.record_convergence(state, delivery, journal_before=0, journal_after_webhook=1,
                                          journal_after_poll=1, wake_before="pending",
                                          wake_after="firing_local", dispatch_calls=0)
        self.assertEqual(state["runtime_counters"]["observation"], 1)
        self.assertEqual(state["delivery"]["head_sha"], "e" * 40)
        with self.assertRaisesRegex(RuntimeError, "exactly one"):
            runner.validate_delivery_window(deliveries + (deliveries[1] | {"delivery_id": "second"},),
                                            trigger=state["trigger"])

    def test_cleanup_interlock_requires_runtime_secret_hook_and_fresh_census(self) -> None:
        with private_packet() as (root, receipt, env):
            runner.prepare_local(root, receipt, env=env, armed=True)
            calls: list[str] = []
            runner.prepare_runtime(root, env=env, effectors=effectors(calls), secret_factory=lambda: "s" * 32, armed=True)
            state = runner.load_private_state(root, env=env)
            state = runner.record_attempt(state, "create")
            state = runner.record_provider_result(state, "create", response=hook_response())
            state = runner.record_attempt(state, "delete")
            state = runner.record_provider_result(state, "delete", response={"hook_id": 456, "absent": True})
            runner.write_private_state(root, state, env=env)
            with self.assertRaisesRegex(RuntimeError, "census"):
                runner.cleanup_runtime(root, env=env, effectors=effectors(calls, bad_census=True), armed=True)
            self.assertTrue(root.exists())

        with private_packet() as (root, receipt, env):
            runner.prepare_local(root, receipt, env=env, armed=True)
            calls: list[str] = []
            runner.prepare_runtime(root, env=env, effectors=effectors(calls), secret_factory=lambda: "s" * 32, armed=True)
            with self.assertRaisesRegex(RuntimeError, "systemctl query"):
                runner.cleanup_runtime(root, env=env, effectors=effectors(calls, bad_query=True), armed=True)
            self.assertTrue(root.exists())

        with private_packet() as (root, receipt, env):
            runner.prepare_local(root, receipt, env=env, armed=True)
            calls: list[str] = []
            runner.prepare_runtime(root, env=env, effectors=effectors(calls), secret_factory=lambda: "s" * 32, armed=True)
            state = runner.load_private_state(root, env=env)
            state = runner.record_attempt(state, "create")
            state = runner.record_provider_result(state, "create", response=hook_response())
            state = runner.record_attempt(state, "delete")
            state = runner.record_provider_result(state, "delete", response={"hook_id": 456, "absent": True})
            runner.write_private_state(root, state, env=env)
            runner.cleanup_runtime(root, env=env, effectors=effectors(calls), armed=True)
            self.assertFalse(runner.environment_path(root).exists())
            self.assertFalse(runner.provider_payload_path(root).exists())
            result = runner.cleanup_local(root, env=env, armed=True)
            self.assertTrue(result["safe"])
            self.assertTrue(result["root_removed"])
            self.assertFalse(root.exists())
            self.assertIn("uninstall", calls)
            self.assertIn("census", calls)

    def test_cli_defaults_to_read_only_preflight_and_effects_require_arm_and_root(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(runner.main([]), 0)
            self.assertEqual(runner.main(["prepare"]), 2)
        self.assertIn("--execute", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
