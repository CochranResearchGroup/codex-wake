"""Explicit modes and verified session closure through native registration/poll."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from codex_wake.cli import run
from codex_wake.daemon import poll_once
from codex_wake.records import all_records
from codex_wake.process import process_identity
THREAD = "11111111-1111-4111-8111-111111111111"
CLOCK = {"utc": {"lower": 2000000000, "upper": 2000000000, "status": "network", "sources": ["clock-a", "clock-b"]}, "counter": None}
class WakeSessionModes(unittest.TestCase):
    def test_session_only_survives_detach_and_cancels_after_exact_process_exits(self):
        with tempfile.TemporaryDirectory() as d:
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            try:
                identity = process_identity(child.pid)
                snapshot = {"complete": True, "sessions": [{"thread_id": THREAD, "binding_status": "metadata_matched", "attachments": [{"client_pid": child.pid, "client_start_time_ticks": identity["start_time_ticks"], "pane_id": "%1", "socket": None}]}]}
                out = io.StringIO()
                with patch("codex_wake.sessions.observe", return_value=snapshot), patch("codex_wake.native_clock.snapshot", return_value=CLOCK), contextlib.redirect_stdout(out):
                    code = run(["--wake-root", d, "native", "after", "--json", "--session-mode", "session_only", "--codex-path", sys.executable, THREAD, "1h", "--", "check"])
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(out.getvalue())["session_mode"], "session_only")
                with patch("codex_wake.native_clock.snapshot", return_value=CLOCK): poll_once(Path(d), dispatch=False)
                self.assertEqual(all_records(Path(d))[0].record["status"], "pending")
                child.terminate(); child.wait(timeout=5)
                with patch("codex_wake.native_clock.snapshot", return_value=CLOCK): poll_once(Path(d), dispatch=False)
                self.assertEqual(all_records(Path(d))[0].record["status"], "cancelled")
                self.assertEqual(all_records(Path(d))[0].record["attempts"], 0)
            finally:
                if child.poll() is None: child.terminate(); child.wait(timeout=5)
    def test_native_agent_schema_requires_explicit_mode(self):
        from codex_wake.harness_mcp import tool_specs
        for verb in ("after", "at", "file"):
            self.assertIn("session_mode", tool_specs()["wake_native_" + verb][4])
