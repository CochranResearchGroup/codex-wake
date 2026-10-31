#!/usr/bin/env python3
"""Real native/TUI regression for unnamed saved-conversation attachment discovery.

Uses two successful local Responses fixtures, a private native home/socket and a
private tmux server. No external inference, production tabs or shared restart.
Run with the exact candidate/installed interpreter and intended PYTHONPATH.
"""
import argparse
import hashlib
import os
import json
import subprocess
import sys
import tempfile
import time
import signal
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from codex_wake.native_protocol import native_request
parser = argparse.ArgumentParser(description='Opt-in exact saved-session close/resume through real native and private tmux; loopback fixture only.')
parser.add_argument('--native', type=Path, required=True)
parser.add_argument('--models', type=Path, required=True, help='Existing local model catalog; prevents remote catalog discovery.')
parser.add_argument('--output', type=Path, required=True)
options = parser.parse_args()
binary = str(options.native.resolve(strict=True))
output = options.output.resolve()
output.mkdir(parents=True, mode=0o700, exist_ok=False)
started = time.monotonic()
with open(binary, 'rb') as executable:
    native_sha256 = hashlib.file_digest(executable, 'sha256').hexdigest()
count = 0

class LocalOnly(BaseHTTPRequestHandler):

    def do_POST(self):
        global count
        count += 1
        if count > 2:
            self.send_error(429)
            return
        self.rfile.read(int(self.headers.get('Content-Length', '0')))
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Connection', 'close')
        self.end_headers()
        events = [{'type': 'response.created', 'response': {'id': f'fixture-{count}'}}, {'type': 'response.output_item.done', 'item': {'id': f'msg-{count}', 'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'LOCAL RECOVERY FIXTURE'}]}}, {'type': 'response.completed', 'response': {'id': f'fixture-{count}', 'usage': {'input_tokens': 10, 'input_tokens_details': {'cached_tokens': 0}, 'output_tokens': 3, 'total_tokens': 13}}}]
        for event in events:
            self.wfile.write(('event: ' + event['type'] + '\n' + 'data: ' + json.dumps(event) + '\n\n').encode())
            self.wfile.flush()
        self.close_connection = True

    def log_message(self, *args):
        pass
with tempfile.TemporaryDirectory(prefix='cw-close-resume-') as tmp:
    root = Path(tmp)
    home = root / 'home'
    home.mkdir(mode=0o700)
    model = ThreadingHTTPServer(('127.0.0.1', 0), LocalOnly)
    threading.Thread(target=model.serve_forever, daemon=True).start()
    model_info = json.loads(options.models.read_text())['models'][0]
    catalog = home / 'models.json'
    catalog.write_text(json.dumps({'models': [model_info]}))
    (home / 'config.toml').write_text(f'model={json.dumps(model_info["slug"])}\nmodel_catalog_json={json.dumps(str(catalog))}\ncheck_for_update_on_startup=false\nmodel_provider="local_fixture"\napproval_policy="never"\n[analytics]\nenabled=false\n[model_providers.local_fixture]\nname="No external inference"\nbase_url="http://127.0.0.1:{model.server_port}/v1"\nwire_api="responses"\nrequires_openai_auth=false\nsupports_websockets=false\nrequest_max_retries=0\nstream_max_retries=0\n[projects.{json.dumps(str(root))}]\ntrust_level="trusted"\n')
    env = dict({k: v for k, v in os.environ.items() if not k.startswith('CODEX_')}, CODEX_HOME=str(home), HOME=str(root), XDG_CONFIG_HOME=str(root / 'config'), XDG_STATE_HOME=str(root / 'state'), TERM='xterm-256color', CODEX_WAKE_STABLE_TIME_CONFIG='')
    for k in ('CODEX_THREAD_ID', 'TMUX', 'TMUX_PANE'):
        env.pop(k, None)
    endpoint = 'unix://' + str(root / 'native.sock')
    sock = str(root / 'tmux.sock')

    def tmux(*args, check=True):
        return subprocess.run(['tmux', '-f', '/dev/null', '-S', sock, *args], env=env, capture_output=True, text=True, check=check, timeout=10)
    with (root / 'server.log').open('w') as log:
        proc = subprocess.Popen([binary, 'app-server', '--listen', endpoint], env=env, stdout=log, stderr=log, start_new_session=True)
        try:
            until = time.monotonic() + 15
            while not (root / 'native.sock').exists():
                if proc.poll() is not None:
                    raise RuntimeError('private native exited')
                if time.monotonic() > until:
                    raise TimeoutError('private socket readiness')
                time.sleep(0.05)
            endpoint = 'unix://' + str((root / 'native.sock').resolve(strict=True))

            def rpc(method, **params):
                return native_request(endpoint, binary, method, params, 5)
            threads = []
            for i in range(2):
                identity = rpc('thread/start', cwd=str(root))['thread']['id']
                threads.append(identity)
                rpc('turn/start', threadId=identity, input=[{'type': 'text', 'text': 'Disposable recovery qualification. No tools or external work.', 'text_elements': []}])
                deadline = time.monotonic() + 15
                while count < i + 1:
                    if time.monotonic() > deadline:
                        raise TimeoutError('local fixture request readiness')
                    time.sleep(0.05)
                while True:
                    rows = rpc('thread/read', threadId=identity, includeTurns=True)['thread']['turns']
                    if rows and all((t['status'] != 'inProgress' for t in rows)):
                        break
                    if time.monotonic() > deadline:
                        raise TimeoutError('local-only turn termination')
                    time.sleep(0.05)
                saved = rpc('thread/read', threadId=identity, includeTurns=False)['thread']
                assert Path(saved['path']).exists(), 'seed did not persist history'
            assert count == 2, count
            histories = {t: rpc('thread/read', threadId=t, includeTurns=True)['thread']['turns'] for t in threads}
            tmux('new-session', '-d', '-s', 'fixture', '-n', 'sentinel', 'sleep 120')
            cli = [sys.executable, '-m', 'codex_wake.cli', '--wake-root', str(root / 'wake'), 'sessions']

            def wake(*args):
                result = subprocess.run(cli + list(args) + ['--app-server', endpoint, '--tmux-socket', sock, '--timeout', '8', '--json'], env=env, capture_output=True, text=True, timeout=20)
                if result.returncode:
                    raise RuntimeError('public CLI failed: ' + result.stdout[-1400:] + result.stderr[-400:])
                return json.loads(result.stdout)
            opened = []
            for i, t in enumerate(threads):
                result = wake('open', '--resume', t, '--name', f'conversation-{i}', '--tmux-session', 'fixture', '--codex-path', binary)
                if result.get('ready') is not True:
                    snapshot = wake('list')
                    (output / 'attachment-snapshot.json').write_text(json.dumps(snapshot, indent=2) + '\n')
                    print(json.dumps({'native_threads': [{'id': r.get('thread_id'), 'name': r.get('name'), 'binding_status': r.get('binding_status'), 'attachments': len(r.get('attachments', [])), 'candidates': r.get('candidates')} for r in snapshot['sessions']]}))
                    pane = tmux('capture-pane', '-p', '-t', result['pane_id'], check=False).stdout
                    (output / 'native-session-pane.txt').write_text(pane)
                    raise AssertionError(str(result) + ' pane=' + pane[-2000:])
                opened.append(result)
            first = wake('open', '--resume', threads[0], '--name', 'duplicate-must-not-open', '--tmux-session', 'fixture', '--codex-path', binary)
            assert first['action'] == 'reused', first
            before = tmux('list-windows', '-t', 'fixture', '-F', '#{window_id}').stdout.splitlines()
            closed = wake('close', 'thread:' + threads[0])
            assert closed['action'] == 'closed' and closed['conversation'] == 'preserved', closed
            saved = rpc('thread/read', threadId=threads[0], includeTurns=False)['thread']
            assert saved['id'] == threads[0]
            restored = wake('open', '--resume', threads[0], '--name', 'conversation-0-restored', '--tmux-session', 'fixture', '--codex-path', binary)
            assert restored['ready'] is True and restored['thread_id'] == threads[0], restored
            after = tmux('list-windows', '-t', 'fixture', '-F', '#{window_id}').stdout.splitlines()
            assert len(before) == len(after) == 3, (before, after)
            assert count == 2, 'resume or close caused unexpected provider request'
            for t in threads:
                assert rpc('thread/read', threadId=t, includeTurns=True)['thread']['turns'] == histories[t], 'saved history changed'
            repeat = wake('open', '--resume', threads[0], '--name', 'must-reuse-restored', '--tmux-session', 'fixture', '--codex-path', binary)
            assert repeat['action'] == 'reused' and repeat['thread_id'] == threads[0], repeat
            assert rpc('thread/read', threadId=threads[0], includeTurns=False)['thread']['name'] == 'conversation-0', 'existing name changed'
            rows = wake('list')['sessions']
            peer = next((r for r in rows if r.get('thread_id') == threads[1]))
            assert peer['attachments'] == opened[1]['attachments'], 'peer attachment changed'
            assert tmux('list-windows', '-t', 'fixture', '-F', '#{window_id}').stdout.splitlines() == after, 'duplicate resume created a tab'
            report = {'status': 'PASS', 'native_version': subprocess.check_output([binary, '--version'], text=True).strip(), 'native_sha256': native_sha256, 'elapsed_seconds': round(time.monotonic() - started, 3), 'peer_attachment_unchanged': True, 'existing_name_preserved': True, 'saved_turn_history_preserved': True, 'repeat_after_restore_reused': True, 'distinct_conversations_same_cwd': 2, 'public_open_ready': True, 'duplicate_open_reused': True, 'close_preserved_conversation': True, 'exact_resume_ready': True, 'window_count_before_after': [len(before), len(after)], 'local_fixture_requests': count, 'external_inference': False, 'production_touched': False}
            (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report))
        except Exception as exc:
            report = {'status': 'FAIL', 'error': str(exc), 'local_fixture_requests': count, 'production_touched': False}
            (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report))
            raise
        finally:
            tmux('kill-server', check=False)
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
            (output / 'native.log').write_bytes((root / 'server.log').read_bytes())
            model.shutdown()
            model.server_close()
