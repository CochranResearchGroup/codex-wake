"""Public runner regressions: failure and candidate drift cannot authorize success."""

import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / "scripts/validate_candidate.py"


class CandidateValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "candidate"
        self.repo.mkdir()
        self.runtime = self.base / "selected-python"
        shutil.copyfile(sys.executable, self.runtime)
        self.runtime.chmod(0o755)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        (self.repo / "source.txt").write_text("original")
        self.git("add", ".")
        self.git("commit", "-qm", "candidate")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), *args], text=True
        ).strip()

    def run_candidate(self, checks, actions=None):
        manifest = self.base / "checks.json"
        manifest.write_text(
            json.dumps(
                dict(
                    checks=checks,
                    on_success=actions
                    if actions is not None
                    else [
                        dict(
                            name="commit",
                            argv=[
                                "git",
                                "commit",
                                "--allow-empty",
                                "-qm",
                                "validated candidate",
                            ],
                        )
                    ],
                )
            )
        )
        receipt = self.base / "receipt.json"
        process = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo",
                str(self.repo),
                "--runtime",
                str(self.runtime),
                "--manifest",
                str(manifest),
                "--receipt",
                str(receipt),
            ],
            capture_output=True,
            text=True,
        )
        self.assertTrue(receipt.exists(), process.stderr)
        return process, json.loads(receipt.read_text())

    def test_required_failure_blocks_later_checks_and_commit(self):
        command = [sys.executable, "-c", "raise SystemExit(23)"]
        process, receipt = self.run_candidate(
            [
                dict(name="host", axis="host", argv=command),
                dict(name="ci", axis="ci", argv=[sys.executable, "-c", "pass"]),
            ]
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(receipt["status"], "FAIL")
        self.assertEqual(receipt["checks"][0]["argv"], command)
        self.assertEqual(receipt["checks"][0]["returncode"], 23)
        self.assertEqual(receipt["checks"][1]["status"], "BLOCKED")
        self.assertEqual(self.git("rev-parse", "HEAD"), receipt["source"]["head"])

    def test_source_and_runtime_changes_invalidate_pass_and_block_success(self):
        for target in (
            "source.txt",
            "untracked.txt",
            str(self.runtime),
            str(self.base / "checks.json"),
        ):
            with self.subTest(target=target):
                # Each run gets a new receipt; the failure history remains intact.
                receipt_path = self.base / "receipt.json"
                if receipt_path.exists():
                    receipt_path.rename(
                        self.base
                        / ("prior-" + str(len(list(self.base.glob("prior-*")))))
                    )
                code = (
                    f"from pathlib import Path; Path({target!r}).write_text('changed')"
                )
                process, receipt = self.run_candidate(
                    [
                        dict(name="unit", argv=[sys.executable, "-c", "pass"]),
                        dict(name="host", argv=[sys.executable, "-c", code]),
                    ]
                )
                self.assertNotEqual(process.returncode, 0)
                self.assertEqual(receipt["checks"][0]["status"], "INVALIDATED")
                self.assertIn("changed during validation", receipt["failure"]["reason"])
                self.assertEqual(
                    self.git("rev-parse", "HEAD"), receipt["source"]["head"]
                )

    def test_dirty_candidate_and_independent_optional_axis_are_explicit(self):
        self.runtime = Path(sys.executable).resolve()
        (self.repo / "source.txt").write_text("reviewed dirty content")
        process, receipt = self.run_candidate(
            [
                dict(
                    name="host",
                    axis="host",
                    required=False,
                    argv=[sys.executable, "-c", "raise SystemExit(7)"],
                ),
                dict(name="ci", axis="ci", argv=["{runtime}", "-c", "pass"]),
            ]
        )
        self.assertEqual(process.returncode, 0, receipt)
        self.assertEqual([r["status"] for r in receipt["checks"]], ["FAIL", "PASS"])
        self.assertTrue(receipt["source"]["dirty"])
        self.assertEqual(len(receipt["source"]["head"]), 40)
        self.assertEqual(receipt["runtime"]["path"], str(self.runtime))
        self.assertEqual(len(receipt["environment"]["sha256"]), 64)
        self.assertNotEqual(self.git("rev-parse", "HEAD"), receipt["source"]["head"])
        self.assertEqual(receipt["actions"][0]["status"], "PASS")
        # An attempted rerun cannot replace the earlier outcomes.
        original = (self.base / "receipt.json").read_bytes()
        subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--repo",
                str(self.repo),
                "--runtime",
                str(self.runtime),
                "--manifest",
                str(self.base / "checks.json"),
                "--receipt",
                str(self.base / "receipt.json"),
            ],
            capture_output=True,
        )
        self.assertEqual((self.base / "receipt.json").read_bytes(), original)

    def test_success_action_cannot_mutate_then_commit_unvalidated_content(self):
        process, receipt = self.run_candidate(
            [dict(name="ci", argv=[sys.executable, "-c", "pass"])],
            actions=[
                dict(
                    name="rewrite",
                    argv=[
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('source.txt').write_text('untested')",
                    ],
                ),
                dict(
                    name="commit",
                    argv=["git", "commit", "--allow-empty", "-qm", "untested commit"],
                ),
            ],
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(receipt["actions"][1]["status"], "BLOCKED")
        self.assertEqual(self.git("rev-parse", "HEAD"), receipt["source"]["head"])

    def test_selected_virtual_environment_invocation_is_preserved(self):
        prefix = self.base / "runtime"
        subprocess.run(
            [sys.executable, "-m", "venv", "--without-pip", str(prefix)],
            check=True,
            capture_output=True,
        )
        self.runtime = prefix / "bin/python"
        process, receipt = self.run_candidate(
            [
                dict(
                    name="runtime",
                    argv=["{runtime}", "-c", "import sys; print(sys.prefix)"],
                )
            ],
            actions=[],
        )
        self.assertEqual(process.returncode, 0, receipt.get("failure"))
        self.assertEqual(receipt["checks"][0]["stdout"].strip(), str(prefix))
        self.assertEqual(receipt["runtime"]["path"], str(self.runtime))
        self.assertIn(str(prefix / "pyvenv.cfg"), receipt["runtime"]["files"])


if __name__ == "__main__":
    unittest.main()
