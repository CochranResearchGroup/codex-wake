"""Same-user headless Grok ACP adapter using the existing transport and journal."""
import json
import os
from pathlib import Path

from .controller_grok import ControllerGrok
from .daemon_commands import local_operator
from .managed_inventory import InventoryError


class LocalGrokControl:
    def __init__(self, root, *, request=None):
        self.root = Path(root)
        self.owner = ControllerGrok(root, request=request)
        self.runtime = self.owner.runtime
        self.runtime.adapter = self

    def _profile(self, name):
        value = self.owner.profile(name)
        home = Path(value['target']['home'])
        if not home.is_absolute() or home.stat().st_uid != os.getuid():
            raise InventoryError('foreign_target', 'Grok account home must belong to the local user')
        self.owner._pin(value)
        return value

    def _profiles(self, profile):
        if profile is not None:
            return [profile]
        path = self.root / 'controller-grok.json'
        if not path.exists():
            return []
        # Validate the private registry through its existing owner before I/O.
        if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077 or path.stat().st_size > 1048576:
            raise InventoryError('configuration_unavailable', 'private bounded Grok profiles required')
        value = json.loads(path.read_text())
        if value.get('version') != 1 or not isinstance(value.get('profiles'), dict) or len(value['profiles']) > 256:
            raise InventoryError('configuration_unavailable', 'unsupported Grok profile registry')
        return sorted(value['profiles'])

    def _connection(self, name, target=None):
        profile = self._profile(name)
        expected = profile['target'] if target is None else target
        actor = local_operator(expected)
        arguments = dict(profile=name, expected_target=expected)
        def guard():
            current = self.owner._context(actor, arguments, 'observe', lambda: actor,
                                          conversation='conversation_id' in expected)
            if current['_sha256'] != profile['_sha256']:
                raise InventoryError('stale_target', 'Grok profile changed before native I/O')
        return profile, guard

    def discover(self, profile=None):
        rows, holds = [], []
        for name in self._profiles(profile):
            try:
                selected, guard = self._connection(name)
                with self.owner._connection(selected, guard) as connection:
                    negotiation = self.owner._negotiation(connection, selected)
                    if 'list' not in negotiation['agentCapabilities'].get('sessionCapabilities', {}):
                        raise InventoryError('unsupported_operation', 'native session listing not negotiated')
                    value = connection.call('session/list', dict(cwd=selected['cwd']), 'wake_local_list')
                sessions = value.get('sessions')
                if not isinstance(sessions, list) or len(sessions) > 1000:
                    raise InventoryError('capacity', 'bounded native Grok session list required')
                for item in sessions:
                    identifier = item.get('sessionId')
                    if not isinstance(identifier, str) or not identifier or item.get('cwd') != selected['cwd']:
                        continue
                    target = dict(selected['target'], conversation_id=identifier)
                    rows.append(dict(thread_id=identifier, selector='grok:' + identifier,
                                     name=item.get('title'), target=target, profile=name,
                                     harness='grok', presentation='headless_acp', attachments=[]))
            except (ValueError, OSError, KeyError, TypeError) as error:
                holds.append(dict(profile=name, reason=getattr(error, 'code', 'source_unavailable')))
        return dict(schema_version=1, status='partial' if holds else 'complete', sessions=rows, holds=holds)

    def resolve(self, selector, expected_target=None, profile=None):
        if not isinstance(selector, str) or not selector.startswith('grok:') or not selector[5:]:
            raise InventoryError('invalid_selector', 'Grok selector must be grok:SESSION_ID')
        rows = [row for row in self.discover(profile)['sessions'] if row['selector'] == selector]
        if len(rows) > 1:
            raise InventoryError('ambiguous_target', 'Grok session requires an exact profile')
        if not rows:
            raise InventoryError('target_unavailable', 'no owned Grok ACP session matches')
        if expected_target is not None and rows[0]['target'] != expected_target:
            raise InventoryError('stale_target', 'Grok session generation changed')
        return rows[0]

    @staticmethod
    def _request(target, key, prefix='local-grok-'):
        import hashlib
        from uuid import uuid4
        from .controller_runtime import bounded_id
        key = uuid4().hex if key is None else key
        bounded_id(key)
        identifier = prefix + hashlib.sha256(key.encode()).hexdigest()[:32]
        return dict(operation_id=identifier, idempotency_key=key, correlation_id=identifier,
                    binding='local-grok', target=target)

    def create(self, profile=None, key=None):
        request = self._request({}, key, 'local-grok-create-')
        try:
            retained = self.runtime._load(request['operation_id'])
        except InventoryError as error:
            if error.code != 'operation_not_found':
                raise
        else:
            actor = self._actor(request['operation_id'])
            if retained['operation'] != 'grok.create' or profile is not None and retained['payload']['profile'] != profile:
                raise InventoryError('idempotency_conflict', 'creation key already belongs to another profile or operation')
            return self._activate_created(retained)
        names = self._profiles(profile)
        if len(names) != 1:
            raise InventoryError('ambiguous_target' if names else 'target_unavailable', 'select exactly one owned Grok profile')
        selected = self._profile(names[0]); actor = local_operator(selected['target'])
        request['target'] = selected['target']
        created = self.owner.execute(actor, 'grok.create', dict(profile=names[0], expected_target=selected['target'],
            _request=request), authorize=lambda: actor)
        return self._activate_created(self.runtime._load(created['result']['operation']['operation_id']))

    def load(self, selector, profile=None, key=None, expected_target=None):
        from .controller_runtime import bounded_id
        if not isinstance(selector, str) or not selector.startswith('grok:'):
            raise InventoryError('invalid_selector', 'explicit grok:SESSION_ID required for native load')
        bounded_id(selector[5:])
        request = self._request({}, key, 'local-grok-resume-')
        try:
            retained = self.runtime._load(request['operation_id'])
        except InventoryError as error:
            if error.code != 'operation_not_found':
                raise
        else:
            actor = self._actor(request['operation_id'])
            if (retained['operation'] != 'grok.load'
                    or retained['target'].get('conversation_id') != selector[5:]
                    or profile is not None and profile != retained['payload']['profile']
                    or expected_target is not None and expected_target != retained['target']):
                raise InventoryError('idempotency_conflict', 'load key retains its original session, profile and process pin')
            # A lost acknowledgement is not authority to load again. Completed
            # receipts remain readable even after that original profile disappears.
            return self.runtime.envelope('grok.load', self.runtime._owned(actor, retained, lambda: actor))
        names = self._profiles(profile)
        if len(names) != 1:
            raise InventoryError('ambiguous_target' if names else 'target_unavailable', 'select exactly one owned Grok profile')
        selected = self._profile(names[0])
        target = dict(selected['target'], conversation_id=selector[5:])
        if expected_target is not None and target != expected_target:
            raise InventoryError('stale_target', 'load target differs from the fresh owned profile')
        actor = local_operator(target); request['target'] = target
        return self.owner.execute(actor, 'grok.load', dict(profile=names[0], expected_target=target,
            _request=request), authorize=lambda: actor)

    def _activation_view(self, record):
        value = self.runtime.envelope('grok.create', record)
        readiness = record['local_readiness']
        value['result']['readiness'] = readiness
        if not readiness['ready']:
            value.update(status='failed', error=dict(code='created_not_ready',
                message='Native creation retained; session activation is not ready. Retrieve the original operation IDs; do not create a replacement.'))
        return value

    def _activate_created(self, original):
        identifier = original['operation_id']
        actor = self._actor(identifier)
        with self._interaction_lock(identifier):
            original = self.runtime._owned(actor, self.runtime._load(identifier), lambda: actor)
            if original.get('local_readiness', {}).get('ready'):
                return self._activation_view(original)
            if original['execution'] != 'completed':
                return self.runtime.envelope('grok.create', original)
            target = original['result']['target']
            request = self._request(target, identifier, 'local-grok-load-')
            readiness = dict(ready=False, state='activation_pending', creation_operation_id=identifier,
                load_operation_id=request['operation_id'], reason=None)
            # Bind both original IDs durably before any activation I/O.
            original['local_readiness'] = readiness
            self.runtime._save(original)
            try:
                try:
                    load = self.runtime._load(request['operation_id'])
                except InventoryError as error:
                    if error.code != 'operation_not_found':
                        raise
                    profile = original['payload']['profile']
                    session_actor = local_operator(target)
                    response = self.owner.execute(session_actor, 'grok.load', dict(profile=profile,
                        expected_target=target, _request=request), authorize=lambda: session_actor)
                    load = self.runtime._load(response['result']['operation']['operation_id'])
                else:
                    self._actor(load['operation_id'])
                    if load['operation'] != 'grok.load' or load['target'] != target:
                        raise InventoryError('idempotency_conflict', 'activation ID already belongs to another target')
                    if load['phase'] == 'uncertain':
                        # Only native loaded-session listing may reconcile an uncertain
                        # activation. It never resends session/load or session/new.
                        row = self.resolve('grok:' + target['conversation_id'], target, original['payload']['profile'])
                        proof = dict(session_id=row['thread_id'], reconciliation='native_loaded_session_observed_without_replay')
                        session_actor = local_operator(target)
                        self.runtime.reconcile_result(session_actor, load['operation_id'], expected_operation='grok.load',
                            authorize=lambda: session_actor, observe=lambda record: proof)
                        load = self.runtime._load(load['operation_id'])
                if load['execution'] == 'completed':
                    readiness.update(ready=True, state='ready', reason=None)
                else:
                    readiness.update(state='activation_uncertain' if load['phase'] == 'uncertain' else 'activation_failed',
                                     reason=load.get('reason') or 'native_activation_not_confirmed')
            except (ValueError, OSError, KeyError, TypeError) as error:
                readiness.update(state='activation_uncertain', reason=getattr(error, 'code', 'native_activation_unavailable'))
            original = self.runtime._load(identifier)
            original['local_readiness'] = readiness
            self.runtime._save(original)
            return self._activation_view(original)

    def prompt(self, selector, prompt, key=None, profile=None, expected_target=None):
        request = self._request({}, key)
        try:
            retained = self.runtime._load(request['operation_id'])
        except InventoryError as error:
            if error.code != 'operation_not_found':
                raise
        else:
            actor = self._actor(request['operation_id'])
            if (retained['operation'] != 'grok.prompt' or retained['payload']['prompt'] != prompt
                    or selector != 'grok:' + retained['target']['conversation_id']
                    or profile is not None and profile != retained['payload']['profile']
                    or expected_target is not None and expected_target != retained['target']):
                raise InventoryError('idempotency_conflict', 'retry cannot replace the original Grok intent or target')
            return self.runtime.envelope('grok.prompt', retained)
        row = self.resolve(selector, expected_target, profile)
        actor = local_operator(row['target']); request['target'] = row['target']
        payload = dict(profile=row['profile'], expected_target=row['target'], prompt=prompt, _request=request)
        if self.owner.request is not None:
            return self.owner.execute(actor, 'grok.prompt', payload, authorize=lambda: actor)
        if not isinstance(prompt, str) or not 0 < len(prompt.encode()) <= 32768:
            raise InventoryError('invalid_argument', 'bounded nonempty Grok prompt required')
        from .local_grok_events import launch
        return self.runtime.execute(actor, 'grok.prompt', payload, authorize=lambda: actor,
            dispatch=lambda operation, arguments: dict(_pending=True, handle=launch(self.root, request['operation_id'])))

    def _actor(self, operation_id):
        record = self.runtime._load(operation_id)
        if not record['operation'].startswith('grok.') or record['principal'].get('subject') != 'uid:' + str(os.getuid()):
            raise InventoryError('foreign_target', 'operation is not owned by this local Grok caller')
        home = Path(record['target']['home'])
        if not home.is_absolute() or home.stat().st_uid != os.getuid():
            raise InventoryError('foreign_target', 'Grok operation account home changed owner')
        actor = local_operator(record['target'])
        self.runtime._owned(actor, record, lambda: actor)
        return actor

    def result(self, operation_id, timeout=0):
        actor = self._actor(operation_id)
        record = self.runtime._load(operation_id)
        if record['operation'] == 'grok.create' and record.get('local_readiness'):
            return self._activation_view(record)
        if record['operation'] == 'grok.prompt' and (record.get('result') or {}).get('kind') == 'grok_acp_collecting':
            import time
            if type(timeout) not in (int, float) or not 0 <= timeout <= 30:
                raise InventoryError('invalid_argument', 'result timeout must be0..30')
            deadline = time.monotonic() + timeout
            while True:
                self.observe_native_owned(record)
                if record['phase'] in ('terminal', 'uncertain') or time.monotonic() >= deadline:
                    return self.runtime.envelope('grok.prompt', record)
                time.sleep(min(.02, max(0, deadline - time.monotonic())))
        if record['operation'] == 'grok.slash' and record['phase'] != 'terminal' and record.get('result', {}).get('response_operation_id'):
            with self._interaction_lock(operation_id):
                self._reconcile_model(actor, self.runtime._load(operation_id))
        return self.runtime.operation(actor, 'operations.wait', dict(operation_id=operation_id, timeout=timeout),
                                      authorize=lambda: actor, expected_operation=record['operation'])

    def cancel(self, operation_id):
        actor = self._actor(operation_id)
        if self.runtime._load(operation_id)['operation'] == 'grok.slash':
            return self.slash('cancel', dict(interaction_id=operation_id))
        record = self.runtime._load(operation_id)
        if (record.get('result') or {}).get('kind') == 'grok_acp_collecting':
            value = self.result(operation_id)
            value['result']['cancellation_capability'] = dict(status='unsupported', reason='no exact original-turn cancellation custody')
            return value
        return self.owner.execute(actor, 'grok.cancel', dict(operation_id=operation_id), authorize=lambda: actor)

    def output(self, operation_id, mode='final', cursor=0, limit=100, timeout=0):
        if mode not in ('stream', 'transcript', 'final', 'silent') or type(cursor) is not int or cursor < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise InventoryError('invalid_argument', 'bounded Grok retained-output mode and cursor required')
        from .local_session_events import TurnEvents
        store = TurnEvents(self.root)
        if store.state(operation_id)['status'] != 'unavailable' or (self.runtime._load(operation_id).get('result') or {}).get('kind') == 'grok_acp_collecting':
            return self._native_output(operation_id, mode, cursor, limit, timeout, store)
        record = self.result(operation_id, timeout)['result']['operation']
        answer = record.get('answer') or {}
        terminal = record['phase'] == 'terminal'
        # ACP streams were received synchronously by the original transport owner;
        # this surface truthfully exposes one retained original answer, not live deltas.
        value = dict(operation_id=operation_id, mode=mode, terminal=terminal, execution=record['execution'],
                     phase=record['phase'], reason=record.get('reason'), next_cursor=1 if answer else 0,
                     latest_cursor=1 if answer else 0, provenance='retained_original_grok_acp_reply',
                     retention=dict(status='retained', truncated=answer.get('truncated', False), cursor_gap=False,
                                    history_complete=bool(answer), max_events=1),
                     wait=dict(status='completed' if terminal else 'timeout', ends_work=False))
        if mode == 'transcript':
            value['events'] = [] if cursor or not answer else [dict(sequence=1, kind='agent_message',
                source='original_grok_acp_reply', operation_id=operation_id, text=answer['text'])]
        elif mode in ('stream', 'final'):
            value['text'] = answer.get('text', '') if mode == 'final' or not cursor else ''
        return value

    def _load_session(self, row):
        selected, guard = self._connection(row['profile'], row['target'])
        with self.owner._connection(selected, guard) as connection:
            self.owner._negotiation(connection, selected)
            value = connection.call('session/load', dict(sessionId=row['thread_id'], cwd=selected['cwd'], mcpServers=[]), 'wake_local_load')
        detail = value.get('_meta', {}).get('x.ai/sessionDetail', {})
        if detail.get('sessionId') != row['thread_id'] or detail.get('cwd') != selected['cwd']:
            raise InventoryError('stale_target', 'native loaded session identity differs')
        return value

    def health(self, selector, profile=None, expected_target=None, timeout=3):
        if type(timeout) not in (int, float) or not 0 < timeout <= 30:
            raise InventoryError('invalid_argument', 'health timeout must be0..30 seconds')
        row = self.resolve(selector, expected_target, profile)
        return dict(target=row['target'], observation=dict(status='unsupported', responsive=False,
            reason='headless ACP metadata does not establish controlling TUI-loop health',
            presentation='headless_acp'), grants_recovery=False, application_effects=False)

    def _interaction_lock(self, identifier):
        from .local_slash_commands import LocalSlashCommands
        return LocalSlashCommands._interaction_lock(self, identifier)

    def _perform(self, row, command, arguments):
        current = self.resolve(row['selector'], row['target'], row['profile'])
        native = self._load_session(current)
        if command == '/model':
            available = {item['modelId'] for item in native.get('models', {}).get('availableModels', [])}
            if arguments not in available:
                raise InventoryError('invalid_argument', 'model is not a negotiated native choice')
            selected, guard = self._connection(row['profile'], row['target'])
            with self.owner._connection(selected, guard) as connection:
                self.owner._negotiation(connection, selected)
                connection.call('session/set_model', dict(sessionId=row['thread_id'], modelId=arguments), 'wake_local_model')
            native = self._load_session(current)
            if native.get('models', {}).get('currentModelId') != arguments:
                raise InventoryError('effect_unverified', 'native model readback differs')
        return dict(kind='native_slash_result', command=command, arguments=arguments, received=True,
                    executed=True, completed=True, model_submission=False,
                    native_method='session/set_model' if command == '/model' else 'session/load',
                    observation=dict(session_id=row['thread_id'], models=native.get('models', {})))

    def slash(self, verb, arguments):
        inputs = dict(arguments)
        mode = inputs.pop('mode', None); cursor = inputs.pop('cursor', 0)
        if verb == 'list':
            row = self.resolve(inputs['selector'], inputs.get('expected_target'), inputs.get('profile'))
            native = self._load_session(row)
            return dict(schema_version=1, target=row['target'], harness='grok',
                catalog_source='qualified_native_adapter', complete_native_catalog=False, prompt_fallback=False,
                commands=[dict(command='/status', interactive=False, native_method='session/load'),
                          dict(command='/model', interactive=True, presentation='controller_interaction', native_popup=False,
                               native_method='session/set_model', choices=native.get('models', {}).get('availableModels', []))])
        if verb == 'result':
            value = self.result(inputs['operation_id'])
        elif verb == 'cancel':
            identifier = inputs['interaction_id']; actor = self._actor(identifier)
            with self._interaction_lock(identifier):
                record = self.runtime._owned(actor, self.runtime._load(identifier), lambda: actor, capability='control')
                if record['operation'] != 'grok.slash' or record.get('result', {}).get('interaction_id') != identifier:
                    raise InventoryError('interaction_not_found', 'exact Grok interaction required')
                if record['phase'] != 'terminal':
                    if record['result'].get('response_operation_id'):
                        raise InventoryError('interaction_response_pending', 'reconcile response before cancellation')
                    record.update(phase='terminal', execution='cancelled', cancellation='confirmed', delivery='retained')
                    record['result'].update(state='cancelled', executed=False, completed=False)
                    self.runtime._save(record)
                value = self.runtime.envelope('grok.slash', record)
        elif verb == 'respond':
            value = self._respond(inputs['interaction_id'], inputs['value'], inputs['idempotency_key'])
        elif verb == 'run':
            command = inputs['command']; text = inputs.get('arguments', '')
            if command not in ('/status', '/model'):
                raise InventoryError('unsupported_slash_command', 'Grok adapter supports /status and /model; no model fallback')
            if not isinstance(text, str) or len(text.encode()) > 32768 or '\x00' in text or command == '/status' and text:
                raise InventoryError('invalid_argument', 'invalid native command arguments')
            row = self.resolve(inputs['selector'], inputs.get('expected_target'), inputs.get('profile'))
            actor = local_operator(row['target']); request = self._request(row['target'], inputs['idempotency_key'], 'local-grok-slash-')
            def dispatch(operation, payload):
                if command == '/model' and not text:
                    native = self._load_session(row)
                    choices = native.get('models', {}).get('availableModels', [])
                    if not choices:
                        raise InventoryError('unsupported_operation', 'native model choices unavailable')
                    return dict(_pending=True, handle=dict(kind='controller_interaction', interaction_id=request['operation_id'],
                        operation_id=request['operation_id'], command=command, state='input_required',
                        presentation='controller_interaction', native_popup=False, executed=False, completed=False,
                        model_submission=False, input=dict(name='model', type='select', choices=choices)))
                return self._perform(row, command, text)
            value = self.runtime.execute(actor, 'grok.slash', dict(session=row, command=command, arguments=text,
                _request=request), authorize=lambda: actor, dispatch=dispatch)
            record = value['result']['operation']
            if record.get('result', {}).get('kind') == 'controller_interaction' and record['phase'] != 'terminal':
                with self._interaction_lock(record['operation_id']):
                    current = self.runtime._load(record['operation_id'])
                    if current['phase'] == 'waiting' and current['result'].get('state') == 'input_required':
                        current.update(execution='not_started', delivery='retained', acceptance='interaction_required')
                        self.runtime._save(current)
                    value = self.runtime.envelope('grok.slash', current)
        else:
            raise InventoryError('unsupported_operation', 'unknown Grok slash verb')
        if mode is not None:
            from .local_control_commands import receipt_output
            return dict(schema_version=1, operation='local.slash.' + verb, status='completed',
                        result=dict(output=receipt_output(value, mode, cursor=cursor)))
        return value

    def _respond(self, identifier, value, key):
        actor = self._actor(identifier)
        with self._interaction_lock(identifier):
            original = self.runtime._owned(actor, self.runtime._load(identifier), lambda: actor, capability='control')
            handle = original.get('result', {})
            if original['operation'] != 'grok.slash' or handle.get('interaction_id') != identifier:
                raise InventoryError('interaction_not_found', 'exact owned Grok model interaction required')
            if original['execution'] == 'cancelled':
                raise InventoryError('interaction_cancelled', 'cancelled interaction has no native effect')
            if not isinstance(value, str) or value not in {choice['modelId'] for choice in handle['input']['choices']}:
                raise InventoryError('invalid_argument', 'explicit negotiated model choice required')
            request = self._request(original['target'], key, 'local-grok-response-')
            if handle.get('response_operation_id') and (handle['response_operation_id'] != request['operation_id'] or handle.get('response_value') != value):
                raise InventoryError('interaction_response_conflict', 'interaction already has a different response')
            if original['phase'] == 'terminal':
                return self.runtime.envelope('grok.slash', original)
            row = original['payload']['session']
            self.resolve(row['selector'], row['target'], row['profile'])
            handle.update(response_operation_id=request['operation_id'], response_value=value)
            original['result'] = handle; self.runtime._save(original)
            response = self.runtime.execute(actor, 'grok.slash.response', dict(session=row, interaction_id=identifier,
                value=value, _request=request), authorize=lambda: actor,
                dispatch=lambda operation, payload: self._perform(row, '/model', value))
            if response['result']['operation']['execution'] == 'completed':
                proof = dict(response['result']['operation']['result'], interaction_id=identifier,
                             operation_id=identifier, state='completed', presentation='controller_interaction', native_popup=False,
                             input=handle['input'], response_operation_id=request['operation_id'], response_value=value)
                return self.runtime.reconcile_result(actor, identifier, expected_operation='grok.slash',
                    authorize=lambda: actor, observe=lambda record: proof)
            return self.runtime.envelope('grok.slash', self.runtime._load(identifier))

    def _reconcile_model(self, actor, original):
        handle = original['result']; response = self.runtime._load(handle['response_operation_id'])
        self.runtime._owned(actor, response, lambda: actor)
        if response['execution'] == 'completed':
            proof = response['result']
        else:
            row = original['payload']['session']
            self.resolve(row['selector'], row['target'], row['profile'])
            native = self._load_session(row)
            if native.get('models', {}).get('currentModelId') != handle['response_value']:
                return
            proof = dict(kind='native_slash_result', command='/model', arguments=handle['response_value'],
                received=True, executed=True, completed=True, model_submission=False,
                native_method='session/set_model', reconciliation='native_model_observed_without_replay',
                observation=dict(session_id=row['thread_id'], models=native['models']))
            self.runtime.reconcile_result(actor, response['operation_id'], expected_operation='grok.slash.response',
                authorize=lambda: actor, observe=lambda record: proof)
        proof = dict(proof, interaction_id=original['operation_id'], operation_id=original['operation_id'],
            state='completed', presentation='controller_interaction', native_popup=False,
            input=handle['input'], response_operation_id=handle['response_operation_id'], response_value=handle['response_value'])
        self.runtime.reconcile_result(actor, original['operation_id'], expected_operation='grok.slash',
            authorize=lambda: actor, observe=lambda record: proof)

    def observe_native_owned(self, record):
        if record['operation'] == 'grok.prompt' and (record.get('result') or {}).get('kind') == 'grok_acp_collecting':
            current = self.runtime._load(record['operation_id'])
            record.update(current)
            if record['phase'] != 'terminal':
                from .local_session_events import TurnEvents
                from .controller_health import _process_matches
                state = TurnEvents(self.root).state(record['operation_id'])
                process = state.get('process') or record['result'].get('collector_process')
                if process and not _process_matches(dict(process=dict(pid=state.get('pid', record['result']['collector_pid']), start_ticks=process['start_time_ticks'], boot_id=process['boot_id']))):
                    with self.runtime.connect() as db:
                        db.execute('BEGIN IMMEDIATE')
                        latest = json.loads(db.execute('SELECT record FROM operations WHERE id=?', (record['operation_id'],)).fetchone()[0])
                        if latest['phase'] != 'terminal':
                            latest.update(phase='uncertain', execution='unknown', reason='original_grok_collector_exited')
                            from .controller_runtime import encoded
                            db.execute('UPDATE operations SET record=? WHERE id=?', (encoded(latest), record['operation_id']))
                        record.update(latest)
                    TurnEvents(self.root).update(record['operation_id'], status='uncertain', reason='original_grok_collector_exited')
            return record
        return self.owner.observe_native_owned(record)

    def cancel_native_owned(self, record):
        return self.owner.cancel_native_owned(record)

    def _native_output(self, identifier, mode, cursor, limit, timeout, store):
        import time
        if type(timeout) not in (int, float) or not 0 <= timeout <= 30:
            raise InventoryError('invalid_argument', 'output timeout must be0..30')
        deadline = time.monotonic() + timeout
        while True:
            record = self.result(identifier)['result']['operation']; page = store.read(identifier, cursor, limit)
            terminal = record['phase'] == 'terminal'
            if terminal or mode in ('stream', 'transcript') and page['events'] or store.state(identifier)['status'] in ('uncertain', 'failed') or time.monotonic() >= deadline:
                break
            time.sleep(min(.02, max(0, deadline - time.monotonic())))
        answer = record.get('answer') or {}
        value = dict(operation_id=identifier, mode=mode, terminal=terminal, execution=record['execution'],
            phase=record['phase'], reason=record.get('reason'), next_cursor=page['next_cursor'],
            latest_cursor=page['latest_cursor'], retention=page['retention'], provenance='native_grok_acp_notifications',
            wait=dict(status='completed' if terminal else 'timeout', ends_work=False))
        if mode == 'transcript':
            value['events'] = page['events']
        elif mode == 'stream':
            value['text'] = ''.join(event['params'].get('update', {}).get('content', {}).get('text', '')
                for event in page['events'] if event['kind'] == 'grok/session/update')
        elif mode == 'final':
            value['text'] = answer.get('text', '') if terminal else ''
            value['truncated'] = answer.get('truncated', False)
        return value
