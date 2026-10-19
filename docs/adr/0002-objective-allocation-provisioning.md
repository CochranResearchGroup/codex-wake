# Provision verified callers against objective allocations

Accepted product contract: a private host policy delegates self-enrollment into
named fixed objective allocations to verified local native callers. No per-session
UUID grants or authenticated operator-origin prompt are required. The host-owned
private native MCP connection supplies thread, turn and call identity separately
from model arguments. Successors share cumulative usage, original deadline and
stopping state; self-enrollment cannot mint or renew allowance. Ambiguity holds
with a concrete action. This trusts the local host/native gateway and does not
provide hostile same-UID isolation or public-HTTP authentication.

An explicit host renewal names the prior allocation in `renews_allocation`,
retains its ledger, finalizes the departing member's charges and anchors renewed
spending at the qualified response boundary. Other members and objectives retain
their authority. An interrupted renewal whose persisted boundary differs from
current history holds for exact reconciliation instead of moving the boundary.
Native stop authority remains exact to registered goal campaign turns and does
not authorize adopting or restarting the shared executor.

Historical initial design required verified operator-origin allocation requests;
the accepted revision below supersedes that requirement after stock native
surfaces could not authenticate operator prompt origin.


2026-10-18 clarification: the enforcement subject is the goal campaign, not all
future conversation turns. Reserve/grace requests allow checkpoint winddown;
then pause the goal and stop its observed exact turns. Subsequent operator
messages remain usable while campaign continuation stays held. Persist stop-turn
ownership so controller reconstruction cannot adopt an operator reply as work.

## Accepted revision — host-delegated self-enrollment (2026-10-18)

The operator approved: "agents need to be able to self enroll or the feature is
useless." This supersedes the requirement to authenticate an operator-origin
prompt for each enrollment. A private host policy may delegate enrollment into
a named, fixed objective allocation to verified local native callers. Agents
may enroll themselves and verified successors without per-session UUID grants.
The host policy remains the resource authority: enrollment cannot mint another
allowance, raise ceilings, reset cumulative usage, extend the original deadline,
or modify unrelated objectives. Caller identity still requires a qualified host
binding; model-provided UUIDs and copied checkpoints are not that binding.

Provisioning must work through the public agent-facing path. Missing host-wide
installation setup must produce an actionable diagnostic while preserving
operator replies; it must not require operators to provision each session.

## Accepted clarification — first native enrollment (2026-10-19)

The observed independent /tmp demo rejected a normal small /goal because no
named allocation or default existed. The user requires this path to work without
per-session provisioning. A private host-wide `self_enrollment` envelope therefore
delegates a first allocation to a verified native caller within fixed token/time
ceilings. Its identity is deterministic for the conversation and survives goal
replacement; enrollment cannot mint a second allowance for that conversation.
Explicit host renewal remains separate. Existing caller grants and named
allocations keep their precedence and ledgers. Successors carry their existing
allocation ID; attributable child sessions cannot omit it to mint a fresh budget.
Unknown accounting or caller evidence holds before allocation creation.
This is a local host delegation contract, not authentication of arbitrary model
requests or hostile same-UID clients. Model tools never rewrite host policy.
