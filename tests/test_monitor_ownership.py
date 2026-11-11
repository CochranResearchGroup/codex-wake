from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codex_wake.daemon import poll_once, poll_result_dict
from codex_wake.records import build_record, write_record
from codex_wake.monitor_ownership import MonitorOwnership


class MonitorOwnershipTests(unittest.TestCase):
    """Public polling entrypoints must agree on one canonical root owner."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "wake"
        record = build_record(
            predicate={"type": "not_before", "due_at": "2099-01-01T00:00:00Z"},
            prompt="synthetic ownership fixture",
            cwd=self.base,
            target={"transport": "tmux", "tmux_socket": "/tmp/fixture", "pane": "%1"},
        )
        self.record_path = write_record(self.root, record)
        self.original = self.record_path.read_bytes()
        self.env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
                        XDG_STATE_HOME=str(self.base / "state"),
                        XDG_CONFIG_HOME=str(self.base / "config"))

    def holder(self) -> subprocess.Popen[str]:
        process = subprocess.Popen(
            [sys.executable, "-c", """
import sys
from pathlib import Path
from codex_wake.monitor_ownership import MonitorOwnership
with MonitorOwnership(Path(sys.argv[1])) as owner:
    print('ready' if owner.acquired else 'contended', flush=True)
    sys.stdin.readline()
""", str(self.root)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=self.env,
        )
        self.addCleanup(self.stop, process)
        self.assertEqual(process.stdout.readline().strip(), "ready")
        return process

    @staticmethod
    def stop(process: subprocess.Popen[str]) -> None:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def test_competing_processes_and_root_alias_skip_without_evaluating(self) -> None:
        self.holder()
        alias = self.base / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        result = poll_once(alias, dispatch=False)
        self.assertEqual(poll_result_dict(result).get("skip_reason"), "monitor_owned")
        self.assertEqual(result.checked, 0)
        self.assertEqual(self.record_path.read_bytes(), self.original)

    def test_real_daemon_and_supervisor_report_contended_root(self) -> None:
        self.holder()
        daemon = subprocess.run(
            [sys.executable, "-m", "codex_wake.daemon", "--wake-root", str(self.root),
             "--once", "--no-dispatch"], capture_output=True, text=True,
            env=self.env, timeout=10,
        )
        self.assertEqual(daemon.returncode, 0, daemon.stderr)
        self.assertIn("skipped=monitor_owned", daemon.stdout)
        supervisor = subprocess.run(
            [sys.executable, "-c", """
