"""Owned, bounded read-only stock tmux channel for retained formatting owners.

Only fixed managed-option reads enter this channel. Option writes and pane
capture retain their existing process boundary. No pane output is subscribed.
"""
import os
from pathlib import Path
import re
import select
import selectors
import shlex
import stat
import subprocess
import time
import uuid

from .managed_inventory import InventoryError

_FRAME=re.compile(rb'^%begin ([0-9]+ [0-9]+ [01])$')
_WINDOW_OPTIONS=('window-status-format','window-status-current-format',
                 'window-status-style','window-status-current-style')
_SESSION_OPTIONS=('status-interval','@wake-format-clock')


class FormattingReadChannel:
    MAX_BYTES=1048576
    MAX_COMMANDS=128

    def __init__(self,transport):
        self.transport=transport
        self.socket,self.session=transport.socket,transport.session
        self.identity=list(transport.socket_identity)
        self.process=None;self.selector=None;self.buffer=b''
        self.closed=False;self.retry_at=0.
        self.requests=self.failures=0
        self.state='idle'

    def _accepts(self,commands):
        if not isinstance(commands,(list,tuple)) or not 0<len(commands)<=self.MAX_COMMANDS:return False
        for command in commands:
            if (not isinstance(command,(list,tuple)) or not 1<=len(command)<=7
                    or not all(isinstance(v,str) and len(v)<=128 for v in command)):return False
            parts=tuple(command)
            if (len(parts)==5 and parts[:3]==('display-message','-p','-t')
                    and re.fullmatch(r'@[0-9]+',parts[3]) and parts[4]=='#{window_id}'):continue
            if parts in [('show-options',*flags,'-t',self.session,name)
                         for flags in (('-q',),('-q','-v'),('-q','-A','-v')) for name in _SESSION_OPTIONS]:continue
            if (len(parts)>=5 and parts[0]=='show-options' and parts[-1] in _WINDOW_OPTIONS):
                if parts==('show-options','-g','-w','-v',parts[-1]):continue
                for flags in (('-w',),('-w','-v'),('-w','-A','-v')):
                    if (parts==('show-options',*flags,'-t',parts[-2],parts[-1])
                            and re.fullmatch(r'@[0-9]+',parts[-2])):break
                else:return False
                continue
            return False
        return True

    def _qualify(self):
        info=Path(self.socket).lstat()
        if (not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.geteuid()
                or [info.st_dev,info.st_ino]!=self.identity):
            raise InventoryError('workspace_changed','Formatting read socket ownership or generation changed.')

    def _more(self,deadline):
        remaining=deadline-time.monotonic()
        if remaining<=0 or not self.selector.select(remaining):
            raise InventoryError('formatting_read_timeout','Formatting read deadline exhausted.')
        chunk=os.read(self.process.stdout.fileno(),65536)
        if not chunk:raise InventoryError('formatting_read_unavailable','Formatting read client disconnected.')
        self.buffer+=chunk
        if len(self.buffer)>self.MAX_BYTES:
            raise InventoryError('formatting_read_limit','Formatting read exceeds bounded output.')

    def _connect(self,deadline):
        self._qualify()
        self.process=subprocess.Popen(['tmux','-S',self.socket,'-C','attach-session','-E','-f',
            'no-output,ignore-size,read-only','-t',self.session],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0,env={**os.environ,'TMUX':''})
        os.set_blocking(self.process.stdin.fileno(),False)
        os.set_blocking(self.process.stdout.fileno(),False)
        self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ)
        while True:
            lines=self.buffer.split(b'\n')
            if lines and _FRAME.fullmatch(lines[0]):
                identity=lines[0].split(b' ',1)[1]
                if b'%error '+identity in lines:raise InventoryError('formatting_read_unavailable','Formatting read attach failed.')
                end=b'%end '+identity
                if end in lines:
                    self.buffer=b'\n'.join(lines[lines.index(end)+1:]);break
            self._more(deadline)
        self.state='connected'

    def _send(self,raw,deadline):
        view=memoryview(raw)
        while view:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not select.select([],[self.process.stdin],[],remaining)[1]:
                raise InventoryError('formatting_read_timeout','Formatting read deadline exhausted.')
            try:written=os.write(self.process.stdin.fileno(),view)
            except BlockingIOError:continue
            view=view[written:]

    def read(self,commands,deadline):
        """Return ordinary text-mode command outputs; never submit a mutation."""
        if not self._accepts(commands):
            raise InventoryError('invalid_argument','Only bounded managed formatting reads are allowed.')
        if self.closed:raise InventoryError('formatting_read_unavailable','Formatting read owner is closed.')
        self.requests+=1
        deadline=min(deadline,time.monotonic()+2.)
        try:
            self._qualify()
            if time.monotonic()>=deadline:
                raise InventoryError('formatting_read_timeout','Formatting read deadline exhausted.')
            if time.monotonic()<self.retry_at:
                raise InventoryError('formatting_read_backoff','Formatting read reconnect backoff is active.')
            if self.process is None:self._connect(deadline)
            markers=['wake-read-'+uuid.uuid4().hex for _ in commands]
            parts=[]
            for command,marker in zip(commands,markers):
                parts.extend((' '.join(shlex.quote(v) for v in command),'display-message -p '+marker))
            self._send((' ; '.join(parts)+'\n').encode(),deadline)
            last=markers[-1].encode()
            final=re.compile(rb'^%begin ([0-9]+ [0-9]+ 1)\n'+last+rb'\n%end \1\n',re.M)
            while True:
                match=final.search(self.buffer)
                if match:break
                self._more(deadline)
            raw,self.buffer=self.buffer[:match.end()],self.buffer[match.end():]
            # A marker is unpredictable and emitted by its own fixed command.
            # Payload may contain arbitrary protocol-looking lines. The LAST
            # matching end before the marker's own frame is the real delimiter.
            lines=raw.split(b'\n');cursor=0;outputs=[]
            for marker in markers:
                if time.monotonic()>=deadline:
                    raise InventoryError('formatting_read_timeout','Formatting read deadline exhausted.')
                marker_at=lines.index(marker.encode(),cursor);marker_begin=marker_at-1
                marker_header=_FRAME.fullmatch(lines[marker_begin])
                if not marker_header or lines[marker_at+1]!=b'%end '+marker_header[1]:
                    raise ValueError('marker_frame_mismatch')
                start=next(i for i in range(cursor,marker_begin) if _FRAME.fullmatch(lines[i]))
                identity=lines[start].split(b' ',1)[1]
                ends=[i for i in range(start+1,marker_begin) if lines[i] in (b'%end '+identity,b'%error '+identity)]
                if not ends or lines[ends[-1]].startswith(b'%error '):
                    raise ValueError('read_frame_failed')
                end=ends[-1]
                payload=b'\n'.join(lines[start+1:end])+(b'\n' if end>start+1 else b'')
                # subprocess text=True uses universal newline decoding.
                outputs.append(payload.decode('utf-8').replace('\r\n','\n').replace('\r','\n'))
                cursor=marker_at+2
            return outputs
        except (OSError,ValueError,StopIteration,IndexError,InventoryError) as error:
            if isinstance(error,InventoryError) and error.code=='formatting_read_backoff':raise
            self.failures+=1;self._dispose();self.state='unavailable';self.retry_at=time.monotonic()+1.
            if isinstance(error,InventoryError):raise
            raise InventoryError('formatting_read_unavailable','Formatting read failed without effects.') from None

    def _dispose(self):
        if self.selector is not None:self.selector.close();self.selector=None
        if self.process is not None:
            process,self.process=self.process,None
            for stream in (process.stdin,process.stdout):
                if stream:stream.close()
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=.2)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=.2)
        self.buffer=b''

    def status(self):
        return dict(state=self.state,owned_pid=self.process.pid if self.process else None,
                    requests=self.requests,failures=self.failures,read_only=True)

    def close(self):
        self.closed=True;self._dispose();self.state='closed'
