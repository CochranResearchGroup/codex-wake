"""Cleanup commands retain unknown work and apply only exact disposable plans."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import stat
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/cleanup_worktrees.py"


class CleanupWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        (self.repo / "source").write_text("original")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.target = self.root / "target"
        self.git("worktree", "add", "-qb", "worker", str(self.target))
        self.git(
            "update-ref", "refs/custody/test", self.git("rev-parse", "HEAD").strip()
        )
        self.references = self.root / "references.json"
        self.references.write_text(
            json.dumps(
                {
                    "repository": str(self.repo),
                    "entries": [
                        {
                            "path": str(self.target),
                            "owner": "fixture",
                            "reviewed": True,
                            "service_references": [],
                            "build_references": [],
                            "evidence_references": [],
                        }
                    ],
                }
            )
        )
        self.references.chmod(0o600)

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), *args], text=True, stderr=subprocess.DEVNULL
        )

    def command(self, args, census="empty"):
        # Substitute only the OS observation boundary, never cleanup internals.
        program = """import os,sys,runpy,subprocess
from types import SimpleNamespace
original = os.scandir
mode = sys.argv[1]
original_link = os.readlink
original_run = subprocess.run
def readlink(path, *args, **kwargs):
    if mode == 'reference' and str(path).startswith('/proc/999999999/'):
        return os.environ['FIXTURE_TARGET']
    return original_link(path, *args, **kwargs)
def run(command, *args, **kwargs):
    if mode == 'timeout' and command[-3:-1] == ['worktree','remove']:
        raise subprocess.TimeoutExpired(command, 30)
    return original_run(command, *args, **kwargs)
os.readlink = readlink
subprocess.run = run
class Empty:
    def __enter__(self): return iter([SimpleNamespace(name='999999999')] if mode == 'reference' else ())
    def __exit__(self,*args): pass
def scandir(path):
    if str(path) == '/proc':
        if mode == 'denied': raise PermissionError('fixture inaccessible proc')
        return Empty()
    return original(path)
