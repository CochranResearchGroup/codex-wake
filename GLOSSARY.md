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

**Resource allocation**:
The resources a user authorizes for a named objective and its continuations.
Conversation identity does not determine or replenish that authority.

**Allocation renewal**:
An explicit user change to a named objective's resource allocation. It does not
change unrelated allocations or erase their usage history.

**Allocation continuity**:
The verified relationship that charges a successor's work to the same objective's
existing allocation, preserving cumulative usage and its original deadline.

**Caller provisioning**:
Binding a verified conversation to the resource authority it may exercise.
Provisioning alone is not proof of accounting or running enforcement.

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

**Recipient binding**:
The verified relationship between one conversation and the live client that
currently owns its input. A tab label or working directory alone is not a binding.

**Observed delivery**:
Inspection evidence that a wake prompt was accepted in the bound recipient's
interface. It does not establish a receiver acknowledgment or a work claim.

**Receiver acknowledgment**:
An attributable receipt from the exact recipient confirming a specified delivery
outcome. Its meaning is limited to that outcome; it does not imply completed work.

**Busy delivery policy**:
The selected behavior when an exact recipient is already working: wait, verified
queueing or explicitly authorized interruption, within the original deadline.


**Host-bound runtime actor context**:
An operator-issued mailbox actor capability paired with a private frozen runtime
binding. Grok invocation checks the managed process generation, inherited session
claim, caller ancestry and enrolled root. This is host delegation, not native Grok
caller attestation; terminal text and claimed IDs alone grant no work authority.

**Definitive pre-I/O non-submission**:
Positive adapter evidence that a selected method was unavailable before any
submission bytes. An absent response, missing marker or timeout is insufficient.
Only a host-approved fallback profile may switch methods on this evidence.


**Terminal attachment**:
A particular terminal view associated with a conversation. Its label and position
are separate from the conversation's identity.

**Managed agent**:
An agent whose one exact conversation, execution context and permitted operations
are explicitly tracked by a controller. Its identity survives verified process
and terminal changes; a successor conversation is a separate managed agent.

**Agent instruction**:
One bounded agent turn admitted as a declared instruction in a workflow.

**Step attempt**:
One attempt to execute a declared workflow operation. Its reported completion
and acceptance are separate outcomes.

**Work acceptance**:
An evidence-backed decision that a result meets its declared acceptance
conditions. A worker's completion report alone is not that decision.

**Scheduled occurrence**:
One planned execution arising from a recurring schedule, distinct from attempts
to deliver or execute that occurrence.

**Wake durability**:
The interruptions or owner lifecycles a retained wake is required to survive.
Durability is separate from its deadline and delivery outcome.

**Parking a tab**:
Moving a live terminal attachment into a holding workspace while preserving its
agent. Parking alone does not pause work or renew resource allowance.

**Agent succession**:
The relationship between a predecessor and successor managed agent continuing
the same task, with outstanding obligations and resource continuity preserved.

**Task brief**:
The approved objective, phase, boundaries, acceptance conditions and context for
an assignment. An admitted instruction refers to a particular revision.

**Recipient-startup policy**:
The selected conditions under which a wake may use an existing recipient, load
a saved conversation or start its declared task. It is separate from wake lifetime.

**Semantic agent state**:
A fresh evidence-backed account of what an exact managed conversation is doing.
It is distinct from binding readiness, work acceptance and permission to act.

**Mutation resource claim**:
Exclusive cooperative custody of a declared resource while work may mutate it.
Losing contact with its owner does not release custody or authorize a new writer.
