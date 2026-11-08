"""Public route/admission regressions; native execution has a separate receipt."""
import contextlib
import io
import json
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch
import test_tab_reattach as fixture
from codex_wake.controller_tabs import ControllerTabs,AuthorizedTabs
from codex_wake.controller_auth import Actor,AuthError
from codex_wake.controller_runtime import ControllerRuntime


class ReattachPublicTests(unittest.TestCase):
    setUp=fixture.TabReattachTests.setUp
    tmux=fixture.TabReattachTests.tmux
    owner=fixture.TabReattachTests.owner

    def test_cli_preview_apply_and_status_use_retained_plan_without_workspace(self):
        from codex_wake.cli import run
        tabs=ControllerTabs(self.root,workspaces=self.workspaces,host='fixture',environment='fixture')
        owner=self.owner()
        tabs.reattach_owner=lambda:owner
        def cli(*args):
            out=io.StringIO()
            with patch('codex_wake.controller_tabs.controller_tabs_from_root',return_value=tabs),contextlib.redirect_stdout(out):
                code=run(['--wake-root',str(self.root),'tabs',*args])
            self.assertEqual(code,0,out.getvalue())
            return json.loads(out.getvalue())
        preview=cli('reattach-preview','--workspace','source','--window',self.source_window,'--destination','destination')
        ready=preview['result']['operation']['result']
        self.assertEqual(ready['status'],'ready')
        result=cli('reattach-apply','--plan-id',ready['plan_id'])
        applied=result['result']['operation']['result']
        self.assertEqual(applied['status'],'applied')
        self.assertTrue(applied['source_preserved'])
        status=cli('reattach-status','--plan-id',ready['plan_id'])
        self.assertEqual(status['status'],'applied')
        self.assertEqual(self.runtime.launches,1)

    def test_apply_checks_retained_destination_even_when_caller_omits_destination(self):
        tabs=ControllerTabs(self.root,workspaces=self.workspaces,host='fixture',environment='fixture')
        owner=self.owner();tabs.reattach_owner=lambda:owner
        ready=owner.execute('tabs.reattach-preview',dict(workspace='source',window=self.source_window,
            destination='destination',expected_target=owner.lifecycle.inspect('source')['target'],
            expected_destination=owner.lifecycle.inspect('destination')['target']))
        actor=Actor('caller','service','client','grant','issuer','resource',frozenset(['control']),[ready['target']],time.time()+60)
        admission=AuthorizedTabs(SimpleNamespace(authenticate=lambda token:actor),tabs,ControllerRuntime(self.root))
        with self.assertRaises(AuthError):
            admission.execute('token','tabs.reattach-apply',dict(plan_id=ready['plan_id'],expected_target=ready['target']))
        self.assertEqual(self.runtime.launches,0)
