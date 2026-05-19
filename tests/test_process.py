from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from codex_wake.process import boot_id_value, process_identity, process_start_time_ticks


class ProcessIdentityTests(unittest.TestCase):
    def test_process_start_time_ticks_reads_linux_proc_stat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc_root = Path(tmp)
            proc_dir = proc_root / "123"
            proc_dir.mkdir()
            fields = ["S"] + [str(value) for value in range(4, 22)] + ["98765"]
            (proc_dir / "stat").write_text(f"123 (name with spaces) {' '.join(fields)}\n", encoding="utf-8")

            self.assertEqual(process_start_time_ticks(123, proc_root=proc_root), 98765)

    def test_process_identity_includes_boot_id_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc_root = Path(tmp)
            proc_dir = proc_root / "123"
            proc_dir.mkdir()
            fields = ["S"] + [str(value) for value in range(4, 22)] + ["98765"]
            (proc_dir / "stat").write_text(f"123 (cmd) {' '.join(fields)}\n", encoding="utf-8")
            boot_dir = proc_root / "sys" / "kernel" / "random"
            boot_dir.mkdir(parents=True)
            (boot_dir / "boot_id").write_text("boot-abc\n", encoding="utf-8")

            self.assertEqual(boot_id_value(proc_root=proc_root), "boot-abc")
            self.assertEqual(process_identity(123, proc_root=proc_root), {"start_time_ticks": 98765, "boot_id": "boot-abc"})

    def test_process_identity_returns_none_without_proc_stat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(process_identity(123, proc_root=Path(tmp)))


if __name__ == "__main__":
    unittest.main()
