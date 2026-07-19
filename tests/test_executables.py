from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from codex_wake.executables import resolve_stable_executable
from codex_wake.records import WakeError


class StableExecutableTests(unittest.TestCase):
    def make_executable(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_rejects_structural_version_manager_layouts_at_custom_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            managed = [
                base / "custom-nvm" / "versions" / "node" / "v24.1.0" / "bin" / "codex",
                base / "xdg" / "fnm" / "node-versions" / "v24.1.0" / "installation" / "bin" / "codex",
                base / "runtime" / "fnm_multishells" / "123" / "bin" / "codex",
                base / "asdf-data" / "installs" / "nodejs" / "24.1.0" / "bin" / "codex",
                base / "asdf-data" / "installs" / "nodejs" / "ref-main" / "bin" / "codex",
                base / "volta-home" / "tools" / "image" / "node" / "24.1.0" / "bin" / "codex",
                base / "mise-data" / "installs" / "node" / "24.1.0" / "bin" / "codex",
                base / "codex" / "packages" / "standalone" / "releases" / "0.144.5-x86_64" / "bin" / "codex",
            ]
            for executable in managed:
                self.make_executable(executable)
                with self.subTest(executable=executable):
                    with self.assertRaisesRegex(WakeError, "stable wrapper or symlink"):
                        resolve_stable_executable(
                            str(executable),
                            default_command="codex",
                            label="Codex CLI",
                            reject_node_versioned=True,
                        )

    def test_path_resolution_skips_managed_layouts_and_keeps_stable_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            managed_dirs = [
                base / "custom-nvm" / "versions" / "node" / "v24.1.0" / "bin",
                base / "xdg" / "fnm" / "node-versions" / "v24.1.0" / "installation" / "bin",
                base / "runtime" / "fnm_multishells" / "123" / "bin",
                base / "asdf-data" / "installs" / "nodejs" / "24.1.0" / "bin",
                base / "volta-home" / "tools" / "image" / "node" / "24.1.0" / "bin",
                base / "mise-data" / "installs" / "node" / "24.1.0" / "bin",
            ]
            for directory in managed_dirs:
                self.make_executable(directory / "openclaw")
            stable_target = self.make_executable(base / "packages" / "openclaw")
            stable = base / "bin" / "openclaw"
            stable.parent.mkdir()
            stable.symlink_to(stable_target)

            resolved = resolve_stable_executable(
                None,
                default_command="openclaw",
                label="OpenClaw CLI",
                path=os.pathsep.join(str(directory) for directory in [*managed_dirs, stable.parent]),
                reject_node_versioned=True,
            )

            self.assertEqual(resolved, str(stable))

    def test_accepts_regular_stable_custom_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stable = self.make_executable(
                Path(tmp) / "custom" / "installs" / "node" / "current" / "bin" / "codex"
            )

            self.assertEqual(
                resolve_stable_executable(
                    str(stable),
                    default_command="codex",
                    label="Codex CLI",
                    reject_node_versioned=True,
                ),
                str(stable),
            )


if __name__ == "__main__":
    unittest.main()
