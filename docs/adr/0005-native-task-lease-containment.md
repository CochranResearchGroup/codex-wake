# Keep task-loss containment in the native harness

An external watcher cannot stop work after it is abruptly killed. UI polling can
report lost contact but cannot establish that active work paused. P220 therefore
uses a native per-task lease and causal-root cancellation, alongside the existing
external accounting owner.

Lease expiry cancels only the qualified task and its native delegated lineage,
including children starting after the last external poll. Exact goal/turn identity,
controller/enrollment generations, BOOTTIME and durable recovery marks prevent
stale renewal or automatic cold resumption. Operator inspection/replies and
unrelated work remain available. No goal is created merely to engage supervision.

The tradeoff is that strict fail-closed engagement requires a matched modded native
build and compatible watcher. Older builds must report that limitation, with an
explicit advisory choice; a fresh heartbeat alone is insufficient. Existing
historical enrollment semantics and accounting remain attributable.

Authority: accepted P220 loss-containment and isolation decisions, spec #570 and
Plan0220. This decision records the architecture; exact native/installed acceptance
is still a separate gate in ticket #574.
