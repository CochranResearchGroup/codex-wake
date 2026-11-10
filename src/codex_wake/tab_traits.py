"""Read-only attachment traits with independent, freshness-qualified evidence.

Host callers supply structured session evidence, never terminal titles or caller
claims. Process observations and visible-screen reads add context, not native
conversation or health authority.
"""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
import re
import subprocess
import time
import tomllib

from .process import process_identity

_ACTIVITY = {'working': 'running', 'active': 'running', 'ready': 'idle', 'idle': 'idle',
             'awaiting-human': 'waiting-for-input', 'waiting-for-input': 'waiting-for-input',
             'disconnected': 'disconnected', 'not_loaded': 'disconnected'}
_ANSI = re.compile(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]')
_ERROR = re.compile(r'^(?:[✗×!⚠●■]\s*)?(?:error\s*:|fatal(?:\s+error)?\s*:|panic\s*:|'
                    r'thread\s+.+\s+panicked\b|traceback\s*\(most recent call last\)|'
                    r'error\s+(?:running|connecting|sending|loading|executing)\b)', re.I)
# Explicit terminal status markers only; READY/success output is not evidence
# that an unrelated error was resolved. These markers apply to earlier lines.
_RESOLVED = re.compile(r'^(?:[✓✔]\s*)?(?:resolved|error\s+(?:resolved|dismissed))\s*:\s*\S', re.I)
_SECRET_PROMPT = re.compile(r'^(?:enter\s+(?:your\s+)?)?(?:password|passphrase|api[ _-]?key|'
                            r'access[ _-]?token|secret|token|authorization)\b.*[:=]', re.I)
_COMPOSER = re.compile(r'^(?:[›❯>$#]|[^\s]+[$#])(?:\s|$)')
_HASHES = {}


def _trait(value='unknown', *, source='none', observed_at=None, status='unknown', reason=None):
    return dict(value=value, status=status, source=source, observed_at=observed_at,
                freshness='fresh' if status == 'observed' else status, reason=reason)


def _same_process(expected, observed):
    return (isinstance(expected, dict) and observed is not None
            and expected.get('pid') == observed.get('pid')
            and str(expected.get('start_ticks')) == str(observed.get('start_ticks'))
            and expected.get('boot_id') == observed.get('boot_id'))


def _processes(pid, deadline):
    """Walk only this same-user pane's descendants, without a host-wide ps dump."""
    pending, rows, seen = [pid], [], set()
    complete = True
    while pending:
        if time.monotonic() >= deadline or len(seen) >= 256:
            complete = False
            break
        current = pending.pop(0)
        if current in seen or type(current) is not int or current <= 0:
            continue
        seen.add(current)
        base = Path('/proc') / str(current)
        try:
            if base.stat().st_uid != os.geteuid():
                complete = False
                continue
            before = process_identity(current)
            if not before:
                complete = False
                continue
            argv = (base / 'cmdline').read_bytes()[:16384].decode(errors='replace').split('\0')
            executable = (base / 'exe').resolve(strict=True)
            cwd = str((base / 'cwd').resolve(strict=True))
            children = (base / 'task' / str(current) / 'children').read_text()[:16384]
            if process_identity(current) != before:
                complete = False
                continue
            rows.append(dict(pid=current, process=dict(pid=current, start_ticks=before['start_time_ticks'],
                             boot_id=before.get('boot_id')), executable=str(executable), argv=argv, cwd=cwd))
            pending.extend(int(value) for value in children.split())
        except (OSError, ValueError):
            complete = False
    return rows, complete


def _image_digest(path, deadline):
    info = path.stat()
    key = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if key in _HASHES:
        return _HASHES[key]
    if info.st_size > 512 * 1024 * 1024:
        return None
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            if time.monotonic() >= deadline:
                return None
            digest.update(block)
    if len(_HASHES) >= 64:
        _HASHES.pop(next(iter(_HASHES)))
    _HASHES[key] = digest.hexdigest()
    return digest.hexdigest()


