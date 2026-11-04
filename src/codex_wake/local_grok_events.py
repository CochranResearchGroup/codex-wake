"""One detached ACP prompt owner; original journal intent is never redispatched."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from .controller_grok import ControllerGrok
from .daemon_commands import local_operator
from .grok_acp import ACPRefusal
from .local_session_events import TurnEvents
from .process import process_identity


def launch(root, identifier):
    # Called only by the journal's once-only admission dispatcher.
    process = subprocess.Popen([sys.executable, '-m', 'codex_wake.local_grok_events',
        '--root', str(Path(root).resolve()), '--operation', identifier], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
    threading.Thread(target=process.wait, daemon=True).start()
    return dict(kind='grok_acp_collecting', collector_pid=process.pid, collector_process=process_identity(process.pid), native_request_id=identifier)


def collect(root, identifier):
    from .local_grok_control import LocalGrokControl
    local = LocalGrokControl(root); actor = local._actor(identifier)
    store = TurnEvents(root); runtime = local.runtime
    lock_path = runtime.path.parent / (identifier + '.collector.lock')
    with lock_path.open('a') as lock:
        os.chmod(lock_path, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if store.state(identifier)['status'] != 'unavailable':
            return
        store.update(identifier, status='connecting', pid=os.getpid(), process=process_identity(os.getpid()),
                     provider='grok', unsupported_event_kinds=[])
        try:
            deadline = time.monotonic() + 10
            while True:
                record = runtime._load(identifier)
                if record['phase'] == 'waiting':
                    break
                if record['phase'] != 'dispatching' or time.monotonic() >= deadline:
                    raise RuntimeError('original admission did not publish collector custody')
                time.sleep(.01)
            payload = record['payload']; target = record['target']
            row = local.resolve('grok:' + target['conversation_id'], target, payload['profile'])
            def update(event):
                change = event.get('update', {}); kind = change.get('sessionUpdate')
                if kind == 'agent_message_chunk' and change.get('content', {}).get('type') == 'text':
                    store.append(identifier, 'grok/session/update', event)
                elif kind not in ('agent_thought_chunk', 'user_message_chunk'):
                    state = store.state(identifier)
                    store.update(identifier, unsupported_event_kinds=sorted(set(state.get('unsupported_event_kinds', []) + [str(kind)])))
                store.update(identifier, status='running')
            owner = ControllerGrok(root, on_update=update)
            selected, guard = local._connection(row['profile'], target)
            with owner._connection(selected, guard) as connection:
                owner._negotiation(connection, selected)
                store.update(identifier, status='running', transmitted=True)
                result = owner.prompt_native(connection, target['conversation_id'], payload['prompt'], identifier)
            current = runtime._load(identifier)
            current['result'] = result
            owner.observe_native_owned(current)
            # Publish complete retention before a caller can observe terminal work.
            store.update(identifier, status='completed')
            runtime._save(current)
        except ACPRefusal as error:
            current = runtime._load(identifier)
            current['result'] = dict(kind='grok_acp_refusal', reason=error.code,
                native_error_code=error.native_code, execution='not_started', provider_work=False)
            local.owner.observe_native_owned(current); runtime._save(current)
            store.update(identifier, status='failed', reason=error.code)
        except Exception as error:
            current = runtime._load(identifier)
            if current['phase'] != 'terminal':
                current.update(phase='uncertain', execution='unknown', reason=getattr(error, 'code', 'native_owner_unavailable'))
                runtime._save(current)
            store.update(identifier, status='uncertain', reason=getattr(error, 'code', 'native_owner_unavailable'))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--root', required=True); parser.add_argument('--operation', required=True)
    arguments = parser.parse_args(); collect(arguments.root, arguments.operation)


if __name__ == '__main__':
    main()
