"""Human target behavior through public CLI; fixtures do not authorize live effects."""
import io
import json
import unittest
from unittest.mock import patch

from codex_wake.cli import main
from tests.test_sessions import pane, snapshot


class TabTargetTests(unittest.TestCase):
    def invoke(self, selector, state=None, *options):
        state = state or snapshot(panes=[pane('18', 'policies')])
        with patch('codex_wake.sessions_cli.observe', return_value=state), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            code = main(['sessions', 'resolve', selector, '--json', *options])
        return code, json.loads(output.getvalue())

    def test_informal_descriptors_resolve_without_caller_enumeration(self):
        for descriptor in ('tab 18', '18:policies', 'poicys', ' Policies '):
            with self.subTest(descriptor=descriptor):
                code, value = self.invoke(descriptor)
                self.assertEqual(code, 0, value)
                self.assertEqual(value['session']['thread_id'], 'full-thread-id')
                self.assertIn(value['resolution']['match_method'], ('index', 'exact', 'normalized', 'fuzzy'))

    def test_target_conditions_distinguish_missing_dormant_busy_and_cwd(self):
        cases = [
            ('absent', snapshot(panes=[pane('18', 'policies')]), [], 'tab_not_found'),
            ('tab 18', snapshot(panes=[pane('18', 'policies', pid=None)]), [], 'no_live_codex'),
            ('18', snapshot(threads=[dict(id='full-thread-id', name='Session', cwd='/repo',
                 status={'type':'active'})], panes=[pane('18','policies')]), [], 'target_busy'),
            ('18', snapshot(panes=[pane('18','policies')]), ['--expected-cwd','/other'], 'cwd_mismatch'),
            ('18:other', snapshot(panes=[pane('18','policies')]), [], 'descriptor_conflict'),
        ]
        for selector, state, options, expected in cases:
            with self.subTest(expected=expected), patch('codex_wake.tab_targets.observe', return_value=state), \
                    patch('sys.stdout', new_callable=io.StringIO) as output:
                self.assertNotEqual(main(['sessions','target',selector,'--json',*options]),0)
                value=json.loads(output.getvalue())
                self.assertEqual(value['status'],expected)
                self.assertEqual(value['effects'],[])

    def test_exact_name_wins_fuzzy_ties_hold_and_partial_is_not_absence(self):
        state=snapshot(panes=[pane('18','policies'),pane('19','policy',identifier='%19')])
        self.assertEqual(self.invoke('policies',state)[0],0)
        code,value=self.invoke('polics',state)
        self.assertEqual(code,4,value)
        state['complete']=False
        code,value=self.invoke('absent',state)
        self.assertEqual(code,5,value)

    def test_normalized_numeric_name_precedes_a_different_tab_index(self):
        state=snapshot(panes=[pane('4','18'),pane('18','policies',identifier='%18')])
        code,value=self.invoke(' 18 ',state)
        self.assertEqual(code,0,value)
        self.assertEqual(value['session']['selected_attachment']['window_name'],'18')

    def test_saved_history_is_cwd_scoped_complete_and_metadata_only(self):
        from tests.test_shared_app_server import SharedReaderTests, result
        fixture=SharedReaderTests();fixture.setUp()
        try:
            reader,connection=fixture.reader([result(1,{}),result(2,{'data':[
                dict(id='saved',cwd='/repo',name='Policies',updatedAt=123,source='cli',
                     status={'type':'notLoaded'},preview='PRIVATE',turns=['PRIVATE'])],
                'nextCursor':None})])
            with reader:
                rows=reader.saved_threads('/repo')
            self.assertEqual(rows,[dict(id='saved',cwd='/repo',name='Policies',updatedAt=123,
                                       source='cli',status={'type':'notLoaded'})])
            request=connection.sent[-1]
            self.assertEqual(request['method'],'thread/list')
            self.assertEqual(request['params']['cwd'],'/repo')
            self.assertIs(request['params']['archived'],False)
            self.assertIn('vscode',request['params']['sourceKinds'])
        finally:fixture.doCleanups()

    def test_nondefault_policy_requires_host_scope_before_any_effect(self):
        state=snapshot(panes=[pane('18','policies',pid=None)])
        with patch('codex_wake.tab_targets.observe', return_value=state), \
                patch('sys.stdout', new_callable=io.StringIO) as out, \
                patch('subprocess.run') as external:
            self.assertEqual(main(['sessions','target','tab 18','--on-inactive','fresh','--json']),5)
        self.assertEqual(json.loads(out.getvalue())['status'],'policy_denied')
        external.assert_not_called()


class TargetLifecycleTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.profiles=self.root/'profiles.json'
        self.profile=dict(cwd=str(self.root), app_server='unix:///fixture.sock',codex_path='/bin/true',
                          tmux_session='byobu',tmux_socket='/tmp/example',timeout=1)
        self.profiles.write_text(json.dumps(dict(version=1,profiles={'worker':self.profile},
                                                callers={'caller':['worker']})))
        self.shell=pane('18','policies',pid=None)
        self.shell.update(pane_current_path=str(self.root),pane_current_command='bash',pane_pid='9')
        self.state=snapshot(threads=[],panes=[self.shell]);self.saved=[];self.calls=[]

    def call(self, *options, selector='tab 18'):
        from contextlib import redirect_stdout
        output=io.StringIO()
        with redirect_stdout(output),patch('codex_wake.tab_targets.observe',return_value=self.state), \
                patch('codex_wake.target_lifecycle.observe',return_value=self.state), \
                patch('codex_wake.target_lifecycle.saved_history',side_effect=lambda *a:self.saved), \
                patch('codex_wake.native_clock.snapshot',return_value={'utc':{'lower':1,'upper':2}}), \
                patch('codex_wake.target_lifecycle.native_request',side_effect=self.native), \
                patch('codex_wake.target_lifecycle.tmux_command',side_effect=self.tmux):
            code=main(['--wake-root',str(self.root),'sessions','target',selector,'--json',
                '--profiles',str(self.profiles),'--profile','worker','--intent','fixture',
                '--caller-thread-id','caller','--expires-at','2030-01-01T00:00:00Z',
                '--app-server','unix:///fixture.sock','--tmux-socket','/tmp/example',
                '--tmux-session','byobu',*options])
        return code,json.loads(output.getvalue())

    def native(self, endpoint,codex,method,params,timeout):
        self.calls.append((method,params))
        return {'thread':dict(id=params.get('threadId','new-thread'),cwd=str(self.root),name='Saved',
                              status={'type':'notLoaded'})}

    def tmux(self, args,*command,**kwargs):
        self.calls.append((command[0],command[1:]))
        return '@18\t%19' if command[0]=='split-window' else '@19\t%19'

    def test_missing_and_inactive_policy_matrix_keeps_effects_explicit(self):
        for n,(selector,option,policy,expected) in enumerate([
                ('missing-worker','--on-missing','error','tab_not_found'),
                ('missing-worker','--on-missing','tab_only','tab_created'),
                ('missing-worker','--on-missing','fresh','starting'),
                ('missing-worker','--on-missing','resume','resume_not_found'),
                ('tab 18','--on-inactive','error','no_live_codex'),
                ('tab 18','--on-inactive','tab_only','tab_ready'),
                ('tab 18','--on-inactive','fresh','starting'),
                ('tab 18','--on-inactive','resume','resume_not_found')]):
            with self.subTest(selector=selector,policy=policy):
                self.calls=[]
                code,value=self.call(option,policy,'--intent','matrix'+str(n),selector=selector)
                self.assertEqual(value['status'],expected,value)
                if policy in ('error','resume') or expected=='tab_ready':
                    self.assertEqual(self.calls,[])

    def test_resume_zero_and_multiple_histories_never_launch_or_fallback(self):
        for rows,expected in [([], 'resume_not_found'),([
            dict(id='a',cwd=str(self.root)),dict(id='b',cwd=str(self.root))],'resume_ambiguous')]:
            with self.subTest(expected=expected):
                self.saved=rows
                code,value=self.call('--on-inactive','resume')
                self.assertEqual(value['status'],expected,value)
                self.assertEqual(self.calls,[])
                self.assertEqual(value['effects'],[])

    def test_fresh_preserves_shell_and_repeated_intent_does_not_create_again(self):
        code,value=self.call('--on-inactive','fresh')
        self.assertEqual(value['status'],'starting',value)
        self.assertEqual(value['thread_id'],'new-thread')
        self.assertEqual([m for m,p in self.calls],['thread/start','thread/name/set','split-window'])
        self.assertEqual(value['effects'][-1]['preserved_pane_id'],'%15')
        self.assertNotIn('-k',self.calls[-1][1])
        self.calls=[]
        code,value=self.call('--on-inactive','fresh')
        self.assertEqual(value['thread_id'],'new-thread')
        self.assertEqual(self.calls,[])

    def test_missing_tab_only_needs_profile_cwd_and_never_starts_codex(self):
        code,value=self.call('--on-missing','tab_only',selector='new-worker')
        self.assertEqual(value['status'],'tab_created',value)
        self.assertEqual([m for m,p in self.calls],['new-window'])
        self.assertIsNone(value.get('thread_id'))
        self.calls=[]
        self.assertEqual(self.call('--on-missing','tab_only',selector='new-worker')[1]['status'],'tab_created')
        self.assertEqual(self.calls,[])

    def test_resume_launches_exact_saved_thread_without_creating_or_renaming_history(self):
        self.saved=[dict(id='saved-thread',cwd=str(self.root),name='Saved')]
        code,value=self.call('--on-inactive','resume')
        self.assertEqual(value['status'],'starting',value)
        self.assertEqual(value['thread_id'],'saved-thread')
        self.assertEqual([m for m,p in self.calls],['thread/read','split-window'])
        self.assertIn('saved-thread',self.calls[-1][1][-1])

    def test_exact_resume_validates_cwd_even_when_native_history_list_omits_empty_thread(self):
        self.saved=[]
        code,value=self.call('--on-inactive','resume','--resume-thread-id','exact-thread')
        self.assertEqual(value['status'],'starting',value)
        self.assertEqual(value['thread_id'],'exact-thread')
        self.assertNotIn('thread/start',[m for m,p in self.calls])

    def test_lost_launch_reply_holds_same_intent_without_duplicate_effects(self):
        original=self.tmux
        def lost(*args,**kwargs):
            original(*args,**kwargs)
            raise TimeoutError('fixture lost reply')
        self.tmux=lost
        code,value=self.call('--on-inactive','fresh')
        self.assertEqual(value['status'],'effect_uncertain',value)
        self.calls=[]
        self.assertEqual(self.call('--on-inactive','fresh')[1]['status'],'effect_uncertain')
        self.assertEqual(self.calls,[])

    def test_lost_tab_reply_reconciles_visible_exact_client_without_relaunch(self):
        original=self.tmux
        def lost(*args,**kwargs):
            original(*args,**kwargs)
            raise TimeoutError('fixture lost reply')
        self.tmux=lost
        self.assertEqual(self.call('--on-inactive','fresh')[1]['status'],'effect_uncertain')
        p=pane('18','policies',identifier='%19');p['pane_current_path']=str(self.root)
        self.state=snapshot(threads=[dict(id='new-thread',cwd=str(self.root),name='Session',
                                        status={'type':'idle'})],panes=[self.shell,p])
        self.calls=[]
        self.assertEqual(self.call('--on-inactive','fresh')[1]['status'],'resolved')
        self.assertEqual(self.calls,[])

    def test_startup_becomes_exact_ready_identity_and_reuse_is_detected(self):
        self.call('--on-inactive','fresh')
        p=pane('18','policies',identifier='%19');p['pane_current_path']=str(self.root)
        self.state=snapshot(threads=[dict(id='new-thread',cwd=str(self.root),name='Session',
                                        status={'type':'idle'})],panes=[self.shell,p])
        self.calls=[]
        code,value=self.call('--on-inactive','fresh')
        self.assertEqual(value['status'],'resolved',value)
        self.assertEqual(value['session']['selected_attachment']['pane_id'],'%19')
        self.assertEqual(self.calls,[])
        self.state=snapshot(threads=[],panes=[dict(p,client_start_time_ticks=999)])
        self.assertEqual(self.call('--on-inactive','fresh')[1]['status'],'target_changed')

    def test_completed_intent_recovers_after_transient_busy_without_retargeting(self):
        self.call('--on-inactive','fresh')
        p=pane('18','policies',identifier='%19');p['pane_current_path']=str(self.root)
        thread=dict(id='new-thread',cwd=str(self.root),name='Session',status={'type':'idle'})
        self.state=snapshot(threads=[thread],panes=[self.shell,p])
        self.assertEqual(self.call('--on-inactive','fresh')[1]['status'],'resolved')
        thread['status']={'type':'active'}
        self.state=snapshot(threads=[thread],panes=[self.shell,p])
        self.assertEqual(self.call('--on-inactive','fresh')[1]['status'],'target_busy')
        thread['status']={'type':'idle'}
        self.state=snapshot(threads=[thread],panes=[self.shell,p])
        self.assertEqual(self.call('--on-inactive','fresh')[1]['status'],'resolved')

    def test_changed_options_and_profile_or_cwd_cannot_reuse_launch_intent(self):
        self.call('--on-inactive','fresh')
        self.calls=[]
        self.assertEqual(self.call('--on-inactive','resume')[1]['status'],'policy_denied')
        self.assertEqual(self.calls,[])

