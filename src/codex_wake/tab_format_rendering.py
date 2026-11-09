"""Portable rendering fallbacks and evidence-bounded capability descriptions."""
import unicodedata

MODES=('full','basic','plain')
_BASIC_COLOURS={'colour238':'black','colour30':'cyan','colour99':'magenta','colour67':'blue'}
_KNOWN_BACKENDS=frozenset(('tmux','byobu','psmux'))
_PSMUX_SHA='bbe825a30f7cddc91b043084049143a381aba5f7e9e36e4d0bb587e296d262ca'


def badge_text(value,width=16,*,ascii_only=True):
    """Conservatively bound display cells and escape native format introducers.

    Native #W expands manual names separately. Only Wake-generated metadata is
    normalized here. Complex grapheme layout is terminal-specific; ASCII is the
    default fallback, while Unicode bounds count each visible codepoint safely.
    """
    value=str(value)
    if ascii_only:
        value=unicodedata.normalize('NFKD',value).encode('ascii','replace').decode('ascii')
    output=[];used=0
    for char in value:
        if unicodedata.category(char).startswith('C'):continue
        cells=0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in ('W','F') else 1
        if used+cells>width:break
        output.append(char);used+=cells
    return ''.join(output).replace('#','##')


def styles(colour,state,mode):
    if mode not in MODES:raise ValueError('Unsupported rendering mode.')
    if mode=='plain':return 'fg=default,bg=default','fg=default,bg=default,bold,underscore'
    if mode=='basic':colour=_BASIC_COLOURS.get(colour,'blue' if colour.startswith('colour') else colour)
    intensity=',bold' if state in ('running','error','health-warning','waiting') else ',dim'
    return f'fg=white,bg={colour}{intensity}',f'fg=white,bg={colour},bold,underscore'


def capabilities(backend,*,identity=None,colour_depth=None):
    """Describe protocol knowledge separately from an observed native identity.

    The native psmux hash was qualified in a disposable namespace. A backend name
    alone never proves installed support, nor a client's colour/glyph fidelity.
    """
    identity=identity or {}
    known=backend in _KNOWN_BACKENDS
    qualified=backend=='psmux' and identity.get('executable_sha256')==_PSMUX_SHA
    return dict(backend=backend,status='conditional' if known else 'unsupported',
                protocol='qualified_identity' if qualified else 'requires_native_qualification' if known else 'unsupported',
                observed_identity=identity,colour_depth=colour_depth or 'unknown',
                client_rendering='requires_client_acceptance',
                native_selection=known,modes=list(MODES) if known else [],
                ascii_fallback=known,unicode_width='conservative_cells_terminal_dependent',
                qualification_scope='option readback and native format expansion; client pixels are a separate acceptance boundary')
