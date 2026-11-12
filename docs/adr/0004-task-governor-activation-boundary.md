# Start new task governor windows at successful activation

The operator wants an ordinary existing session to accept a new task allowance
without charging unrelated work earlier in that conversation. A task allowance
includes its qualified delegated work, retries and continuations; it is distinct
from any broader shared allocation.

For the new governor activation workflow, freeze a qualified usage boundary and
start elapsed time at successful activation. Count subsequent usage and elapsed
waits. Include earlier usage only when explicitly requested. Preserve lifetime
accounting and existing historical enrollment semantics. This supersedes ADR0001's
original-goal-start rule only for explicitly new task windows; it does not renew
or rewrite existing allocations.

Both task-local and shared ceilings apply. Raising one cannot bypass the other.
An explicit reset starts a new generation while retaining charges and stop
history. Fresh context, reconnect, delegation, enrollment and service restart
cannot reset a window. Unknown accounting or lost enforcement pauses affected
work with a truthful visible state; advisory operation requires explicit choice.

The tradeoff is an additional explicit accounting boundary rather than treating
conversation lifetime as task identity. This is necessary to keep ordinary task
limits useful while preserving cumulative delegated/shared accounting.

Authority: accepted P220 interview, spec #570, Plan0220. Source implementation,
installed enforcement and native UI qualification remain distinct proof stages.
