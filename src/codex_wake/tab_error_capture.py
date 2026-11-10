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
    def __init__(self, original, candidates, scheduler, privacy, force):
        self.original=original
        self.pending=candidates
        self.scheduler=scheduler
        self.privacy=privacy
        self.force=force
        self.screens={}
        self.unavailable=False
        self.total_bytes=0

    def __getattr__(self,name):
        return getattr(self.original,name)

    def command(self,deadline,*args):
        return self.original.command(deadline,*args)

    def _owned(self,pane):
        if self.privacy is not None:
            return self.privacy(pane['pane_id'])=='safe'
        try:
            return (Path('/proc',str(pane.get('pid'))).stat().st_uid==os.geteuid()
                    and Path(self.original.socket).lstat().st_uid==os.geteuid())
        except OSError:
            return False

    def visible_screen(self,pane_id,deadline):
        from .tab_format_transport import _command_batch
        if pane_id not in self.screens and not self.unavailable:
            # A health inquiry may have advanced the cadence boundary since
            # inventory preparation. Select due panes at the actual read, not
            # earlier, and allow a later due cohort without retrying failures.
            due=[pane for pane,(row,key,eligible) in self.pending.items()
                 if self.scheduler.is_due('errors',key,force=self.force,eligible=eligible) and self._owned(row)]
            for offset in range(0,len(due),16):
                group=due[offset:offset+16]
                try:
                    values=_command_batch(self.original,[('capture-pane','-p','-e','-t',pane) for pane in group],deadline)
                    for pane,value in zip(group,values):
                        self.total_bytes+=len(value.encode())
                        if self.total_bytes>1048576:
                            raise OSError('capture batch capacity')
                        self.screens[pane]=value
                        self.pending.pop(pane,None)
                except (OSError,ValueError,InventoryError,TabError,subprocess.SubprocessError):
                    self.unavailable=True
                    self.pending.clear()
                    break
        if pane_id not in self.screens:
            raise OSError('bounded current-screen capture unavailable')
        return self.screens.pop(pane_id)


def capture_transport(transport, panes, *, investigated, scheduler, namespace,
                      active_panes=(), dirty_panes=(), privacy=None, force=False):
    """Batch only due, same-user, privacy-qualified native panes."""
    if not isinstance(transport,TmuxTransport) or not scheduler.status()['enabled']['errors']:
        return transport
    from .tab_traits import error_check_key
    candidates={}
    for pane in panes[:512]:
        pane_id=pane.get('pane_id')
        if not isinstance(pane_id,str) or not re.fullmatch(r'%[0-9]+',pane_id):
            continue
        identities=[row['process'] for row in investigated.get(pane.get('pid'),([],False))[0]]
        key=error_check_key(namespace,pane_id,identities)
        candidates[pane_id]=(pane,key,pane_id in active_panes or pane_id in dirty_panes)
    return _CaptureTransport(transport,candidates,scheduler,privacy,force) if len(candidates)>1 else transport
