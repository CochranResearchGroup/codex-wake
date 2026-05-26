from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.openclaw_plugin import (
    PROVENANCE_FILE,
    install_openclaw_plugin,
    materialize_plugin_from_git,
    pack_openclaw_plugin,
    prune_openclaw_linked_plugin_path,
    safe_ref_slug,
    validate_plugin_source_dir,
)
from codex_wake.records import WakeError


def write_plugin_fixture(path: Path, *, plugin_id: str = "codex-wake", version: str = "0.1.1") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "openclaw.plugin.json").write_text(
        json.dumps({"id": plugin_id, "version": version}),
        encoding="utf-8",
    )
    (path / "package.json").write_text(
        json.dumps(
            {
                "name": "@cochranresearchgroup/openclaw-codex-wake",
                "version": version,
                "type": "module",
                "main": "./index.js",
            }
        ),
        encoding="utf-8",
    )
    (path / "index.js").write_text("export function register() {}\n", encoding="utf-8")


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path | None]] = []

    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((args, cwd))
        if args[:2] == ["git", "clone"]:
            repo_dir = Path(args[-1])
            write_plugin_fixture(repo_dir / "plugins" / "openclaw-codex-wake")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if len(args) >= 4 and args[:2] == ["git", "-C"] and args[3:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, stdout="abc123\n", stderr="")
        if args[:3] == ["/usr/bin/openclaw", "plugins", "install"]:
            return subprocess.CompletedProcess(args, 0, stdout="Installed codex-wake\n", stderr="")
        if args == ["/usr/bin/openclaw", "plugins", "registry", "--refresh"]:
            return subprocess.CompletedProcess(args, 0, stdout='{"refreshed":true}\n', stderr="")
        if args[:2] == ["npm", "pack"]:
            return subprocess.CompletedProcess(args, 0, stdout="cochranresearchgroup-openclaw-codex-wake-0.1.1.tgz\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")


