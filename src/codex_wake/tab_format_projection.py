"""Pure visual projection of independently qualified attachment traits.

No terminal commands, process probes, provider calls or capability inference live
here. A backend renders the returned options; its native #W keeps manual names.
"""
import math
import time
from .tab_format_rendering import badge_text as _text, styles, capabilities

_FRESH_SECONDS = 20
_TYPES = {'codex': ('CX?', 'colour238'), 'codex:stock': ('CX', 'blue'),
          'codex:modded': ('CX+', 'colour30'),
          'grok': ('GK', 'colour99'), 'ssh': ('SSH', 'colour67'),
          'mixed': ('MIX', 'colour238'), 'shell': ('SH', 'colour238'),
          'unknown': ('?', 'colour238')}
_ATTENTION = {'error': ('ERR', 'red'), 'health-warning': ('HLTH', 'magenta'),
              'waiting': ('WAIT', 'yellow'), 'stale': ('STALE', 'colour238')}
_ACTIVITY = {'running': 'RUN', 'idle': 'IDLE', 'disconnected': 'OFF',
             'waiting-for-input': 'WAIT', 'unknown': '?', 'mixed': 'MIX'}
_DIMENSIONS = ('harness', 'build', 'profile', 'model', 'inference_provider',
               'execution_host', 'activity')
_WARNING_HEALTH = frozenset(('unresponsive', 'offline', 'degraded', 'warning', 'error'))


def _fresh(observation, now):
    if not isinstance(observation, dict):
        return False
    if observation.get('status') in ('unknown', 'unsupported', 'stale', 'configured', None):
        return False
    if observation.get('freshness') in ('stale', 'unknown', 'unsupported', 'configured'):
        return False
    stamp = observation.get('observed_at')
    return (type(stamp) in (int, float) and math.isfinite(stamp)
            and 0 <= now - stamp <= _FRESH_SECONDS)


def _pane_traits(resource):
    observed = resource.get('traits', {})
    panes = observed.get('panes') or []
    return panes or [dict(pane_id=None, traits=observed.get('traits', {}))]


def _dimension_traits(traits, resource):
    # Bare `provider` remains the legacy harness/runtime field, never inference.
    values = {key: traits.get(key, {}) for key in _DIMENSIONS}
    values['profile'] = traits.get('profile') or traits.get('account', {})
    values['model'] = traits.get('model_identity') or traits.get('model', {})
    if not values['execution_host']:
        target = resource.get('target', {})
        values['execution_host'] = dict(value=target.get('host'), status='configured',
                                        source='workspace_target', observed_at=None)
    return values


def _type(traits, now):
    harness = traits.get('harness', {}).get('value', 'unknown')
    remote = traits.get('remote_host', {})
    if harness in ('unknown', None) and _fresh(remote, now) and remote.get('value') not in ('unknown', None):
        return 'ssh'
    build = traits.get('build', {})
    if harness == 'codex' and _fresh(build, now) and build.get('value') in ('stock', 'modded'):
        return 'codex:' + build['value']
    if harness not in ('unknown', None):
        return str(harness)
    if traits.get('session_presence', {}).get('value') == 'absent':
        return 'shell'
    return 'unknown'


def _observed_value(observation, now):
    value = observation.get('value') if isinstance(observation, dict) else None
    return value if value not in (None, 'unknown') and _fresh(observation, now) else None