def _ssh_destination(argv):
    # No ssh invocation or remote command. Only retain the destination operand;
    # flags with arguments must not accidentally become the remote host trait.
    consumes = set('BbcDEeFIiJLlmOopQRSWw')
    i = 1
    while i < len(argv):
        value = argv[i]
        if not value:
            return None
        if value == '--':
            i += 1
            return argv[i].rsplit('@', 1)[-1][:256] if i < len(argv) else None
        if value.startswith('-'):
            if len(value) == 2 and value[1] in consumes:
                i += 2
            else:
                i += 1
            continue
        return value.rsplit('@', 1)[-1][:256]
    return None


def session_rows(root, *, socket_path=None, endpoints=(), deadline=None, reader_factory=None, panes=None):
    """Bounded metadata discovery through existing readers and pane matching.

    Endpoints and optional panes are host-owned discoveries, never caller-selected
    command data. Default discovery follows existing account socket locators and
    starts neither CLI locator processes nor daemons. Reader factories are the
    transport seam used by existing native-protocol conformance tests.
    """
    import socket
    import stat
    import struct
    from .shared_app_server import SharedAppServerReader
    from .sessions import build_snapshot, tmux_inventory
    from .records import WakeError
    deadline = min(deadline or time.monotonic() + 3, time.monotonic() + 10)
    root = Path(root)
    reader_factory = reader_factory or SharedAppServerReader
    candidates = list(endpoints)[:64]
    holds, rows = [], []
    if not candidates:
        homes = [Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))]
        try:
            from codex_profiles.config import load_settings
            from .controller_accounts import account_inventory
            path = root / 'controller-accounts.toml'
            data = tomllib.loads(path.read_text())
            settings = load_settings(path)
            names, _ = account_inventory(settings, data)
            homes.extend(settings.account_root(name) for name in names)
            homes.extend(Path(value['home']) for value in data.get('stores', {}).values()
                         if isinstance(value, dict) and isinstance(value.get('home'), str))
        except (OSError, ValueError, KeyError, TypeError, WakeError):
            pass
        for home in homes[:256]:
            if time.monotonic() >= deadline:
                holds.append(dict(reason='discovery_deadline'))
                break
            try:
                if not home.is_absolute() or home.stat().st_uid != os.geteuid():
                    continue
                path = (home / 'app-server-control/app-server-control.sock').resolve(strict=True)
                if path.stat().st_uid == os.geteuid() and stat.S_ISSOCK(path.stat().st_mode):
                    candidates.append('unix://' + str(path))
            except OSError:
                continue
    if panes is None:
        remaining = deadline-time.monotonic()
        try:
            panes = tmux_inventory(socket_path, max(.001, remaining)) if remaining > 0 else []
        except (OSError, ValueError, WakeError, subprocess.SubprocessError):
            panes = []
            holds.append(dict(reason='pane_inventory_unavailable'))
    for address in dict.fromkeys(candidates):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            holds.append(dict(reason='discovery_deadline'))
            break
        try:
            with reader_factory(address, timeout=remaining) as reader:
                peer_pid, peer_uid, _ = struct.unpack('3i', reader.connection.socket.getsockopt(
                    socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if peer_uid != os.geteuid():
                    raise ValueError('foreign_native_peer')
                home = Path(reader.server_metadata['codexHome'])
                if not home.is_absolute() or home.stat().st_uid != peer_uid:
                    raise ValueError('foreign_native_home')
                birth = process_identity(peer_pid)
                if not birth:
                    raise ValueError('native_peer_generation_unavailable')
                executable = Path('/proc') / str(peer_pid) / 'exe'
                digest = _image_digest(executable, deadline)
                threads = reader.loaded_threads(maximum=1000)
                if process_identity(peer_pid) != birth or time.monotonic() >= deadline:
                    raise ValueError('native_peer_changed_or_deadline')
                snapshot = build_snapshot(threads, panes, {'app_server':{'availability':'available'},
                                                         'tmux':{'availability':'available'}})
                home_info, endpoint_info = home.stat(), reader.path.stat()
                for row in snapshot['sessions']:
                    if not row.get('thread_id'):
                        continue
                    target = dict(host=socket.gethostname(), environment=os.environ.get('WSL_DISTRO_NAME') or os.name,
                                  provider='codex', uid=peer_uid, account=home.name, home=str(home),
                                  home_generation=f'{home_info.st_dev}:{home_info.st_ino}',
                                  executable=str(executable.resolve()), build_sha256=digest,
                                  process=dict(pid=peer_pid,start_ticks=birth['start_time_ticks'],boot_id=birth.get('boot_id')),
                                  socket_generation=f'{endpoint_info.st_dev}:{endpoint_info.st_ino}',
                                  conversation_id=row['thread_id'])
                    rows.append(dict(row, target=target, endpoint='unix://' + str(reader.path),
                                     codex_cmd=[target['executable']]))
        except (OSError, ValueError, KeyError, TypeError, WakeError):
            holds.append(dict(endpoint=address, reason='native_metadata_unavailable'))
    return dict(schema_version=1, status='partial' if holds else 'complete', sessions=rows,
                holds=holds, observed_at=time.time(), application_effects=False)


class TabTraits:
    """Observe one window at the host-owned public attachment boundary.

    evidence is the existing WorkspaceObserver's pane map. sessions optionally
    supplies exact rows from local_sessions.discover; they are matched to pane
    descendants and used by existing local health, without another discovery
    pass. All arguments are host-owned, not fields accepted from remote clients.
    """
    def __init__(self, root, *, sessions=(), health_probe=None, process_probe=None,
                 clock=time.time, freshness=30, check_scheduler=None, check_namespace=None,
                 explicit_checks=False, dirty_panes=()):
        self.root = Path(root)
        self.sessions = list(sessions)[:1000]
        self.health_probe = health_probe
        self.process_probe = process_probe or _processes
        self.clock = clock
        self.freshness = freshness
        self._builds = None
        self.check_scheduler=check_scheduler
        self.check_namespace=check_namespace
        self.explicit_checks=explicit_checks
        self.dirty_panes=frozenset(dirty_panes)

    def observe_window(self, window, *, evidence=None, transport=None, privacy=None, deadline=None):
        deadline = min(deadline or time.monotonic() + 2, time.monotonic() + 10)
        panes = [self._pane(pane, (evidence or {}).get(pane.get('pane_id')), transport, privacy, deadline)
                 for pane in window.get('panes', [])[:256]]
        names = ('harness', 'build', 'account', 'repository', 'remote_host', 'session_presence', 'activity', 'health', 'error')
        summary = {}
        mixed = False
        for name in names:
            values = {str(pane['traits'][name]['value']) for pane in panes}
            if len(values) > 1:
                summary[name] = _trait('mixed', source='pane_summary', observed_at=self.clock(), status='observed')
                mixed = True
            elif panes:
                # Preserve stale/unknown provenance, even when values agree.
                candidates = [pane['traits'][name] for pane in panes]
                summary[name] = dict(next((value for value in candidates if value['status'] != 'observed'), candidates[0]))
            else:
                summary[name] = _trait(reason='no_pane_observation')
        return dict(schema_version=1, panes=panes, traits=summary, mixed=mixed,
                    observed_at=self.clock(), application_effects=False)

    def _registered_build(self, executable, deadline):
        from codex_profiles.build_channels import load_build, BuildError
        if self._builds is None:
            self._builds = []
            try:
                data = tomllib.loads((self.root / 'controller-accounts.toml').read_text())
                manifest = Path(data['builds']['manifest'])
                for channel in ('stock', 'modded'):
                    try:
                        self._builds.append(load_build(manifest, channel))
                    except (OSError, ValueError, BuildError):
                        pass
            except (OSError, KeyError, ValueError, TypeError):
                pass
        for build in self._builds:
            try:
                if executable.samefile(build.executable) and _image_digest(executable, deadline) == build.sha256:
                    return build.channel
            except OSError:
                continue
        return None

    def _pane(self, pane, sample, transport, privacy, deadline):
        if pane.get('platform')=='windows':
            return self._windows_pane(pane,transport,privacy,deadline)
        stamp = self.clock()
        names = ('harness', 'build', 'account', 'repository', 'remote_host', 'session_presence', 'activity', 'health', 'error')
        traits = {name: _trait(reason='evidence_unavailable') for name in names}
        rows, complete = self.process_probe(pane.get('pid'), deadline)
        identities = [row['process'] for row in rows]
        recognized = []
        for row in rows:
            executable = Path(row['executable'])
            name = executable.name.lower()
            if name == 'codex':
                recognized.append('codex')
                traits['harness'] = _trait('codex', source='process_executable', observed_at=stamp, status='observed')
                channel = self._registered_build(executable, deadline)
                traits['build'] = _trait(channel or 'unknown', source='registered_build_sha256' if channel else 'none',
                                         observed_at=stamp, status='observed' if channel else 'unknown',
                                         reason=None if channel else 'build_not_registered_or_unverified')
            elif name == 'grok' or (name in ('node', 'nodejs') and len(row.get('argv', [])) > 1
                                  and '/@x-ai/grok/' in row['argv'][1]):
                recognized.append('grok')
                traits['harness'] = _trait('grok', source='process_executable', observed_at=stamp, status='observed')
            elif name in ('ssh', 'ssh.exe'):
                host = _ssh_destination(row.get('argv', []))
                traits['remote_host'] = _trait(host or 'unknown', source='ssh_destination_operand', observed_at=stamp,
                                               status='observed' if host else 'unknown')
        if len(set(recognized)) > 1:
            traits['harness'] = _trait('mixed', source='process_descendants', observed_at=stamp, status='observed')
        if recognized:
            traits['session_presence'] = _trait('present', source='process_descendants', observed_at=stamp, status='observed')
        elif complete:
            traits['session_presence'] = _trait('absent', source='process_descendants', observed_at=stamp, status='observed')

        native = self._session(pane, identities)
        if sample is None and native is not None:
            target = native.get('target', {})
            flags = native.get('active_flags', [])
            state = native.get('runtime_state')
            if state == 'active' and flags:
                state = 'awaiting-human' if set(flags) <= {'waitingOnApproval', 'waitingOnUserInput'} else 'unknown'
            state = {'active':'working', 'idle':'ready', 'not_loaded':'disconnected'}.get(state,state)
            sample = dict(runtime=target.get('provider'), namespace=target.get('account'),
                          conversation_id=target.get('conversation_id'), account=target.get('account'),
                          root=native.get('cwd'), state=state,
                          process=next((v for v in identities if v['pid'] in [a.get('client_pid') for a in native.get('attachments', [])]), None),
                          observed_at=stamp, fresh=True, source='native_metadata')
        qualified = (isinstance(sample, dict) and sample.get('fresh') is True
                     and any(_same_process(sample.get('process'), row) for row in identities)
                     and sample.get('conversation_id') and sample.get('namespace'))
        if qualified:
            at = sample.get('observed_at', stamp)
            fresh = type(at) in (int, float) and math.isfinite(at) and at <= stamp <= at + self.freshness
            status = 'observed' if fresh else 'stale'
            source = sample.get('source', 'native_metadata')
            runtime = sample.get('runtime', 'codex')
            if runtime in ('codex', 'grok'):
                traits['harness'] = _trait(runtime, source=source, observed_at=at, status=status)
            traits['session_presence'] = _trait('present', source=source, observed_at=at, status=status)
            traits['activity'] = _trait(_ACTIVITY.get(sample.get('state'), 'unknown'), source=source,
                                        observed_at=at, status=status if sample.get('state') in _ACTIVITY else 'unknown')
            for name, key in (('account', 'account'), ('repository', 'root')):
                value = sample.get(key)
                if value:
                    traits[name] = _trait(value, source=source, observed_at=at, status=status)
        if native is not None and native.get('target', {}).get('build_sha256'):
            client=(sample or {}).get('process') or {}
            target=native['target']
            key=(target.get('provider'),target.get('account'),target.get('build_sha256'),
                 client.get('pid'),str(client.get('start_ticks')),client.get('boot_id'))
            probe=lambda:self._health(native,sample,deadline)
            traits['health']=(self.check_scheduler.run('health',key,probe,force=self.explicit_checks)
                              if self.check_scheduler else probe())
        error=lambda:self._error(pane,transport,privacy,deadline)
        key=(self.check_namespace,pane.get('pane_id'),tuple((r.get('pid'),str(r.get('start_ticks')),
                                                        r.get('boot_id')) for r in identities))
        traits['error']=(self.check_scheduler.run('errors',key,error,force=self.explicit_checks,
                           eligible=pane.get('pane_id') in self.dirty_panes or
                                    traits['activity'].get('value') in ('running','waiting-for-input'))
                         if self.check_scheduler else error())
        return dict(pane_id=pane.get('pane_id'), processes=identities, process_complete=complete, traits=traits,
                    binding=dict(sample) if qualified and traits['activity']['status'] == 'observed' else None)

    def _health(self,native,sample,deadline):
        if time.monotonic() >= deadline - .05:
            return _trait(reason='observation_deadline')
        try:
            probe=self.health_probe
            if probe is None:
                from .local_health import observe_row
                probe=observe_row
            options=dict(timeout=min(1,max(.05,deadline-time.monotonic())))
            if self.health_probe is None and isinstance(sample,dict):
                options['client_process']=sample.get('process')
            observed=probe(self.root,native,**options)['observation']
            value=observed.get('status','unknown')
            if value=='responsive' and observed.get('evidence')!='tui_main_loop_ack':
                value='unknown'
            return _trait(value,source=observed.get('evidence','none'),observed_at=observed.get('observed_at'),
                          status='observed' if value=='responsive' else value,reason=observed.get('reason'))
        except (ImportError,OSError,ValueError,KeyError,TimeoutError):
            return _trait(reason='health_observation_unavailable')

    def _windows_pane(self,pane,transport,privacy,deadline):
        import ntpath
        stamp=self.clock()
        names=('harness','build','account','repository','remote_host','session_presence','activity','health','error')
        traits={name:_trait(source='windows_presentation',reason='native_runtime_observation_unavailable') for name in names}
        processes=pane.get('windows_processes',[])[:256]
        kinds=set()
        for row in processes:
            executable=ntpath.basename(row.get('executable','')).lower()
            if executable in ('codex.exe','codex'):kinds.add('codex')
            elif executable in ('grok.exe','grok'):kinds.add('grok')
        if kinds:
            traits['harness']=_trait(next(iter(kinds)) if len(kinds)==1 else 'mixed',source='windows_process_image',observed_at=stamp,status='observed')
            traits['session_presence']=_trait('present',source='windows_process_image',observed_at=stamp,status='observed')
        elif any(ntpath.basename(r.get('executable','')).lower() in ('wsl.exe','ssh.exe') for r in processes):
            traits['session_presence']=_trait(source='windows_relay',reason='remote_runtime_unverified')
        elif pane.get('windows_processes_complete'):
            traits['session_presence']=_trait('absent',source='windows_process_tree',observed_at=stamp,status='observed')
        error=lambda:self._error(pane,transport,privacy,deadline)
        key=(self.check_namespace,pane.get('pane_id'),tuple((r.get('pid'),r.get('creation_filetime')) for r in processes))
        traits['error']=(self.check_scheduler.run('errors',key,error,force=self.explicit_checks,
                           eligible=pane.get('pane_id') in self.dirty_panes)
                         if self.check_scheduler else error())
        return dict(pane_id=pane.get('pane_id'),platform='windows',processes=[dict(pid=r.get('pid'),creation_filetime=r.get('creation_filetime'),platform='windows') for r in processes],
                    process_complete=bool(pane.get('windows_processes_complete')),traits=traits,binding=None)

    def _session(self, pane, identities):
        matches = []
        for row in self.sessions:
            if row.get('target', {}).get('provider') != 'codex':
                continue
            for attachment in row.get('attachments', []):
                if attachment.get('pane_id') != pane.get('pane_id'):
                    continue
                if any(value['pid'] == attachment.get('client_pid') and
                       str(value['start_ticks']) == str(attachment.get('client_start_time_ticks')) for value in identities):
                    matches.append(row)
                    break
        return matches[0] if len(matches) == 1 else None

    def _error(self, pane, transport, privacy, deadline):
        if time.monotonic() >= deadline:
            return _trait(reason='observation_deadline')
        redacted = privacy is None
        if privacy is not None and privacy(pane.get('pane_id')) != 'safe':
            return _trait(reason='presentation_privacy_unknown')
        if redacted:
            # Host-created adapters qualify presentation ownership independently
            # of capture/input grants. No raw terminal content leaves this owner.
            from .tab_organization import TmuxTransport
            from .controller_tab_adapters import PsmuxAttachmentTransport
            owned = isinstance(transport, PsmuxAttachmentTransport) and pane.get('platform') == 'windows'
            if isinstance(transport, TmuxTransport):
                try:
                    owned = (Path('/proc', str(pane.get('pid'))).stat().st_uid == os.geteuid()
                             and Path(transport.socket).lstat().st_uid == os.geteuid())
                except OSError:
                    owned = False
            if not owned:
                return _trait(reason='presentation_ownership_unknown')
        if transport is None or not (hasattr(transport, 'command') or hasattr(transport,'visible_screen')):
            return _trait(status='unsupported', reason='visible_screen_capture_unavailable')
        try:
            # Default tmux capture range is the current visible screen, not history.
            text = (transport.visible_screen(pane['pane_id'],deadline) if hasattr(transport,'visible_screen') else
                    transport.command(deadline, 'capture-pane', '-p', '-e', '-t', pane['pane_id']))
            if not isinstance(text, str) or len(text) > 1048576:
                return _trait(reason='visible_screen_exceeds_bound')
            lines = text.splitlines()
            visible = [(i, _ANSI.sub('', value).strip()) for i, value in enumerate(lines)]
            nonempty = [(i, value) for i, value in visible if value]
            bottom = nonempty[-8:]
            # A composer may wrap onto bare error-looking lines. Suppress the
            # whole uncertain bottom region rather than infer draft/output.
            for position, (_, value) in enumerate(bottom):
                prompt = _COMPOSER.match(value)
                if (_SECRET_PROMPT.match(value) or
                    (prompt and (value[prompt.end():].strip() or
                                 any(_ERROR.match(tail) for _, tail in bottom[position+1:])))):
                    return _trait(reason='visible_input_or_secret_prompt')
            for i, value in reversed(bottom):
                if _RESOLVED.match(value):
                    return _trait('absent', source='current_visible_screen', observed_at=self.clock(), status='observed',
                                  reason='later_explicit_visible_resolution_marker')
                if _ERROR.match(value):
                    result = _trait('present', source='current_visible_screen', observed_at=self.clock(), status='observed')
                    result.update(message='Terminal error (content redacted)' if redacted else value[:512],
                                  location=dict(pane_id=pane['pane_id'], row=i, region='bottom'),
                                  confidence='suspected', reason='current_visible_error_marker')
                    return result
            return _trait('absent', source='current_visible_screen', observed_at=self.clock(), status='observed',
                          reason='no_current_bottom_error_marker')
        except (OSError, ValueError, TimeoutError, subprocess.SubprocessError):
            return _trait(reason='visible_screen_unavailable')


class WorkspaceTraitsObserver:
    """Adapt bounded native metadata observations to existing layout ownership."""
    def __init__(self,root,transport,privacy=None):
        self.root,self.transport,self.privacy=root,transport,privacy
        from .tab_observation import ObservationCache
        self.cache=ObservationCache(root)

    def __call__(self,timeout):
        deadline=time.monotonic()+min(5,max(.001,timeout))
        snapshot=self.transport.snapshot(deadline)
        observed,_=self.cache.observe('workspace',snapshot,socket_path=getattr(self.transport,'socket',None),
                                      transport=self.transport,privacy=self.privacy,deadline=deadline)
        first=list(observed.values())
        result={}
        for window in first:
            for pane in window['panes']:
                if pane.get('binding'):
                    result[pane['pane_id']]=dict(pane['binding'],traits=pane['traits'])
        return result
