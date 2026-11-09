"""Durable routing holds keyed by process birth, independent of tab placement."""
from pathlib import Path
from .shortcut_store import read, write, locked
from .terminal_sessions import _digest
import time
import os


class TabHolds:
    def __init__(self,root):
        self.directory=Path(root)/'terminal-tab-holds'
        self.path=self.directory/'holds.json'

    @staticmethod
    def identity(resource):
        target=resource['target'];window=resource['window']
        return _digest(dict(host=target['host'],environment=target['environment'],window=window['window_id'],
            panes=sorted([(p['pane_id'],p.get('process_generation'),p.get('windows_creation_filetime')) for p in window['panes']])))

    def get(self,identity):
        try:return read(self.path).get(identity)
        except FileNotFoundError:return None

    def hold(self,identity,*,reason='manual_relocation',receipt_id=None):
        with locked(self.directory):
            try:state=read(self.path)
            except FileNotFoundError:state={}
            state[identity]=dict(identity=identity,reason=reason,receipt_id=receipt_id,held_at=time.time())
            write(self.path,state)
            fd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
            return state[identity]

    def resume(self,identity):
        with locked(self.directory):
            try:state=read(self.path)
            except FileNotFoundError:state={}
            previous=state.pop(identity,None);write(self.path,state)
            return dict(identity=identity,resumed=previous is not None)
