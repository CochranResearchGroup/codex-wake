"""Durable bot lineage and exact client attachments; metadata grants no authority."""
from copy import deepcopy
from pathlib import Path
import json

from .managed_inventory import InventoryError
from .shortcut_store import read, write, locked
from .tab_organization import digest


def text(value, field, *, empty=False):
    if not isinstance(value, str) or (not value and not empty) or len(value.encode()) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise InventoryError('invalid_argument', field + ' must be bounded display-safe text.')
    return value


def binding_key(client_id, environment):
    return json.dumps([text(client_id, 'client_id'), text(environment, 'environment')], separators=(',', ':'))


class BotFamilies:
    READS = frozenset(('tabs.family.list', 'tabs.family.show'))
    FIELDS = {'bot_id', 'parent_bot_id', 'name', 'scope_kind', 'scope_ref', 'temporary'}
    LIFECYCLE = frozenset(('open', 'accept', 'adopt', 'focus'))

    def __init__(self, root, *, tabs):
        self.root = Path(root)
        self.tabs = tabs
        self.directory = self.root / 'bot-families'
        self.path = self.directory / 'registry.json'

    def state(self):
        try:
            value = read(self.path)
        except FileNotFoundError:
            return dict(version=1, bots={})
        if not isinstance(value, dict) or value.get('version') != 1 or not isinstance(value.get('bots'), dict):
            raise InventoryError('configuration_unavailable', 'Unsupported bot family registry.')
        return value

    def save(self, state):
        write(self.path, state)

    def target(self):
        return dict(host=self.tabs.host, environment=self.tabs.environment,
                    workspace='@bot-families', presentation='logical', generation=digest(self.state()))

    def get(self, bot_id, state=None):
        text(bot_id, 'bot_id')
        bot = (self.state() if state is None else state)['bots'].get(bot_id)
        if bot is None:
            raise InventoryError('target_not_found', 'Bot is not registered.')
        return deepcopy(bot)

    def ancestors(self, bot, state=None):
        state = self.state() if state is None else state
        seen = {bot['bot_id']}
        result = []
        while bot.get('parent_bot_id'):
            parent = bot['parent_bot_id']
            if parent in seen:
                raise InventoryError('configuration_unavailable', 'Bot lineage contains a cycle.')
            seen.add(parent)
            bot = self.get(parent, state)
            result.append(bot)
        return list(reversed(result))

    def register(self, arguments, state):
        if set(arguments) - self.FIELDS:
            raise InventoryError('invalid_argument', 'Unsupported bot descriptor.')
        bot_id = text(arguments.get('bot_id'), 'bot_id')
        parent = arguments.get('parent_bot_id')
        parent_bot = self.get(parent, state) if parent is not None else None
        if parent == bot_id:
            raise InventoryError('invalid_argument', 'A bot cannot parent itself.')
        kind = arguments.get('scope_kind', 'specialist')
        if kind not in ('specialist', 'account', 'task'):
            raise InventoryError('invalid_argument', 'Unknown bot scope kind.')
        temporary = arguments.get('temporary', False)
        if type(temporary) is not bool:
            raise InventoryError('invalid_argument', 'temporary must be boolean.')
        bot = dict(bot_id=bot_id, parent_bot_id=parent, root_bot_id=parent_bot['root_bot_id'] if parent_bot else bot_id,
                   name=text(arguments.get('name', bot_id), 'name'), scope_kind=kind,
                   scope_ref=text(arguments.get('scope_ref', ''), 'scope_ref', empty=True), temporary=temporary)
        existing = state['bots'].get(bot_id)
        if existing is not None:
            if {k: existing[k] for k in bot} != bot:
                raise InventoryError('identity_conflict', 'Bot descriptor conflicts with its registered identity.')
            return deepcopy(existing)
        if len(state['bots']) >= 2048:
            raise InventoryError('capacity', 'Bot registry capacity reached.')
        bot['bindings'] = {}
        state['bots'][bot_id] = bot
        self.save(state)
        return deepcopy(bot)

    def observations(self):
        """Read enrolled namespaces directly; never recurse through tab inventory."""
        import time
        from .process import process_identity
        for workspace, config in list(self.tabs.workspaces.items()):
            transport = config['transport']
            try:
                snapshot = transport.snapshot(time.monotonic() + 2)
            except (OSError, ValueError):
                continue
            namespace = digest({k: snapshot.get(k) for k in ('server', 'socket_identity', 'bridge_generation')})
            for window in snapshot['windows']:
                for pane in window.get('panes', []):
                    birth = pane.get('process_generation') or process_identity(pane.get('pid'))
                    if not birth:
                        continue
                    yield dict(workspace=workspace, window_id=window['window_id'], pane_id=pane['pane_id'],
                               namespace=namespace, process=birth, backend=config['kind'],
                               server=str(config.get('socket_path') or snapshot.get('server', '')))

    def resolve_binding(self, bot, client_id, environment=None):
        environment = environment or self.tabs.environment
        saved = bot.get('bindings', {}).get(binding_key(client_id, environment))
        if not saved:
            return None
        attachment = saved.get('attachment', {})
        matches = [row for row in self.observations() if all(row.get(k) == attachment.get(k)
                   for k in ('pane_id', 'namespace', 'process'))]
        if len(matches) != 1:
            return None
        return dict(saved, attachment=matches[0], manually_moved=matches[0]['workspace'] != attachment.get('workspace'))

    def bind(self, arguments, state):
        allowed = {'bot_id', 'client_id', 'environment', 'workspace', 'window_id', 'pane_id', 'thread_id'}
        if set(arguments) - allowed:
            raise InventoryError('invalid_argument', 'Unsupported bot binding fields.')
        bot = self.get(arguments.get('bot_id'), state)
        client = text(arguments.get('client_id'), 'client_id')
        environment = arguments.get('environment', self.tabs.environment)
        if environment != self.tabs.environment:
            raise InventoryError('unsupported_target', 'Bind attachments only in this host environment.')
        matches = [row for row in self.observations() if all(row.get(k) == arguments.get(k)
                   for k in ('workspace', 'window_id', 'pane_id'))]
        if len(matches) != 1:
            raise InventoryError('stale_target', 'Exact live attachment is required for a bot binding.')
        key = binding_key(client, environment)
        existing = bot['bindings'].get(key)
        live = self.resolve_binding(bot, client, environment)
        if live and live['attachment'] != matches[0]:
            raise InventoryError('binding_conflict', 'Bot already has a live primary attachment for this client.')
        for other in state['bots'].values():
            for other_key, other_binding in other.get('bindings', {}).items():
                if other['bot_id'] == bot['bot_id'] and other_key == key:
                    continue
                attachment = other_binding.get('attachment', {})
                if all(attachment.get(k) == matches[0].get(k) for k in ('pane_id', 'namespace', 'process')):
                    raise InventoryError('binding_conflict', 'Attachment already belongs to another bot/client binding.')
        bound = dict(existing or {}, client_id=client, environment=environment, attachment=matches[0])
        if arguments.get('thread_id') is not None:
            bound['thread_id'] = text(arguments['thread_id'], 'thread_id')
        bot['bindings'][key] = bound
        state['bots'][bot['bot_id']] = bot
        self.save(state)
        return deepcopy(bound)

    def annotate(self, resources):
        state = self.state()
        if not state['bots']:
            return resources
        live = list(self.observations())
        for row in resources:
            pane_ids = {p['pane_id'] for p in row.get('window', {}).get('panes', [])}
            matches = []
            for bot in state['bots'].values():
                for bound in bot.get('bindings', {}).values():
                    attachment = bound.get('attachment', {})
                    if attachment.get('pane_id') not in pane_ids:
                        continue
                    exact = [p for p in live if all(p.get(k) == attachment.get(k)
                             for k in ('pane_id', 'namespace', 'process'))]
                    if len(exact) == 1 and exact[0]['workspace'] == row['target']['workspace']:
                        matches.append(bot)
            if len(matches) == 1:
                row['bot_family'] = {k: v for k, v in matches[0].items() if k != 'bindings'}
        return resources

    def execute(self, operation, arguments):
        if not isinstance(arguments, dict):
            raise InventoryError('invalid_argument', 'Bot family arguments must be an object.')
        args = dict(arguments)
        expected = args.pop('expected_target', None)
        args.pop('_request', None)
        verb = operation.removeprefix('tabs.family.')
        if verb not in {'register', 'list', 'show', 'bind'} | self.LIFECYCLE:
            raise InventoryError('unsupported_operation', 'Unsupported bot family operation.')
        with locked(self.directory):
            if expected is not None and expected != self.target():
                raise InventoryError('stale_target', 'Bot family registry changed.')
            state = self.state()
            if verb == 'register':
                return dict(bot=self.register(args, state), grants_authority=False)
            if verb == 'bind':
                return dict(binding=self.bind(args, state), grants_authority=False)
            if verb == 'list':
                if set(args) - {'root_bot_id'}:
                    raise InventoryError('invalid_argument', 'Unsupported family list arguments.')
                return dict(bots=[deepcopy(b) for b in state['bots'].values() if not args.get('root_bot_id') or b['root_bot_id'] == args['root_bot_id']], grants_authority=False)
            if verb == 'show':
                if set(args) != {'bot_id'}:
                    raise InventoryError('invalid_argument', 'A bot_id is required.')
                bot = self.get(args['bot_id'], state)
                return dict(bot=bot, ancestors=self.ancestors(bot, state), bindings=list(bot['bindings'].values()), grants_authority=False)
            from .bot_family_placement import execute
            return execute(self, verb, args, state)