class OpenClawPluginTests(unittest.TestCase):
    def test_validate_plugin_source_dir_reads_manifest_and_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "plugin"
            write_plugin_fixture(source)

            plugin = validate_plugin_source_dir(source)

            self.assertEqual(plugin.plugin_id, "codex-wake")
            self.assertEqual(plugin.plugin_version, "0.1.1")
            self.assertEqual(plugin.package_name, "@cochranresearchgroup/openclaw-codex-wake")
            self.assertEqual(plugin.package_version, "0.1.1")

    def test_validate_plugin_source_dir_rejects_wrong_plugin_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "plugin"
            write_plugin_fixture(source, plugin_id="other")

            with self.assertRaisesRegex(WakeError, "unexpected OpenClaw plugin id"):
                validate_plugin_source_dir(source)

    def test_install_openclaw_plugin_from_source_runs_openclaw_without_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "plugin"
            write_plugin_fixture(source)
            runner = FakeRunner()

            result = install_openclaw_plugin(
                source_dir=source,
                openclaw_path="/usr/bin/openclaw",
                force=True,
                runner=runner,
            )

            self.assertEqual(result["plugin_id"], "codex-wake")
            self.assertEqual(result["source_kind"], "local-path")
            self.assertEqual(
                runner.calls[-1][0],
                ["/usr/bin/openclaw", "plugins", "install", "--force", str(source.resolve())],
            )
            self.assertNotIn("--link", runner.calls[-1][0])
            self.assertIn("Installed codex-wake", result["stdout"])

    def test_install_openclaw_plugin_dry_run_does_not_run_openclaw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "plugin"
            write_plugin_fixture(source)
            runner = FakeRunner()

            result = install_openclaw_plugin(
                source_dir=source,
                openclaw_path="/usr/bin/openclaw",
                force=True,
                dry_run=True,
                runner=runner,
            )

            self.assertTrue(result["dry_run"])
            self.assertEqual(result["command"], ["/usr/bin/openclaw", "plugins", "install", "--force", str(source.resolve())])
            self.assertEqual(runner.calls, [])

    def test_prune_openclaw_linked_plugin_path_backs_up_config_and_keeps_plugin_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked = root / "repo" / "plugins" / "openclaw-codex-wake"
            other = root / "other-plugin"
            config = root / "openclaw.json"
            linked.mkdir(parents=True)
            other.mkdir()
            config.write_text(
                json.dumps(
                    {
                        "plugins": {
                            "allow": ["codex-wake"],
                            "entries": {"codex-wake": {"enabled": True}},
                            "load": {"paths": [str(linked), str(other)]},
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = prune_openclaw_linked_plugin_path(
                config_path=config,
                linked_source_dir=linked,
                now=datetime(2026, 5, 26, 12, 0, tzinfo=UTC),
            )

            self.assertTrue(result.changed)
            self.assertEqual(result.removed_paths, [str(linked)])
            self.assertTrue(Path(result.backup_path).exists())
            payload = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(payload["plugins"]["load"]["paths"], [str(other)])
            self.assertEqual(payload["plugins"]["entries"], {"codex-wake": {"enabled": True}})
            self.assertIn(str(linked), Path(result.backup_path).read_text(encoding="utf-8"))

    def test_prune_openclaw_linked_plugin_path_can_find_codex_wake_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked = root / "repo" / "plugins" / "openclaw-codex-wake"
            other = root / "other-plugin"
            config = root / "openclaw.json"
            write_plugin_fixture(linked)
            write_plugin_fixture(other, plugin_id="other")
            config.write_text(
                json.dumps({"plugins": {"load": {"paths": [str(linked), str(other)]}}}),
                encoding="utf-8",
            )

            result = prune_openclaw_linked_plugin_path(config_path=config)

            self.assertEqual(result.linked_source_dir, "")
            self.assertEqual(result.removed_paths, [str(linked)])
            payload = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(payload["plugins"]["load"]["paths"], [str(other)])

    def test_prune_openclaw_linked_plugin_path_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            linked = Path(tmp) / "repo" / "plugins" / "openclaw-codex-wake"
            config = Path(tmp) / "openclaw.json"
            linked.mkdir(parents=True)
            original = json.dumps({"plugins": {"load": {"paths": [str(linked)]}}})
            config.write_text(original, encoding="utf-8")

            result = prune_openclaw_linked_plugin_path(config_path=config, linked_source_dir=linked, dry_run=True)

            self.assertTrue(result.changed)
            self.assertEqual(result.backup_path, "")
            self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_install_openclaw_plugin_can_prune_repo_linked_path_after_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "plugin"
            linked = Path(tmp) / "repo" / "plugins" / "openclaw-codex-wake"
            config = Path(tmp) / "openclaw.json"
            write_plugin_fixture(source)
            linked.mkdir(parents=True)
            config.write_text(json.dumps({"plugins": {"load": {"paths": [str(linked)]}}}), encoding="utf-8")
            runner = FakeRunner()

            result = install_openclaw_plugin(
                source_dir=source,
                openclaw_path="/usr/bin/openclaw",
                force=True,
                prune_linked_path=True,
                linked_source_dir=linked,
                openclaw_config=config,
                runner=runner,
            )

            self.assertIn(
                (["/usr/bin/openclaw", "plugins", "install", "--force", str(source.resolve())], None),
                runner.calls,
            )
            self.assertEqual(runner.calls[-1][0], ["/usr/bin/openclaw", "plugins", "registry", "--refresh"])
            self.assertEqual(result["prune_linked_path"]["removed_paths"], [str(linked)])
            self.assertTrue(result["prune_linked_path"]["backup_path"])
            self.assertFalse(result["registry_refresh"]["dry_run"])
            payload = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(payload["plugins"]["load"]["paths"], [])

    def test_materialize_plugin_from_git_copies_subdir_and_writes_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination_root = Path(tmp) / "materialized"
            runner = FakeRunner()

            plugin = materialize_plugin_from_git(
                repo_url="https://github.com/CochranResearchGroup/codex-wake.git",
                ref="v0.4.15",
                destination_root=destination_root,
                runner=runner,
            )

            self.assertEqual(plugin.path, destination_root / "v0.4.15")
            self.assertTrue((plugin.path / "openclaw.plugin.json").exists())
            provenance = json.loads((plugin.path / PROVENANCE_FILE).read_text(encoding="utf-8"))
            self.assertEqual(provenance["source"], "git")
            self.assertEqual(provenance["ref"], "v0.4.15")
            self.assertEqual(provenance["commit"], "abc123")

    def test_pack_openclaw_plugin_returns_npm_pack_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "plugin"
            output = Path(tmp) / "dist"
            write_plugin_fixture(source)
            runner = FakeRunner()

            result = pack_openclaw_plugin(source_dir=source, output_dir=output, runner=runner)

            self.assertEqual(result["plugin_id"], "codex-wake")
            self.assertEqual(
                result["tarball"],
                str(output.resolve() / "cochranresearchgroup-openclaw-codex-wake-0.1.1.tgz"),
            )
            self.assertEqual(runner.calls[-1][0], ["npm", "pack", str(source.resolve()), "--pack-destination", str(output.resolve())])

    def test_safe_ref_slug_keeps_refs_path_safe(self) -> None:
        self.assertEqual(safe_ref_slug("release/v0.5.0 beta"), "release-v0.5.0-beta")


if __name__ == "__main__":
    unittest.main()
