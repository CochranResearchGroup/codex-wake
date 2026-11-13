"""Bound family metadata rendered through Wake's reversible tab decoration."""
import hashlib
from .tab_format_rendering import badge_text, styles

# Muted, non-alert hues; independent of Python's randomized hash seed.
ACCENTS=('colour60','colour66','colour67','colour95','colour103','colour109')
ATTENTION=frozenset(('error','health-warning','waiting','stale'))


def decorate(projection, resource, policy):
    """Only consume descriptors supplied by the exact-binding inventory owner."""
    family=resource.get('bot_family')
    if not isinstance(family,dict) or not family.get('root_bot_id'):return projection
    root=family['root_bot_id']
    colour=ACCENTS[int.from_bytes(hashlib.sha256(root.encode()).digest()[:4],'big')%len(ACCENTS)]
    def text(value,width):
        return badge_text(value,width,ascii_only=policy.get('ascii',True),
                          space_style=resource.get('target',{}).get('presentation')=='psmux')
    label=text(family.get('scope_kind','specialist'),12)+':'+text(family.get('name',family.get('bot_id','')),24)
    if family.get('scope_ref'):label+=' '+text(family['scope_ref'],20)
    # Keep existing attention cues and preset colours; family text is readable
    # even in plain mode and never replaces the user's native window name.
    for key in ('window-status-format','window-status-current-format'):
        projection['options'][key]=projection['options'][key].replace('#W',label+' #W')
    if projection['state'] not in ATTENTION:
        projection['colour']=colour
        normal,current=styles(colour,projection['state'],policy.get('render_mode','full'))
        projection['options']['window-status-style']=normal
        projection['options']['window-status-current-style']=current
    normal,current=styles(colour,'idle',policy.get('render_mode','full'))
    projection['fallback_styles']=dict(zip(('window-status-style','window-status-current-style'),(normal,current)))
    projection['details']['bot_family']=dict(family)
    return projection
