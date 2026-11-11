"""An exact active-tab wake must not rediscover Codex from the monitor's PATH."""
import unittest
from unittest.mock import patch
from codex_wake.native_delivery import _codex_adapter
from codex_wake.shared_app_server import SharedSourceError

THREAD='11111111-1111-4111-8111-111111111111'
CODEX='/synthetic/pinned/bin/codex'
ENDPOINT='unix:///synthetic/daemon.sock'

class ActiveTabExecutableTests(unittest.TestCase):
    def observe(self, *, endpoint='unix://', attached=True):
        thread={'id':THREAD,'name':'Synthetic receiver','cwd':'/synthetic/work','status':{'type':'idle'}}
        panes=[{'pane_title':'Synthetic receiver','pane_current_path':'/synthetic/work','client_pid':123,'client_start_time_ticks':7}] if attached else []
        calls=[]
        def locate(*,codex_cmd=None,timeout=10):
            calls.append(codex_cmd)
            if codex_cmd!=CODEX:raise SharedSourceError('synthetic monitor PATH has no codex')
            return ENDPOINT
        class Reader:
            def __init__(self,actual,**kwargs):
                if actual!=ENDPOINT:raise AssertionError('wrong endpoint')
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def loaded_threads(self):return [thread]
        with patch('codex_wake.native_delivery.read_native_thread',return_value=thread), \
             patch('codex_wake.shared_app_server.locate_shared_endpoint',side_effect=locate), \
             patch('codex_wake.sessions.locate_shared_endpoint',side_effect=locate), \
             patch('codex_wake.sessions.SharedAppServerReader',Reader), \
             patch('codex_wake.sessions.tmux_inventory',return_value=panes):
            adapter=_codex_adapter()
            target={'transport':'native','thread_id':THREAD,'endpoint':endpoint,'codex_cmd':CODEX,'startup_policy':'active_tab'}
            result=adapter.observe(adapter.resolve(target))
        return result,calls

    def test_monitor_without_path_codex_uses_pinned_executable_for_attachment(self):
        observation,calls=self.observe()
        self.assertEqual(observation.state,'ready')
        self.assertEqual(observation.capabilities['active_tab'].state,'supported',
                         'attached exact recipient must remain usable without PATH codex')
        self.assertEqual(calls,[CODEX])

    def test_explicit_endpoint_needs_no_executable_rediscovery(self):
        observation,calls=self.observe(endpoint=ENDPOINT)
        self.assertEqual(observation.capabilities['active_tab'].state,'supported')
        self.assertEqual(calls,[])

    def test_pinned_executable_does_not_grant_an_unbound_tab(self):
        observation,_=self.observe(attached=False)
        self.assertEqual(observation.capabilities['active_tab'].state,'unavailable')
