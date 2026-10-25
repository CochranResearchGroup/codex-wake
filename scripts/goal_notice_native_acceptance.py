"""Owned native/stock-TUI notice acceptance, with no provider request or shared effects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time

from codex_wake.native_protocol import native_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-server', type=Path, required=True)
    parser.add_argument('--frontend', default='codex')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    executable = args.app_server.resolve(strict=True)
    frontend = Path(shutil.which(args.frontend) or args.frontend).resolve(strict=True)
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmux_name = 'cw345-owned-' + str(os.getpid())
    processes = []
    report = dict(state='running', app_server=str(executable),
        app_server_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
        frontend=str(frontend), shared_runtime_changed=False, provider_turns=0)
    with tempfile.TemporaryDirectory(prefix='cw345-native-') as temporary:
        root = Path(temporary)
        home = root / 'home'
        home.mkdir(mode=0o700)
        (home/'config.toml').write_text(f'''model = "mock-model"
model_provider = "notice_fixture"
approval_policy = "never"
sandbox_mode = "read-only"
[model_providers.notice_fixture]
name = "Owned no-provider notice fixture"
base_url = "http://127.0.0.1:9/v1"
wire_api = "responses"
request_max_retries = 0
stream_max_retries = 0
[projects.{json.dumps(str(root))}]
trust_level = "trusted"
''')
        env = dict(os.environ, CODEX_HOME=str(home))
        socket = root/'app-server.sock'
        log = (output/'native.log').open('w')
        server = subprocess.Popen([str(executable), '--listen', 'unix://'+str(socket)],
            env=env, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        processes.append(server)
        def wait_for(function, timeout=20):
            end = time.monotonic()+timeout
            while time.monotonic()<end:
                value = function()
                if value: return value
                if server.poll() is not None: raise RuntimeError('owned native server exited')
                time.sleep(.1)
            raise TimeoutError('owned acceptance readiness expired')
        def tmux(*arguments, check=True):
            return subprocess.run(['tmux','-L',tmux_name,*arguments],capture_output=True,text=True,timeout=10,check=check)
        def capture():
            return tmux('capture-pane','-t','notice:0.0','-p','-S','-200',check=False).stdout
        try:
            wait_for(socket.exists)
            endpoint = 'unix://'+str(socket.resolve())
            def rpc(method, **params):
                return native_request(endpoint,str(frontend),method,params,15)
            thread = rpc('thread/start',cwd=str(root))['thread']
            peer = rpc('thread/start',cwd=str(root))['thread']
            thread_id, peer_id = thread['id'], peer['id']
            rpc('thread/notice/read',threadId=thread_id,eventId='notice_setup_probe')
            rpc('thread/notice/read',threadId=peer_id,eventId='notice_setup_probe')
            goal = rpc('thread/goal/set',threadId=thread_id,objective='Owned notice presentation qualification',status='paused')['goal']
            assert goal['status'] == 'paused', goal
            peer_before = rpc('thread/read',threadId=peer_id,includeTurns=True)['thread']['turns']
            command = shlex.join(['env','CODEX_HOME='+str(home),'TERM=xterm-256color',str(frontend),
                '--remote',endpoint,'--no-alt-screen','resume',thread_id])
            tmux('new-session','-d','-s','notice','-x','160','-y','55',command)
            # Confirm the actual frontend is attached before emitting a notice.
            baseline = wait_for(lambda: text if (text := capture()) and ('mock-model' in text or 'context left' in text) else None)
            (output/'before.txt').write_text(baseline)
            event_id = 'notice_owned_render_1'
            text = ('Goal paused: external allowance reached. Used 100,000 of 100,000 fresh tokens. '
                'Extend allowance / Reset budget window / Keep stopped. '
                'Native /goal resume alone does not renew this external allowance. '
                f'[External supervision event {event_id}]')
            appended = rpc('thread/notice/append',threadId=thread_id,eventId=event_id,text=text)
            rendered = wait_for(lambda: frame if 'Goal paused: external allowance reached.' in (frame := capture()) else None)
            (output/'rendered.txt').write_text(rendered)
            assert rendered.count('Goal paused: external allowance reached.') == 1, rendered
            # An explicitly owned shell task exercises the real busy-tool path.
            rpc('thread/shellCommand',threadId=thread_id,command='sleep 20')
            active = wait_for(lambda: turns if (turns := [turn for turn in rpc('thread/turns/list',threadId=thread_id,limit=128,itemsView='notLoaded')['data'] if turn['status']=='inProgress']) else None)
            work_turn = active[0]['id']
            busy_id = 'notice_owned_busy_tool_1'
            busy_text = 'Stop requested while owned tool is busy. Keep stopped. [External supervision event '+busy_id+']'
            busy_result = rpc('thread/notice/append',threadId=thread_id,eventId=busy_id,text=busy_text)
            busy_frame = wait_for(lambda: frame if 'Stop requested while owned tool is busy.' in (frame := capture()) else None)
            (output/'busy-tool.txt').write_text(busy_frame)
            assert rpc('thread/notice/read',threadId=thread_id,eventId=busy_id)['modelContextAvailable'] is True
            rpc('turn/interrupt',threadId=thread_id,turnId=work_turn)
            wait_for(lambda: not [turn for turn in rpc('thread/turns/list',threadId=thread_id,limit=128,itemsView='notLoaded')['data'] if turn['status']=='inProgress'])
            # Lose the acknowledgement at the Wake/native seam after a real
            # native append. Reconciliation must observe, never replay, it.
            from codex_wake.goal_notices import NativeNoticeAdapter, record_notice, present_notice
            from codex_wake.goal_supervision import _directory, _name, _save
            wake_root = root/'wake'
            receipt = dict(thread_id=thread_id,allocation_id='owned-presentation',generation='owned-window',
                state='stopped',reason='allocation_exhausted',used_tokens=100000,token_limit=100000,
                token_accounting='fresh',deadline=time.time(),stop_turns=[work_turn],stop_proof=True,
                grant=dict(app_server=endpoint,codex_path=str(frontend),rpc_timeout=15))
            _save(_directory(wake_root)/(_name(thread_id)+'.json'),receipt)
            notice = record_notice(wake_root,receipt,'stop')
            native_adapter = NativeNoticeAdapter(wake_root)
            class LostAcknowledgement:
                def append(self, event):
                    native_adapter.append(event)
                    raise TimeoutError('injected acknowledgement loss after actual append')
                def reconcile(self, event): return native_adapter.reconcile(event)
            unknown = present_notice(wake_root,notice['event_id'],adapter=LostAcknowledgement())
            assert unknown['delivery']['state'] == 'unknown', unknown
            reconciled = present_notice(wake_root,notice['event_id'],adapter=native_adapter)
            assert reconciled['delivery']['state'] == 'recorded', reconciled
            assert reconciled['delivery']['attempts'] == 1, reconciled
            duplicate = rpc('thread/notice/append',threadId=thread_id,eventId=event_id,text=text)
            assert duplicate['alreadyRecorded'] is True and duplicate['notificationPublished'] is False, duplicate
            retained = rpc('thread/notice/read',threadId=thread_id,eventId=event_id)
            assert retained['notice'] == dict(eventId=event_id,text=text), retained
            assert retained['modelContextAvailable'] is True, retained
            # Reattach a new frontend to the same saved conversation; no new turn.
            tmux('kill-session','-t','notice')
            tmux('new-session','-d','-s','notice','-x','160','-y','55',command)
            replayed = wait_for(lambda: frame if 'Goal paused: external allowance reached.' in (frame := capture()) else None)
            (output/'reconnected.txt').write_text(replayed)
            assert replayed.count('Goal paused: external allowance reached.') == 1, replayed
            peer_after = rpc('thread/read',threadId=peer_id,includeTurns=True)['thread']['turns']
            assert peer_before == peer_after, (peer_before,peer_after)
            history = [json.loads(line) for line in Path(thread['path']).read_text().splitlines()]
            started = [row for row in history if row.get('type') == 'event_msg' and row.get('payload',{}).get('type') == 'task_started']
            assert len(started) == 1, started
            context = [row for row in history if row.get('type') == 'response_item' and row.get('payload',{}).get('id') == event_id]
            assert len(context) == 1, context
            report.update(state='passed', thread_id=thread_id, peer_id=peer_id,
                append=appended, duplicate=duplicate, retained=retained,
                native_model_turns_started=0, explicit_shell_turns_started=1, rendered_live=True, rendered_reconnected_once=True, busy_tool_notice=busy_result,
                model_context_retained=True, peer_unchanged=True, fixture_external_usage=True, lost_ack_reconciled_once=True)
        except Exception as error:
            report.update(state='failed', failure=type(error).__name__)
            (output/'last-frame.txt').write_text(capture())
            raise
        finally:
            from codex_wake.process import process_identity
            census = subprocess.check_output(['ps','-eo','pid=,ppid='],text=True)
            parents = {int(pid):int(parent) for pid,parent in (line.split() for line in census.splitlines())}
            owned = {process.pid for process in processes}
            tmux_pid = tmux('display-message','-p','#{pid}',check=False).stdout.strip()
            if tmux_pid.isdigit(): owned.add(int(tmux_pid))
            changed = True
            while changed:
                previous = set(owned)
                owned.update(pid for pid,parent in parents.items() if parent in owned)
                changed = previous != owned
            identities = {}
            for pid in owned:
                try: identities[pid] = process_identity(pid)
                except (OSError,ValueError): pass
            tmux('kill-server',check=False)
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=15)
            log.close()
            end = time.monotonic()+5
            while True:
                remaining = []
                for pid,identity in identities.items():
                    try:
                        state = Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[0]
                        if state != 'Z' and process_identity(pid) == identity: remaining.append(pid)
                    except (OSError,ValueError): pass
                if not remaining or time.monotonic()>=end: break
                time.sleep(.02)
            report['owned_processes_terminal'] = not remaining
            report['owned_process_census'] = dict(observed_pids=sorted(owned),remaining_pids=remaining)
            if remaining: report['state'] = 'cleanup_incomplete'
            (output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,sort_keys=True))


if __name__ == '__main__':
    main()
