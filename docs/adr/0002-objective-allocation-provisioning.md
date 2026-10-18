# Provision verified callers against objective allocations

Accepted product contract; implementation pending under Plan0169. A verified
user allocation request authorizes automatic provisioning for its verified
caller, avoiding manual UUID grants. Continuations bind to the same objective
allocation and retain cumulative usage and the original deadline; ambiguous
links hold with a concrete recovery action. Only an explicit user renewal or
reset changes its named allocation, preserving history and leaving unrelated
objectives unchanged. This extends ADR0001's same-session enrollment model;
native stop authority remains exact to verified registered conversations and
does not authorize adopting or restarting the shared executor. We choose this
over tab/CWD-based inheritance because conversation location is neither user
resource authority nor proof of allocation continuity.


2026-10-18 clarification: the enforcement subject is the goal campaign, not all
future conversation turns. Reserve/grace requests allow checkpoint winddown;
then pause the goal and stop its observed exact turns. Subsequent operator
messages remain usable while campaign continuation stays held. Persist stop-turn
ownership so controller reconstruction cannot adopt an operator reply as work.
