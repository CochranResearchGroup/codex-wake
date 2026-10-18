"""OS-only acceptance helpers; no provider calls, signal effects, or product imports."""
import json
from pathlib import Path
import subprocess


def unit_snapshot(unit):
    raw = subprocess.check_output(['systemctl', '--user', 'show', unit,
        '-p', 'MainPID', '-p', 'ControlGroup', '-p', 'ActiveState', '-p', 'SubState',
        '-p', 'Result', '-p', 'KillMode', '-p', 'RuntimeMaxUSec', '-p', 'MemoryMax',
        '-p', 'MemorySwapMax', '-p', 'TasksMax', '-p', 'CPUQuotaPerSecUSec'], text=True)
    props = dict(line.split('=', 1) for line in raw.splitlines())
    cgroup = props.get('ControlGroup', '')
    processes = {}
    if cgroup:
        for cgfile in (Path('/sys/fs/cgroup') / cgroup.lstrip('/')).rglob('cgroup.procs'):
            for item in cgfile.read_text().split():
                proc = Path('/proc') / item
                try:
                    processes[item] = {
                        'comm': (proc / 'comm').read_text().strip(),
                        'cgroup': (proc / 'cgroup').read_text().strip(),
                        'state': (proc / 'stat').read_text().split()[2],
                        'ppid': next(line.split(':', 1)[1].strip()
                            for line in (proc / 'status').read_text().splitlines()
                            if line.startswith('PPid:')),
                    }
                except FileNotFoundError:
                    pass
    return {'properties': props, 'processes': processes}


def assert_native_membership(unit, child_path):
    child = json.loads(Path(child_path).read_text())
    snapshot = unit_snapshot(unit)
    cg = snapshot['properties']['ControlGroup']
    assert cg, 'owned service has no cgroup'
    assert str(child['pid']) in snapshot['processes'], 'actual tool child outside cgroup'
    assert cg in child['cgroup'], 'worker and host cgroup observations disagree'
    assert any(p['comm'] == 'codex' for p in snapshot['processes'].values()), 'no native Codex executor'
    assert any(p['comm'] in ('zsh', 'bash', 'sh') for p in snapshot['processes'].values()), 'no actual tool shell'
    return {'child': child, 'unit': snapshot}


def remaining_live(pids):
    output = []
    for pid in pids:
        try:
            if (Path('/proc') / str(pid) / 'stat').read_text().split()[2] != 'Z':
                output.append(int(pid))
        except FileNotFoundError:
            pass
    return output


def native_token_usage(home):
    snapshots = []
    for source in (Path(home) / 'sessions').rglob('*.jsonl'):
        for line in source.read_text().splitlines():
            row = json.loads(line)
            payload = row.get('payload', {})
            if payload.get('type') == 'token_count':
                usage = payload.get('info', {}).get('total_token_usage')
                if usage:
                    snapshots.append({'source': str(source), 'usage': usage})
    return snapshots
