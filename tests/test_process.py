from __future__ import annotations

import tempfile
import subprocess
import sys
import json
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
            (boot_dir / "boot_id").write_text("boot-def\n", encoding="utf-8")
            self.assertEqual(process_identity(123, proc_root=proc_root)["boot_id"], "boot-def")

    def test_live_identity_rechecks_each_birth_without_reopening_host_boot_id(self) -> None:
        # A new interpreter gives this filesystem-read budget an independent cache.
        code = """import io,json,os
from pathlib import Path
from unittest.mock import patch
from codex_wake.process import process_identity
counts={'stat':0,'boot_id':0}
original=io.open
def observed(path,*args,**kwargs):
 name=Path(path).name
 if name in counts: counts[name]+=1
 return original(path,*args,**kwargs)
with patch('io.open',side_effect=observed):
 identities=[process_identity(os.getpid()) for _ in range(10)]
assert all(value==identities[0] and value.get('boot_id') for value in identities)
print(json.dumps(counts))
"""
        counts = json.loads(subprocess.check_output([sys.executable, '-c', code], text=True))
        self.assertEqual(counts['stat'], 10)
        self.assertLessEqual(counts['boot_id'], 1)

    def test_process_identity_returns_none_without_proc_stat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(process_identity(123, proc_root=Path(tmp)))


if __name__ == "__main__":
    unittest.main()
