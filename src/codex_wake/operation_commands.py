"""CLI/native-MCP operations adapter over explicit host caller mappings."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from .controller_auth import Actor
from .controller_job_adapter import ControllerEffects
from .controller_mailbox import ControllerMailbox
from .controller_runtime import ControllerRuntime
from .managed_inventory import InventoryError


def owner(root):
    if root is None: raise InventoryError('host_wake_root_required', 'host Wake root required')
    return ControllerRuntime(Path(root), adapter=ControllerEffects(Path(root)))


def local_actor(root):
    config = ControllerMailbox(root).config()
    value = config.get('local_caller')
    if not isinstance(value, dict): raise InventoryError('unauthorized_target', 'explicit host-approved local caller binding required')
    return Actor(value['subject'], 'service', value['client_id'], value['grant_id'],
        value['issuer'], value['resource'], frozenset(value['scopes']), value['targets'], value['expires_at'])


def execute(operation, arguments, root, *, actor=None, authorize=None):
    if actor is None:
        actor = local_actor(root)
        authorize = lambda: local_actor(root)
    if authorize is None: raise InventoryError('unauthorized_target', 'current caller authentication callback required')
    return owner(root).operation(actor, operation, arguments, authorize=authorize)


def register_parser(subparsers):
    parser = subparsers.add_parser('operations', help='send, await and retrieve durable correlated operation answers')
    commands = parser.add_subparsers(dest='operation_verb', required=True)
    for verb in ('send', 'result', 'wait', 'stream', 'cancel', 'rebind'):
        command = commands.add_parser(verb)
        command.add_argument('--json', dest='as_json', action='store_true')
        if verb == 'send':
            command.add_argument('--request', type=json.loads, required=True)
            command.add_argument('--sender-binding', required=True)
            command.add_argument('--backend', choices=['mailbox', 'job'], default='mailbox')
            command.add_argument('--body-file', type=Path)
            command.add_argument('--job-profile')
            command.add_argument('--delivery', choices=['inbox', 'notify'], default='notify')
            command.add_argument('--queue', action='store_true')
            command.add_argument('--ttl', type=float, default=86400)
            command.add_argument('--no-wait', action='store_true')
            command.add_argument('--timeout', type=float, default=30)
        else:
            command.add_argument('operation_id')
            if verb in ('wait', 'stream'): command.add_argument('--timeout', type=float, default=30 if verb == 'wait' else 0)
            if verb == 'stream':
                command.add_argument('--cursor', type=int, default=0); command.add_argument('--limit', type=int, default=100)
            if verb == 'rebind':
                command.add_argument('--successor', type=json.loads, required=True)
                command.add_argument('--binding', required=True)


def command(args, root=None):
    operation = 'operations.' + args.operation_verb
    try:
        root = root or args.wake_root
        if args.operation_verb == 'send':
            arguments = dict(_request=args.request, sender_binding=args.sender_binding, expected_target=args.request.get('target'),
                backend=args.backend, response_requested=not args.no_wait, wait_timeout=args.timeout)
            if args.backend == 'mailbox':
                if args.body_file is None: raise InventoryError('invalid_argument', 'explicit UTF8 body file required')
                arguments.update(body=args.body_file.read_text(), delivery=args.delivery, queue=args.queue, ttl=args.ttl)
            else: arguments['job_profile'] = args.job_profile
        else:
            arguments = {'operation_id': args.operation_id}
            if args.operation_verb in ('wait', 'stream'): arguments['timeout'] = args.timeout
            if args.operation_verb == 'stream': arguments.update(cursor=args.cursor, limit=args.limit)
            if args.operation_verb == 'rebind': arguments.update(successor=args.successor, binding=args.binding)
        value = execute(operation, arguments, root)
        record = value['result']['operation']
        print(json.dumps(dict(event='operation_status', operation_id=record['operation_id'], correlation_id=record['correlation_id'],
            execution=record['execution'], wait=value['result'].get('wait')), sort_keys=True), file=sys.stderr)
        if not args.as_json and args.operation_verb != 'stream' and record.get('answer'):
            print(record['answer']['text'], end='' if record['answer']['text'].endswith('\n') else '\n')
        else: print(json.dumps(value, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps(dict(schema_version=1, operation=operation, status='failed', error=dict(code=getattr(error, 'code', 'invalid_argument'), message=str(error))), sort_keys=True))
        return 2


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--wake-root', type=Path, required=True)
    register_parser(parser.add_subparsers(dest='command', required=True))
    return command(parser.parse_args(argv))


def mcp_call(runner, verb, arguments, native_context):
    """Pin native sends to private transport metadata, never model identity claims.

    CLI/OAuth service clients may select explicit host-approved bindings. Native
    MCP callers additionally prove the selected sender is their invoking session.
    The existing verifier owns the native metadata trust boundary.
    """
    operation = verb if verb.startswith('operations.') else 'operations.' + verb
    root = runner.wake_root
    if operation == 'operations.send':
        from .goal_supervision import verified_native_caller
        config = ControllerMailbox(root).config()
        key = arguments.get('sender_binding')
        if not isinstance(key, str): raise InventoryError('native_caller_unverified', 'host native sender binding required')
        if arguments.get('backend', 'mailbox') == 'job':
            mapping = config.get('job_bindings', {}).get(key, {})
            claimed = mapping.get('native_thread_id', mapping.get('native_subject'))
        else:
            mapping = config.get('bindings', {}).get(key, {})
            claimed = mapping.get('identity', {}).get('thread_id')
        try: verified_native_caller(native_context, claimed)
        except ValueError: raise InventoryError('native_caller_unverified', 'selected sender differs from verified invoking native session') from None
    return execute(operation, arguments, root)


if __name__ == '__main__': raise SystemExit(main())
