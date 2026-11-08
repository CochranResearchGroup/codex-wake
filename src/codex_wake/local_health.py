"""Same-user local session health observation, without action capabilities.

Discovery owns selection and endpoint provenance; native loop evidence owns
health. A discovered live daemon alone never establishes a responsive TUI.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
from websockets.exceptions import WebSocketException
from .controller_health import ControllerHealth, _TARGET_FIELDS
from .managed_inventory import InventoryError
from .records import WakeError
from .native_protocol import native_request, NativeCapabilityUnavailable
from .controller_health import _image_hash

INPUT_SCHEMA = {'type': 'object', 'properties': {
    'selector': {'type': 'string', 'minLength': 1, 'maxLength': 4096},
    'expected_target': {'type': 'object'},
    'endpoint': {'type': 'string'},
    'timeout': {'type': 'number', 'minimum': .05, 'maximum': 5}},
    'required': ['selector'], 'additionalProperties': False}


def observe(root, selector, *, expected_target=None, timeout=1, endpoint='unix://'):
    """Resolve one pinned local session and freshly challenge its controlling TUI."""
    from .local_sessions import resolve
    if type(timeout) not in (int, float) or not .05 <= timeout <= 5:
        raise InventoryError('invalid_argument', 'timeout must be 0.05..5 seconds')
    row = resolve(root, selector, expected_target=expected_target, endpoint=endpoint)
    return observe_row(root, row, timeout=timeout)


def observe_row(root, row, *, timeout=1, request=native_request, client_process=None):
    """Observe a resolved same-user row; daemon identity is never TUI identity."""
    target = row['target']
    def unknown(reason, status='unknown'):
        return dict(target=target, observation=dict(status=status, responsive=False,
            evidence='none', observed_at=time.time(), reason=reason),
            grants_recovery=False, application_effects=False)
    if type(timeout) not in (int, float) or not .05 <= timeout <= 5:
        raise InventoryError('invalid_argument', 'timeout must be 0.05..5 seconds')
    process = target.get('process')
    if isinstance(process, dict) and type(process.get('pid')) is int and process['pid'] > 0:
        try:
            (Path('/proc') / str(process['pid'])).stat()
        except FileNotFoundError:
            return unknown('pinned_runtime_process_gone', 'offline')
        except OSError:
            return unknown('pinned_runtime_process_unobservable')
    deadline = time.monotonic() + timeout
    endpoint, command = row.get('endpoint'), row.get('codex_cmd')
    if not isinstance(endpoint, str) or not endpoint.startswith('unix:///'):
        return unknown('existing_local_endpoint_required')
    if not isinstance(command, list) or not command or any(not isinstance(item, str) for item in command):
        return unknown('native_command_unavailable')
    try:
        executable = Path(target['executable']).stat()
        if client_process is not None:
            from .process import process_identity
            if not isinstance(client_process,dict) or type(client_process.get('pid')) is not int:
                return unknown('exact_client_process_required')
            current=process_identity(client_process['pid'])
            if (current is None or str(current['start_time_ticks'])!=str(client_process.get('start_ticks'))
                    or current.get('boot_id')!=client_process.get('boot_id')):
                return unknown('exact_client_process_changed')
        preferred = [item.get('client_pid') for item in row.get('attachments', []) if isinstance(item, dict)]
        pids = ([client_process['pid']] if client_process is not None else
                list(dict.fromkeys(preferred + [int(item.name) for item in Path('/proc').iterdir() if item.name.isdigit()])))
        candidates = []
        for pid in pids:
            if type(pid) is not int or pid <= 0: continue
            if time.monotonic() >= deadline: return unknown('discovery_deadline')
            try:
                proc = Path('/proc') / str(pid)
                if proc.stat().st_uid != os.geteuid(): continue
                image = (proc / 'exe').stat()
                if (image.st_dev, image.st_ino) != (executable.st_dev, executable.st_ino): continue
                if _image_hash(pid) != target['build_sha256']: continue
                candidates.append(pid)
            except OSError: continue
            if len(candidates) >= 256: break
        last = None
        for pid in candidates:
            remaining = deadline - time.monotonic()
            if remaining < .05: return unknown('discovery_deadline')
            frame = request(endpoint, command, 'tui/health/describe', {'pid': pid}, remaining)
            bindings = frame.get('bindings') if isinstance(frame, dict) else None
            if not isinstance(bindings, list) or len(bindings) > 256: return unknown('invalid_native_description')
            for binding in bindings:
                if not isinstance(binding, dict) or binding.get('pid') != pid: continue
                if client_process is not None and (str(binding.get('startTicks'))!=str(client_process['start_ticks']) or binding.get('bootId')!=client_process['boot_id']):continue
                if binding.get('home') != target['home'] or binding.get('provider') != row.get('model_provider', target['provider']): continue
                try:
                    native = dict(host=target['host'], environment=target['environment'], runtime='codex',
                        namespace='codex:' + hashlib.sha256(json.dumps([str(Path(binding['home']).resolve()), binding['provider']], separators=(',', ':')).encode()).hexdigest(),
                        build_sha256=target['build_sha256'], conversation_id=target['conversation_id'],
                        home=binding['home'], provider=binding['provider'], backend_id=binding['backendId'],
                        channel=binding['channel'], connection_generation=binding['connectionGeneration'],
                        process=dict(pid=pid, start_ticks=binding['startTicks'], boot_id=binding['bootId']))
                    remaining = deadline - time.monotonic()
                    if remaining < .05: return unknown('discovery_deadline')
                    def probe(endpoint, command, method, arguments, budget):
                        # Leave transport headroom to receive the native deadline verdict.
                        arguments = dict(arguments, timeoutMs=max(50, int((budget - .05) * 1000)))
                        return request(endpoint, command, method, arguments, budget)
                    last = ControllerHealth(root, request=probe).observe_binding(native,
                        dict(target=native, endpoint=endpoint, codex_cmd=command), timeout=min(5, remaining))
                    if last['observation']['responsive']: return last
                except KeyError: return unknown('incomplete_native_description')
        return last or unknown('exact_controlling_tui_unavailable')
    except NativeCapabilityUnavailable: return unknown('native_health_capability_unavailable', 'unsupported')
    except (WakeError, OSError, ValueError, TypeError, TimeoutError, WebSocketException): return unknown('native_loop_unobserved')


def execute(operation, arguments, root):
    try:
        if operation not in ('local.health', 'local.health.observe'):
            raise InventoryError('unsupported_operation', 'unsupported local health operation')
        if not isinstance(arguments, dict) or set(arguments) - set(INPUT_SCHEMA['properties']):
            raise InventoryError('invalid_argument', 'local health requires one session selector')
        selector = arguments.get('selector')
        if not isinstance(selector, str) or not selector or len(selector) > 4096:
            raise InventoryError('invalid_argument', 'bounded session selector required')
        result = observe(root, selector, expected_target=arguments.get('expected_target'), timeout=arguments.get('timeout', 1), endpoint=arguments.get('endpoint', 'unix://'))
        return dict(schema_version=1, operation=operation, status='completed', result=result)
    except (WakeError, ValueError, OSError, TypeError, KeyError) as error:
        return dict(schema_version=1, operation=operation, status='failed',
            error=dict(code=getattr(error, 'code', 'invalid_argument'), message=str(error)))


def register_parser(subparsers):
    parser = subparsers.add_parser('health', help='fresh read-only health of one local controlling TUI')
    from .local_control_routing import parser_options
    parser_options(parser)
    parser.add_argument('selector')
    parser.add_argument('--expected-target', type=json.loads)
    parser.add_argument('--timeout', type=float, default=1)
    parser.add_argument('--endpoint', default='unix://')
    parser.add_argument('--json', dest='as_json', action='store_true')
    return parser


def command(args, root=None):
    from .local_control_service import LocalOperations
    values=dict(selector=args.selector,expected_target=args.expected_target,timeout=args.timeout,endpoint=args.endpoint,harness=args.harness,profile=args.profile)
    value = LocalOperations(root or args.wake_root).execute('local.health',{key:value for key,value in values.items() if value is not None})
    print(json.dumps(value, sort_keys=True))
    return 0 if value['status'] == 'completed' else 2


def tool_specs():
    return {'wake_local_health': ('local', 'health',
        'Read-only same-user exact controlling TUI health; observation grants no action authority.',
        INPUT_SCHEMA['properties'], INPUT_SCHEMA['required'], True)}
