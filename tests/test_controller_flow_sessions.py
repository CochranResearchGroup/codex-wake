import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from codex_wake.controller_auth import Actor


class SessionOperationsTests(unittest.TestCase):
    def test_scoped_native_create_prompt_and_late_result_preserve_native_ownership(self):
        from codex_wake.controller_flow_sessions import ControllerFlowSessions
        from codex_wake.process import process_identity
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = process_identity(os.getpid())
            process = dict(pid=os.getpid(), start_ticks=identity['start_time_ticks'], boot_id=identity['boot_id'])
            base = dict(host='host', environment='test', provider='codex', account='alice', home=str(root),
                home_generation='fixture', configuration_revision='one', build_channel='modded',
                build_sha256=hashlib.sha256(Path('/proc/self/exe').read_bytes()).hexdigest(), build_revision='fixture', executable='/fixture/native')
            profile = dict(target=base, endpoint='unix:///fixture/owned.sock', process=process,
                modes=['new_session', 'sequential'], native_provider='codex', cwd=str(root), methods=['thread/start','turn/start','thread/read','turn/interrupt'])
            config = root / 'controller-flow-sessions.json'
            config.write_text(json.dumps(dict(version=1, profiles={'fixture': profile})));config.chmod(0o600)
            effects = []
            completed = [False]
            interrupted = [False]
            def request(endpoint, codex, method, params, timeout):
                if method == 'thread/start':
                    effects.append(method)
                    return {'thread': {'id': 'created', 'cwd': str(root), 'modelProvider': 'codex'}}
                if method == 'turn/start':
                    effects.append((method, params['threadId'], params['input'][0]['text']))
                    return {'turn': {'id': 'turn-one', 'status': 'inProgress'}}
                if method == 'thread/read':
                    return {'thread': {'id': 'created', 'cwd': str(root), 'modelProvider': 'codex',
                        'turns': [{'id': 'turn-one', 'status': 'interrupted' if interrupted[0] else 'completed' if completed[0] else 'inProgress',
                            'items': [{'type': 'agentMessage', 'text': 'native final'}]}]}}
                if method == 'turn/interrupt':
                    effects.append('interrupt')
                    interrupted[0] = True
                    return {}
                raise AssertionError(method)
            owner = ControllerFlowSessions(root, resolve_build=lambda target: base, request=request, metadata=lambda profile: {'codexHome': str(root), 'peer_pid': os.getpid()})
            target = owner.target('fixture')
            actor = Actor('caller','service','client','grant','local://test','wake:controller',
                frozenset({'observe','control'}), [base], time.time()+600)
            def invoke(verb, args):
                return owner.execute(actor, 'sessions.' + verb, args, authorize=lambda: actor)
            def metadata(identifier, target):
                return dict(operation_id=identifier,idempotency_key=identifier,correlation_id=identifier,binding='original',target=target)
            created = invoke('create',dict(profile='fixture',expected_target=target,_request=metadata('create',target)))
            child = created['result']['operation']['result']['target']
            sent = invoke('prompt',dict(profile='fixture',expected_target=child,prompt='hello',_request=metadata('prompt',child)))
            self.assertEqual(invoke('wait',dict(operation_id='prompt',timeout=0))['result']['wait']['status'],'timeout')
            completed[0] = True
            restarted = ControllerFlowSessions(root, resolve_build=lambda target: base, request=request, metadata=lambda profile: {'codexHome': str(root), 'peer_pid': os.getpid()})
            generic=restarted.runtime.operation(actor,'operations.result',dict(operation_id='prompt'),authorize=lambda:actor)
            self.assertEqual(generic['result']['operation']['answer']['text'],'native final')
            answer = restarted.execute(actor,'sessions.wait',dict(operation_id='prompt',timeout=0),authorize=lambda: actor)
            self.assertEqual(answer['result']['operation']['answer']['text'],'native final')
            self.assertEqual(answer['result']['operation']['target'],child)
            self.assertEqual(len(effects),2)
            self.assertEqual(invoke('create',dict(profile='fixture',expected_target=target,_request=metadata('create',target))),created)
            from codex_wake.wake_control import change_control
            from codex_wake.records import WakeError
            change_control(root,'pause')
            with self.assertRaises(WakeError):
                invoke('create',dict(profile='fixture',expected_target=target,_request=metadata('paused',target)))
            self.assertEqual(len(effects),2)
            change_control(root,'resume')
            completed[0] = False
            invoke('prompt',dict(profile='fixture',expected_target=child,prompt='owned active work',_request=metadata('revoked-prompt',child)))
            owner.runtime.revoke_grant('grant',issuer='local://test',resource='wake:controller')
            self.assertEqual(effects[-1],'interrupt')
