# First frontier interview: operator decisions and remaining wake policy

Date: 2026-10-24
State: HF-02/HF-07 product decisions resolved; HF-13 follow-up pending
Authority: questionnaire 1edde8f79e72, response e7d360f4df91425fb8a251ac51bdec42,
revision 15e287fb35e466ab49aafdae39c0567b3b36b34951741190bfdb04f981de09b5,
submitted 2026-10-24T17:08:11.568103+00:00.

## HF-02 inventory and enrollment

Enrollment supports configurable policies, including operator-selected enrollment,
operator-only enrollment and self-enrollment. The operator's selected default is
self-enrollment with explicit operator unenrollment. Do not turn this into a
per-session manual approval requirement. An explicit operator unenrollment must
be effective rather than immediately undone by the same automatic policy; the
concrete suppression/re-enrollment mechanism belongs in the HF-02 design.
Discovery is distinct from enrollment and from mutation authority. Verify native
conversation and current process binding; self-enrollment is not self-asserted
identity. Preserve unavailable records and rebind automatically only with exact
conversation and authorized-context evidence. A successor conversation gets a new
managed-agent identity and retains linked task/allocation history.

First implementation handoff: introduce the smallest persistent inventory and
policy projection that adopts one existing qualified conversation, preserves
identity across controller restart and exposes stale/ambiguous bindings. Include
configurable admission and durable explicit unenrollment in caller-level proof.
Do not change the independently owned self-refresh host-policy repair.

## Session-control permission profiles: HF-06 overlap

The operator requires selectable permission profiles and prefers permissive:
every session may refresh, hand off, resume itself and opt into external resource
enforcement. An operator request for self-refresh is explicit permission; do not
invent an additional per-session approval gate for that request. Preserve exact
self identity and declared resource allowance. This does not claim unsupported
runtime controls exist or grant control of unrelated conversations.

The operator reports another agent is repairing the existing host enrollment
restriction for auto-handoff/refresh. This lane records the requirement and
consumes that repair's eventual published contract. It neither duplicates the
repair nor changes global host policy. Its branch/issue/receipt must be identified
before future overlapping implementation; do not guess that #282 is its sole scope.

## HF-07 task brief

An operator or controller explicitly delegated the relevant scope approves brief
revisions affecting objective or acceptance; workers may propose them. Routine
implementation choices within the approved brief need no separate approval.
The running instruction retains its admitted brief revision. New revisions apply
at the next boundary unless an explicit stop/steer handles an urgent change.
A revision cannot retroactively authorize an earlier effect.

First implementation handoff: pin a bounded brief revision to one assignment,
link objective/phase/non-goals/acceptance and source evidence, and distinguish
worker proposals from approved revisions. Verify admission revision survives
restart and an in-flight instruction cannot silently adopt changed scope. Reuse
existing checkpoint and authority references; no new corpus ingestion system.

## HF-13 lifetime and recipient startup are independent

The operator accepted conversation-owned, task-owned and persistent lifetimes,
with existing wakes retaining their behavior when no lifetime is specified.
Original intent, due time, expiry and uncertain-attempt state remain authoritative.

The operator separately requested selectable recipient-startup modes:

- Require an existing active session/tab.
- Permit background app-server delivery to a verified saved conversation with no visible tab.
- Permit creating a tab/loading a session as needed and running the task.

These are requested capabilities, not proof every adapter supports them. Background
submission, same-conversation resume and fresh task launch have different evidence
and authorization boundaries. HF-13 owns the policy declaration and conservative
unsupported result; HF-18 owns binding/resume execution, HF-19 workspace/tab
reconstruction, and HF-20 daily-task launch/occurrence admission. Do not silently
expand HF-13 into an entire lifecycle or recurrence engine. Existing delivery
behavior remains unchanged unless a new explicit policy is selected.

The owner-end question was not answered by the recipient-startup response.
Two follow-ups are pending: retirement/hold/expiry behavior after verified owner
completion, and the preferred default startup mode for newly registered wakes.
Do not infer owner cancellation from tab disappearance, or infer permission to
start a fresh conversation from permission to resume an exact saved one.

## Acceptance status and next steps

HF-02 and HF-07 have resolved product inputs; their concrete bounded technical
design and caller-level validation plans must be reconciled before coding.
HF-13 remains in interview for the two stated decisions. No implementation,
live wakes, provider input, installed-policy repair, tab creation or deployment
was performed. Shared contracts and final integration remain with the primary.


## Common session permissions clarification, 2026-10-24

The operator now explicitly requires a common globally configurable model with
action-specific tailoring, including auto-refresh, auto-handoff, external resource
enforcement, A2A send/receive, and separate background/existing-tab/new-tab wake
delivery. [HF-06's contract proposal](session-permissions-contract.md) owns this
requirement across execution consumers. It preserves the recorded permissive
self-control preference and the two pending HF-13 decisions. Issue310 / PR311 is
the independently owned refresh repair; it must converge with this model rather
than become the final cross-feature policy schema.
