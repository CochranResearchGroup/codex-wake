# Codex Wake

Codex Wake records wake requests and agent messages whose deadlines must remain meaningful across outages and restarts.

## Language

**Wake deadline**:
The point in time when a registered wake becomes due, including time spent asleep.

**Message expiration**:
The deadline after which a message is no longer eligible for delivery, including time spent asleep.

**Trusted time**:
A bounded estimate of current time accepted under the configured source-selection rules.

**Time uncertainty**:
The condition in which available evidence cannot establish whether a deadline has passed.

**Scheduling intent**:
The durable original request to schedule one follow-up, retained even when a
clock cannot yet qualify its deadline. Reusing its key returns that request;
it does not authorize another submission.

**Relative clock continuity**:
Evidence that elapsed observations belong to the same qualified host-counter
epoch and rate policy. Losing continuity holds the original anchor rather than
starting the delay again. Elapsed evidence does not establish absolute UTC.

**Message receipt**:
An attributable record of retrieval, acceptance or another message outcome.
Reading records retrieval; it does not accept the work.

**Work claim**:
The exact recipient's explicit acceptance of processing a message. Only a newly
accepted claim permits that worker to begin; it grants no additional task rights.
Successful or failed processing requires this claim before terminal acknowledgment.

**Receipt publication**:
Making an existing receipt available to observers. Publication is durable journal
work and does not itself require the recipient's tab to remain open.

**Recovery disposition**:
The operator's attributable decision to retain snapshot-era work as unknown and
prohibit its processing or replay. It does not infer missing outcomes.

**Recovery hold release**:
A separate operator action after committed disposition. It leaves the bus paused
and requires fresh grants before new work; original history stays fenced.

**Agent spawn**:
Starting a separate agent conversation with an explicit assignment and scope.

**Agent refresh**:
Reloading selected runtime resources while preserving the conversation identity
and unfinished work. Legacy profiles reopen its client; approved shared MCP
refresh keeps clients and reconnects the shared server's MCP connections after
idle observations. Neither path renews counters or resource allocation.

**Agent handoff**:
Passing an unfinished objective and its checkpoint to a different conversation,
without implicitly transferring identity, permissions or resource allowance.

**Handoff checkpoint**:
The outgoing agent's durable account of completed work, remaining work, evidence,
authority, pending obligations and resource allowance for its successor to verify.

**Lifecycle controller**:
The external owner that observes and coordinates an agent's lifecycle transition.

**Continuation allowance**:
The explicitly authorized resources remaining for work on the same objective.
Fresh context does not replenish that allowance.

**Session budget**:
The user-authorized token and elapsed-time limits for one agent goal session.

**Objective budget**:
The user-authorized cumulative token and elapsed-time limits for an objective,
including successors, reviewers, delegated work, retries and failed attempts.
Changing conversation does not replenish this budget.

**Goal supervision**:
Observing an existing goal's authorized resource usage, requesting a checkpoint
before its limits, and pausing continuation when its stopping condition is reached.

**Handoff preflight**:
The successor's verification of runtime readiness and assessment of whether the
outgoing work advanced the approved objective with adequate evidence and scope
discipline. Runtime readiness alone does not establish work acceptance.


**Emergency pause**:
An operator-controlled hold preventing new wake deliveries in its selected scope
until explicitly resumed. It preserves scheduled work and original deadlines.

**Wake cancellation**:
Retiring an eligible wake so it no longer delivers, while preserving its history.
It cannot retract work already submitted to a recipient.

**Owned-turn interruption**:
Stopping a running turn only when durable assignment evidence identifies it as
Wake-owned. It is separate from pausing future deliveries and cancelling wakes.