class HumanSendTests(unittest.TestCase):
    def test_initial_busy_send_holds_identity_across_replacement(self):
        from tests.test_messages_cli import MessageCLITests
        fixture=MessageCLITests();fixture.setUp()
        try:
            p=pane('18','policies');p['pane_current_path']=str(fixture.repo)
            thread=dict(id='recipient',name='Session',cwd=str(fixture.repo),status={'type':'active'})
            state=snapshot(threads=[thread],panes=[p])
            args=['send','--to','tab 18','--body-file',str(fixture.body),
                  '--idempotency-key','busy-send','--delivery','inbox']
            with patch('codex_wake.tab_targets.observe',return_value=state):
                self.assertEqual(fixture.invoke(args)[1][0]['target']['status'],'target_busy')
            state=snapshot(threads=[dict(thread,id='replacement',status={'type':'idle'})],
                           panes=[dict(p,client_start_time_ticks=999)])
            with patch('codex_wake.tab_targets.observe',return_value=state):
                self.assertEqual(fixture.invoke(args)[1][0]['target']['status'],'target_changed')
            self.assertEqual(fixture.invoke(['outbox'])[1][0]['messages'],[])
        finally:fixture.doCleanups()

    def test_message_send_resolves_and_pins_inside_service_and_holds_reused_tab(self):
        from tests.test_messages_cli import MessageCLITests
        fixture=MessageCLITests();fixture.setUp()
        try:
            p=pane('18','policies');p['pane_current_path']=str(fixture.repo)
            state=snapshot(threads=[dict(id='recipient',name='Session',cwd=str(fixture.repo),
                                        status={'type':'idle'})],panes=[p])
            arguments=['send','--to','poicys','--body-file',str(fixture.body),
                       '--idempotency-key','human-send','--delivery','inbox']
            with patch('codex_wake.tab_targets.observe',return_value=state):
                code,values=fixture.invoke(arguments)
            self.assertEqual(code,0,values)
            original=values[0]['message']['message_id']
            self.assertEqual(values[0]['target']['session']['thread_id'],'recipient')
            changed=snapshot(threads=[dict(id='replacement',name='Session',cwd=str(fixture.repo),
                                           status={'type':'idle'})],panes=[dict(p,client_start_time_ticks=999)])
            with patch('codex_wake.tab_targets.observe',return_value=changed):
                code,values=fixture.invoke(arguments)
            self.assertNotEqual(code,0)
            self.assertEqual(values[0]['target']['status'],'target_changed')
            self.assertEqual(fixture.invoke(['outbox'])[1][0]['messages'][0]['message_id'],original)
            self.assertEqual(len(fixture.invoke(['outbox'])[1][0]['messages']),1)
        finally:fixture.doCleanups()

