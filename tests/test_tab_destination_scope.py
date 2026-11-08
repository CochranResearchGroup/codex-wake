import time
from types import SimpleNamespace
import unittest
from codex_wake.controller_auth import Actor,AuthError
from codex_wake.controller_tabs import AuthorizedTabs


class DestinationScopeTests(unittest.TestCase):
    def test_source_only_remote_grant_cannot_mutate_destination_workspace(self):
        source=dict(host='h',environment='e',workspace='source',presentation='tmux',generation='1')
        destination=dict(source,workspace='destination',generation='2')
        actor=Actor('caller','service','client','grant','issuer','resource',frozenset(['control']),[source],time.time()+60)
        class Runtime:
            def execute(self,*args,**kwargs):
                raise AssertionError('Destination mutation reached the effect owner without destination authority')
        facade=AuthorizedTabs(SimpleNamespace(authenticate=lambda token:actor),SimpleNamespace(execute=lambda op,args:None),Runtime())
        with self.assertRaises(AuthError):
            facade.execute('token','tabs.move',dict(workspace='source',expected_target=source,
                destination='destination',expected_destination=destination,window='@1'))

    def test_workspace_only_remote_grant_cannot_launch_an_ungranted_profile(self):
        source=dict(host='h',environment='e',workspace='source',presentation='tmux',generation='1')
        account=dict(host='h',environment='e',provider='codex',account='other',home='/synthetic/other')
        actor=Actor('caller','service','client','grant','issuer','resource',frozenset(['control']),[source],time.time()+60)
        class Runtime:
            def execute(self,*args,**kwargs):
                raise AssertionError('Profile launch reached effect owner without account authority')
        tabs=SimpleNamespace(profile_owner=lambda:SimpleNamespace(authorization_target=lambda profile:account))
        facade=AuthorizedTabs(SimpleNamespace(authenticate=lambda token:actor),tabs,Runtime())
        with self.assertRaises(AuthError):
            facade.execute('token','tabs.create',dict(workspace='source',expected_target=source,name='tab',profile='other'))
