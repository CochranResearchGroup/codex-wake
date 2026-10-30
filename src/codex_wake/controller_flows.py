"""Versioned structured flow definitions and durable host-owned run state.

Definitions are data. Invocation and current authorization are trusted host seams;
flow definitions cannot supply Python code, caller identity or new authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time

from .a2a_bus import private_path
from .controller_runtime import ControllerRuntime, encoded, identity
from .managed_inventory import InventoryError

_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')


def flow_error(code, message):
    raise InventoryError(code, message)


def name(value):
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        flow_error('invalid_argument', 'flow and node IDs must be bounded names')
    return value


@dataclass(frozen=True)
class FlowDefinition:
    document: str
    digest: str

    @classmethod
    def compile(cls, definition):
        if isinstance(definition, cls):
            definition = definition.as_dict()
        if not isinstance(definition, dict) or set(definition) - {'id', 'version', 'entry', 'nodes', 'limits'}:
            flow_error('invalid_flow', 'versioned structured definition required')
        name(definition.get('id'))
        if type(definition.get('version')) is not int or definition['version'] < 1:
            flow_error('invalid_flow', 'positive integer flow version required')
        nodes = definition.get('nodes')
        if not isinstance(nodes, list) or not 1 <= len(nodes) <= 64:
            flow_error('invalid_flow', 'flow requires between one and 64 nodes')
        by_id = {}
        for node in nodes:
            if not isinstance(node, dict):
                flow_error('invalid_flow', 'node must be a structured object')
            identifier = name(node.get('id'))
            if identifier in by_id:
                flow_error('invalid_flow', 'node IDs must be unique')
            kind = node.get('type')
            fields = {
                'call': {'id', 'type', 'operation', 'arguments', 'next'},
                'branch': {'id', 'type', 'condition', 'then', 'else', 'unknown'},
                'wait': {'id', 'type', 'operation_id', 'timeout', 'next', 'operation'},
                'foreach': {'id', 'type', 'items', 'mode', 'profile', 'expected_target', 'prompt', 'parallelism', 'join', 'next'},
                'end': {'id', 'type', 'value'},
            }
            if kind not in fields or set(node) - fields[kind]:
                flow_error('unsupported_flow_node', 'node type or fields are unsupported')
            if kind == 'foreach':
                from .controller_flow_foreach import validate
                validate(node)
            if kind == 'call' and (not isinstance(node.get('operation'), str) or not isinstance(node.get('arguments', {}), dict)):
                flow_error('invalid_flow', 'call requires an operation and object arguments')
            if kind == 'branch' and not {'condition', 'then', 'else'} <= node.keys():
                flow_error('invalid_flow', 'branch requires typed condition and explicit paths')
            if kind == 'branch':
                condition = node['condition']
                if type(condition) is not bool and (not isinstance(condition, dict)
                        or set(condition) != {'op', 'left', 'right'}
                        or condition['op'] not in ('eq', 'ne', 'lt', 'lte', 'gt', 'gte')):
                    flow_error('invalid_condition', 'supported typed deterministic condition required')
            if kind == 'wait' and (type(node.get('timeout', 0)) not in (int, float) or not 0 <= node.get('timeout', 0) <= 30):
                flow_error('invalid_flow', 'wait timeout must be between zero and 30 seconds')
            by_id[identifier] = node
        entry = definition.get('entry')
        if entry not in by_id:
            flow_error('invalid_flow', 'entry must name a node')
        visited, active = set(), set()
        def visit(identifier):
            if identifier is None:
                return
            if identifier not in by_id:
                flow_error('invalid_flow', 'flow references a missing node')
            if identifier in active:
                flow_error('invalid_flow', 'unbounded cycles are unsupported')
            if identifier in visited:
                return
            active.add(identifier)
            node = by_id[identifier]
            paths = ('then', 'else', 'unknown') if node['type'] == 'branch' else ('next',)
            for path in paths:
                visit(node.get(path))
            active.remove(identifier)
            visited.add(identifier)
        for identifier in by_id:
            visit(identifier)
        if not isinstance(definition.get('limits', {}), dict):
            flow_error('invalid_flow', 'limits must be an explicit object')
        try:
            document = encoded(definition)
        except (ValueError, TypeError):
            flow_error('invalid_flow', 'definition must contain finite JSON data')
        if len(document.encode()) > 262144:
            flow_error('invalid_flow', 'definition exceeds its bounded size')
        return cls(document, hashlib.sha256(document.encode()).hexdigest())

    def as_dict(self):
        return json.loads(self.document)


class ControllerFlows:
    def __init__(self, root, *, host, environment, invoke, authorize, now=time.time):
        self.root, self.host, self.environment = Path(root), host, environment
        self.invoke, self.authorize, self.now = invoke, authorize, now
        self.runtime = ControllerRuntime(self.root, now=now)
        directory = self.root / 'controller-flows'
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        private_path(directory, directory=True)
        self.path = directory / 'flows.sqlite'
        if self.path.exists() or self.path.is_symlink():
            private_path(self.path)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(descriptor)
        private_path(self.path)
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS definitions (
                flow_id TEXT, version INTEGER, digest TEXT, definition TEXT,
                PRIMARY KEY(flow_id,version));
                CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, intent TEXT UNIQUE, fingerprint TEXT, state TEXT);''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def target(self, flow_id):
        return dict(host=self.host, environment=self.environment, flow_id=name(flow_id))

    def check(self, actor, flow_id, capability):
        return self.runtime.check_authority(actor, self.target(flow_id), capability, authorize=self.authorize)

    def propose(self, actor, definition):
        compiled = FlowDefinition.compile(definition)
        value = compiled.as_dict()
        self.check(actor, value['id'], 'observe')
        return dict(definition=value, definition_sha256=compiled.digest, effects='none', executable=False)

    def publish(self, actor, definition):
        compiled = FlowDefinition.compile(definition)
        value = compiled.as_dict()
        self.check(actor, value['id'], 'control')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT digest FROM definitions WHERE flow_id=? AND version=?',
                (value['id'], value['version'])).fetchone()
            if previous and previous[0] != compiled.digest:
                flow_error('immutable_flow_version', 'published version cannot change; publish a new version')
            db.execute('INSERT OR IGNORE INTO definitions VALUES(?,?,?,?)',
                (value['id'], value['version'], compiled.digest, compiled.document))
        return dict(flow_id=value['id'], version=value['version'], definition_sha256=compiled.digest)

    def _definition(self, flow_id, version):
        with self.connect() as db:
            row = db.execute('SELECT definition,digest FROM definitions WHERE flow_id=? AND version=?',
                (name(flow_id), version)).fetchone()
        if row is None:
            flow_error('flow_version_not_found', 'published flow version is unavailable')
        compiled = FlowDefinition.compile(json.loads(row[0]))
        if compiled.digest != row[1]:
            flow_error('flow_store_invalid', 'definition revision changed')
        return compiled

    def definition(self, actor, flow_id, version):
        self.check(actor, flow_id, 'observe')
        compiled = self._definition(flow_id, version)
        return dict(definition=compiled.as_dict(), definition_sha256=compiled.digest)

    def _load(self, run_id, db=None):
        from .controller_runtime import bounded_id
        bounded_id(run_id)
        if db is None:
            with self.connect() as connection:
                return self._load(run_id, connection)
        row = db.execute('SELECT state FROM runs WHERE run_id=?', (run_id,)).fetchone()
        if row is None:
            flow_error('flow_run_not_found', 'flow run is unavailable')
        return json.loads(row[0])

    @staticmethod
    def _write(db, state):
        text = encoded(state)
        if len(text.encode()) > 4194304:
            flow_error('flow_store_limit', 'retained flow state exceeds its declared bound')
        db.execute('UPDATE runs SET state=? WHERE run_id=?', (text, state['run_id']))

    def _owned(self, actor, state, capability):
        from .controller_auth import AuthError
        self.check(actor, state['flow_id'], capability)
        if identity(actor) != state['owner']:
            raise AuthError('insufficient_scope')
        return state

    @staticmethod
    def projection(state):
        return {key: value for key, value in state.items() if key not in ('owner', 'attempt')}

    def inspect(self, actor, run_id):
        return self.projection(self._owned(actor, self._load(run_id), 'observe'))

    def start(self, actor, flow_id, version, *, inputs, intent, binding):
        from uuid import uuid4
        from .controller_runtime import bounded_id
        self.check(actor, flow_id, 'control')
        bounded_id(intent); bounded_id(binding)
        if not isinstance(inputs, dict) or len(encoded(inputs).encode()) > 65536:
            flow_error('invalid_argument', 'bounded object flow inputs required')
        compiled = self._definition(flow_id, version)
        definition = compiled.as_dict()
        if definition.get('limits'):
            flow_error('unsupported_flow_limits', 'qualified usage/limit owner is required before executing limited flows')
        fingerprint = hashlib.sha256(encoded(dict(definition=compiled.digest, inputs=inputs, binding=binding)).encode()).hexdigest()
        key = hashlib.sha256(encoded(dict(owner=identity(actor), intent=intent)).encode()).hexdigest()
        state = dict(schema_version=1, run_id='flowrun_' + uuid4().hex, flow_id=flow_id, version=version,
            definition_sha256=compiled.digest, target=self.target(flow_id), owner=identity(actor), inputs=inputs,
            binding=binding, created_at=self.now(), phase='ready', cursor=definition['entry'],
            steps={}, result=None, reason=None, cancellation=False, completed_steps=0)
        for node in definition['nodes']:
            if node['type'] == 'foreach':
                capabilities = self.invoke('sessions.capabilities',
                    dict(profile=node['profile'], expected_target=node['expected_target']),
                    authorize=lambda: self.check(actor, flow_id, 'control'))
                if node['mode'] not in capabilities.get('result', {}).get('modes', []):
                    flow_error('unsupported_session_mode', 'host cannot execute the requested foreach session mode')
        from .controller_flow_foreach import expand
        execution, memberships = expand(definition, state, self._resolve, _UNKNOWN)
        state.update(execution_definition=execution, memberships=memberships, cursor=execution['entry'])
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT fingerprint,state FROM runs WHERE intent=?', (key,)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    flow_error('idempotency_conflict', 'flow intent already names a different pinned definition or input')
                return self.projection(json.loads(previous[1]))
            if db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] >= 256:
                flow_error('flow_capacity', 'retained run capacity reached; no history was removed')
            db.execute('INSERT INTO runs VALUES(?,?,?,?)', (state['run_id'], key, fingerprint, encoded(state)))
        return self.projection(state)

    @staticmethod
    def _unknown_value(value):
        return isinstance(value, dict) and 'value' in value and (
            value.get('status') in ('unknown', 'unsupported', 'error', 'timeout')
            or ('observed_at' in value and value.get('value') in ('unknown', 'unsupported', 'unavailable', 'stale')))

    @staticmethod
    def _resolve(value, state):
        if isinstance(value, dict) and set(value) == {'ref'}:
            if not isinstance(value['ref'], str):
                flow_error('invalid_reference', 'reference must be a dotted context path')
            current = {'inputs': state['inputs'], 'steps': state['steps']}
            for key in value['ref'].split('.'):
                if key == 'value' and ControllerFlows._unknown_value(current):
                    return _UNKNOWN
                if not isinstance(current, dict) or key not in current:
                    return _UNKNOWN
                current = current[key]
            return current
        if isinstance(value, dict):
            result = {key: ControllerFlows._resolve(item, state) for key, item in value.items()}
            return _UNKNOWN if any(item is _UNKNOWN for item in result.values()) else result
        if isinstance(value, list):
            result = [ControllerFlows._resolve(item, state) for item in value]
            return _UNKNOWN if any(item is _UNKNOWN for item in result) else result
        return value

    def _condition(self, expression, state):
        if type(expression) is bool:
            return expression
        if not isinstance(expression, dict) or set(expression) != {'op', 'left', 'right'}:
            flow_error('invalid_condition', 'typed deterministic condition required')
        left, right = (self._resolve(expression[key], state) for key in ('left', 'right'))
        if self._unknown_value(left) or self._unknown_value(right):
            return None
        if left is _UNKNOWN or right is _UNKNOWN:
            return None
        operation = expression['op']
        if operation in ('eq', 'ne'):
            equal = type(left) is type(right) and left == right
            return equal if operation == 'eq' else not equal
        if operation not in ('lt', 'lte', 'gt', 'gte'):
            flow_error('invalid_condition', 'deterministic comparison is unsupported')
        if type(left) not in (int, float) or type(right) not in (int, float):
            return None
        return {'lt': left < right, 'lte': left <= right, 'gt': left > right, 'gte': left >= right}[operation]

    def _step_guard(self, actor, run_id, attempt=None):
        state = self._owned(actor, self._load(run_id), 'control')
        if attempt is not None and state.get('attempt') != attempt:
            flow_error('stale_flow_attempt', 'step ownership changed')
        if state['cancellation']:
            flow_error('flow_cancelled', 'flow cancellation prevents new steps')
        return actor

    def cancel(self, actor, run_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state = self._owned(actor, self._load(run_id, db), 'control')
            if state['phase'] in ('completed', 'cancelled'):
                return self.projection(state)
            active = state['phase'] in ('executing', 'uncertain', 'waiting')
            child_id = state.get('waiting_on') if state['phase'] == 'waiting' else state.get('child_operation_id')
            state.update(cancellation=True, phase='uncertain' if active else 'cancelled',
                reason='child_cancellation_requested' if active else 'caller_cancelled')
            self._write(db, state)
        if active and child_id:
            try:
                cancel_operation = 'sessions.cancel' if state.get('waiting_operation') == 'sessions.wait' else 'operations.cancel'
                value = self.invoke(cancel_operation, {'operation_id': child_id},
                    authorize=lambda: self._owned(actor, self._load(run_id), 'control') and actor)
                child = value.get('result', {}).get('operation', {})
                if child.get('cancellation') == 'confirmed':
                    with self.connect() as db:
                        db.execute('BEGIN IMMEDIATE')
                        state = self._owned(actor, self._load(run_id, db), 'control')
                        state.update(phase='cancelled', reason='child_cancellation_confirmed')
                        state.pop('attempt', None)
                        self._write(db, state)
            except Exception:
                # Cancellation cannot establish that an unknown effect stopped.
                pass
        return self.projection(state)

    def reconcile(self, actor, run_id):
        state = self._owned(actor, self._load(run_id), 'control')
        if state['phase'] not in ('executing', 'uncertain') or not state.get('child_operation_id'):
            return self.projection(state)
        attempt = state.get('attempt')
        value = self.invoke('operations.result', {'operation_id': state['child_operation_id']},
            authorize=lambda: self._step_guard(actor, run_id, attempt))
        child = value.get('result', {}).get('operation', {})
        if child.get('phase') != 'terminal' or child.get('execution') != 'completed':
            return self.projection(state)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            latest = self._owned(actor, self._load(run_id, db), 'control')
            if latest.get('attempt') != attempt or latest['phase'] not in ('executing', 'uncertain'):
                return self.projection(latest)
            definition = latest.get('execution_definition') or self._definition(latest['flow_id'], latest['version']).as_dict()
            node = next(item for item in definition['nodes'] if item['id'] == latest['cursor'])
            latest['steps'][node['id']] = value
            selected = node.get('next')
            latest.update(cursor=selected, phase='ready' if selected is not None else 'completed', reason=None)
            latest['completed_steps'] += 1
            latest.pop('attempt', None)
            latest.pop('executing_node', None)
            self._write(db, latest)
            return self.projection(latest)

    def advance(self, actor, run_id):
        from uuid import uuid4
        for unused in range(16):
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                state = self._owned(actor, self._load(run_id, db), 'control')
                if state['phase'] in ('completed', 'cancelled', 'failed', 'held', 'uncertain'):
                    return self.projection(state)
                if state['phase'] == 'executing':
                    # Never retry an effect merely because another caller resumed.
                    return self.projection(dict(state, reason='step_in_progress_or_interrupted'))
                if state['cancellation']:
                    state.update(phase='cancelled', reason='caller_cancelled')
                    self._write(db, state)
                    return self.projection(state)
                definition = self._definition(state['flow_id'], state['version']).as_dict()
                if state['definition_sha256'] != FlowDefinition.compile(definition).digest:
                    flow_error('flow_store_invalid', 'run definition pin changed')
                definition = state.get('execution_definition') or definition
                node = next(item for item in definition['nodes'] if item['id'] == state['cursor'])
                if node['type'] == 'branch':
                    value = self._condition(node['condition'], state)
                    state['steps'][node['id']] = dict(type='boolean', value=value, status='unknown' if value is None else 'known')
                    selected = node.get('unknown') if value is None else node['then'] if value else node['else']
                    if value is None and selected is None:
                        state.update(phase='held', reason='condition_unknown')
                    else:
                        state.update(cursor=selected, phase='ready' if selected is not None else 'completed')
                    state['completed_steps'] += 1
                    self._write(db, state)
                    continue
                if node['type'] == 'collect':
                    value = self._resolve(node['value'], state)
                    if value is _UNKNOWN:
                        state.update(phase='held', reason='output_unknown')
                    else:
                        statuses = [item['result'].get('execution','unknown') for item in value['items']]
                        value['status'] = 'completed' if all(status=='completed' for status in statuses) else 'failed' if all(status in ('completed','failed','cancelled') for status in statuses) else 'unknown'
                        state['steps'][node['id']] = value
                        if value['status']=='unknown' or (value['status']=='failed' and node['join']=='all_success'):
                            state.update(phase='held' if value['status']=='unknown' else 'failed',reason='aggregate_'+value['status'],result=value)
                            self._write(db,state)
                            return self.projection(state)
                        selected = node.get('next')
                        state.update(cursor=selected, phase='ready' if selected is not None else 'completed')
                    state['completed_steps'] += 1
                    self._write(db, state)
                    continue
                if node['type'] == 'end':
                    value = self._resolve(node.get('value'), state)
                    state.update(phase='held' if value is _UNKNOWN else 'completed',
                        result=None if value is _UNKNOWN else value, reason='output_unknown' if value is _UNKNOWN else None)
                    self._write(db, state)
                    return self.projection(state)
                if node['type'] == 'wait':
                    operation_id = self._resolve(node.get('operation_id'), state)
                    arguments = _UNKNOWN if operation_id is _UNKNOWN else {'operation_id': operation_id, 'timeout': node.get('timeout', 0)}
                    operation = node.get('operation', 'operations.wait')
                    if operation not in ('operations.wait', 'sessions.wait'):
                        flow_error('unsupported_operation', 'wait operation is unsupported')
                else:
                    arguments = self._resolve(node.get('arguments', {}), state)
                    operation = node['operation']
                if arguments is _UNKNOWN:
                    state.update(phase='held', reason='input_unknown')
                    self._write(db, state)
                    return self.projection(state)
                attempt = uuid4().hex
                child_id = state['run_id'] + '.' + node['id']
                request = dict(operation_id=child_id, idempotency_key=child_id, correlation_id=child_id,
                    binding=state['binding'], target=arguments.get('expected_target', state['target']))
                state.update(phase='executing', attempt=attempt, executing_node=node['id'], child_operation_id=child_id)
                self._write(db, state)
            try:
                value = self.invoke(operation, arguments,
                    authorize=lambda: self._step_guard(actor, run_id, attempt), request=request)
                if not isinstance(value, dict):
                    flow_error('invalid_step_result', 'host invocation must return a typed object result')
                encoded(value)
            except Exception as error:
                with self.connect() as db:
                    latest = self._load(run_id, db)
                    if latest.get('attempt') == attempt:
                        latest.update(phase='uncertain', reason=getattr(error, 'code', 'step_effect_uncertain'))
                        self._write(db, latest)
                    return self.projection(latest)
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                latest = self._load(run_id, db)
                if latest.get('attempt') != attempt:
                    return self.projection(latest)
                if value.get('status') in ('failed', 'held'):
                    latest.update(phase='held', reason=value.get('error', {}).get('code', 'child_not_completed'))
                    latest['steps'][node['id']] = value
                    latest.pop('attempt', None)
                    self._write(db, latest)
                    return self.projection(latest)
                if node['type'] == 'wait' and value.get('result', {}).get('wait', {}).get('status') == 'timeout':
                    latest.update(phase='waiting', reason='wait_timeout', waiting_on=arguments['operation_id'], waiting_operation=operation)
                    latest.pop('attempt', None)
                    latest.pop('executing_node', None)
                    self._write(db, latest)
                    return self.projection(latest)
                latest['steps'][node['id']] = value
                selected = node.get('next')
                latest.update(cursor=selected, phase='ready' if selected is not None else 'completed', reason=None)
                latest['completed_steps'] += 1
                latest.pop('attempt', None)
                latest.pop('executing_node', None)
                self._write(db, latest)
        return self.inspect(actor, run_id)


_UNKNOWN = object()
