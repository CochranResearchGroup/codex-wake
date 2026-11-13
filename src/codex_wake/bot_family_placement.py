"""Background presentation of exact bot attachments; never conversation ownership."""
from copy import deepcopy
import time

from .bot_families import binding_key, text
from .managed_inventory import InventoryError
from .tab_lifecycle import TabLifecycle
from .terminal_sessions import TerminalSessions
from .terminal_relocation import TerminalRelocation
from .terminal_tab_holds import TabHolds
from .tab_views import TabViews
from .tab_organization import digest


FIELDS = {
    'open': {'workspace', 'server', 'profile', 'cwd', 'thread_id', 'argv', 'placement'},
    'accept': {'parent_bot_id', 'result_id', 'successful'},
    'adopt': set(), 'focus': {'relation'},
}


class _FamilyLifecycle(TabLifecycle):
    def _protection(self, config, window, deadline):
        reasons, affected = super()._protection(config, window, deadline)
        if 'focused' in reasons and config['kind'] in ('tmux', 'byobu'):
            transport = config['transport']
            attached = transport.command(deadline, 'display-message', '-p', '-t', transport.session,
                                         '#{session_attached}').strip()
            if attached == '0':
                reasons.remove('focused')
        return reasons, affected


def _lifecycle(registry):
    tabs = registry.tabs
    return _FamilyLifecycle(registry.root, workspaces=tabs.workspaces, host=tabs.host, environment=tabs.environment)


def _resource(registry, attachment):
    rows = registry.tabs.execute('tabs.list', {})['resources']
    matches = [r for r in rows if r['target']['workspace'] == attachment['workspace']
               and r['window']['window_id'] == attachment['window_id']]
    if len(matches) != 1:
        raise InventoryError('stale_target', 'Exact bot presentation is unavailable.')
    return matches[0]


def _store(registry, state, bot, key, bound):
    state['bots'][bot['bot_id']]['bindings'][key] = bound
    registry.save(state)


def _result(bound, **fields):
    return dict(binding=deepcopy(bound), grants_authority=False, **fields)