def project(resource, policy=None, *, now=None):
    """Produce labels, options and per-pane provenance from an observed resource.

    Optional style rules match fresh dimensions exactly and only change base hue;
    they cannot override current error, health warning, waiting or stale states.
    Configured model/provider badges are explicitly marked cfg, never observed.
    """
    now = time.time() if now is None else now
    policy = policy or {}
    backend=resource.get('target',{}).get('presentation','unknown')
    def text(value,width=16):
        return _text(value,width,ascii_only=policy.get('ascii',True),space_style=backend=='psmux')
    panes = _pane_traits(resource)
    kinds = {_type(pane.get('traits', {}), now) for pane in panes}
    kind = next(iter(kinds)) if len(kinds) == 1 else 'mixed'
    label, colour = _TYPES.get(kind, (text(kind,8).upper(),'colour238'))
    details = []
    fresh = False
    priorities = set()
    activities = set()
    badges = {'profile': set(), 'model': set(), 'inference_provider': set()}
    matches = []
    for pane in panes:
        traits = pane.get('traits', {})
        dimensions = _dimension_traits(traits, resource)
        qualified = {key: _observed_value(value, now) for key, value in dimensions.items()}
        matches.append(qualified)
        pane_fresh = any(_fresh(value, now) for value in traits.values() if isinstance(value, dict))
        fresh = fresh or pane_fresh
        error = traits.get('error', {})
        health = traits.get('health', {})
        activity = traits.get('activity', {})
        if _fresh(error, now) and error.get('value') == 'present':
            priorities.add('error')
        if _fresh(health, now) and health.get('value') in _WARNING_HEALTH:
            priorities.add('health-warning')
        if _fresh(activity, now) and activity.get('value') == 'waiting-for-input':
            priorities.add('waiting')
        activities.add(qualified['activity'] or 'unknown')
        for key in badges:
            value = qualified[key]
            if value is not None:
                badges[key].add(text(value))
            elif key != 'profile' and dimensions[key].get('status') == 'configured':
                configured = dimensions[key].get('value')
                if configured not in (None, 'unknown'):
                    badges[key].add('cfg:' + text(configured,12))
        details.append(dict(pane_id=pane.get('pane_id'), type=_type(traits, now),
                            dimensions=dimensions, attention={key: traits.get(key, {}) for key in ('health', 'error')},
                            fresh=pane_fresh))
    for rule in policy.get('style_rules', []):
        if any(all(values.get(key) == value for key, value in rule['match'].items()) for values in matches):
            colour = rule['colour']
            break
    activity = next(iter(activities)) if len(activities) == 1 else 'mixed'
    state = next((state for state in ('error', 'health-warning', 'waiting') if state in priorities), None)
    if state is None and not fresh:
        state = 'stale' if any(trait.get('observed_at') is not None for pane in panes
                               for trait in pane.get('traits', {}).values() if isinstance(trait, dict)) else 'unknown'
    state = state or activity
    if state in _ATTENTION:
        marker, colour = _ATTENTION[state]
    else:
        marker = _ACTIVITY.get(activity, text(activity,8).upper())
    pieces = [label]
    if badges['profile']:
        pieces.append(next(iter(badges['profile'])) if len(badges['profile']) == 1 else 'profiles:MIX')
    if state != 'stale' or policy.get('show_stale', True):
        pieces.append(marker)
    for key, enabled in (('model', 'show_model'), ('inference_provider', 'show_provider')):
        if policy.get(enabled) and badges[key]:
            pieces.append(next(iter(badges[key])) if len(badges[key]) == 1 else key + ':MIX')
    if policy.get('compact'):
        pieces = [] if kind in ('shell', 'unknown') else [label]
        cue = {'running': '*', 'waiting': '?', 'error': '!', 'health-warning': '!'}.get(state, '')
        if cue:pieces.append(cue)
    badge = ' '.join(pieces)
    compact_normal = f' #I:{badge + " " if badge else ""}#W '
    compact_current = f'#[bold,underscore] [#I:{badge + " " if badge else ""}#W] '
    normal_style,current_style=styles(colour,state,policy.get('render_mode','full'))
    rendering=capabilities(resource.get('target',{}).get('presentation','unknown'),
        identity=resource.get('backend_identity'))
    rendering['requested_mode']=policy.get('render_mode','full')
    return dict(label=label, state=state, colour=colour,
                details=dict(panes=details,mixed=len(kinds)>1,activity=activity,rendering=rendering),
                options={'window-status-format': compact_normal if policy.get('compact') else f' #I {badge} #W ',
                         'window-status-current-format': compact_current if policy.get('compact') else f'#[bold,underscore] [#I {badge} #W] ',
                         'window-status-style': normal_style,
                         'window-status-current-style': current_style})
