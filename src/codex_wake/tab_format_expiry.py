"""Expire only dynamic cues using one shared publisher lease, never the palette."""
import math

CLOCK_OPTION = '@wake-format-clock'
STALE_AFTER = 20.0
LEASE_VALID = '#{&&:#{>:#{@wake-format-clock},#{T:#{l:%s}}},#{<=:#{@wake-format-clock},#{e|+|:#{T:#{l:%s}},30}}}'


def leased_fragment(fragment):
    """Guard a fixed generated cue; never pass user text through this helper."""
    return '#{?' + LEASE_VALID + ',' + fragment.replace(',', '#,') + ',}'


def expiring_options(options, *, observed_at, stale_after=STALE_AFTER,
                     render_mode='full', show_stale=True, shared_lease=False,
                     fallback_styles=None):
    """Keep options byte-stable across samples and restore only type styles on loss.

    observed_at and legacy keyword arguments remain accepted for compatibility.
    The host updates the existing managed session option with an absolute lease
    deadline. Native time keeps cues honest even if the publisher stops entirely.
    No label, native name or type palette is put behind an age deadline.
    """
    if not isinstance(observed_at, (int, float)) or not math.isfinite(observed_at):
        raise ValueError('Formatting observation needs a finite timestamp.')
    result = dict(options)
    if not shared_lease:
        return result
    fallback_styles = fallback_styles or options
    for name in ('window-status-format', 'window-status-current-format'):
        style_name = name.removesuffix('format') + 'style'
        current = options[style_name]
        fallback = fallback_styles[style_name]
        result[style_name] = fallback
        if current != fallback:
            active = ('#[default,' + current + ']').replace(',', '#,')
            inactive = ('#[default,' + fallback + ']').replace(',', '#,')
            result[name] = '#{?' + LEASE_VALID + ',' + active + ',' + inactive + '}' + options[name]
    return result
