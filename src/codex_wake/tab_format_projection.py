"""Pure visual projection; no terminal commands, runtime probes or model work."""


def project(resource, policy=None, *, now=None):
    """Return managed window options and the human-readable visual decision."""
    traits=resource.get('traits',{}).get('traits',{})
    harness=traits.get('harness',{}).get('value')
    activity=traits.get('activity',{}).get('value') or 'unknown'
    label,colour={'codex':('CX','blue'),'grok':('GK','magenta'),
                  'ssh':('SSH','colour67'),'mixed':('MIX','colour238')}.get(harness,('SH','colour238'))
    return dict(label=label,state=activity,options={
        'window-status-format':f' #I {label} {activity} #W ',
        'window-status-current-format':f'#[bold,underscore] #I {label} {activity} #W ',
        'window-status-style':f'fg=white,bg={colour}',
        'window-status-current-style':f'fg=white,bg={colour},bold,underscore'})