def execute(registry, verb, args, state):
    if set(args) - ({'bot_id', 'client_id', 'environment'} | FIELDS[verb]):
        raise InventoryError('invalid_argument', 'Unsupported family lifecycle arguments.')
    bot = registry.get(args.get('bot_id'), state)
    client = text(args.get('client_id'), 'client_id')
    environment = args.get('environment', registry.tabs.environment)
    if environment != registry.tabs.environment:
        raise InventoryError('unsupported_target', 'Select this host environment.')
    key = binding_key(client, environment)
    saved = bot['bindings'].get(key, {})
    live = registry.resolve_binding(bot, client, environment)
    if verb == 'open':
        return _open(registry, args, state, bot, key, saved, live)
    if verb == 'focus':
        relation = args.get('relation', 'self')
        if relation not in ('self', 'parent', 'root'):
            raise InventoryError('invalid_argument', 'Unknown family relation.')
        related = bot['bot_id'] if relation == 'self' else bot['parent_bot_id'] if relation == 'parent' else bot['root_bot_id']
        target = registry.get(related, state) if related else None
        bound = registry.resolve_binding(target, client, environment) if target else None
        if not bound:
            return dict(status='root-tab-unavailable' if relation == 'root' else 'tab-unavailable', bot_id=related, grants_authority=False)
        attachment = bound['attachment']; owner = _lifecycle(registry)
        result = owner.execute('tabs.focus', dict(workspace=attachment['workspace'], window=attachment['window_id'],
                              expected_target=owner.inspect(attachment['workspace'])['target']))
        return _result(bound, status=result['status'], bot_id=related)
    if not saved:
        raise InventoryError('target_not_found', 'Bot has no attachment for this client.')
    if verb == 'adopt':
        if not live:
            raise InventoryError('stale_target', 'Adoption requires the exact live attachment.')
        saved.update(adopted=True, attachment=live['attachment'])
        _store(registry, state, bot, key, saved)
        return _result(saved, status='adopted')
    parent = text(args.get('parent_bot_id'), 'parent_bot_id')
    result_id = text(args.get('result_id'), 'result_id')
    if parent != bot['parent_bot_id']:
        raise InventoryError('identity_conflict', 'Only the immediate parent may accept this child result.')
    if type(args.get('successful')) is not bool:
        raise InventoryError('invalid_argument', 'successful must be boolean.')
    accepted = dict(parent_bot_id=parent, result_id=result_id, successful=args['successful'])
    if saved.get('close_intent'):
        # A missing reply never permits a second close of a potentially reused ID.
        if saved.get('closed') or (not live and _closed_observed(registry, saved)):
            saved['closed'] = True
            _store(registry, state, bot, key, saved)
            _delete_empty(registry, saved)
            return _result(saved, status='closed')
        return _result(saved, status='uncertain', reason='close_requires_reconciliation')
    saved['acceptance'] = accepted
    _store(registry, state, bot, key, saved)
    if (not args['successful'] or not bot['temporary'] or saved.get('adopted') or not live
            or not saved.get('organized') or live.get('manually_moved') or saved.get('closed')):
        return _result(saved, status='retained')
    resource = _resource(registry, live['attachment'])
    if TabHolds(registry.root).get(TabHolds.identity(resource)):
        return _result(saved, status='retained', reason='manual_hold')
    owner = _lifecycle(registry); attachment = live['attachment']
    payload = dict(workspace=attachment['workspace'], window=attachment['window_id'],
                   expected_target=owner.inspect(attachment['workspace'])['target'])
    preview = owner.execute('tabs.close', dict(payload, preview=True))
    if preview.get('protection'):
        return _result(saved, status='retained', reason='tab_protected')
    saved['close_intent'] = True
    _store(registry, state, bot, key, saved)
    outcome = owner.execute('tabs.close', payload)
    saved.update(closed=True, close_receipt=outcome['receipt_id'])
    _store(registry, state, bot, key, saved)
    _delete_empty(registry, saved)
    return _result(saved, status='closed')


def _closed_observed(registry, saved):
    attachment = saved.get('attachment', {})
    # Missing binding alone could mean a respawn, ambiguous enrollment, or an
    # unavailable server. Require an observed roster in the exact namespace.
    observations = list(registry.observations())
    same = [row for row in observations if row['namespace'] == attachment.get('namespace')]
    if not same:
        return False
    config = registry.tabs.workspaces[same[0]['workspace']]
    try:
        windows = config['transport'].command(time.monotonic()+5, 'list-windows', '-a', '-F', '#{window_id}').splitlines()
    except Exception:
        return False
    return attachment.get('window_id') not in windows


def _delete_empty(registry, bound):
    if not bound.get('workers_session_owned') or not bound.get('session_id'):
        return
    sessions = TerminalSessions(registry.root, tabs=registry.tabs)
    record = sessions.state()['sessions'].get(bound['session_id'], {})
    if record.get('deleted'):
        return
    observed = sessions.resolve(bound['session_id'])
    if observed['state'] == 'empty' and observed['tab_count'] == 0:
        sessions.execute('tabs.session.delete', dict(session=observed['id']))


