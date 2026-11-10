"""Disposable stock tmux qualification; never connects to production sockets."""
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time
from codex_wake.tab_tmux_feed import TmuxMetadataFeed


def qualify():
    with tempfile.TemporaryDirectory(prefix='wake543-acceptance-') as directory:
        socket = str(Path(directory) / 'tmux.sock')
        def tmux(*args):
            return subprocess.check_output(['tmux', '-S', socket, *args], text=True, timeout=3).strip()
        tmux('new-session', '-d', '-s', 'private-fixture', '-x', '111', '-y', '37', 'exec sleep 90')
        feed = TmuxMetadataFeed(socket, '$0')
        before = tmux('list-panes', '-a', '-F', '#{pane_id}:#{pane_pid}:#{window_layout}:#{window_active}')
        try:
            baseline = feed.poll()
            assert baseline[0]['kind'] == 'baseline', baseline
            flags = tmux('list-clients', '-F', '#{client_flags}')
            assert all(flag in flags for flag in ('no-output', 'ignore-size', 'read-only'))
            samples = []
            for index in range(20):
                started = time.monotonic()
                tmux('rename-window', '-t', '@0', 'private-' + str(index))
                while time.monotonic() - started < 2:
                    events = feed.poll(.05)
                    if any(event['kind'] == 'update' and event['data']['snapshot']['windows'][0]['name'] == 'private-' + str(index) for event in events):
                        samples.append(time.monotonic() - started)
                        break
                else:
                    raise AssertionError('metadata update missed two-second target')
            pid = feed.status()['owned_pid']
            status = feed.status()
            feed.close()
            assert tmux('list-clients', '-F', '#{client_pid}') == ''
            assert before == tmux('list-panes', '-a', '-F', '#{pane_id}:#{pane_pid}:#{window_layout}:#{window_active}')
            assert not Path('/proc/' + str(pid)).exists()
            return dict(tmux_version=subprocess.check_output(['tmux', '-V'], text=True).strip(),
                        sample_count=len(samples), p95_seconds=sorted(samples)[18],
                        max_seconds=max(samples), mean_seconds=statistics.mean(samples),
                        child_reaped=True, pane_identity_layout_focus_preserved=True,
                        startup_seconds=status['startup_seconds'], client_flags=flags,
                        owned_processes_after=0, uid=os.geteuid())
        finally:
            feed.close()
            tmux('kill-server')


if __name__ == '__main__':
    print(json.dumps(qualify(), indent=2, sort_keys=True))
