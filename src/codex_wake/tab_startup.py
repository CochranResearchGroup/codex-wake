"""Local operator opt-in for an owned per-controller systemd user service."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from .managed_inventory import InventoryError
from .tab_monitor import TabMonitor, _lock, _read, _save


def _quote(value):
    value=str(value)
    if any(ord(c)<32 or ord(c)==127 for c in value):
        raise InventoryError('invalid_argument','Startup paths cannot contain control characters.')
    return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('%','%%').replace('$','$$')+'"'


class TabStartup:
    def __init__(self,root,*,unit_dir=None,runner=subprocess.run):
        self.monitor=TabMonitor(root)
        self.root=self.monitor.root
        self.runner=runner
        directory=Path(unit_dir) if unit_dir is not None else Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'systemd/user'
        name='codex-wake-tabs-'+hashlib.sha256(str(self.root).encode()).hexdigest()[:12]+'.service'
        self.unit=directory.resolve()/name
        self.manifest=self.monitor.directory/'startup.json'

    def unit_text(self):
        return ('# Managed by Codex Wake tab startup v1\n'
                '[Unit]\nDescription=Codex Wake tab monitor\n\n'
                '[Service]\nType=simple\nExecStart='+_quote(sys.executable)+
                ' -m codex_wake.tab_monitor --serve '+_quote(self.root)+'\n'
                'Restart=on-failure\nRestartSec=3\nTimeoutStopSec=10\n'
                'KillMode=control-group\nUMask=0077\n\n[Install]\nWantedBy=default.target\n')

    def systemd(self,*args,check=True):
        result=self.runner(['systemctl','--user',*args],capture_output=True,text=True,timeout=20)
        if check and result.returncode:
            raise InventoryError('startup_service_failed','User service command failed; inspect startup status and the unit journal.')
        return result

    def owned(self):
        manifest=_read(self.manifest)
        if self.unit.is_symlink():
            raise InventoryError('startup_unit_conflict','Startup unit must not be a symlink.')
        if self.unit.exists():
            if (not manifest or manifest.get('unit')!=str(self.unit)
                    or manifest.get('root')!=str(self.root)
                    or manifest.get('unit_text')!=self.unit.read_text()):
                raise InventoryError('startup_unit_conflict','Existing startup unit is foreign or edited; it was preserved.')
        return manifest

    def status(self):
        manifest=self.owned()
        enabled=self.systemd('is-enabled',self.unit.name,check=False)
        active=self.systemd('is-active',self.unit.name,check=False)
        return dict(status='inspection',unit=self.unit.name,unit_path=str(self.unit),root=str(self.root),
                    configured=bool(manifest and self.unit.exists()),
                    enabled=enabled.returncode==0,active=active.returncode==0,
                    service_state=active.stdout.strip() or 'unavailable')

    def execute(self,verb):
        if verb=='status':return self.status()
        if verb not in ('enable','disable'):
            raise InventoryError('invalid_argument','Startup supports enable, disable and status.')
        with _lock(self.monitor.directory/'startup.lock'):
            manifest=self.owned()
            # Verify a user manager before changing the unit or existing monitor.
            self.systemd('show-environment')
            if verb=='disable':
                if manifest and self.unit.exists():self.systemd('disable','--now',self.unit.name)
                return self.status()
            wanted=self.unit_text()
            before=self.status()
            if before['configured'] and before['enabled'] and before['active'] and self.unit.read_text()==wanted:
                return dict(before,already_enabled=True)
            if before['active'] and not manifest:
                raise InventoryError('startup_unit_conflict','A service with this name is already active without matching custody.')
            if before['active']:self.systemd('stop',self.unit.name)
            monitor=self.monitor.execute('tabs.monitor.stop',{})
            if monitor['monitor']['status']=='running':
                raise InventoryError('startup_monitor_busy','Existing monitor did not stop; no startup unit was changed.')
            self.unit.parent.mkdir(parents=True,exist_ok=True)
            fd,name=tempfile.mkstemp(dir=self.unit.parent,prefix='.wake-tabs-')
            try:
                with os.fdopen(fd,'w') as stream:
                    stream.write(wanted);stream.flush();os.fsync(stream.fileno())
                os.replace(name,self.unit)
            finally:
                if os.path.exists(name):os.unlink(name)
            _save(self.manifest,dict(schema_version=1,root=str(self.root),unit=str(self.unit),unit_text=wanted))
            self.systemd('daemon-reload')
            self.systemd('enable','--now',self.unit.name)
            result=self.status()
            if not result['active'] or not result['enabled']:
                raise InventoryError('startup_service_failed','Startup service did not become active and enabled; inspect its journal.')
            return dict(result,already_enabled=False)


def command(args):
    from .cli_output import emit
    from .shortcut_store import default_root
    from .records import WakeError
    try:
        value=TabStartup(default_root(args.wake_root)).execute(args.startup_command)
        emit(value,args)
        return 0
    except (WakeError,OSError,ValueError,subprocess.SubprocessError) as error:
        emit(dict(status='held',error=dict(code=getattr(error,'code','startup_unavailable'),
            message=str(error) if isinstance(error,WakeError) else 'Startup service is unavailable; inspect the user manager and owned unit.')),args)
        return 2
