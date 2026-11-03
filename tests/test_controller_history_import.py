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

    def test_import_is_exposed_as_explicit_source_destination_cli_operation(self):
        import argparse
        from codex_wake.history_commands import register_parser
        parser=argparse.ArgumentParser()
        register_parser(parser.add_subparsers(dest='command',required=True))
        args=parser.parse_args(['history','import',SOURCE,'--owner','alice','--destination','bob','--channel','modded',
            '--expected-source',json.dumps(self.pin),'--expected-target',json.dumps(self.destination),'--idempotency-key','copy-1'])
        self.assertEqual(args.destination,'bob')
        self.assertEqual(args.expected_source,self.pin)
