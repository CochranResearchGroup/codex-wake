"""Bounded bridge from observed monitor snapshots to formatting projection."""
import time


def refresh_formatting(root,snapshot,*,tabs=None,deadline=None):
    """Consume trusted host observations; no new trait/runtime probing here.

    Hosts with reliable event snapshots can call the same seam immediately.
    Current terminal discovery has no complete reliable trait-event stream, so
    the existing five-second monitor is the fallback owner, not a new daemon.
    """
    from .controller_tabs import controller_tabs_from_root
    from .tab_formatting import TabFormatting
    tabs=tabs or controller_tabs_from_root(root)
    return TabFormatting(root,tabs=tabs).refresh(snapshot,deadline=deadline or time.monotonic()+10)
