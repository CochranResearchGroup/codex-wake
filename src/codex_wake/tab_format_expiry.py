"""Backend-native expiry: no shell jobs, runtime probes or Wake redraw hooks."""
import math

CLOCK_OPTION='@wake-format-clock'
STALE_AFTER=20.0


def expiring_options(options, *, observed_at, stale_after=STALE_AFTER, render_mode='full', show_stale=True):
    """Embed an absolute deadline evaluated by the backend's native clock.

    The session clock option is owned/restored with other formatting settings.
    Native selection is still chosen by current-format, never by Wake focus.
    """
    if not isinstance(observed_at,(int,float)) or not math.isfinite(observed_at):
        raise ValueError('Formatting observation needs a finite timestamp.')
    lower=int(observed_at);expiry=int(observed_at+stale_after)
    clock='#{T:'+CLOCK_OPTION+'}'
    condition='#{||:#{>=:'+clock+','+str(expiry)+'},#{<:'+clock+','+str(lower)+'}}'
    result=dict(options)
    for name in ('window-status-format','window-status-current-format'):
        current=name=='window-status-current-format'
        style=options['window-status-current-style' if current else 'window-status-style']
        # Commas inside a format conditional must be escaped; inline styles
        # preserve the current-window cue in both current and stale branches.
        fresh_style='#[default,'+style+']'
        plain=render_mode=='plain' or style.startswith('fg=default,bg=default')
        stale_colour='fg=default,bg=default' if plain else 'fg=white,bg=black' if render_mode=='basic' else 'fg=white,bg=colour238'
        stale_style='#[default,'+stale_colour+(',bold,underscore' if current else '')+']'
        # Keep projected/user text OUTSIDE the conditional branches. This avoids
        # reinterpreting literal commas/braces in profile/model/provider labels.
        if not show_stale:
            stale_style='#[default,'+style+',dim]'
        stale_label = ' STALE ' if show_stale else ''
        result[name]='#{?'+condition+','+stale_style.replace(',','#,')+stale_label+','+fresh_style.replace(',','#,')+'}'+options[name]
    return result