def _open(registry, args, state, bot, key, saved, live):
    placement = args.get('placement', 'workers')
    if placement not in ('workers', 'adjacent'):
        raise InventoryError('invalid_argument', 'Unknown family placement.')
    if saved.get('close_intent'):
        return _result(live or saved, status='closed' if saved.get('closed') else 'uncertain', reused=True)
    if saved.get('relocation_plan') and not saved.get('organized'):
        relocation = TerminalRelocation(registry.root, tabs=registry.tabs, automatic=True)
        receipt = relocation.execute('tabs.relocate.status', dict(plan_id=saved['relocation_plan']))
        if receipt['status'] != 'completed' or not live:
            return _result(saved, status=receipt['status'], reused=True)
        saved['attachment'] = live['attachment']
        live['manually_moved'] = False
        _store(registry, state, bot, key, saved)
    if live and (saved.get('organized') or saved.get('adopted') or live.get('manually_moved')):
        return _result(live, status='reused', reused=True, session_id=saved.get('session_id'))
    if saved.get('launch_intent') and not live:
        raise InventoryError('uncertain_effect', 'Prior bot launch needs reconciliation; no launch was repeated.')
    sessions = TerminalSessions(registry.root, tabs=registry.tabs)
    parent = registry.get(bot['parent_bot_id'], state) if bot['parent_bot_id'] else None
    parent_bound = registry.resolve_binding(parent, saved.get('client_id') or args['client_id']) if parent else None
    if placement == 'adjacent' and not parent_bound:
        return _result(live or saved, status='root-tab-unavailable', reused=bool(live))
    if placement == 'adjacent':
        destination = sessions.resolve(parent_bound['attachment']['workspace'])
        owned = False
    else:
        server = args.get('server') or (live or {}).get('attachment', {}).get('server')
        selected = sessions.creation_selection(dict(name='workers', backend='tmux', server=server), ensure=True)
        # Never turn an operator's same-name session into an owned cleanup target.
        existing = selected['existing']
        owned = bool(existing and existing[0].get('description') == 'Codex Wake bot family workers')
        if existing and not owned:
            raise InventoryError('name_conflict', 'An existing workers session is not family-owned.')
        destination = sessions.execute('tabs.session.ensure', dict(name='workers', server=selected['server'], start=False))['session']
        if not existing:
            sessions.execute('tabs.session.update', dict(session=destination['id'], changes={'description': 'Codex Wake bot family workers'}))
            owned = True
            destination = sessions.resolve(destination['id'])
    saved.update(client_id=args['client_id'], environment=registry.tabs.environment,
                 session_id=destination['id'], workers_session_owned=owned)
    _store(registry, state, bot, key, saved)
    if not live:
        if saved.get('attachment'):
            raise InventoryError('stale_target', 'Saved bot attachment is absent; explicit rebinding is required.')
        # Materialize using the existing session owner; its launch uncertainty is durable.
        materialized = destination['state'] == 'empty'
        destination = sessions.open(destination, container_only=True)
        owner = _lifecycle(registry)
        bootstrap = destination['snapshot']['windows'][0] if materialized and destination['tab_count'] == 1 else None
        saved['launch_intent'] = True
        _store(registry, state, bot, key, saved)
        payload = dict(workspace=destination['workspace'], name='bot-' + bot['bot_id'][:100] + '-' + digest(key)[:12],
                       expected_target=owner.inspect(destination['workspace'])['target'])
        payload.update({k: args[k] for k in ('cwd', 'argv', 'profile') if k in args})
        outcome = registry.tabs.create_tab(payload)
        if outcome['status'] != 'applied' or not outcome.get('window'):
            return _result(saved, status='uncertain', reused=False)
        window = outcome['window']
        bound_args = dict(bot_id=bot['bot_id'], client_id=args['client_id'], workspace=destination['workspace'],
                          window_id=window['window_id'], pane_id=window['panes'][0]['pane_id'])
        if 'thread_id' in args:
            bound_args['thread_id'] = args['thread_id']
        saved = registry.bind(bound_args, state)
        saved.pop('launch_intent', None)
        saved['launch_receipt'] = outcome['receipt_id']
        # Only the first materialization's shell bootstrap belongs to this launch.
        if bootstrap and owned and not destination.get('family_initialized'):
            cfg = registry.tabs.workspaces[destination['workspace']]
            saved['bootstrap_removing'] = bootstrap['window_id']
            _store(registry, state, bot, key, saved)
            cfg['transport'].command(time.monotonic()+5, 'kill-window', '-t', bootstrap['window_id'])
            saved.pop('bootstrap_removing', None)
        live = registry.resolve_binding(dict(bot, bindings={key: saved}), args['client_id'])
        reused = False
    else:
        reused = True
    resource = _resource(registry, live['attachment'])
    reasons, _ = _lifecycle(registry)._protection(registry.tabs.workspaces[live['attachment']['workspace']], resource['window'], time.monotonic()+5)
    if set(reasons) & {'active_or_waiting_work', 'pending_work', 'pinned', 'linked'}:
        return _result(live, status='retained', reason='tab_protected', reused=True)
    if TabHolds(registry.root).get(TabHolds.identity(resource)):
        return _result(live, status='retained', reason='manual_hold', reused=True)
    if live['attachment']['workspace'] != destination.get('workspace'):
        relocation = TerminalRelocation(registry.root, tabs=registry.tabs, automatic=True)
        if saved.get('relocation_plan'):
            receipt = relocation.execute('tabs.relocate.status', dict(plan_id=saved['relocation_plan']))
        else:
            receipt = relocation.execute('tabs.relocate.preview', dict(destination=destination['id'], selection={'tabs': [TabViews.identity(resource)]}))
            saved['relocation_plan'] = receipt['plan_id']
            _store(registry, state, bot, key, saved)
            receipt = relocation.execute('tabs.relocate.apply', dict(plan_id=receipt['plan_id']))
        if receipt['status'] != 'completed':
            return _result(saved, status=receipt['status'], reused=reused)
        live = registry.resolve_binding(dict(bot, bindings={key: saved}), args['client_id'])
        if not live:
            raise InventoryError('uncertain_effect', 'Moved attachment is not uniquely observable.')
    saved['attachment'] = live['attachment']
    _store(registry, state, bot, key, saved)
    _group(registry, state, bot, key, saved, parent_bound if placement == 'adjacent' else None)
    saved['organized'] = True
    _store(registry, state, bot, key, saved)
    return _result(saved, status='opened', reused=reused, session_id=destination['id'])


