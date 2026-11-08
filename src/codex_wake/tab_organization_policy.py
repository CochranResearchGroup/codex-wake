"""Opt-in bounded physical ordering over existing layout owners and receipts.

This owner does not start a daemon. The existing same-root monitor may invoke a
single admitted tick after explicit enablement. Saved views remain read-only.
ControllerRuntime owns operation admission/replay; retained pending layout plans
pause after interruption instead of being automatically executed on restart.
"""
from pathlib import Path
import math
import re
import time

from .managed_inventory import InventoryError
from .shortcut_store import locked, read, write
from .tab_organization import TabOrganization, digest
from .tab_views import FIELDS, TabViews


DEFAULTS = dict(mode='activity', criteria=[], pins=[], debounce_seconds=5.0,
                min_interval_seconds=30.0, max_swaps_per_tick=8, stale_after_seconds=20.0)


class TabOrganizationPolicy:
    ARGUMENTS = {
        'tabs.policy.configure': {'workspace', 'mode', 'criteria', 'view', 'pins', 'debounce_seconds',
                                  'min_interval_seconds', 'max_swaps_per_tick', 'stale_after_seconds'},
        'tabs.policy.status': set(), 'tabs.policy.enable': {'acknowledge_pending'}, 'tabs.policy.pause': {'reason'},
        'tabs.policy.disable': set(), 'tabs.policy.tick': set(),
    }

    def __init__(self, root, *, workspaces, clock=time.time):
        self.root = Path(root)
        self.workspaces = dict(workspaces)
        self.clock = clock
        self.directory = self.root / 'tab-organization-policy'
        self.path = self.directory / 'policy.json'

    def _read(self):
        try:
            state = read(self.path)
        except FileNotFoundError:
            return dict(version=1, revision=0, control_revision=0, state='disabled', last_reason='opt_in_required',
                        settings=None, baseline=None, candidate=None, pending_plan=None,
                        last_apply_at=None, last_tick_at=None, last_receipt=None)
        if (not isinstance(state, dict) or state.get('version') != 1
                or state.get('state') not in ('disabled', 'enabled', 'paused')):
            raise InventoryError('policy_state_unavailable', 'unsupported physical organization policy state')
        return state

    def _save(self, state):
        previous=self._read()
        control=max(state.get('control_revision',0),previous.get('control_revision',0))
        if previous['state']!=state['state'] and control==previous.get('control_revision',0):
            control+=1
        state['control_revision']=control
        state['revision'] += 1
        write(self.path, state)

    @staticmethod
    def _result(state, *, result=None, effects=False):
        return dict(policy=state, result=result, physical_effects=effects)

    def execute(self, operation, arguments):
        if operation not in self.ARGUMENTS:
            raise InventoryError('unsupported_operation', 'unsupported physical organization policy action')
        if not isinstance(arguments, dict) or set(arguments) - self.ARGUMENTS[operation]:
            raise InventoryError('invalid_argument', 'unsupported physical policy arguments')
        if operation == 'tabs.policy.status':
            return self._result(self._read())
        with locked(self.directory):
            state = self._read()
            if operation == 'tabs.policy.configure':
                if state['pending_plan']:
                    raise InventoryError('policy_reconciliation_required', 'reconcile the retained layout receipt before replacing policy')
                settings = dict(DEFAULTS, **arguments)
                self._validate(settings)
                state.update(state='disabled', settings=settings, baseline=None, candidate=None,
                             last_reason='configured_requires_opt_in')
            elif operation == 'tabs.policy.enable':
                if not state['settings']:
                    raise InventoryError('policy_not_configured', 'configure a workspace ordering policy before enabling')
                acknowledge = arguments.get('acknowledge_pending', False)
                if type(acknowledge) is not bool:
                    raise InventoryError('invalid_argument', 'acknowledge_pending must be Boolean')
                if state['pending_plan'] and not acknowledge:
                    raise InventoryError('policy_reconciliation_required', 'inspect retained plan/receipt; use explicit acknowledge_pending to accept current layout without replay')
                self._validate(dict(state['settings']))
                owner = self._owner(state['settings'])
                owner.criteria = state['settings']['criteria'] if state['settings']['mode'] == 'traits' else []
                snapshot = owner.snapshot(state['settings']['pins'], time.monotonic() + 10)
                baseline = self._layout(snapshot)
                if state['pending_plan']:
                    state['last_reconciled_plan'] = dict(plan_id=state['pending_plan'],
                        acknowledged_at=self.clock(), layout=digest(baseline),
                        prior_effect_outcome='retained_unchanged', action='accept_current_layout_without_replay')
                state.update(state='enabled', baseline=baseline, candidate=None, pending_plan=None,
                             last_reason='enabled', last_tick_at=self.clock())
            elif operation in ('tabs.policy.pause', 'tabs.policy.disable'):
                reason = arguments.get('reason', 'operator_paused')
                if not isinstance(reason, str) or len(reason) > 256 or any(ord(c) < 32 for c in reason):
                    raise InventoryError('invalid_argument', 'pause reason must be bounded single-line text')
                state.update(state='paused' if operation.endswith('pause') else 'disabled', candidate=None,
                             last_reason=reason if operation.endswith('pause') else 'operator_disabled')
            else:
                return self._tick(state)
            state['control_revision']=state.get('control_revision',0)+1
            self._save(state)
            return self._result(state)

    def _validate(self, settings):
        workspace = settings.get('workspace')
        if not isinstance(workspace, str) or workspace not in self.workspaces:
            raise InventoryError('unsupported_target', 'select an observed host-owned workspace')
        if settings['mode'] not in ('activity', 'repository', 'traits'):
            raise InventoryError('invalid_argument', 'physical ordering mode must be activity, repository or traits')
        if 'view' in settings:
            view = TabViews(self.root).execute('tabs.view-show', {'name': settings['view']})['view']
            definition = view['definition']
            if definition.get('filters') or definition.get('group'):
                raise InventoryError('unsupported_target', 'automatic filtered/named-group placement is not qualified; use explicit criteria or manual preview')
            settings.update(mode='traits', criteria=list(dict.fromkeys(definition.get('group_by', []) + definition.get('sort_by', []))),
                            view_revision=digest(view))
        criteria = settings['criteria']
        if (not isinstance(criteria, list) or len(criteria) > len(FIELDS) or any(not isinstance(v, str) or v not in FIELDS for v in criteria)
                or (settings['mode'] == 'traits' and not criteria)):
            raise InventoryError('invalid_argument', 'trait ordering requires a bounded list of known criteria')
        pins = settings['pins']
        if not isinstance(pins, list) or len(pins) > 4096 or any(not isinstance(p, str) or not re.fullmatch(r'@[0-9]+', p) for p in pins):
            raise InventoryError('invalid_argument', 'pins must be bounded exact window IDs')
        for key, low, high in (('debounce_seconds', 0, 300), ('min_interval_seconds', 1, 3600), ('stale_after_seconds', .1, 600)):
            value = settings[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                raise InventoryError('invalid_argument', key + ' is outside bounded physical policy settings')
        if type(settings['max_swaps_per_tick']) is not int or not 1 <= settings['max_swaps_per_tick'] <= 64:
            raise InventoryError('invalid_argument', 'max_swaps_per_tick must be 1 through 64')

    def _owner(self, settings):
        config = self.workspaces[settings['workspace']]
        if not hasattr(config['transport'], 'swap'):
            raise InventoryError('unsupported_target', 'backend has no qualified ordering adapter')
        fields = settings['criteria'] if settings['mode'] == 'traits' else [settings['mode']]
        observer = config.get('observer')
        def fresh_observer(timeout):
            evidence = observer(timeout) if observer else {}
            result = {}
            for key, sample in evidence.items():
                value = dict(sample)
                for field in fields:
                    trait = sample.get('traits', {}).get(field, {})
                    observed = trait.get('observed_at')
                    fresh = (trait.get('status') == 'observed' and trait.get('freshness') == 'fresh'
                        and type(observed) in (int, float) and math.isfinite(observed)
                        and 0 <= self.clock() - observed <= settings['stale_after_seconds'])
                    if not fresh:
                        value['fresh'] = False
                result[key] = value
            return result
        return TabOrganization(self.root, transport=config['transport'], observer=fresh_observer,
                               authorize=lambda action: None)

    @staticmethod
    def _layout(snapshot):
        """Manual layout/process identity, deliberately excluding activity traits."""
        from .process import process_identity
        windows = []
        for window in snapshot['windows']:
            panes = []
            for pane in window['panes']:
                process = (dict(creation_filetime=pane.get('windows_creation_filetime'))
                           if pane.get('platform') == 'windows' else process_identity(pane['pid']))
                binding = pane.get('binding')
                panes.append(dict(pane=pane['pane_id'], pid=pane['pid'], process=process,
                    binding={k: binding.get(k) for k in ('process', 'conversation_id', 'namespace')} if binding else None))
            windows.append(dict(window=window['window_id'], index=window['index'], name=window['name'],
                                focused=window['focused'], linked=window['linked'], panes=panes))
        return dict(server=snapshot['server'], session=snapshot['session_id'], socket=snapshot.get('socket_identity',snapshot.get('server_identity')), windows=windows)

    @staticmethod
    def _layout_changed(before, after):
        if before is None:
            return True
        def physical(layout):
            return dict(layout, windows=[dict(w, panes=[{k: v for k, v in p.items() if k != 'binding'}
                                                        for p in w['panes']]) for w in layout['windows']])
        if physical(before) != physical(after):
            return True
        for old, new in zip(before['windows'], after['windows']):
            for old_pane, new_pane in zip(old['panes'], new['panes']):
                if old_pane['binding'] and new_pane['binding'] and old_pane['binding'] != new_pane['binding']:
                    return True
        return False

    @staticmethod
    def _swaps(plan):
        ids = [w['window_id'] for w in plan['before']['windows']]
        count = 0
        for index, target in enumerate(plan['target']):
            if ids[index] != target['window_id']:
                other = ids.index(target['window_id'])
                ids[index], ids[other] = ids[other], ids[index]
                count += 1
        return count

    def _tick(self, state):
        if state['state'] != 'enabled':
            return self._result(state)
        if state['pending_plan']:
            state.update(state='paused', last_reason='incomplete_layout_operation', candidate=None)
            self._save(state)
            return self._result(state)
        now = self.clock()
        if not math.isfinite(now) or state['last_tick_at'] is not None and now < state['last_tick_at']:
            state.update(state='paused', last_reason='clock_regressed', candidate=None)
            self._save(state)
            return self._result(state)
        settings = state['settings']
        if settings.get('view'):
            view = TabViews(self.root).execute('tabs.view-show', {'name': settings['view']})['view']
            if digest(view) != settings['view_revision']:
                state.update(state='paused', last_reason='saved_view_changed', candidate=None)
                self._save(state)
                return self._result(state)
        owner = self._owner(settings)
        plan = None
        deadline = time.monotonic() + 10
        try:
            plan = owner.preview(mode=settings['mode'], criteria=settings['criteria'],
                                 pins=settings['pins'], deadline=deadline)['plan']
            layout = self._layout(plan['before'])
            state['last_tick_at'] = now
            if self._layout_changed(state['baseline'], layout):
                state.update(state='paused', last_reason='manual_layout_or_binding_changed', candidate=None)
            elif self._swaps(plan) == 0:
                unqualified = any('unqualified' in reason for w in plan['before']['windows'] for reason in w['pins'])
                state.update(last_reason='unqualified_observations' if unqualified else 'already_arranged', candidate=None)
            elif self._swaps(plan) > settings['max_swaps_per_tick']:
                state.update(last_reason='swap_limit', candidate=None)
            elif state['last_apply_at'] is not None and now - state['last_apply_at'] < settings['min_interval_seconds']:
                state.update(last_reason='rate_limited', candidate=None)
            else:
                desired = digest(plan['target'])
                candidate = state['candidate']
                if candidate is None or candidate['desired'] != desired:
                    state.update(candidate=dict(desired=desired, since=now), last_reason='debouncing')
                elif now - candidate['since'] < settings['debounce_seconds']:
                    state['last_reason'] = 'debouncing'
                else:
                    state.update(pending_plan=plan['plan_id'], last_reason='applying')
                    self._save(state)
                    result = owner.apply(plan['plan_id'], deadline=deadline)
                    receipt = result['receipt']
                    state['last_receipt'] = receipt['receipt_id']
                    if result['status'] == 'applied':
                        state.update(baseline=self._layout(receipt['after']), pending_plan=None,
                                     candidate=None, last_apply_at=now, last_reason='arranged')
                    else:
                        state.update(state='paused', last_reason='layout_' + result['status'], candidate=None)
                    self._save(state)
                    return self._result(state, result=result, effects=bool(receipt['swaps']))
            self._save(state)
            return self._result(state)
        except Exception:
            if state['pending_plan']:
                state.update(state='paused', last_reason='incomplete_layout_operation', candidate=None)
                self._save(state)
            raise
        finally:
            if plan and state['pending_plan'] != plan['plan_id'] and not plan.get('receipt_id'):
                # Unapplied tick previews are owned ephemeral files, not a growing
                # journal. Retain any plan referenced by a pending/applied receipt.
                path = owner.directory / (plan['plan_id'] + '.json')
                if not state['last_receipt'] or owner.read(plan['plan_id']).get('receipt_id') is None:
                    path.unlink(missing_ok=True)
