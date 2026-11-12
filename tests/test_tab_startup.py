"""Local startup API over real private files and an injected systemd boundary."""
from pathlib import Path
import subprocess
import tempfile
import unittest


class StartupTests(unittest.TestCase):
    def test_owned_service_enable_is_idempotent_and_disable_retains_other_units(self):
        from codex_wake.tab_startup import TabStartup
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'root';units=Path(directory)/'units'
            units.mkdir();foreign=units/'unrelated.service';foreign.write_text('keep')
            active=False;enabled=False;calls=[]
            def systemd(argv,**kwargs):
                nonlocal active,enabled
                calls.append(argv)
                if 'enable' in argv:active=enabled=True
                if 'disable' in argv:active=enabled=False
                code=0;out=''
                if 'is-active' in argv:code=0 if active else 3;out='active' if active else 'inactive'
                if 'is-enabled' in argv:code=0 if enabled else 1;out='enabled' if enabled else 'disabled'
                return subprocess.CompletedProcess(argv,code,out,'')
            owner=TabStartup(root,unit_dir=units,runner=systemd)
            self.assertFalse(owner.execute('status')['enabled'])
            result=owner.execute('enable')
            self.assertTrue(result['enabled']);self.assertTrue(result['active'])
            text=owner.unit.read_text()
            self.assertIn('-m codex_wake.tab_monitor --serve',text)
            self.assertIn('WantedBy=default.target',text)
            self.assertIn('Restart=on-failure',text)
            enables=len([row for row in calls if 'enable' in row])
            self.assertTrue(owner.execute('enable')['active'])
            self.assertEqual(len([row for row in calls if 'enable' in row]),enables)
            self.assertFalse(owner.execute('disable')['enabled'])
            self.assertEqual(foreign.read_text(),'keep')
            self.assertTrue(owner.unit.exists())
            from codex_wake.managed_inventory import InventoryError
            owner.unit.write_text(text+'# edited externally\n')
            with self.assertRaises(InventoryError) as error:owner.execute('disable')
            self.assertEqual(error.exception.code,'startup_unit_conflict')
            self.assertEqual(owner.unit.read_text(),text+'# edited externally\n')

    def test_foreign_or_edited_unit_is_never_overwritten(self):
        from codex_wake.tab_startup import TabStartup
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            owner=TabStartup(Path(directory)/'root',unit_dir=Path(directory)/'units',
                             runner=lambda argv,**kw:subprocess.CompletedProcess(argv,0,'',''))
            owner.unit.parent.mkdir(parents=True)
            owner.unit.write_text('foreign unit')
            with self.assertRaises(InventoryError) as error:owner.execute('enable')
            self.assertEqual(error.exception.code,'startup_unit_conflict')
            self.assertEqual(owner.unit.read_text(),'foreign unit')

    def test_unit_escapes_systemd_specifiers_and_quoted_paths(self):
        from codex_wake.tab_startup import TabStartup
        with tempfile.TemporaryDirectory() as directory:
            owner=TabStartup(Path(directory)/'root %i $HOME "quoted"',unit_dir=Path(directory)/'units')
            text=owner.unit_text()
            self.assertIn('%%i',text)
            self.assertIn('$$HOME',text)
            self.assertIn('\\"quoted\\"',text)
            self.assertNotIn('ExecStart=/bin/sh',text)
