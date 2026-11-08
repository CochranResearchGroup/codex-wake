import copy
import subprocess
import time
import unittest
from unittest.mock import patch

from codex_wake.tab_traits import _trait


class ManagedTraitsTests(unittest.TestCase):
    def setUp(self):
        self.owner=type('Owner',(),{'root':'/tmp','calls':0})()
        self.window={'attach_intent':'a'*32,'panes':[{'pane_id':'%1','pid':777,'platform':'windows'}]}
        names=('harness','build','account','repository','remote_host','session_presence','activity','health','error')
        self.existing={'panes':[{'pane_id':'%1','platform':'windows','processes':[{'pid':777,'platform':'windows'}],
            'traits':{k:_trait(reason='windows_unknown') for k in names},'binding':None}],
            'traits':{k:_trait(reason='windows_unknown') for k in names},'mixed':False}
        self.existing['panes'][0]['traits']['error']=_trait('present',source='current_visible_screen',status='observed')
        self.binding={'provenance':'verified_managed_reattachment','identity':{'runtime':'codex','namespace':'exact-account','conversation_id':'thread'},
            'process':{'pid':123,'start_time_ticks':99,'boot_id':'boot'},
            'native_row':{'cwd':'/project','runtime_state':'idle','target':{'account':'research','executable':'/fixed/codex','build_sha256':'b'*64}},
            'health':{'observation':{'status':'responsive','responsive':True,'evidence':'tui_main_loop_ack','observed_at':time.time()}}}
        def binding_for(workspace,window,*,deadline):
            self.owner.calls+=1
            self.assertLessEqual(deadline,self.deadline)
            return self.binding
        self.owner.binding_for=binding_for
        self.deadline=time.monotonic()+5

    def observe(self):
        from codex_wake.tab_reattach_traits import observe_managed
        with patch('codex_wake.tab_reattach_traits.process_identity',return_value={'start_time_ticks':99,'boot_id':'boot'}) as probe,patch('codex_wake.tab_traits.TabTraits._registered_build',return_value='modded'):
            result=observe_managed(self.owner,'destination',self.window,self.existing,self.deadline)
            self.assertTrue(all(call.args==(123,) for call in probe.call_args_list))
            return result

    def test_verified_linux_binding_overrides_traits_without_replacing_windows_identity_or_error(self):
        original=copy.deepcopy(self.existing)
        result=self.observe()
        self.assertEqual(result['traits']['harness']['value'],'codex')
        self.assertEqual(result['traits']['account']['value'],'research')
        self.assertEqual(result['traits']['activity']['value'],'idle')
        self.assertEqual(result['traits']['health']['value'],'responsive')
        self.assertEqual(result['traits']['build']['value'],'modded')
        self.assertEqual(result['panes'][0]['processes'],original['panes'][0]['processes'])
        self.assertEqual(result['panes'][0]['traits']['error'],original['panes'][0]['traits']['error'])
        self.assertEqual(self.existing,original)

    def test_unknown_or_changed_binding_is_exact_noop(self):
        self.binding=None
        self.assertIs(self.observe(),self.existing)
        self.binding={'provenance':'unverified'}
        self.assertIs(self.observe(),self.existing)

    def test_stale_process_and_non_native_health_are_noop(self):
        self.binding['process']['start_time_ticks']=100
        self.assertIs(self.observe(),self.existing)
        self.binding['process']['start_time_ticks']=99
        self.binding['health']['observation']['evidence']='socket_connect'
        self.assertIs(self.observe(),self.existing)

    def test_bridge_timeout_preserves_existing_evidence(self):
        def timeout(*args,**kwargs):
            raise subprocess.TimeoutExpired('fixed-host-bridge',.1)
        self.owner.binding_for=timeout
        self.assertIs(self.observe(),self.existing)

    def test_global_deadline_and_probe_cap_bound_all_windows(self):
        self.observe();self.observe();self.observe()
        self.assertEqual(self.owner.calls,2)
        self.deadline=time.monotonic()-1
        self.assertIs(self.observe(),self.existing)
        self.assertEqual(self.owner.calls,2)
