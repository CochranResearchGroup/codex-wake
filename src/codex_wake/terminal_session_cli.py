"""Human presentation and terminal-only selection over the portable session API."""
import os
import sys

from .managed_inventory import InventoryError


def sessions(owner):
    return owner.execute('tabs.session.list', {})['sessions']


def select_workspace(owner, selector=None, *, server=None, interactive=False):
    records = sessions(owner)
    if selector is not None:
        matches = [r for r in records if selector in (r['id'], r['name'], r.get('workspace'))
                   and (server is None or r['server'] == server)]
    else:
        context = os.environ.get('TMUX', '').rsplit(',', 2)
        matches = []
        if len(context) == 3:
            matches = [r for r in records if r['server'] == context[0]
                       and (r.get('snapshot') or {}).get('session_id') == '$' + context[2]]
        if not matches:
            matches = [r for r in records if r.get('workspace')]
    if len(matches) != 1 and matches and interactive and sys.stdin.isatty() and sys.stderr.isatty():
        for n, record in enumerate(matches, 1):
            print(f"{n}. {record['name']} ({record['backend']}, {record['server']})", file=sys.stderr)
        print('Session number: ', end='', file=sys.stderr, flush=True)
        answer = sys.stdin.readline().strip()
        if answer.isdigit() and 1 <= int(answer) <= len(matches):
            matches = [matches[int(answer)-1]]
    if len(matches) != 1 or not matches[0].get('workspace'):
        error = InventoryError('ambiguous_target' if len(matches)>1 else 'target_not_found',
                               'Select a running terminal session with --session NAME and --server when needed.')
        error.candidates = [{k:r.get(k) for k in ('id','name','server','backend','state')} for r in matches or records]
        raise error
    return matches[0]['workspace']


def render(value):
    """Render successful session records, including journal-wrapped mutation results."""
    current = value
    for _ in range(5):
        if not isinstance(current, dict): return None
        if 'sessions' in current or 'session' in current: break
        if isinstance(current.get('result'), dict): current = current['result']
        elif isinstance(current.get('operation'), dict): current = current['operation']
        else: return None
    records = current.get('sessions', [current['session']] if 'session' in current else [])
    rows = [('NAME','BACKEND','SERVER','STATE','TABS','HEALTH / ACTIVITY')]
    for r in records:
        rows.append((r['name'],r['backend'],str(r.get('server','?')),r.get('state','unknown'),str(r.get('tab_count') if r.get('tab_count') is not None else '?'),
                     str(r.get('health_summary') or r.get('activity_summary') or 'unobserved')))
    widths = [max(len(row[i]) for row in rows) for i in range(6)]
    return '\n'.join('  '.join(cell.ljust(widths[i]) for i,cell in enumerate(row)).rstrip() for row in rows)