os.scandir = scandir
sys.argv = sys.argv[2:]
runpy.run_path(sys.argv[0],run_name='__main__')
"""
        return subprocess.run(
            [sys.executable, "-c", program, census, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            timeout=15,
            env=dict(os.environ, FIXTURE_TARGET=str(self.target)),
        )

    def plan(self, census="empty"):
        path = self.root / "plan.json"
        result = self.command(
            [
                "plan",
                "--repo",
                str(self.repo),
                "--target",
                str(self.target),
                "--custody",
                "refs/custody/test",
                "--references",
                str(self.references),
                "--output",
                str(path),
            ],
            census,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return path, json.loads(path.read_text())

    def summarize(self, path):
        original = path.read_bytes()
        result = subprocess.run(
            [sys.executable, str(SCRIPT.with_name("summarize_receipt.py")), str(path)],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLessEqual(len(result.stdout), 8192)
        self.assertEqual(path.read_bytes(), original)
        return json.loads(result.stdout)

    def test_denied_census_retains_checkout(self):
        path, plan = self.plan("denied")
        self.assertEqual(plan["entries"][0]["disposition"], "retained_unknown")
        self.assertEqual(plan["entries"][0]["action"], "retain")
        self.assertTrue(self.target.exists())
        summary = self.summarize(path)
        self.assertEqual(summary["status"], "HELD")
        self.assertEqual(summary["unknown_count"], 1)
        self.assertEqual(summary["omitted_count"], 0)

    def test_plan_and_result_are_private_under_permissive_umask(self):
        previous = os.umask(0o022)
        try:
            path, plan = self.plan()
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            result = self.apply(path, plan)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                stat.S_IMODE((self.root / "result.json").stat().st_mode), 0o600
            )
        finally:
            os.umask(previous)

    def apply(self, path, plan):
        return self.command(
            [
                "apply",
                "--plan",
                str(path),
                "--approve-plan",
                plan["plan_id"],
                "--output",
                str(self.root / "result.json"),
            ]
        )

    def test_exact_disposable_removal_preserves_custody_and_peer(self):
        path, plan = self.plan()
        result = self.apply(path, plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.git("show", "refs/custody/test:source"), "original")
        self.assertTrue((self.repo / "source").exists())
        receipt = json.loads((self.root / "result.json").read_text())
        self.assertEqual(receipt["entries"][0]["disposition"], "removed")
        for receipt_path in (path, self.root / "result.json"):
            summary = self.summarize(receipt_path)
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(summary["unknown_count"], 0)
            self.assertEqual(summary["failure_count"], 0)
            self.assertEqual(summary["omitted_count"], 0)

    def test_changed_target_refuses_apply(self):
        path, plan = self.plan()
        (self.target / "source").write_text("pending work")
        result = self.apply(path, plan)
        self.assertEqual(result.returncode, 2)
        self.assertIn("drift", result.stderr)
        self.assertEqual((self.target / "source").read_text(), "pending work")

    def test_custody_drift_refuses_apply(self):
        path, plan = self.plan()
        self.git("update-ref", "-d", "refs/custody/test")
        self.assertEqual(self.apply(path, plan).returncode, 2)
        self.assertTrue(self.target.exists())

    def test_retained_plan_cannot_be_applied(self):
        path, plan = self.plan("denied")
        self.assertEqual(self.apply(path, plan).returncode, 2)
        self.assertTrue(self.target.exists())

    def test_dirty_ignored_locked_and_reviewed_references_retain(self):
        for kind in ("dirty", "ignored", "locked", "reference", "unreviewed"):
            with self.subTest(kind=kind):
                if kind == "dirty":
                    (self.target / "pending").write_text("work")
                elif kind == "ignored":
                    (self.target / ".gitignore").write_text("cache\n")
                    (self.target / "cache").write_text("generated hold")
                elif kind == "locked":
                    self.git("worktree", "lock", str(self.target))
                else:
                    report = json.loads(self.references.read_text())
                    report["entries"][0]["service_references"] = (
                        ["owned-service"] if kind == "reference" else []
                    )
                    report["entries"][0]["reviewed"] = kind != "unreviewed"
                    self.references.write_text(json.dumps(report))
                _, plan = self.plan()
                self.assertEqual(plan["entries"][0]["action"], "retain")
                (self.root / "plan.json").unlink()
                for name in ("pending", ".gitignore", "cache"):
                    (self.target / name).unlink(missing_ok=True)
                if kind == "locked":
                    self.git("worktree", "unlock", str(self.target))

    def test_exact_missing_registration_prune_preserves_commit(self):
        shutil.rmtree(self.target)
        path, plan = self.plan()
        self.assertEqual(plan["entries"][0]["action"], "prune")
        result = self.apply(path, plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("show", "refs/custody/test:source"), "original")
        self.assertNotIn(str(self.target), self.git("worktree", "list", "--porcelain"))

    def test_visible_process_reference_retains_checkout(self):
        _, plan = self.plan("reference")
        self.assertEqual(plan["entries"][0]["action"], "retain")
        self.assertIn("process_reference", plan["entries"][0]["reasons"])

    def test_timeout_keeps_unknown_receipt_and_refuses_overwrite(self):
        path, plan = self.plan()
        args = [
            "apply",
            "--plan",
            str(path),
            "--approve-plan",
            plan["plan_id"],
            "--output",
            str(self.root / "result.json"),
        ]
        result = self.command(args, "timeout")
        self.assertEqual(result.returncode, 2, result.stderr)
        receipt = (self.root / "result.json").read_bytes()
        self.assertEqual(json.loads(receipt)["entries"][0]["disposition"], "unknown")
        self.assertTrue(self.target.exists())
        self.assertEqual(self.command(args).returncode, 2)
        self.assertEqual((self.root / "result.json").read_bytes(), receipt)
        self.assertTrue(self.target.exists())
