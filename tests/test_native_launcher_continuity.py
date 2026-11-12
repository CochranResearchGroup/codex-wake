"""Durable native registration must preserve an operator-selected launcher."""
import json
import os
from pathlib import Path
import shlex
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from codex_wake.native_intents import _request
from codex_wake.native_delivery import _codex_adapter
from codex_wake.app_server import resolve_codex_cmd

THREAD = '11111111-1111-4111-8111-111111111111'


class LauncherContinuity(unittest.TestCase):
    def test_registered_launcher_observes_same_thread_after_build_rotation(self):
        with tempfile.TemporaryDirectory() as directory, socket.socket(socket.AF_UNIX) as sock:
            root = Path(directory)
            endpoint = root / 'daemon.sock'
            sock.bind(str(endpoint))
            response = json.dumps({'status': 'running', 'socketPath': str(endpoint)})
            builds = [root / 'build-v1', root / 'build-v2']
            for build in builds:
                build.write_text('#!/bin/sh\nprintf "%s\\n" ' + shlex.quote(response) + '\n')
                build.chmod(0o700)
            launcher = root / 'codex'
            launcher.symlink_to(builds[0])
            args = SimpleNamespace(native_command='at', trigger='2035-01-01T00:00:00Z',
                                   ttl='24h', prompt=['synthetic continuity check'],
                                   thread_id=THREAD, codex_path=str(launcher),
                                   endpoint='unix://', resume_missing=False)
            _, content, _, fingerprint, *_ = _request(args, root / 'wakes')
            self.assertEqual(resolve_codex_cmd(str(launcher), required=True), str(builds[0]))
            target = json.loads(json.dumps(content['target']))
            launcher.unlink()
            launcher.symlink_to(builds[1])
            builds[0].unlink()
            self.assertEqual(resolve_codex_cmd(str(launcher), required=True), str(builds[1]))
            self.assertEqual(_request(args, root / 'wakes')[3], fingerprint)
            with patch('codex_wake.shared_app_server.SharedAppServerReader') as reader:
                reader.return_value.__enter__.return_value.read_thread.return_value = {
                    'id': THREAD, 'status': {'type': 'idle'}}
                adapter = _codex_adapter()
                observed = adapter.observe(adapter.resolve(target))
            self.assertEqual(observed.state, 'ready', observed.reason)
            self.assertEqual(target['codex_cmd'], str(launcher))
            self.assertEqual(target['thread_id'], THREAD)

    def test_path_lookup_retains_selected_launcher_not_resolved_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / 'versioned-build'
            build.write_text('#!/bin/sh\nexit 0\n')
            build.chmod(0o700)
            launcher = root / 'codex'
            launcher.symlink_to(build)
            args = SimpleNamespace(native_command='at', trigger='2035-01-01T00:00:00Z',
                                   ttl='24h', prompt=['synthetic PATH check'], thread_id=THREAD,
                                   codex_path='codex', endpoint='unix://', resume_missing=False)
            with patch.dict(os.environ, {'PATH': str(root)}):
                _, content, *_ = _request(args, root / 'wakes')
            self.assertEqual(content['target']['codex_cmd'], str(launcher))

    def test_literal_build_pin_is_not_replaced_with_another_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pinned = root / 'specific-build'
            pinned.write_text('#!/bin/sh\nexit 1\n')
            pinned.chmod(0o700)
            args = SimpleNamespace(native_command='at', trigger='2035-01-01T00:00:00Z',
                                   ttl='24h', prompt=['synthetic pin check'], thread_id=THREAD,
                                   codex_path=str(pinned), endpoint='unix://', resume_missing=False)
            _, content, *_ = _request(args, root / 'wakes')
            pinned.unlink()
            adapter = _codex_adapter()
            observed = adapter.observe(adapter.resolve(content['target']))
            self.assertEqual(observed.state, 'unavailable')
            self.assertEqual(content['target']['codex_cmd'], str(pinned))


if __name__ == '__main__':
    unittest.main()
