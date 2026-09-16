from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/webhook_live_github_local.py"
SPEC = importlib.util.spec_from_file_location("webhook_live_github_local", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
local = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = local
SPEC.loader.exec_module(local)


class FakeAdapter(local.ProductionLocalAdapter):
    def __init__(self, root: Path, repo: Path, env: dict[str, str]):
        super().__init__(root, repo_root=repo, env=env)
        self.commands: list[list[str]] = []
        self.outputs: list[tuple[int, str]] = []

    def queue(self, *outputs: tuple[int, str]) -> None:
        self.outputs.extend(outputs)

    def _command(self, argv, *, name, timeout=local.MAX_COMMAND_SECONDS,
                 cwd=None, allow=(0,), binary=False):
        self.commands.append(list(argv))
        returncode, stdout = self.outputs.pop(0) if self.outputs else (0, "")
        if returncode not in allow:
            raise RuntimeError(f"{name} failed with exit code {returncode}")
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")


class LiveGitHubLocalAdapterTests(unittest.TestCase):
    def test_source_configuration_is_exact_disabled_then_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, repo = base / "root", base / "repo"
            root.mkdir(); repo.mkdir()
            adapter = FakeAdapter(root, repo, {"XDG_CONFIG_HOME": str(base / "config")})
            with patch.object(adapter, "_port_free", return_value=True):
                self.assertEqual(adapter.configure_source(root, {}), {
                    "source": local.contract.SOURCE, "enabled": False,
                })
            disabled = adapter.commands[-1]
            self.assertIn("--disabled", disabled)
            self.assertEqual(disabled[disabled.index("--repository-id") + 1], "1242753508")
            self.assertEqual(disabled[disabled.index("--workflow-id") + 1], "279450573")
            self.assertEqual(disabled[disabled.index("--ref") + 1], "refs/heads/main")
            self.assertEqual(disabled[disabled.index("--credential-ref") + 1],
                             local.contract.TOKEN_REF)
            self.assertIn("--enabled", adapter._source_args(True))

    def test_service_install_uses_isolated_listener_and_exact_unit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, repo = base / "root", base / "repo"
            root.mkdir(); repo.mkdir()
            adapter = FakeAdapter(root, repo, {"XDG_CONFIG_HOME": str(base / "config")})
            result = adapter.install_service(root, {})
            self.assertEqual(result, {"unit": local.contract.UNIT})
            command = adapter.commands[-1]
            self.assertEqual(command[command.index("--executable-path") + 1],
                             str(root / "venv/bin/codex-wake-github-webhook"))
            self.assertEqual(command[command.index("--unit-dir") + 1],
                             str(base / "config/systemd/user"))

    def test_candidate_must_equal_origin_main_and_records_unrelated_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, repo = base / "root", base / "repo"
            root.mkdir(); repo.mkdir()
            adapter = FakeAdapter(root, repo, {})
            adapter.queue((0, ""), (0, "a" * 40 + "\n"), (0, "a" * 40 + "\n"),
                          (0, "b" * 40 + "\n"), (0, ""))
            value = adapter.canonical_candidate(root)
            self.assertEqual(value["commit"], "a" * 40)
            baseline = json.loads((root / "evidence/failed-units-before-state.json").read_text())
            self.assertEqual(baseline, [])
            adapter = FakeAdapter(root, repo, {})
            adapter.queue((0, ""), (0, "a" * 40 + "\n"), (0, "c" * 40 + "\n"),
                          (0, "b" * 40 + "\n"))
            with self.assertRaisesRegex(RuntimeError, "origin/main"):
                adapter.canonical_candidate(root)

    def test_runtime_census_normalizes_absent_unit_and_checks_port_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, repo = base / "root", base / "repo"
            root.mkdir(); repo.mkdir()
            adapter = FakeAdapter(root, repo, {})
            adapter.queue((3, "inactive\n"), (1, "not-found\n"), (1, "0\n"))
            with patch.object(adapter, "_matching_processes", return_value=0), \
                    patch.object(adapter, "_port_free", return_value=True):
                value = adapter.runtime_census(root, {})
            self.assertEqual(value, {
                "unit_absent": True, "active": "inactive", "enabled": "disabled",
                "pid": 0, "matching_processes": 0, "port_8820_released": True,
            })

    def test_module_has_no_github_transport_merge_redelivery_or_dispatch_path(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("api.github.com", "gh pr merge", "/deliveries/", "--dispatch"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_journal_snapshot_and_poll_use_exact_source_and_no_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, repo = base / "root", base / "repo"
            root.mkdir(); repo.mkdir()
            wake_root = root / "wake"
            (wake_root / "signals").mkdir(parents=True)
            database = wake_root / "signals/journal.sqlite3"
            with sqlite3.connect(database) as connection:
                connection.executescript("""
                    CREATE TABLE receipts (
                      local_sequence INTEGER, receipt_id TEXT, source TEXT,
                      source_instance TEXT, occurrence_namespace TEXT,
                      occurrence_value TEXT, attributes_json TEXT,
                      verification_state TEXT, verification_method TEXT
                    );
                    CREATE TABLE arms (wake_id TEXT, registered_at TEXT, source_anchor TEXT);
                    CREATE TABLE match_reservations (wake_id TEXT);
                    CREATE TABLE source_state (
                      source TEXT, source_instance TEXT, checkpoint TEXT,
                      checkpoint_order INTEGER, observed_through TEXT
                    );
                    INSERT INTO arms VALUES ('wake_test', '2026-09-16T00:00:00+00:00', 'anchor');
                    INSERT INTO source_state VALUES ('github', 'p53-c6-live-github', NULL, NULL, NULL);
                """)
            (wake_root / "pending").mkdir()
            (wake_root / "pending/wake_test.json").write_text("{}")
            adapter = FakeAdapter(root, repo, {})
            snapshot = adapter.journal_snapshot("wake_test")
            self.assertEqual(snapshot["receipt_count"], 0)
            self.assertEqual(snapshot["statuses"], {
                "pending": 1, "firing": 0, "submitted": 0, "failed": 0,
            })
            adapter.queue((0, "checked=1 dispatched=0\n"))
            evidence = adapter.poll_once_no_dispatch("wake_test")
            self.assertEqual(evidence["dispatch_calls"], 0)
            self.assertIn("--no-dispatch", adapter.commands[-1])


if __name__ == "__main__":
    unittest.main()
