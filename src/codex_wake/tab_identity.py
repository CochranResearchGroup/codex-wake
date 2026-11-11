"""Stable terminal facts for management; observation metadata stays in inventory."""

_DISPLAY_FIELDS = frozenset(('pane_title', 'pane_current_path', 'pane_current_command'))


def stable_panes(panes):
    """Retain births, bindings and unknown fields; omit only transient metadata."""
    return [{key: value for key, value in pane.items() if key not in _DISPLAY_FIELDS}
            for pane in panes]


def stable_snapshot(snapshot):
    return dict(snapshot, windows=[dict(window, panes=stable_panes(window['panes']))
                                   for window in snapshot['windows']])


def stable_tab_birth(birth):
    # Also accepts retained version-one records containing full pane metadata.
    return dict(birth, panes=stable_panes(birth['panes']))
