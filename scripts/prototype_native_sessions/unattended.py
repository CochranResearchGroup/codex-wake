"""PROTOTYPE unattended native CLI submission; no MCP or TUI dependency."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

thread_id, receipt = sys.argv[1:]
env = dict(os.environ)
for key in ('CODEX_THREAD_ID', 'TMUX', 'TMUX_PANE'):
    env.pop(key, None)
started = time.time()
result = subprocess.run(
    [str(Path.home() / '.local/bin/codex'), 'queue', '--thread', thread_id, '--message',
     'Authorized unattended submission experiment. Reply exactly '
     'UNATTENDED_NATIVE_RECEIVED_20261009. Do not run commands, edit files, or message anyone.'],
    env=env, text=True, capture_output=True, timeout=60)
Path(receipt).write_text(json.dumps({
    'prototype': True, 'thread_id': thread_id, 'pid': os.getpid(),
    'started_at': started, 'finished_at': time.time(),
    'transport': 'codex queue', 'exit_code': result.returncode,
    'stdout': result.stdout, 'stderr': result.stderr,
    'calling_tui_environment_removed': True}, indent=2)+'\n')
raise SystemExit(result.returncode)
