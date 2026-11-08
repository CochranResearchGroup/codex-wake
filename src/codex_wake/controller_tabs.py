"""Host-enrolled presentation attachments, separate from runtime identity/input.

No terminal discovery grants stdin ownership. Brokers are host-owned structured
connections; fallback is visible and separately selected for each request.
"""
import time

from .managed_inventory import InventoryError
from .tab_organization import TabOrganization, TabError, digest


class ControllerTabs:
    READS = frozenset(('tabs.list','tabs.show','tabs.view-list','tabs.view-show','tabs.view-evaluate','tabs.group-list','tabs.group-show','tabs.monitor.status','tabs.monitor.refresh'))
    MUTATIONS = frozenset(('tabs.preview', 'tabs.apply', 'tabs.undo', 'tabs.capture', 'tabs.input'))

    def __init__(self, root, *, workspaces, host, environment):
        self.root, self.workspaces = root, dict(workspaces)
        self.host, self.environment = host, environment

    def execute(self, operation, arguments):
        if operation.startswith('tabs.monitor.'):
            from .tab_monitor import TabMonitor
            payload=dict(arguments)
            expected=payload.pop('expected_target',None)
            if expected is not None and expected!=self.monitor_target():
                raise InventoryError('stale_target','Monitor generation changed; refresh status before controlling.')
            return TabMonitor(self.root).execute(operation,payload)
        from .tab_views import TabViews
        if operation in TabViews.READS|TabViews.MUTATIONS:
            payload=dict(arguments)
            expected=payload.pop('expected_target',None)
            if expected is not None and expected != self.logical_target():
                raise InventoryError('stale_target','Saved view definitions changed; refresh before applying.')
            resources=self.execute('tabs.list',{})['resources'] if operation in ('tabs.view-evaluate','tabs.group-save') else []
            return TabViews(self.root).execute(operation,payload,resources=resources)
        from .tab_lifecycle import TabLifecycle
        if operation in TabLifecycle.ARGUMENTS:
            return TabLifecycle(self.root,workspaces=self.workspaces,host=self.host,environment=self.environment).execute(operation,arguments)
        allowed = {
            'tabs.list': set(), 'tabs.show': {'workspace', 'selector'},
            'tabs.preview': {'workspace','expected_target','mode','pins','criteria'},
            'tabs.apply': {'workspace','expected_target','plan_id'},
            'tabs.undo': {'workspace','expected_target','receipt_id'},
            'tabs.capture': {'workspace','expected_target','pane','lines'},
            'tabs.input': {'workspace','expected_target','pane','input','custody','transport'},
        }
        if operation not in allowed:
            raise InventoryError('unsupported_operation', 'unsupported attachment operation')
        if not isinstance(arguments, dict) or set(arguments) - allowed[operation]:
            raise InventoryError('invalid_argument', 'unsupported attachment arguments')
        names = list(self.workspaces) if operation == 'tabs.list' else [arguments.get('workspace')]
        resources, unavailable = [], []
        deadline = time.monotonic() + 10
        for name in names:
            if name not in self.workspaces:
                raise InventoryError('unsupported_target', 'workspace is not host enrolled')
            config = self.workspaces[name]
            transport = config['transport']
            try:
                snapshot = transport.snapshot(deadline)
                if config['kind'] in ('tmux', 'byobu'):
                    from .process import process_identity
                    for window in snapshot['windows']:
                        for pane in window['panes']:
                            pane['process_generation'] = process_identity(pane['pid'])
            except Exception as error:
                if getattr(error,'code',None) == 'stale_target':
                    raise
                if operation == 'tabs.list':
                    unavailable.append(dict(workspace=name,status='unavailable',code='attachment_unavailable'))
                    continue
                raise InventoryError('attachment_unavailable', 'host presentation observation failed') from error
            target = dict(host=self.host, environment=self.environment, workspace=name,
                          presentation=config['kind'], generation=digest(snapshot))
            observation = None
            if operation in self.READS:
                from .tab_traits import TabTraits, session_rows
                traits = TabTraits(self.root)
                initial = {w['window_id']:traits.observe_window(w,transport=transport,
                           privacy=config.get('privacy'),deadline=deadline) for w in snapshot['windows']}
                needs_native = any(p['traits']['harness']['value']=='codex'
                                   for result in initial.values() for p in result['panes'])
                rows = session_rows(self.root,socket_path=config.get('socket_path'),
                                    deadline=min(deadline,time.monotonic()+2)) if needs_native else dict(sessions=[],holds=[])
                if rows['sessions']:
                    traits = TabTraits(self.root,sessions=rows['sessions'])
                    initial = {w['window_id']:traits.observe_window(w,transport=transport,
                               privacy=config.get('privacy'),deadline=deadline) for w in snapshot['windows']}
                observation = (initial, rows)
            broker = config.get('broker')
            custody = broker.inspect() if broker else dict(available=False, transport='unowned', generation=None)
            if operation not in self.READS and arguments.get('expected_target') != target:
                raise InventoryError('stale_target', 'exact current presentation generation required')
            if operation in self.READS:
                selector = arguments.get('selector')
                windows = snapshot['windows']
                if selector:
                    windows = [w for w in windows if selector in (w['window_id'], w['name'])]
                    if len(windows) != 1:
                        raise InventoryError('ambiguous_target' if windows else 'target_not_found', 'friendly selector must identify one attachment')
                for w in windows:
                    observed, rows = observation
                    evidence = observed[w['window_id']]
                    resources.append(dict(target=target,window=w,input_custody=custody,
                                          traits=evidence,runtime_identity='unverified',fallback='explicit_only',
                                          observation_holds=rows['holds'],workspace_label=config.get('label',name)))
                continue
            if operation in ('tabs.input', 'tabs.capture'):
                privacy = config.get('privacy')
                if privacy is None or privacy(arguments.get('pane')) != 'safe':
                    raise InventoryError('presentation_privacy_unknown', 'private input, draft or unqualified privacy prevents content access')
            if operation == 'tabs.input':
                if not broker or not custody.get('available') or arguments.get('custody') != custody:
                    raise InventoryError('input_custody_required', 'host broker ownership generation required')
                mode = arguments.get('transport')
                if mode not in ('structured', 'terminal') or mode != custody.get('transport'):
                    raise InventoryError('unsupported_transport', 'fallback requires explicit owned transport selection')
                text = arguments.get('input')
                if not isinstance(text, str) or not text or len(text.encode()) > 16384:
                    raise InventoryError('invalid_argument', 'input must be bounded text')
                if mode == 'terminal' and ('\n' in text or '\r' in text or '\x1b' in text):
                    raise InventoryError('invalid_argument', 'terminal fallback permits one literal line')
                self._pane(snapshot, arguments.get('pane'))
                return dict(target=target, transport=mode, fallback=mode == 'terminal',
                            result=broker.send(arguments['pane'], text, expected_custody=custody))
            if operation == 'tabs.capture':
                self._pane(snapshot, arguments.get('pane'))
                lines = arguments.get('lines', 50)
                if type(lines) is not int or not 1 <= lines <= 200:
                    raise InventoryError('invalid_argument', 'capture must be between 1 and 200 lines')
                if not hasattr(transport, 'capture'):
                    raise InventoryError('unsupported_target', 'presentation has no bounded capture adapter')
                text = transport.capture(arguments['pane'], lines, deadline)
                return dict(target=target, text=text[-32768:], truncated=len(text) > 32768,
                            transport='terminal', fallback=True, input_custody=custody)
            owner = TabOrganization(self.root, transport=transport, observer=config.get('observer'),
                                    authorize=lambda action: None)
            try:
                if operation == 'tabs.preview':
                    return dict(target=target, **owner.preview(mode=arguments.get('mode','activity'), pins=arguments.get('pins',[]), criteria=arguments.get('criteria',[]), deadline=deadline))
                if operation == 'tabs.apply':
                    return dict(target=target, **owner.apply(arguments['plan_id'], deadline=deadline))
                return dict(target=target, **owner.undo(arguments['receipt_id'], deadline=deadline))
            except TabError as error:
                raise InventoryError(error.code, str(error)) from error
        value = dict(resources=resources)
        if unavailable:
            value['unavailable'] = unavailable
        if hasattr(self, 'discovery_diagnostics'):
            value['discovery'] = dict(source='automatic', status='ready' if resources else 'not_found',
                                     diagnostics=self.discovery_diagnostics,
                                     message='Existing owned workspaces discovered.' if resources else
                                     'No live owned workspace found; start Byobu/tmux or register a supported psmux bridge, then refresh.')
        return value

    def monitor_target(self):
        from .tab_monitor import TabMonitor
        monitor=TabMonitor(self.root).execute('tabs.monitor.status',{})['monitor']
        return dict(host=self.host,environment=self.environment,workspace='@monitor',presentation='logical',
                    generation=monitor.get('generation') or 'inactive')

    def logical_target(self):
        from .tab_views import TabViews
        return dict(host=self.host,environment=self.environment,workspace='@views',
                    presentation='logical',generation=digest(TabViews(self.root)._read()))

    @staticmethod
    def _pane(snapshot, pane):
        if not any(p['pane_id'] == pane for w in snapshot['windows'] for p in w['panes']):
            raise InventoryError('stale_target', 'pane is absent from pinned presentation')


