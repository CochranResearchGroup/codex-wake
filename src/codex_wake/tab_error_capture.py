"""Ephemeral current-screen batches, classified by the existing error owner.

This adapter never enters persisted state. Raw screens are consumed once and
released at the end of one inventory pass; only redacted traits leave that pass.
"""
import os
from pathlib import Path
import re
import subprocess

from .managed_inventory import InventoryError
from .tab_organization import TmuxTransport, TabError


class _CaptureTransport(TmuxTransport):
    def __init__(self, original, panes):
        self.original=original
        self.pending=list(panes)
        self.screens={}
        self.loaded=False

    def __getattr__(self,name):
        return getattr(self.original,name)

    def command(self,deadline,*args):
        return self.original.command(deadline,*args)

    def visible_screen(self,pane_id,deadline):
        from .tab_format_transport import _command_batch
        if not self.loaded:
            self.loaded=True
            total=0
            for offset in range(0,len(self.pending),16):
                group=self.pending[offset:offset+16]
                try:
                    values=_command_batch(self.original,[('capture-pane','-p','-e','-t',pane) for pane in group],deadline)
                    for pane,value in zip(group,values):
                        total+=len(value.encode())
                        if total>1048576:
                            raise OSError('capture batch capacity')
                        self.screens[pane]=value
                except (OSError,ValueError,InventoryError,TabError,subprocess.SubprocessError):
                    # Incomplete or over-budget screens remain unknown; never
                    # manufacture an empty screen or a fresh negative result.
                    break
            self.pending.clear()
        if pane_id not in self.screens:
            raise OSError('bounded current-screen capture unavailable')
        return self.screens.pop(pane_id)


def capture_transport(transport, panes, *, investigated, scheduler, namespace,
                      active_panes=(), dirty_panes=(), privacy=None, force=False):
    """Batch only due, same-user, privacy-qualified native panes."""
    if not isinstance(transport,TmuxTransport) or not scheduler.status()['enabled']['errors']:
        return transport
    from .tab_traits import error_check_key
    due=[]
    for pane in panes:
        pane_id=pane.get('pane_id')
        if not isinstance(pane_id,str) or not re.fullmatch(r'%[0-9]+',pane_id):
            continue
        identities=[row['process'] for row in investigated.get(pane.get('pid'),([],False))[0]]
        key=error_check_key(namespace,pane_id,identities)
        if not scheduler.is_due('errors',key,force=force,eligible=pane_id in active_panes or pane_id in dirty_panes):
            continue
        try:
            if privacy is not None and privacy(pane_id)!='safe':
                continue
            if (Path('/proc',str(pane.get('pid'))).stat().st_uid!=os.geteuid()
                    or Path(transport.socket).lstat().st_uid!=os.geteuid()):
                continue
        except OSError:
            continue
        due.append(pane_id)
    return _CaptureTransport(transport,dict.fromkeys(due)) if len(set(due))>1 else transport
