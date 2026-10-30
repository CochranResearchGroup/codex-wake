"""Host-enrolled presentation attachments, separate from runtime identity/input.

No terminal discovery grants stdin ownership. Brokers are host-owned structured
connections; fallback is visible and separately selected for each request.
"""
import math
import time

from .managed_inventory import InventoryError
from .tab_organization import TabOrganization, TabError, digest


class ControllerTabs:
    READS = frozenset(('tabs.list', 'tabs.show'))
    MUTATIONS = frozenset(('tabs.preview', 'tabs.apply', 'tabs.undo', 'tabs.capture', 'tabs.input'))

    def __init__(self, root, *, workspaces, host, environment):
        self.root, self.workspaces = root, dict(workspaces)
        self.host, self.environment = host, environment

    def execute(self, operation, arguments):
        allowed = {
            'tabs.list': set(), 'tabs.show': {'workspace', 'selector'},
            'tabs.preview': {'workspace','expected_target','mode','pins'},
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
        resources = []
        deadline = time.monotonic() + 10
        for name in names:
            if name not in self.workspaces:
                raise InventoryError('unsupported_target', 'workspace is not host enrolled')
            config = self.workspaces[name]
            transport = config['transport']
            try:
                snapshot = transport.snapshot(deadline)
            except Exception as error:
                raise InventoryError('attachment_unavailable', 'host presentation observation failed') from error
            target = dict(host=self.host, environment=self.environment, workspace=name,
                          presentation=config['kind'], generation=digest(snapshot))
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
                resources.extend(dict(target=target, window=w, input_custody=custody,
                                      runtime_identity='unverified', fallback='explicit_only') for w in windows)
                continue
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
                    return dict(target=target, **owner.preview(mode=arguments.get('mode','activity'), pins=arguments.get('pins',[]), deadline=deadline))
                if operation == 'tabs.apply':
                    return dict(target=target, **owner.apply(arguments['plan_id'], deadline=deadline))
                return dict(target=target, **owner.undo(arguments['receipt_id'], deadline=deadline))
            except TabError as error:
                raise InventoryError(error.code, str(error)) from error
        return dict(resources=resources)

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
        required = {'host','environment','workspace','presentation','generation'}
        if not isinstance(target, dict) or not required <= target.keys() or not any(
                required <= scope.keys() and all(target.get(k) == v for k,v in scope.items()) for scope in actor.targets):
            raise AuthError('insufficient_scope')
        def authorize():
            current = self.authority.authenticate(token)
            if current != actor: raise AuthError()
            return current
        return self.runtime.execute(actor, operation, arguments, authorize=authorize, dispatch=self.tabs.execute)
