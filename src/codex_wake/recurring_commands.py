"""Operator CLI for explicit recurring schedules."""
import json
from pathlib import Path
from .records import WakeError
from .recurring_schedules import ScheduleStore


def register_parser(subparsers):
    group = subparsers.add_parser('schedules', help='explicit durable recurring schedules')
    verbs = group.add_subparsers(dest='schedule_command', required=True)
    p = verbs.add_parser('register')
    p.add_argument('--request', type=Path, required=True)
    p.add_argument('--codex-path', default='codex')
    p.add_argument('--endpoint', default='unix://')
    p = verbs.add_parser('show'); p.add_argument('schedule_id')
    verbs.add_parser('list')


def command(args, root):
    store = ScheduleStore(root)
    principal = getattr(args, '_permission_principal', None)
    if args.schedule_command == 'register':
        if args.request.stat().st_size > 65536:
            raise WakeError('schedule_request_too_large')
        request = json.loads(args.request.read_text())
        value = store.register(request, codex_path=args.codex_path, endpoint=args.endpoint, principal=principal)
    elif args.schedule_command == 'show':
        value = store.read(args.schedule_id)
        store.authorize(value, principal)
        value = store.receipt(value)
    else:
        values = []
        for item in store.records():
            try:
                store.authorize(item, principal)
                values.append(store.receipt(item))
            except WakeError:
                continue
        value = values
    print(json.dumps(value, sort_keys=True))
    return 0