def _group(registry, state, bot, key, saved, adjacent):
    """Move only the new member after an exact live family anchor, detached."""
    attachment = saved['attachment']; owner = _lifecycle(registry)
    inspected = owner.inspect(attachment['workspace']); windows = inspected['snapshot']['windows']
    anchor = adjacent['attachment'] if adjacent else None
    if not anchor:
        for other in state['bots'].values():
            if other['root_bot_id'] != bot['root_bot_id']:
                continue
            for bound in other['bindings'].values():
                if bound is saved or bound.get('adopted') or not bound.get('organized'):
                    continue
                live = registry.resolve_binding(other, bound['client_id'])
                if live and not live.get('manually_moved') and live['attachment']['workspace'] == attachment['workspace']:
                    row = _resource(registry, live['attachment'])
                    if not TabHolds(registry.root).get(TabHolds.identity(row)):
                        if anchor is None or next(w['index'] for w in windows if w['window_id']==live['attachment']['window_id']) > next(w['index'] for w in windows if w['window_id']==anchor['window_id']):
                            anchor = live['attachment']
    if not anchor:
        others = [w for w in windows if w['window_id'] != attachment['window_id']]
        if others:
            anchor = dict(window_id=others[-1]['window_id'])
    if not anchor or anchor['window_id'] == attachment['window_id']:
        return
    order = [w['window_id'] for w in windows]
    if order.index(attachment['window_id']) == order.index(anchor['window_id']) + 1:
        saved.pop('group_intent', None)
        return
    if saved.get('group_intent'):
        raise InventoryError('uncertain_effect', 'Prior family ordering needs reconciliation; no move was repeated.')
    saved['group_intent'] = dict(after=anchor['window_id'])
    _store(registry, state, bot, key, saved)
    cfg = registry.tabs.workspaces[attachment['workspace']]
    cfg['transport'].command(time.monotonic()+5, 'move-window', '-d', '-a', '-s', attachment['window_id'], '-t', anchor['window_id'])
    observed = owner.inspect(attachment['workspace'])['snapshot']['windows']
    order = [w['window_id'] for w in observed]
    if order.index(attachment['window_id']) != order.index(anchor['window_id']) + 1:
        raise InventoryError('uncertain_effect', 'Family ordering was not observed.')
    saved.pop('group_intent', None)
