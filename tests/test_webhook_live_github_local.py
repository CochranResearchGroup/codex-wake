from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
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
    @staticmethod
    def _write_wheel(path: Path, *, include_hook: bool = True) -> None:
        scripts = {
            "codex-wake": "codex_wake.cli:main",
            "codex-waked": "codex_wake.daemon:main",
            "codex-wake-github-webhook": "codex_wake.webhook_listener:main",
        }
        if include_hook:
            scripts["codex-wake-hook"] = "codex_wake.hook:main"
        modules = {entry.split(":", 1)[0] for entry in scripts.values()}
        with zipfile.ZipFile(path, "w") as wheel:
            wheel.writestr("codex_wake/__init__.py", "")
            for module in modules:
                wheel.writestr(module.replace(".", "/") + ".py", "def main(): return 0\n")
            wheel.writestr("codex_wake-0.5.2.dist-info/METADATA", "Metadata-Version: 2.1\nName: codex-wake\nVersion: 0.5.2\n")
            wheel.writestr("codex_wake-0.5.2.dist-info/WHEEL", "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
            wheel.writestr("codex_wake-0.5.2.dist-info/entry_points.txt", "[console_scripts]\n" + "".join(
                f"{name} = {target}\n" for name, target in scripts.items()
            ))
            wheel.writestr("codex_wake-0.5.2.dist-info/RECORD", "")

    def test_install_wheel_ignores_pythonpath_egg_info_and_proves_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, repo = base / "root", base / "repo"
            root.mkdir(); repo.mkdir()
            adapter = local.ProductionLocalAdapter(root, repo_root=repo, env={})
            adapter.create_venv(root)
            adapter.context.wheel_dir.mkdir()
            wheel = adapter.context.wheel_dir / "codex_wake-0.5.2-py3-none-any.whl"
            self._write_wheel(wheel)
            contaminated = base / "contaminated"
            egg_info = contaminated / "codex_wake.egg-info"
            egg_info.mkdir(parents=True)
            (egg_info / "PKG-INFO").write_text(
                "Metadata-Version: 2.1\nName: codex-wake\nVersion: 0.5.2\n", encoding="utf-8",
            )
            adapter.env.update({"PYTHONPATH": str(contaminated), "PYTHONHOME": sys.base_prefix})

            installed = adapter.install_wheel(root, {"wheel_path": str(wheel)})

            self.assertEqual(installed["global_install_mutations"], 0)
            self.assertEqual(adapter.env["PYTHONPATH"], str(contaminated))
            self.assertEqual(adapter.env["PYTHONHOME"], sys.base_prefix)
            self.assertTrue((adapter.context.venv / "bin/codex-wake-hook").is_file())

    def test_install_wheel_rejects_distribution_missing_a_console_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, repo = base / "root", base / "repo"
            root.mkdir(); repo.mkdir()
            adapter = local.ProductionLocalAdapter(root, repo_root=repo, env={})
            adapter.create_venv(root)
            adapter.context.wheel_dir.mkdir()
            wheel = adapter.context.wheel_dir / "codex_wake-0.5.2-py3-none-any.whl"
            self._write_wheel(wheel, include_hook=False)

            with self.assertRaisesRegex(RuntimeError, "console scripts"):
                adapter.install_wheel(root, {"wheel_path": str(wheel)})

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
            adapter.queue((4, "inactive\n"), (4, "not-found\n"), (0, "0\n"), (0, ""))
            with patch.object(adapter, "_matching_processes", return_value=0), \
                    patch.object(adapter, "_port_free", return_value=True):
                value = adapter.runtime_census(root, {})
            self.assertEqual(value, {
                "unit_absent": True, "active": "inactive", "enabled": "disabled",
                "pid": 0, "matching_processes": 0, "port_8820_released": True,
                "unit_query": {"ok": True, "returncode": 0,
                               "observed_returncodes": {"active": 4, "enabled": 4, "pid": 0}},
                "failed_units_query": {"ok": True, "returncode": 0, "units": []},
            })

    def test_runtime_census_rejects_empty_or_bus_failed_systemctl_queries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, repo = base / "root", base / "repo"
            root.mkdir(); repo.mkdir()
            adapter = FakeAdapter(root, repo, {})
            adapter.queue((3, "inactive\n"), (1, ""))
            with self.assertRaisesRegex(RuntimeError, "enabled-state"):
                adapter.runtime_census(root, {})
            adapter = FakeAdapter(root, repo, {})
            adapter.queue((4, "active\n"))
            with self.assertRaisesRegex(RuntimeError, "active-state"):
                adapter.runtime_census(root, {})
            adapter = FakeAdapter(root, repo, {})
            adapter.queue((4, "inactive\n"), (4, "disabled\n"))
            with self.assertRaisesRegex(RuntimeError, "enabled-state"):
                adapter.runtime_census(root, {})
            adapter = FakeAdapter(root, repo, {})
            adapter.queue((3, "inactive\n"), (1, "not-found\n"), (0, "0\n"), (1, "failed to connect to bus"))
            with self.assertRaisesRegex(RuntimeError, "failed-units"):
                adapter.runtime_census(root, {})

    def test_archive_binding_and_argv_use_exact_candidate_not_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, repo = base / "root", base / "repo"
            root.mkdir(); repo.mkdir()
            adapter = FakeAdapter(root, repo, {})
            candidate = {"canonical_ref": "refs/remotes/origin/main", "commit": "a" * 40, "tree": "b" * 40}
            adapter.queue((0, "a" * 40 + "\n"), (0, "a" * 40 + "\n"), (0, "b" * 40 + "\n"))
            binding = adapter._archive_binding(candidate)
            self.assertEqual(binding, {
                "archive_ref": "refs/remotes/origin/main", "archive_commit": "a" * 40,
                "archive_tree": "b" * 40, "build_commit": "a" * 40,
            })
            adapter._archive_candidate(binding)
            self.assertEqual(adapter.commands[-1][-1], "a" * 40)
            self.assertNotEqual(adapter.commands[-1][-1], "HEAD")
            adapter = FakeAdapter(root, repo, {})
            adapter.queue((0, "c" * 40 + "\n"), (0, "a" * 40 + "\n"), (0, "b" * 40 + "\n"))
            with self.assertRaisesRegex(RuntimeError, "no longer bound"):
                adapter._archive_binding(candidate)

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