import json, sys
from pathlib import Path
from codex_wake.supervisor import build_supervisor_config, enroll_root, supervisor_poll_once
base, root = Path(sys.argv[1]), Path(sys.argv[2])
config=build_supervisor_config(registry_dir=base/'registry', state_dir=base/'supervisor', validate_executable=False)
enroll_root(wake_root=root, repo_root=base, registry_dir=config.registry_dir)
print(json.dumps(supervisor_poll_once(config, dispatch=False)))
""", str(self.base), str(self.root)], capture_output=True, text=True,
            env=self.env, timeout=10,
        )
        self.assertEqual(supervisor.returncode, 0, supervisor.stderr)
        rows = json.loads(supervisor.stdout)
        self.assertEqual(rows[0]["result"].get("skip_reason"), "monitor_owned")
        self.assertEqual(self.record_path.read_bytes(), self.original)


    def test_owner_crash_releases_custody_without_replacing_lock_inode(self) -> None:
        process = self.holder()
        lock = self.root / "locks" / "monitor.lock"
        inode = lock.stat().st_ino
        self.assertEqual(lock.stat().st_mode & 0o777, 0o600)
        process.send_signal(signal.SIGKILL)
        process.communicate(timeout=5)
        result = poll_once(self.root, dispatch=False)
        self.assertIsNone(result.skip_reason)
        self.assertEqual(result.checked, 1)
        self.assertEqual(lock.stat().st_ino, inode)

    def test_contended_loop_does_not_publish_or_stop_another_lifecycle(self) -> None:
        self.holder()
        lifecycle = self.root / "lifecycle"
        lifecycle.mkdir()
        proof = lifecycle / "supervision.json"
        proof.write_text('{"fixture": "existing owner"}')
        before = proof.read_bytes()
        daemon = subprocess.run(
            [sys.executable, "-m", "codex_wake.daemon", "--wake-root", str(self.root),
             "--interval", "0.1", "--no-dispatch"], capture_output=True, text=True,
            env=self.env, timeout=10,
        )
        self.assertEqual(daemon.returncode, 2, daemon.stderr)
        self.assertIn("skipped=monitor_owned", daemon.stdout)
        self.assertEqual(proof.read_bytes(), before)
        self.assertEqual(self.record_path.read_bytes(), self.original)

    def test_reconciliation_marker_holds_poll_and_loop_but_allows_raw_custody(self) -> None:
        # An undecodable marker still means an unresolved interrupted poll.
        marker = self.root / "monitor-reconciliation.json"
        marker.write_text("unreadable as a reconciliation record")
        with MonitorOwnership(self.root) as owner:
            self.assertTrue(owner.acquired)
            result = poll_once(self.root, dispatch=False)
        self.assertEqual(result.skip_reason, "reconciliation_required")
        self.assertEqual(result.checked, 0)
        self.assertEqual(self.record_path.read_bytes(), self.original)
        daemon = subprocess.run(
            [sys.executable, "-m", "codex_wake.daemon", "--wake-root", str(self.root),
             "--interval", "0.1", "--no-dispatch"], capture_output=True, text=True,
            env=self.env, timeout=10,
        )
        self.assertEqual(daemon.returncode, 2, daemon.stderr)
        self.assertIn("skipped=reconciliation_required", daemon.stdout)
        self.assertFalse((self.root / "lifecycle").exists())
        marker.unlink()
        self.assertEqual(poll_once(self.root, dispatch=False).checked, 1)

    def test_forked_child_does_not_retain_or_reuse_parent_custody(self) -> None:
        read_fd, write_fd = os.pipe()
        result_path = self.base / "fork-result.json"
        child_pid = None
        try:
            with MonitorOwnership(self.root):
                child_pid = os.fork()
                if child_pid == 0:
                    os.close(write_fd)
                    os.read(read_fd, 1)
                    try:
                        result_path.write_text(json.dumps(poll_result_dict(
                            poll_once(self.root, dispatch=False))))
                    finally:
                        os._exit(0)
            os.write(write_fd, b"x")
            waited, status = os.waitpid(child_pid, 0)
            child_pid = None
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(result_path.read_text())["checked"], 1)
        finally:
            os.close(read_fd)
            os.close(write_fd)
            if child_pid:
                os.kill(child_pid, signal.SIGKILL)
                os.waitpid(child_pid, 0)

    def test_executed_child_does_not_keep_owner_custody_after_exit(self) -> None:
        # Keep the child alive across owner exit, without relying on descriptor
        # introspection: a later real poll must acquire while that child lives.
        owner = subprocess.Popen(
            [sys.executable, "-c", r"""
import subprocess, sys
from pathlib import Path
from codex_wake.monitor_ownership import MonitorOwnership
with MonitorOwnership(Path(sys.argv[1])) as owner:
    child = subprocess.Popen([sys.executable, '-c',
        'import sys; print("ready", flush=True); sys.stdin.readline()'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, close_fds=False)
    assert child.stdout.readline() == b'ready\n'
    print(child.pid, flush=True)
    sys.stdin.readline()
# The caller released custody while the exec child is still running.
print('released', flush=True)
sys.stdin.readline()
child.communicate(input=b'done\n', timeout=5)
""", str(self.root)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=self.env,
        )
        self.addCleanup(self.stop, owner)
        child_pid = int(owner.stdout.readline())
        owner.stdin.write("release\n")
        owner.stdin.flush()
        self.assertEqual(owner.stdout.readline().strip(), "released")
        os.kill(child_pid, 0)
        self.assertEqual(poll_once(self.root, dispatch=False).checked, 1)
        owner.communicate(input="finish\n", timeout=5)
        self.assertEqual(owner.returncode, 0)

class CopiedContextOwnershipTests(unittest.TestCase):
    def test_async_thread_cannot_reuse_another_threads_polling_lease(self):
        import asyncio

        async def contend(root):
            with MonitorOwnership(root):
                return await asyncio.to_thread(poll_once, root, dispatch=False)

        with tempfile.TemporaryDirectory() as tmp:
            result = asyncio.run(contend(Path(tmp) / 'wake'))
            self.assertEqual(result.skip_reason, 'monitor_owned')


if __name__ == "__main__":
    unittest.main()
