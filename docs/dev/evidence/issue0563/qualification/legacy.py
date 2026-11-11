"""Create old-version records, then exercise new-version public operations."""
import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    import codex_wake
    from codex_wake.controller_tabs import ControllerTabs
    from codex_wake.terminal_relocation import TerminalRelocation
    from codex_wake.tab_organization import TabOrganization, TmuxTransport
    from codex_wake.process import process_identity
    mode, base = sys.argv[1], Path(sys.argv[2])
    path = base / 'legacy-contexts.json'

    def tmux(sock, *args):
        return subprocess.check_output(['tmux', '-S', str(sock), *args], text=True).strip()

    def observations(sock, repo):
        result = {}
        for line in tmux(sock, 'list-panes', '-a', '-F', '#{pane_id}\t#{pane_pid}\t#{window_name}').splitlines():
            pane, pid, name = line.split('\t')
            birth = process_identity(int(pid))
            result[pane] = dict(conversation_id='fixture-'+pane, namespace='fixture',
                process=dict(pid=int(pid), start_ticks=birth['start_time_ticks'], boot_id=birth['boot_id']),
                root=str(repo), state='working' if name == 'working' else 'ready', fresh=True)
        return result

    if mode == 'create':
        assert codex_wake.__version__ == '0.22.0.dev5'
        assert not path.exists()
        contexts = []
        for lost in (False, True):
            root = base / ('legacy-lost' if lost else 'legacy-transfer')
            root.mkdir(mode=0o700)
            tabs = ControllerTabs(root, workspaces={}, host='fixture', environment='fixture')
            source = tabs.execute('tabs.session.create', dict(name='source', start=True))['session']
            tabs.execute('tabs.session.create', dict(name='peer', start=True))
            sock = root / 'terminal-sessions/tmux.sock'
            owner = TerminalRelocation(root, tabs=tabs)
            plan = owner.execute('tabs.relocate.preview', dict(session='source', destination='peer'))
            wid = plan['outcomes'][0]['birth']['window_id']
            before = tmux(sock, 'list-panes', '-s', '-t', 'source', '-F', '#{pane_id}:#{pane_pid}')
            if lost:
                transport = tabs.workspaces[source['workspace']]['transport']
                original = transport.command
                def interrupted(deadline, *args):
                    result = original(deadline, *args)
                    if args[0] == 'move-window':
                        raise KeyboardInterrupt('owned lost-reply fixture')
                    return result
                transport.command = interrupted
                try:
                    owner.execute('tabs.relocate.apply', dict(plan_id=plan['plan_id']))
                except KeyboardInterrupt:
                    pass
                else:
                    raise AssertionError('lost-reply fixture did not interrupt')
            tmux(sock, 'select-pane', '-t', wid, '-T', 'new observation metadata')
            contexts.append(dict(kind='lost' if lost else 'transfer', root=str(root),
                                 socket=str(sock), plan=plan['plan_id'], window=wid, before=before))
            path.write_text(json.dumps(contexts))
        root = base / 'legacy-order'
        root.mkdir(mode=0o700)
        sock = root / 'tmux.sock'
        tmux(sock, 'new-session', '-d', '-s', 'fixture', '-n', 'focused', 'sleep 600')
        for name in ('ready', 'working'):
            tmux(sock, 'new-window', '-d', '-t', 'fixture', '-n', name, 'sleep 600')
        repo = root / 'repo'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        session = tmux(sock, 'display-message', '-p', '#{session_id}')
        order = TabOrganization(root / 'wake', transport=TmuxTransport(sock, session),
            observer=lambda timeout: observations(sock, repo), authorize=lambda action: None)
        plan = order.preview(deadline=time.monotonic()+5)['plan']
        tmux(sock, 'select-pane', '-t', '@1', '-T', 'new observation metadata')
        contexts.append(dict(kind='order', root=str(root), socket=str(sock),
                             repo=str(repo), session=session, plan=plan['plan_id']))
        path.write_text(json.dumps(contexts))
        print(json.dumps(dict(created=len(contexts), version=codex_wake.__version__)))
        return

    if mode == 'cleanup':
        sockets=[base/name/'terminal-sessions/tmux.sock' for name in ('legacy-transfer','legacy-lost')]
        sockets.append(base/'legacy-order/tmux.sock')
        for sock in sockets:
            subprocess.run(['tmux', '-S', str(sock), 'kill-server'], capture_output=True)
        return
    contexts = json.loads(path.read_text())
    assert mode == 'check' and codex_wake.__version__ == '0.22.0.dev6'
    checks = []
    for case in contexts:
        root, sock = Path(case['root']), Path(case['socket'])
        if case['kind'] == 'order':
            order = TabOrganization(root / 'wake', transport=TmuxTransport(sock, case['session']),
                observer=lambda timeout: observations(sock, Path(case['repo'])), authorize=lambda action: None)
            moved = order.apply(case['plan'], deadline=time.monotonic()+5)
            assert moved['status'] == 'applied', moved
            tmux(sock, 'select-pane', '-t', '@2', '-T', 'new metadata before undo')
            assert order.undo(moved['receipt']['receipt_id'], deadline=time.monotonic()+5)['status'] == 'undone'
            assert tmux(sock, 'list-windows', '-F', '#{window_name}').splitlines() == ['focused', 'ready', 'working']
            checks.append('old raw-fingerprint order plan apply and undo')
        else:
            tabs = ControllerTabs(root, workspaces={}, host='fixture', environment='fixture')
            owner = TerminalRelocation(root, tabs=tabs)
            operation = 'status' if case['kind'] == 'lost' else 'apply'
            moved = owner.execute('tabs.relocate.'+operation, dict(plan_id=case['plan']))
            assert moved['status'] == 'completed' and moved['outcomes'][0]['status'] == 'moved', moved
            replay = owner.execute('tabs.relocate.apply', dict(plan_id=case['plan']))
            assert replay['receipt_id'] == moved['receipt_id']
            tmux(sock, 'select-pane', '-t', case['window'], '-T', 'new metadata before undo')
            undone = owner.execute('tabs.relocate.undo', dict(receipt_id=moved['receipt_id']))
            assert undone['outcomes'][0]['status'] == 'undone', undone
            assert tmux(sock, 'list-panes', '-s', '-t', 'source', '-F', '#{pane_id}:#{pane_pid}') == case['before']
            checks.append('old full-pane '+case['kind']+' receipt reconcile/apply/undo')
    report = dict(status='PASS', old_version='0.22.0.dev5', new_version=codex_wake.__version__,
                  package=codex_wake.__file__, checks=checks, production_effects=False)
    (base / 'legacy-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
