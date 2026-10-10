"""Exercise the policy guard at its CLI boundary on disposable repositories."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PolicyWiringTests(unittest.TestCase):
    def test_current_and_missing_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy(ROOT / "AGENTS.md", root)
            shutil.copytree(ROOT / "docs/dev/policies", root / "docs/dev/policies")
            shutil.copytree(ROOT / ".governance", root / ".governance")
            def run():
                return subprocess.run([sys.executable, str(ROOT / "scripts/check_policy_wiring.py"),
                                       "--repo-root", str(root)], capture_output=True, text=True)
            current = run()
            self.assertEqual(current.returncode, 0, current.stdout + current.stderr)
            with (root / "AGENTS.md").open("a") as stream:
                stream.write("\n- `docs/dev/policies/9999-missing.md`\n")
            broken = run()
            self.assertEqual(broken.returncode, 1)
            self.assertIn("missing policy target: docs/dev/policies/9999-missing.md",
                          json.loads(broken.stdout)["errors"])


if __name__ == "__main__":
    unittest.main()
