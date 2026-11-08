import tempfile
import unittest
from codex_wake.controller_tabs import ControllerTabs


class TabViewTests(unittest.TestCase):
    def test_public_saved_view_roundtrip_and_trait_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            owner=ControllerTabs(directory,workspaces={},host='h',environment='e')
            definition=dict(filters={'harness':'codex','error':'present'},group_by=['remote_host','build'],sort_by=['activity'])
            saved=owner.execute('tabs.view-save',dict(name='errors',definition=definition))
            self.assertEqual(saved['view']['definition'],definition)
            recreated=ControllerTabs(directory,workspaces={},host='h',environment='e')
            self.assertEqual(recreated.execute('tabs.view-show',dict(name='errors'))['view'],saved['view'])

    def test_filter_uses_qualified_traits_and_named_membership_survives_only_same_birth(self):
        from codex_wake.tab_views import TabViews
        def resource(window,build,error,birth):
            return dict(target={'workspace':'fixture'},window={'window_id':window,'panes':[{'pane_id':'%'+window[1:],'process_generation':birth}]},
                        traits={'traits':{'harness':dict(value='codex',status='observed'),
                                          'build':dict(value=build,status='observed'),
                                          'error':dict(value=error,status='observed')}})
        with tempfile.TemporaryDirectory() as directory:
            owner=TabViews(directory)
            rows=[resource('@1','stock','absent',1),resource('@2','modded','present',2)]
            owner.execute('tabs.group-save',dict(name='work',members=['fixture/@2']),resources=rows)
            owner.execute('tabs.view-save',dict(name='errors',definition=dict(group='work',filters={'error':'present'},group_by=['build'])))
            result=owner.execute('tabs.view-evaluate',dict(name='errors'),resources=rows)
            self.assertEqual(result['groups'],[dict(key=['modded'],attachments=['fixture/@2'])])
            self.assertFalse(result['physical_effects'])
            rows[1]['window']['panes'][0]['process_generation']=3
            self.assertEqual(owner.execute('tabs.view-evaluate',dict(name='errors'),resources=rows)['resources'],[])

    def test_windows_named_group_cannot_adopt_a_reused_native_pid(self):
        from codex_wake.tab_views import TabViews
        with tempfile.TemporaryDirectory() as directory:
            owner=TabViews(directory)
            row=dict(target={'workspace':'native'},window={'window_id':'@1','panes':[dict(pane_id='%1',platform='windows',windows_creation_filetime=10)]})
            owner.execute('tabs.group-save',dict(name='work',members=['native/@1']),resources=[row])
            owner.execute('tabs.view-save',dict(name='work',definition=dict(group='work')))
            row['window']['panes'][0]['windows_creation_filetime']=11
            self.assertEqual(owner.execute('tabs.view-evaluate',dict(name='work'),resources=[row])['resources'],[])
