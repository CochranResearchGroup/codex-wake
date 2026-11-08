import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.managed_inventory import InventoryError


@unittest.skipUnless(shutil.which('tmux'),'tmux required')
class ProfileCreateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.root.chmod(0o700)
        self.socket=str(self.root/'tmux.sock')
        subprocess.run(['tmux','-S',self.socket,'new-session','-d','-s','test','sleep 60'],check=True)
        self.addCleanup(lambda:subprocess.run(['tmux','-S',self.socket,'kill-server'],capture_output=True))
        self.transport=TmuxAttachmentTransport(self.socket,'$0')

    def owner(self):
        from codex_wake.tab_profile_create import TabProfileCreate
        return TabProfileCreate(self.root,host='fixture',environment='fixture')

    def create(self,profile,**kwargs):
        return self.owner().create(profile,transport=self.transport,name='selected',cwd=str(self.root),
                                  deadline=time.monotonic()+5,guard=lambda:None,**kwargs)

    def test_missing_profile_never_falls_back_to_shell(self):
        before=self.transport.snapshot(time.monotonic()+2)
        with self.assertRaises(InventoryError):self.create('missing')
        self.assertEqual(len(self.transport.snapshot(time.monotonic()+2)['windows']),len(before['windows']))

    def configure(self,exit_immediately=False):
        if not shutil.which('cc'):self.skipTest('C fixture compiler required')
        home=self.root/'accounts'/'codex-fixture';home.mkdir(parents=True,mode=0o700)
        source=self.root/'fixture.c';source.write_text('#include <unistd.h>\nint main(void){'+('return 2;' if exit_immediately else 'sleep(60);return 0;')+'}\n')
        binary=self.root/'codex';subprocess.run(['cc','-o',str(binary),str(source)],check=True,capture_output=True)
        manifest=self.root/'builds.json';manifest.write_text(json.dumps({'schema_version':1,'builds':{'modded':{
            'executable':str(binary),'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'upstream_version':'fixture','revision':'fixture','source':'synthetic-fixture'}}}))
        (self.root/'controller-accounts.toml').write_text('[profiles]\nstate_root='+json.dumps(str(home.parent))+'\nselection_mode="launcher"\nknown_profiles=["fixture"]\nshared_links=[]\n[builds]\nmanifest='+json.dumps(str(manifest))+'\n')
        return home,binary

    def test_selected_alias_launch_owns_exact_child_and_home_without_shell_fallback(self):
        home,binary=self.configure()
        result=self.create('fixture')
        self.assertEqual(result['status'],'applied',result)
        self.assertEqual(result['profile'],'codex-fixture')
        self.assertEqual(result['profile_target']['home'],str(home))
        self.assertEqual(result['profile_target']['executable'],str(binary))
        self.assertEqual(result['profile_target']['build_channel'],'modded')
        self.assertGreater(result['process']['pid'],0)
        self.assertEqual(self.owner().authorization_target('fixture')['account'],'codex-fixture')
        from codex_profiles.build_channels import _home_ownership,BuildError
        with self.assertRaises(BuildError):
            with _home_ownership(home):pass

    def test_profile_preview_stale_build_and_exited_child_never_become_shell(self):
        home,binary=self.configure(exit_immediately=True)
        before=len(self.transport.snapshot(time.monotonic()+2)['windows'])
        self.assertEqual(self.create('fixture',preview=True)['status'],'preview')
        self.assertEqual(len(self.transport.snapshot(time.monotonic()+2)['windows']),before)
        result=self.create('fixture')
        self.assertIn(result['status'],('held','uncertain'))
        binary.write_bytes(binary.read_bytes()+b'changed')
        with self.assertRaises(InventoryError) as caught:self.create('fixture')
        self.assertEqual(caught.exception.code,'stale_target')