class AuthorizedTabs:
    """ProtectedOperations plugin using existing durable operation admission."""
    def __init__(self, authority, tabs, runtime):
        self.authority, self.tabs, self.runtime = authority, tabs, runtime

    def execute(self, token, operation, arguments):
        from .controller_auth import AuthError
        actor = self.authority.authenticate(token)
        if 'control' not in actor.scopes:
            raise AuthError('insufficient_scope')
        target = arguments.get('expected_target') if isinstance(arguments, dict) else None
        required = {'host','environment','workspace','presentation'}
        if not isinstance(target, dict) or not (required | {'generation'}) <= target.keys() or not any(
                required <= scope.keys() and all(target.get(k) == v for k,v in scope.items()) for scope in actor.targets):
            raise AuthError('insufficient_scope')
        def authorize():
            current = self.authority.authenticate(token)
            if current != actor: raise AuthError()
            return current
        return self.runtime.execute(actor, operation, arguments, authorize=authorize, dispatch=self.tabs.execute)


def controller_tabs_from_root(root, *, host=None, environment=None):
    """Construct host-owned adapters from fixed private controller-tabs.json.

    Production content privacy is unknown by default. Disposable fixture
    qualification may explicitly declare safe input; this never changes a native
    privacy observer or grants access to production terminal content.
    """
    import json
    import os
    import socket
    import stat
    from pathlib import Path
    from .controller_tab_adapters import (TmuxAttachmentTransport,
        PsmuxAttachmentTransport, ConfiguredBridge, UnixInputBroker)
    from .shortcut_store import default_root
    root = default_root(root)
    path = root / 'controller-tabs.json'
    try:
        fd = os.open(path,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        from .tab_workspace_discovery import discover
        workspaces, diagnostics = discover()
        owner = ControllerTabs(root,workspaces=workspaces,host=host or socket.gethostname(),
                               environment=environment or os.environ.get('WSL_DISTRO_NAME') or os.name)
        from .tab_traits import WorkspaceTraitsObserver
        for workspace in workspaces.values():
            workspace['observer']=WorkspaceTraitsObserver(root,workspace['transport'],workspace.get('privacy'))
        owner.discovery_diagnostics = diagnostics
        return owner
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise InventoryError('configuration_unavailable','host attachment configuration must be private')
        with os.fdopen(os.dup(fd)) as stream:
            raw = stream.read(262145)
        if len(raw)>262144: raise ValueError('configuration exceeds bound')
        try:
            config = json.loads(raw)
        except ValueError:
            raise InventoryError('configuration_unavailable', 'Tab configuration is invalid; repair the selected controller configuration.') from None
    finally:
        os.close(fd)
    if config.get('schema_version') != 1 or not isinstance(config.get('workspaces'),dict):
        raise ValueError('unsupported attachment configuration')
    workspaces = {}
    for name,row in config['workspaces'].items():
        kind = row['kind']
        if kind in ('tmux','byobu'):
            transport = TmuxAttachmentTransport(row['socket_path'],row['session_id'])
        elif kind in ('psmux','stdio'):
            transport = PsmuxAttachmentTransport(ConfiguredBridge(row['bridge_command']),generation=row['bridge_generation'])
        else:
            raise ValueError('unsupported host presentation')
        workspace = dict(kind=kind,transport=transport)
        if kind in ('tmux','byobu'):
            workspace.update(socket_path=row['socket_path'], session_id=row['session_id'])
        if row.get('input_broker_socket'):
            workspace['broker'] = UnixInputBroker(row['input_broker_socket'])
        if row.get('evidence_scope') == 'disposable_fixture' and row.get('privacy') == 'safe':
            workspace['privacy'] = lambda pane:'safe'
        from .tab_traits import WorkspaceTraitsObserver
        workspace['observer']=WorkspaceTraitsObserver(root,transport,workspace.get('privacy'))
        workspaces[name] = workspace
    return ControllerTabs(root,workspaces=workspaces,host=host or socket.gethostname(),
                          environment=environment or os.environ.get('WSL_DISTRO_NAME') or os.name)
