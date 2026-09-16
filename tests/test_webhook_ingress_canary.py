from __future__ import annotations

import importlib.util
import io
import json
import os
import runpy
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/webhook_ingress_canary.py"
SPEC = importlib.util.spec_from_file_location("webhook_ingress_canary", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
canary = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = canary
SPEC.loader.exec_module(canary)


def private_state(root: Path, receipt: Path, *, phase: str = "prepared",
                  attempts: int = 0) -> dict:
    fixture = canary.installed.make_fixture()
    created = datetime.now(UTC)
    return {
        "source": canary.SOURCE,
        "root": str(root.resolve()),
        "receipt": str(receipt.resolve()),
        "phase": phase,
        "service_attempts": attempts,
        "failed_units_before": ["preexisting.service"],
        "tracked_identities": [],
        "wake_id": "wake_c5",
        "successful_checkpoints": [],
        "fixture_created_at": created.isoformat(),
        "fixture_deadline": (created + timedelta(minutes=15)).isoformat(),
        "fixture": {
            "secret": fixture.secret,
            "body_b64": canary.base64.b64encode(fixture.body).decode("ascii"),
            "delivery_id": fixture.delivery_id,
            "restart_delivery_id": fixture.restart_delivery_id,
            "workflow": fixture.workflow,
        },
        "security_header_fingerprint": canary.security_header_fingerprint(fixture),
    }


def test_receipt(root: Path) -> dict:
    value = canary.base_receipt(canary.context_for(root))
    value["wake_id"] = "wake_c5"
    return value


class WebhookIngressCanaryTests(unittest.TestCase):
    def test_every_phase_refuses_without_explicit_execute(self) -> None:
        cases = (
            ["prepare", "--receipt", "/tmp/c5.json"],
            ["start", "--root", "/tmp/c5"],
            ["probe", "--root", "/tmp/c5", "--checkpoint", "raw", "--url", "http://127.0.0.1:8820"],
            ["cleanup", "--root", "/tmp/c5"],
        )
        for argv in cases:
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(canary.main(argv), 2)
                self.assertIn("refuses", stderr.getvalue())

    def test_c5_contract_is_distinct_and_restores_shared_primitives(self) -> None:
        before = (
            canary.installed.SOURCE, canary.installed.UNIT,
            canary.installed.HOST, canary.installed.PORT,
        )
        with canary.c5_contract():
            self.assertEqual(canary.installed.SOURCE, "p53-c5-ingress-canary")
            self.assertEqual(canary.installed.UNIT, canary.UNIT)
            self.assertEqual((canary.installed.HOST, canary.installed.PORT), ("127.0.0.1", 8820))
        self.assertEqual(
            (canary.installed.SOURCE, canary.installed.UNIT,
             canary.installed.HOST, canary.installed.PORT),
            before,
        )

    def test_private_state_requires_exact_identity_owner_and_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt = Path(tmp) / "receipt.json"
            value = private_state(root, receipt)
            canary.write_private(root, value)
            self.assertEqual(canary.load_private(root)["phase"], "prepared")
            os.chmod(canary.state_path(root), 0o644)
            with self.assertRaisesRegex(RuntimeError, "ownership or mode"):
                canary.load_private(root)

    def test_start_consumes_attempt_before_install_and_preserves_uncertain_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path)
            for name in (
                "fixture", "fixture_created_at", "fixture_deadline",
                "security_header_fingerprint",
            ):
                state.pop(name)
            canary.write_private(root, state)
            receipt = test_receipt(root)
            receipt["phase"] = "prepared"
            canary.stage(state, receipt)

            observed = {}

            def fail_install(*args, **kwargs):
                observed.update(canary.load_private(root))
                raise RuntimeError("install uncertain")

            with patch.object(canary.installed, "port_is_free", return_value=True), patch.object(
                canary, "initialize_counters",
            ), patch.object(
                canary.installed, "write_fixture_bootstrap",
            ), patch.object(
                canary.installed, "fixture_preflight",
            ), patch.object(
                canary.installed, "write_service_environment",
            ), patch.object(
                canary.installed, "service_command", side_effect=fail_install,
            ):
                self.assertEqual(canary.start(root), 1)

            self.assertEqual(observed["phase"], "service_installing")
            self.assertEqual(observed["service_attempts"], 1)
            self.assertIn("fixture", observed)
            self.assertEqual(
                datetime.fromisoformat(observed["fixture_deadline"])
                - datetime.fromisoformat(observed["fixture_created_at"]),
                timedelta(minutes=15),
            )
            final_state = canary.load_private(root)
            self.assertEqual(final_state["phase"], "service_uncertain")
            self.assertTrue(root.exists())
            external = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(external["service_attempts"], 1)
            self.assertEqual(external["recovery_root"], str(root.resolve()))

    def test_probe_records_only_sanitized_bounded_observations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path, phase="running", attempts=1)
            canary.write_private(root, state)
            receipt = test_receipt(root)
            receipt.update({"phase": "running", "service_attempts": 1})
            canary.stage(state, receipt)
            replies = iter((
                {"status": 200, "code": "COMMITTED", "leak_free": True},
                {"status": 401, "code": "SIGNATURE_INVALID", "leak_free": True},
                {"status": 404, "code": "ROUTE", "leak_free": True},
                {"status": 405, "code": "METHOD", "leak_free": True},
            ))
            with patch.object(canary, "exchange", side_effect=lambda *a, **k: next(replies)), patch.object(
                canary, "snapshot", return_value={
                    "receipts": 1, "matches": 0, "pending": 1,
                    "firing": 0, "submitted": 0, "failed": 0,
                },
            ), patch.object(canary, "read_counters", return_value={
                "authoritative_attempt_reads": 1,
                "production_provider_factory_calls": 0, "dispatch_calls": 0,
            }), redirect_stderr(io.StringIO()):
                self.assertEqual(
                    canary.probe(root, "raw", "http://127.0.0.1:8820", None), 0,
                )
            external = json.loads(receipt_path.read_text(encoding="utf-8"))
            checkpoint = external["checkpoints"]["raw"]
            self.assertTrue(checkpoint["accepted"])
            self.assertEqual(checkpoint["dispatch"], "absent")
            self.assertEqual(len(checkpoint["request_sha256"]), 64)
            self.assertNotIn(state["fixture"]["secret"], receipt_path.read_text(encoding="utf-8"))
            with self.assertRaisesRegex(RuntimeError, "already consumed"):
                canary.probe(root, "raw", "http://127.0.0.1:8820", None)

    def test_probe_is_ordered_and_a_failed_network_attempt_is_not_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path, phase="running", attempts=1)
            canary.write_private(root, state)
            receipt = test_receipt(root)
            receipt.update({"phase": "running", "service_attempts": 1})
            canary.stage(state, receipt)
            with self.assertRaisesRegex(RuntimeError, "order"):
                canary.probe(root, "public", *canary.ENDPOINTS["public"])
            with patch.object(canary, "exchange", side_effect=OSError("offline")):
                self.assertEqual(
                    canary.probe(root, "raw", "http://127.0.0.1:8820", None), 1,
                )
            failed = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(failed["checkpoints"]["raw"]["stage"], "failed")
            self.assertEqual(failed["checkpoints"]["raw"]["error"], "OSError")
            with self.assertRaisesRegex(RuntimeError, "not running"):
                canary.probe(root, "raw", "http://127.0.0.1:8820", None)

    def test_cleanup_uses_product_uninstall_and_keeps_evidence_on_uncertainty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path, phase="running", attempts=1)
            canary.write_private(root, state)
            receipt = test_receipt(root)
            receipt.update({"phase": "running", "service_attempts": 1})
            canary.stage(state, receipt)
            uncertain = {"safe": False, "recovery_root": str(root)}
            with patch.object(canary.installed, "cleanup", return_value=uncertain) as cleanup:
                self.assertEqual(canary.cleanup(root), 1)
            self.assertTrue(root.exists())
            self.assertTrue(cleanup.call_args.kwargs["service_attempted"])
            self.assertTrue(cleanup.call_args.kwargs["preserve_root_on_safe"])
            external = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(external["phase"], "cleanup_uncertain")
            self.assertEqual(external["cleanup"]["recovery_root"], str(root))

    def test_cleanup_succeeds_only_after_all_acceptance_and_safe_teardown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path, phase="running", attempts=1)
            state["successful_checkpoints"] = list(canary.CHECKPOINTS)
            canary.write_private(root, state)
            receipt = test_receipt(root)
            receipt.update({
                "phase": "public_checked", "service_attempts": 1,
                "checkpoints": {
                    name: {"accepted": True} for name in canary.CHECKPOINTS
                },
            })
            canary.stage(state, receipt)
            safe = {"safe": True, "temporary_roots_removed": True}
            with patch.object(canary.installed, "cleanup", return_value=safe) as cleanup:
                self.assertEqual(canary.cleanup(root), 0)
            self.assertFalse(cleanup.call_args.kwargs["preserve_root_on_safe"])
            external = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(external["overall"], "accepted")

    def test_probe_url_is_origin_only(self) -> None:
        fixture = canary.installed.make_fixture()
        for url in ("ftp://example.test", "http://example.test/path", "relative"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                canary.exchange(
                    url, fixture, "delivery", signed=False,
                    deadline=datetime.now(UTC) + timedelta(minutes=1),
                )

    def test_checkpoint_endpoint_contract_rejects_mismatch_before_socket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path, phase="running", attempts=1)
            canary.write_private(root, state)
            receipt = test_receipt(root)
            receipt.update({"phase": "running", "service_attempts": 1})
            canary.stage(state, receipt)
            with patch.object(canary, "exchange", side_effect=AssertionError("socket")):
                with self.assertRaisesRegex(RuntimeError, "endpoint"):
                    canary.probe(root, "raw", "http://localhost:8820", None)
                with self.assertRaisesRegex(RuntimeError, "endpoint"):
                    canary.probe(
                        root, "cooper_host", "http://192.168.50.108", None,
                    )

    def test_full_success_progression_freezes_identity_and_counters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path, phase="running", attempts=1)
            canary.write_private(root, state)
            receipt = test_receipt(root)
            receipt.update({"phase": "running", "service_attempts": 1})
            canary.stage(state, receipt)
            signed_ids = []
            counter = {"value": 0}

            def exchange(url, fixture, delivery_id, **kwargs):
                if kwargs.get("signed", True) and kwargs.get("method", "POST") == "POST" and kwargs.get("path", "/github/webhook") == "/github/webhook":
                    signed_ids.append(delivery_id)
                    counter["value"] += 1
                    return {"status": 200, "code": "COMMITTED" if counter["value"] == 1 else "DUPLICATE", "leak_free": True}
                if kwargs.get("signed", True) is False:
                    return {"status": 401, "code": "SIGNATURE_INVALID", "leak_free": True}
                if kwargs.get("method") == "GET":
                    return {"status": 405, "code": "METHOD", "leak_free": True} if url == canary.ENDPOINTS["raw"][0] else {"status": 404, "code": None, "leak_free": True}
                return {"status": 404, "code": "ROUTE" if url == canary.ENDPOINTS["raw"][0] else None, "leak_free": True}

            journal = {
                "receipts": 1, "matches": 0, "pending": 1,
                "firing": 0, "submitted": 0, "failed": 0,
            }
            with patch.object(canary, "exchange", side_effect=exchange), patch.object(
                canary, "snapshot", return_value=journal,
            ), patch.object(
                canary, "read_counters", side_effect=lambda context: {
                    "authoritative_attempt_reads": counter["value"],
                    "production_provider_factory_calls": 0, "dispatch_calls": 0,
                },
            ):
                for checkpoint in canary.CHECKPOINTS:
                    url, host = canary.ENDPOINTS[checkpoint]
                    self.assertEqual(canary.probe(root, checkpoint, url, host), 0)
            final_state = canary.load_private(root)
            self.assertEqual(tuple(final_state["successful_checkpoints"]), canary.CHECKPOINTS)
            self.assertEqual(signed_ids, [state["fixture"]["delivery_id"]] * 4)
            external = json.loads(receipt_path.read_text(encoding="utf-8"))
            fingerprints = {
                value["security_header_fingerprint"]
                for value in external["checkpoints"].values()
            }
            self.assertEqual(len(fingerprints), 1)

    def test_prior_failed_receipt_locks_out_later_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path, phase="running", attempts=1)
            state["successful_checkpoints"] = ["raw"]
            canary.write_private(root, state)
            receipt = test_receipt(root)
            receipt.update({
                "phase": "raw_checked", "overall": "failed",
                "checkpoints": {"raw": {"accepted": True}},
            })
            canary.stage(state, receipt)
            with patch.object(canary, "exchange", side_effect=AssertionError("socket")):
                with self.assertRaisesRegex(RuntimeError, "order"):
                    canary.probe(root, "local", *canary.ENDPOINTS["local"])

    def test_canonical_candidate_requires_clean_head_at_fetched_origin_main(self) -> None:
        accepted = "a" * 40
        response = subprocess.CompletedProcess([], 0, accepted + "\n", "")
        with patch.object(canary.installed, "clean_candidate", return_value={
            "commit": accepted, "tree": "b" * 40,
        }), patch.object(canary.installed, "run_command", return_value=response) as run:
            value = canary.canonical_candidate(Path("/repo"), Path("/evidence"))
        self.assertEqual(value["canonical_ref"], "refs/remotes/origin/main")
        self.assertEqual(value["canonical_sha"], accepted)
        self.assertIn("refs/remotes/origin/main", run.call_args.args[0])
        mismatch = subprocess.CompletedProcess([], 0, "c" * 40 + "\n", "")
        with patch.object(canary.installed, "clean_candidate", return_value={
            "commit": accepted, "tree": "b" * 40,
        }), patch.object(canary.installed, "run_command", return_value=mismatch):
            with self.assertRaisesRegex(RuntimeError, "origin/main"):
                canary.canonical_candidate(Path("/repo"), Path("/evidence"))

    def test_receipt_identity_binds_root_unit_loopback_and_wake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path)
            canary.write_private(root, state)
            for name, bad in (
                ("schema_version", 99), ("source", "other"),
                ("root", "/wrong"), ("unit", "wrong.service"),
                ("loopback", "0.0.0.0:8820"), ("wake_id", "wake_wrong"),
            ):
                receipt = test_receipt(root)
                receipt[name] = bad
                canary.stage(state, receipt)
                with self.subTest(name=name), self.assertRaisesRegex(
                    RuntimeError, "identity",
                ):
                    canary.read_receipt(state)

    def test_cooper_checkpoint_requires_ten_minute_publication_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            receipt_path = Path(tmp) / "receipt.json"
            state = private_state(root, receipt_path, phase="running", attempts=1)
            state["successful_checkpoints"] = ["raw", "local"]
            canary.write_private(root, state)
            receipt = test_receipt(root)
            receipt.update({
                "phase": "local_checked", "checkpoints": {
                    "raw": {"accepted": True}, "local": {"accepted": True},
                },
            })
            canary.stage(state, receipt)
            deadline = datetime.fromisoformat(state["fixture_deadline"])
            with patch.object(
                canary, "utc_now", return_value=deadline - timedelta(seconds=599),
            ), patch.object(canary, "exchange", side_effect=AssertionError("socket")):
                with self.assertRaisesRegex(RuntimeError, "window"):
                    canary.probe(
                        root, "cooper_host", *canary.ENDPOINTS["cooper_host"],
                    )

    def test_counted_bootstrap_updates_owner_only_authoritative_read_counter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            context = canary.context_for(root)
            context.fixture_dir.mkdir()
            canary.initialize_counters(context)
            fixture = canary.installed.make_fixture()
            canary.installed.write_fixture_bootstrap(
                context, fixture, counter_path=canary.counter_path(context),
            )
            namespace = runpy.run_path(
                str(context.fixture_dir / "webhook_fixture_bootstrap.py"),
            )
            namespace["_count_fixture_read"]()
            counters = canary.read_counters(context)
            self.assertEqual(counters["authoritative_attempt_reads"], 1)
            self.assertEqual(counters["production_provider_factory_calls"], 0)
            self.assertEqual(counters["dispatch_calls"], 0)
            self.assertEqual(canary.counter_path(context).stat().st_mode & 0o777, 0o600)

    def test_counted_bootstrap_blocks_and_counts_production_provider_factory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            context = canary.context_for(root)
            context.fixture_dir.mkdir()
            canary.initialize_counters(context)
            fixture = canary.installed.make_fixture()
            canary.installed.write_fixture_bootstrap(
                context, fixture, counter_path=canary.counter_path(context),
            )
            namespace = runpy.run_path(
                str(context.fixture_dir / "webhook_fixture_bootstrap.py"),
            )
            with self.assertRaisesRegex(RuntimeError, "production provider factory"):
                namespace["_blocked_production_provider_factory"]()
            counters = canary.read_counters(context)
            self.assertEqual(counters["production_provider_factory_calls"], 1)
            self.assertEqual(counters["authoritative_attempt_reads"], 0)
            self.assertEqual(counters["dispatch_calls"], 0)
            self.assertEqual(canary.counter_path(context).stat().st_mode & 0o777, 0o600)

    def test_snapshot_reads_the_canonical_journal_and_rejects_dispatch_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "p53-c5-ingress-fixture"
            root.mkdir(mode=0o700)
            context = canary.context_for(root)
            context.wake_root.mkdir()
            database = context.wake_root / "signals" / "journal.sqlite3"
            database.parent.mkdir()
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE receipts (source TEXT, source_instance TEXT)")
                connection.execute("CREATE TABLE match_reservations (wake_id TEXT)")
                connection.execute(
                    "INSERT INTO receipts VALUES ('github', ?)", (canary.SOURCE,),
                )
            state = {"wake_id": "wake_c5"}
            context.installed_python.parent.mkdir(parents=True)
            context.installed_python.symlink_to(Path(sys.executable).resolve())
            value = canary.snapshot(context, state)
            self.assertEqual(value["receipts"], 1)
            self.assertEqual(value["pending"], 0)
            submitted = context.wake_root / "submitted" / "wake_c5.json"
            submitted.parent.mkdir()
            submitted.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "dispatch terminal"):
                canary.snapshot(context, state)


if __name__ == "__main__":
    unittest.main()
