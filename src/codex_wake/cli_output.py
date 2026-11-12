"""Human presentation for CLI results; service envelopes remain machine contracts."""
from __future__ import annotations

import json
import sys


# Exact generation pins remain available in explicit JSON rather than obscuring
# the information an operator needs to choose or inspect a resource.
_INTERNAL = {'schema_version', 'target', 'expected_target', 'configuration_revision',
             'home_generation', 'store_id'}


def _text(value):
    if value is None:
        return '—'
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    # Keep data from injecting terminal controls or breaking table rows.
    return ''.join(char if char.isprintable() else ' ' for char in str(value))


def _label(key):
    return _text(key).replace('_', ' ').capitalize()


def _table(headers, rows):
    rows = [[_text(cell) for cell in row] for row in rows]
    widths = [max(len(header), *(len(row[i]) for row in rows))
              for i, header in enumerate(headers)]
    return '\n'.join('  '.join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip()
                     for row in [headers, *rows])


def _details(value, indent=0):
    prefix = ' ' * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if key in _INTERNAL or (key == 'owner' and item == 'codex-wake'):
                continue
            label = _label(key)
            if (isinstance(item, (dict, list)) and item) or (isinstance(item, str) and '\n' in item):
                lines.append(prefix + label + ':')
                lines.append(_details(item, indent + 2))
            else:
                lines.append(prefix + label + ': ' + ('none' if item == [] or item == {} else _text(item)))
        return '\n'.join(lines)
    if isinstance(value, list):
        if not value:
            return prefix + 'None.'
        if all(isinstance(row, dict) for row in value):
            keys = list(dict.fromkeys(key for row in value for key, item in row.items()
                                     if key not in _INTERNAL and not isinstance(item, (dict, list))
                                     and not (isinstance(item, str) and '\n' in item)))
            preferred = ('id', 'name', 'account', 'host', 'environment', 'status', 'state', 'channel')
            keys = [key for key in preferred if key in keys] + [key for key in keys if key not in preferred]
            if keys:
                table = '\n'.join(prefix + line for line in _table(
                    [_text(key).upper().replace('_', ' ') for key in keys],
                    [[row.get(key) for key in keys] for row in value]).splitlines())
                details = []
                for index, row in enumerate(value, 1):
                    nested = {key: item for key, item in row.items()
                              if key not in keys and key not in _INTERNAL}
                    detail = _details(nested, indent + 2)
                    if detail:
                        title = row.get('id', row.get('name', f'Item {index}'))
                        details.append(prefix + _text(title) + ':\n' + detail)
                return '\n'.join([table, *details])
        return '\n'.join(prefix + '- ' + _details(item).replace('\n', '\n' + prefix + '  ') for item in value)
    return '\n'.join(prefix + _text(line) for line in value.split('\n')) if isinstance(value, str) else prefix + _text(value)


def emit(value, args, *, file=None):
    """Print a result using explicit machine output or readable terminal text."""
    stream = sys.stdout if file is None else file
    if getattr(args, 'as_json', False) or getattr(args, 'json', False) or getattr(args, 'output', None) == 'json':
        print(json.dumps(value, sort_keys=True), file=stream)
        return
    result=value.get('result')
    retained=result.get('operation') if isinstance(result,dict) else None
    if not value.get('error') and isinstance(retained,dict) and str(retained.get('operation','')).startswith('tabs.'):
        import shlex
        outcome=retained.get('result')
        outcome=outcome if isinstance(outcome,dict) else {}
        status=('uncertain' if retained.get('phase')=='uncertain' else
                outcome.get('status') or retained.get('execution') or retained.get('phase') or 'unknown')
        print(_text(retained['operation'])+': '+_text(status),file=stream)
        if outcome.get('message'):
            print(_text(outcome['message']),file=stream)
        reason=outcome.get('reason') or retained.get('reason')
        if reason:
            print('Reason: '+_text(reason),file=stream)
        if status=='uncertain':
            print('The effect is unknown. Inspect the retained result before retrying.',file=stream)
        if retained['operation'].startswith('tabs.monitor.'):
            print('Inspect current monitor state with codex-wake tabs monitor-status --json.',file=stream)
        detail=_details({key:item for key,item in outcome.items()
                         if key not in ('status','message','next_action','reason') and item not in ([],{})
                         and not (key=='policy' and status=='disabled')})
        if detail:print(detail,file=stream)
        if outcome.get('next_action'):
            prefix='codex-wake'
            if getattr(args,'wake_root',None):
                prefix+=' --wake-root '+shlex.quote(str(args.wake_root))
            action=outcome['next_action']
            if action.startswith('codex-wake '):action=prefix+action[len('codex-wake'):]
            print('Next: '+_text(action),file=stream)
            if status=='disabled':
                print('Then run the formatting command again; use a new request ID if supplying one.',file=stream)
        identifier=retained.get('operation_id','')
        print('Operation id: '+_text(identifier),file=stream)
        if identifier.startswith('tab-cli-'):
            command=['codex-wake']
            if getattr(args,'wake_root',None):command+=['--wake-root',str(args.wake_root)]
            command+=['tabs','result','--request-id',identifier[len('tab-cli-'):],'--json']
            print('Details: '+_text(shlex.join(command)),file=stream)
        return
    error = value.get('error')
    if error:
        print('Error: ' + _text(error.get('message', error.get('code', 'Command failed'))), file=stream)
        if error.get('code'):
            print('Reason: ' + _text(error['code']), file=stream)
        details = {key: item for key, item in error.items() if key not in ('message', 'code')}
        if details:
            print(_details(details), file=stream)
        if value.get('details'):
            print(_details(value['details']), file=stream)
        return
    result = value.get('result', value)
    if value.get('operation') == 'accounts.list' and 'accounts' in result:
        rows = result['accounts']
        if not rows:
            print('No accounts found.', file=stream)
            return
        print(_table(['ACCOUNT', 'ALIASES', 'HOME'],
              [[row['id'], ', '.join(row.get('aliases', [])) or '—', row.get('home')]
               for row in rows]), file=stream)
        return
    # Successful commands with no payload still need an explicit acknowledgement.
    text = _details(result)
    if not text:
        text = _label(value.get('status', 'completed')) + '.'
    print(text, file=stream)
