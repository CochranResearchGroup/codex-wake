"""Source-preserving destination import through the public operation interface."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from codex_wake.controller_auth import Actor
from codex_wake.controller_history import ControllerHistory
from codex_wake.controller_accounts import ControllerAccounts

SOURCE = '01a123a8-5782-7d43-a214-55b293bbd65f'
CHILD = '01a123a8-5782-7d43-a214-55b293bbd660'


class HistoryImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / 'controller-accounts.toml'
        self.config.write_text(f'''[profiles]
state_root={json.dumps(str(self.root / 'homes'))}
known_profiles=["alice","bob"]
[history]
readable_accounts=["alice","bob"]
''')
        for name in ('alice', 'bob'):
            (self.root / 'homes' / ('codex-' + name) / 'sessions').mkdir(parents=True)
        self.source = self.root / 'homes/codex-alice/sessions/source.jsonl'
        self.source.write_text(json.dumps(dict(type='session_meta', payload=dict(id=SOURCE)))+'\n'+
                               json.dumps(dict(type='response_item',payload=dict(type='message',role='user',content=[dict(type='input_text',text='original question')])) )+'\n')
        with sqlite3.connect(self.source.parent.parent / 'state_5.sqlite') as db:
            db.execute('create table threads (id text primary key,cwd text,title text,rollout_path text)')
            db.execute('insert into threads values(?,?,?,?)',(SOURCE,str(self.root),'original question',str(self.source)))
        self.accounts = ControllerAccounts(self.config,host='local',environment='test')
        self.reader = ControllerHistory(self.config,root=self.root,host='local',environment='test',authorized_accounts=['alice','bob'])
        self.pin = self.reader.execute('history.read',dict(owner='alice',thread_id=SOURCE))['session']['target']
        self.turns = [dict(id='turn-one',status='completed',items=[dict(type='userMessage',text='original question')],itemsView='full')]
        self.forks = 0
        test = self
        class Daemons:
            def execute(self,operation,args):
                account = test.accounts.execute('accounts.resolve',dict(selector=args['account']))['account']
                return {'daemon':dict(state='running',selected_build_running=True,endpoint='unix://'+account['id'],target=dict(account['target'],build_channel='modded',executable='/native/codex',build_sha256='a'*64,build_revision='fixture',process=dict(pid=123,start_ticks='42'),socket_generation='1:2'))}
        self.daemons=Daemons()
        self.destination=self.daemons.execute('daemons.status',dict(account='bob',channel='modded'))['daemon']['target']
        self.actor=Actor('operator','owner','cli','grant','local','wake',frozenset(['control','observe','history.observe']),[self.pin,self.destination],time.time()+600)
        self.arguments=dict(owner='alice',thread_id=SOURCE,expected_source=self.pin,destination='bob',channel='modded',expected_target=self.destination,_request=dict(operation_id='copy-1',idempotency_key='copy-1',correlation_id='copy-1',binding='cli',target=self.destination))

    def request(self,endpoint,executable,method,params,timeout,**kwargs):
        if method=='thread/goal/get':return {'goal':None}
        if method=='thread/list':return {'data': [], 'nextCursor': None}
        if method=='thread/read':
            return {'thread':dict(id=params['threadId'],cwd=str(self.root),ephemeral=False,status={'type':'idle'},turns=self.turns,path=str(self.source) if params['threadId']==SOURCE else str(self.child_path),forkedFromId=None if params['threadId']==SOURCE else SOURCE)}
        if method=='thread/fork':
            self.forks+=1
            self.child_path=self.root/'homes/codex-bob/sessions/child.jsonl'
            self.child_path.write_bytes(Path(params['path']).read_bytes())
            return {'thread':dict(id=CHILD,cwd=str(self.root),ephemeral=False,status={'type':'idle'},turns=self.turns,path=str(self.child_path),forkedFromId=SOURCE)}
        raise AssertionError(method)

    def owner(self):
        from codex_wake.controller_history_import import ControllerHistoryImport
        return ControllerHistoryImport(self.root,host='local',environment='test',daemon_owner=self.daemons,request=self.request)

    def test_import_creates_destination_native_conversation_and_replay_returns_it(self):
        before=self.source.read_bytes()
        first=self.owner().execute(self.actor,'history.import',self.arguments,authorize=lambda:self.actor)
        result=first['result']['operation']['result']
        self.assertEqual(result['thread_id'],CHILD)
        self.assertEqual(result['destination'],'codex-bob')
        self.assertEqual(result['provenance']['source_target'],self.pin)
        self.assertEqual(self.source.read_bytes(),before)
        second=self.owner().execute(self.actor,'history.import',self.arguments,authorize=lambda:self.actor)
        self.assertEqual(second['result']['operation']['result'],result)
        self.assertEqual(self.forks,1)

    def test_unchanged_revision_reuses_copy_across_distinct_requests_and_preserves_destination_work(self):
        first = self.owner().execute(self.actor, 'history.import', self.arguments, authorize=lambda: self.actor)
        original = first['result']['operation']['result']
        self.child_path.write_text(self.child_path.read_text() + 'destination-only work\n')
        args = copy.deepcopy(self.arguments)
        args['_request'].update(operation_id='copy-again', idempotency_key='copy-again')
        second = self.owner().execute(self.actor, 'history.import', args, authorize=lambda: self.actor)
        self.assertEqual(second['result']['operation']['result'], original)
        self.assertEqual(self.forks, 1)
        self.assertIn('destination-only work', self.child_path.read_text())

    def test_advanced_source_creates_linked_snapshot_without_overwriting_prior_destination(self):
        from dataclasses import replace
        from uuid import UUID
        owner = self.owner()
        first = owner.execute(self.actor, 'history.import', self.arguments, authorize=lambda: self.actor)['result']['operation']['result']
        previous_path = self.child_path
        previous_path.write_text(previous_path.read_text() + 'destination-only work\n')
        previous_content = previous_path.read_bytes()
        self.source.write_text(self.source.read_text() + json.dumps(dict(type='response_item', payload=dict(type='message', role='user', content=[]))) + '\n')
        self.turns.append(dict(id='turn-two', status='completed', items=[], itemsView='full'))
        pin = self.reader.execute('history.read', dict(owner='alice', thread_id=SOURCE))['session']['target']
        actor = replace(self.actor, targets=[pin, self.destination])
        args = copy.deepcopy(self.arguments)
        args['expected_source'] = pin
        args['_request'].update(operation_id='advanced', idempotency_key='advanced')
        request = self.request
        new_id = str(UUID(int=UUID(CHILD).int + 1))
        def advanced(endpoint, executable, method, params, timeout, **kwargs):
            if method == 'thread/fork':
                self.forks += 1
                self.child_path = previous_path.with_name('advanced.jsonl')
                self.child_path.write_bytes(Path(params['path']).read_bytes())
                return {'thread': {'id': new_id}}
            return request(endpoint, executable, method, params, timeout, **kwargs)
        owner.request = advanced
        second = owner.execute(actor, 'history.import', args, authorize=lambda: actor)['result']['operation']['result']
        self.assertEqual(second['thread_id'], new_id)
        self.assertEqual(second['provenance']['previous_snapshot_thread_id'], first['thread_id'])
        self.assertEqual(previous_path.read_bytes(), previous_content)
        self.assertEqual(self.forks, 2)

    def test_destination_restart_reuses_known_copy_under_current_store_authority(self):
        from dataclasses import replace
        first = self.owner().execute(self.actor, 'history.import', self.arguments, authorize=lambda: self.actor)['result']['operation']['result']
        previous = self.daemons
        class Restarted:
            def execute(unused, operation, args):
                value = copy.deepcopy(previous.execute(operation, args))
                value['daemon']['target']['socket_generation'] = 'restarted'
                return value
        self.daemons = Restarted()
        target = self.daemons.execute('daemons.status', dict(account='bob', channel='modded'))['daemon']['target']
        args = copy.deepcopy(self.arguments)
        args.update(expected_target=target)
        args['_request'].update(operation_id='after-restart', idempotency_key='after-restart', target=target)
        actor = replace(self.actor, targets=[self.pin, target])
        result = self.owner().execute(actor, 'history.import', args, authorize=lambda: actor)['result']['operation']['result']
        self.assertEqual(result['thread_id'], first['thread_id'])
        self.assertEqual(self.forks, 1)

    def test_ongoing_source_copies_only_saved_completed_prefix(self):
        self.source.write_text(self.source.read_text() + json.dumps(dict(type='event_msg', payload=dict(type='task_complete', turn_id='turn-one'))) + '\n')
        completed = self.source.read_bytes()
        self.source.write_text(self.source.read_text() + json.dumps(dict(type='event_msg', payload=dict(type='task_started', turn_id='turn-two'))) + '\n')
        self.pin = self.reader.execute('history.read', dict(owner='alice', thread_id=SOURCE))['session']['target']
        self.arguments['expected_source'] = self.pin
        from dataclasses import replace
        self.actor = replace(self.actor, targets=[self.pin, self.destination])
        captured = self.source.read_bytes()
        continued = (json.dumps(dict(type='event_msg', payload=dict(type='token_count'))) + '\n').encode()
        original = self.request
        def ongoing(endpoint, executable, method, params, timeout, **kwargs):
            value = copy.deepcopy(original(endpoint, executable, method, params, timeout, **kwargs))
            if method == 'thread/fork':
                with self.source.open('ab') as stream:
                    stream.write(continued)
            if method == 'thread/read' and params['threadId'] == SOURCE:
                value['thread']['status'] = {'type': 'active'}
                value['thread']['turns'].append(dict(id='turn-two', status='inProgress', items=[], itemsView='full'))
            return value
        owner = self.owner()
        owner.request = ongoing
        value = owner.execute(self.actor, 'history.import', self.arguments, authorize=lambda: self.actor)['result']['operation']
        self.assertEqual(value['execution'], 'completed')
        self.assertEqual(self.child_path.read_bytes(), completed)
        result = value['result']['provenance']
        self.assertEqual(result['saved_boundary']['last_completed_turn_id'], 'turn-one')
        self.assertEqual(result['exclusions'], [dict(turn_id='turn-two', reason='incomplete_turn')])
        self.assertEqual(self.source.read_bytes(), captured + continued)

    def test_registered_stock_source_imports_through_same_native_owner(self):
        from dataclasses import replace
        calls = []
        previous = self.daemons
        class SeparateChannels:
            def execute(unused, operation, arguments):
                calls.append((arguments['account'], arguments['channel']))
                value = previous.execute(operation, arguments)
                if arguments['account'] == 'stock':
                    value['daemon']['target']['build_channel'] = 'stock'
                return value
        self.daemons = SeparateChannels()
        self.accounts.execute('stores.register', dict(selector='stock', home=str(self.source.parent.parent)))
        self.config.write_text(self.config.read_text().replace('readable_accounts=["alice","bob"]', 'readable_accounts=["stock","bob"]'))
        reader = ControllerHistory(self.config, root=self.root, host='local', environment='test', authorized_accounts=['stock','bob'])
        pin = reader.execute('history.read', dict(owner='stock', thread_id=SOURCE))['session']['target']
        self.destination = self.daemons.execute('daemons.status', dict(account='bob', channel='modded'))['daemon']['target']
        self.arguments['expected_target'] = self.destination
        self.arguments['_request']['target'] = self.destination
        actor = replace(self.actor, targets=[pin, self.destination])
        self.arguments.update(owner='stock', expected_source=pin)
        value = self.owner().execute(actor, 'history.import', self.arguments, authorize=lambda: actor)['result']['operation']['result']
        self.assertEqual(value['provenance']['source_owner'], 'stock')
        self.assertEqual(value['thread_id'], CHILD)
        self.assertEqual(self.forks, 1)
        self.assertEqual({channel for account, channel in calls if account == 'stock'}, {'stock'})
        self.assertEqual({channel for account, channel in calls if account == 'bob'}, {'modded'})

    def test_registered_stock_destination_imports_without_replacing_shared_home(self):
        from dataclasses import replace
        calls = []
        previous = self.daemons
        class SeparateChannels:
            def execute(unused, operation, arguments):
                calls.append((arguments['account'], arguments['channel']))
                value = previous.execute(operation, arguments)
                if arguments['account'] == 'stock':
                    value['daemon']['target']['build_channel'] = 'stock'
                return value
        self.daemons = SeparateChannels()
        stock_home = self.root / 'homes/codex-bob'
        self.accounts.execute('stores.register', dict(selector='stock', home=str(stock_home)))
        destination = self.daemons.execute('daemons.status', dict(account='stock', channel='stock'))['daemon']['target']
        self.pin = self.reader.execute('history.read', dict(owner='alice', thread_id=SOURCE))['session']['target']
        self.arguments['expected_source'] = self.pin
        actor = replace(self.actor, targets=[self.pin, destination])
        self.arguments.update(destination='stock', expected_target=destination)
        self.arguments['_request']['target'] = destination
        before = stock_home.stat().st_ino
        value = self.owner().execute(actor, 'history.import', self.arguments, authorize=lambda: actor)['result']['operation']['result']
        self.assertEqual(value['destination'], 'stock')
        self.assertEqual(stock_home.stat().st_ino, before)
        self.assertEqual(value['target']['home'], str(stock_home))
        self.assertEqual({channel for account, channel in calls if account == 'stock'}, {'stock'})
        self.assertEqual({channel for account, channel in calls if account == 'alice'}, {'modded'})

    def test_completed_unloaded_saved_source_can_be_copied_and_replayed(self):
        original = self.request
        def unloaded(endpoint, executable, method, params, timeout, **kwargs):
            value = original(endpoint, executable, method, params, timeout, **kwargs)
            if method == 'thread/read' and params['threadId'] == SOURCE:
                value['thread']['status'] = {'type': 'notLoaded'}
            return value
        owner = self.owner()
        owner.request = unloaded
        first = owner.execute(self.actor, 'history.import', self.arguments, authorize=lambda: self.actor)['result']['operation']
        self.assertEqual(first['execution'], 'completed')
        self.assertEqual(first['result']['thread_id'], CHILD)
        second = owner.execute(self.actor, 'history.import', self.arguments, authorize=lambda: self.actor)['result']['operation']
        self.assertEqual(second, first)
        self.assertEqual(self.forks, 1)

    def test_active_unknown_and_incomplete_unloaded_sources_never_fork(self):
        for status, turn_status in [('active', 'completed'), ('unknown', 'completed'), ('notLoaded', 'inProgress')]:
            with self.subTest(status=status, turn_status=turn_status):
                original = self.request
                def unsafe(endpoint, executable, method, params, timeout, **kwargs):
                    value = copy.deepcopy(original(endpoint, executable, method, params, timeout, **kwargs))
                    if method == 'thread/read' and params['threadId'] == SOURCE:
                        value['thread']['status'] = {'type': status}
                        value['thread']['turns'][0]['status'] = turn_status
                    return value
                owner = self.owner()
                owner.request = unsafe
                args = copy.deepcopy(self.arguments)
                key = status + turn_status
                args['_request'].update(operation_id=key, idempotency_key=key)
                result = owner.execute(self.actor, 'history.import', args, authorize=lambda: self.actor)['result']['operation']
                self.assertEqual(result['reason'], 'unsupported_target')
                self.assertIsNone(result['result'])
                self.assertEqual(self.forks, 0)

    def test_conflicting_intent_and_changed_native_goal_never_create_another_copy(self):
        from codex_wake.managed_inventory import InventoryError
        owner=self.owner()
        owner.execute(self.actor,'history.import',self.arguments,authorize=lambda:self.actor)
        changed=copy.deepcopy(self.arguments)
        changed['owner']='bob'
        with self.assertRaises(InventoryError) as conflict:
            owner.execute(self.actor,'history.import',changed,authorize=lambda:self.actor)
        self.assertEqual(conflict.exception.code,'idempotency_conflict')
        self.assertEqual(self.forks,1)
        original=self.request
        def goal(endpoint,executable,method,params,timeout,**kwargs):
            if method=='thread/goal/get':return {'goal':{'status':'active'}}
            return original(endpoint,executable,method,params,timeout,**kwargs)
        owner.request=goal
        new=copy.deepcopy(self.arguments)
        new['_request'].update(operation_id='goal-held',idempotency_key='goal-held')
        held=owner.execute(self.actor,'history.import',new,authorize=lambda:self.actor)['result']['operation']
        self.assertEqual(held['reason'],'unsupported_goal_import')
        self.assertIsNone(held['result'])
        self.assertEqual(self.forks,1)

    def test_missing_source_scope_and_stale_destination_do_not_copy_history(self):
        from dataclasses import replace
        from codex_wake.controller_auth import AuthError
        unauthorized=replace(self.actor,targets=[self.destination])
        with self.assertRaises(AuthError):
            self.owner().execute(unauthorized,'history.import',self.arguments,authorize=lambda:unauthorized)
        changed=copy.deepcopy(self.arguments)
        changed['expected_target']['socket_generation']='replaced'
        changed['_request']['target']=changed['expected_target']
        actor=replace(self.actor,targets=[self.pin,changed['expected_target']])
        held=self.owner().execute(actor,'history.import',changed,authorize=lambda:actor)['result']['operation']
        self.assertEqual(held['reason'],'stale_target')
        self.assertIsNone(held['result'])
        self.assertEqual(self.forks,0)

    def test_lost_native_fork_result_is_retained_as_uncertain_without_replay(self):
        owner=self.owner()
        original=self.request
        def lost(endpoint,executable,method,params,timeout,**kwargs):
            result=original(endpoint,executable,method,params,timeout,**kwargs)
            if method=='thread/fork':raise TimeoutError('lost native result')
            return result
        owner.request=lost
        first=owner.execute(self.actor,'history.import',self.arguments,authorize=lambda:self.actor)['result']['operation']
        self.assertEqual(first['phase'],'uncertain')
        self.assertIsNone(first['result'])
        second=owner.execute(self.actor,'history.import',self.arguments,authorize=lambda:self.actor)['result']['operation']
        self.assertEqual(second,first)
        self.assertEqual(self.forks,1)

    def test_new_request_after_unknown_revision_does_not_fork_again(self):
        owner = self.owner()
        request = self.request
        def lost(*args, **kwargs):
            value = request(*args, **kwargs)
            if args[2] == 'thread/fork':
                raise TimeoutError('lost native result')
            return value
        owner.request = lost
        owner.execute(self.actor, 'history.import', self.arguments, authorize=lambda: self.actor)
        args = copy.deepcopy(self.arguments)
        args['_request'].update(operation_id='unknown-again', idempotency_key='unknown-again')
        value = self.owner().execute(self.actor, 'history.import', args, authorize=lambda: self.actor)
        self.assertEqual(value['result']['operation']['reason'], 'uncertain_effect')
        self.assertEqual(self.forks, 1)

    def test_lost_result_is_reconciled_from_unique_native_lineage_and_saved_content(self):
        from dataclasses import replace
        rows = [dict(json.loads(line), timestamp='2026-11-07T10:00:00Z') for line in self.source.read_text().splitlines()]
        self.source.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        self.pin = self.reader.execute('history.read', dict(owner='alice', thread_id=SOURCE))['session']['target']
        self.arguments['expected_source'] = self.pin
        self.actor = replace(self.actor, targets=[self.pin, self.destination])
        owner = self.owner()
        request = self.request
        def lost(*args, **kwargs):
            value = request(*args, **kwargs)
            if args[2] == 'thread/fork':
                self.child_path.write_text(''.join(json.dumps(dict(row, timestamp='2026-11-07T11:00:00Z'))+'\n' for row in rows))
                raise TimeoutError('lost native result')
            return value
        owner.request = lost
        owner.execute(self.actor, 'history.import', self.arguments, authorize=lambda: self.actor)
        args = copy.deepcopy(self.arguments)
        # Reconciliation reuses the original immutable operation, not a retry.
        owner = self.owner()
        def recovery(endpoint, executable, method, params, timeout, **kwargs):
            if method == 'thread/list':
                return {'data': [dict(id=CHILD, forkedFromId=SOURCE)], 'nextCursor': None}
            return request(endpoint, executable, method, params, timeout, **kwargs)
        owner.request = recovery
        value = owner.execute(self.actor, 'history.import', args, authorize=lambda: self.actor)['result']['operation']
        self.assertEqual(value['execution'], 'completed')
        self.assertEqual(value['result']['thread_id'], CHILD)
        self.assertEqual(self.forks, 1)

    def test_import_is_exposed_as_explicit_source_destination_cli_operation(self):
        import argparse
        from codex_wake.history_commands import register_parser
        parser=argparse.ArgumentParser()
        register_parser(parser.add_subparsers(dest='command',required=True))
        args=parser.parse_args(['history','import',SOURCE,'--owner','alice','--destination','bob','--channel','modded',
            '--expected-source',json.dumps(self.pin),'--expected-target',json.dumps(self.destination),'--idempotency-key','copy-1'])
        self.assertEqual(args.destination,'bob')
        self.assertEqual(args.expected_source,self.pin)
