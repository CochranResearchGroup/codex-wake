# Build usable live agent-to-agent messaging

State: OPEN
Lane: P63
Owner: primary integration lane
Branch: docs/p63-soak-closeout
Target: origin/main
Integration: squash_pr
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/181
Supersedes: Plan0101 execution sequencing; not its original acceptance obligations
Depends-On: existing P63 mailbox, identity, scheduler, receipt and discovery implementation

## Objective

An agent in Byobu `wakeA` sends a request to `wakeB`. B is notified in its exact
existing thread, reads the request, acknowledges it and replies. A can suspend
its turn and is notified when the reply arrives. Both agents can inspect what
happened using the normal installed CLI. After one-time enrollment and workflow
setup, the controller does not paste prompts, poll inboxes or relay message bodies.

Build and demonstrate this feature before expanding supporting infrastructure.
A passing live behavior gate is progress; another green fixture suite is supporting
evidence. A message admitted to SQLite is not a delivered notification.

## Current State

Reconciled planning snapshot:2026-10-10. Execution sequencing is now
[Plan0141](0141-2026-10-10-a2a-completion-stream.md), with eight bounded
repo-native tickets through final campaign acceptance. This plan remains OPEN
as the usable-feature requirement record; Plan0101 retains original obligations.

Verification0122 accepts the prior live cancellation, reconnect, owned-worker
restart, released0.7.1 multiroot/rollback and thirty-minute soak on its exact
recorded source/workload. Plan0138 ships explicit saved-recipient reopening;
Plan0139 ships claim instructions and ordinary close fixes, active0.11.1.
Plan0140 diagnosis is complete: actual notification consumption coexists with
uncertain pane visibility. Original uncertainty is preserved; native live queue
submission is the next implementation ticket0142, not yet implemented.

Remaining campaign gates are owned explicitly: current-transport qualification
and release, genuinely server-unloaded recipient evidence, held-recovery gap
and legacy-notification disposition, cross-generation claims, remaining ancestry/
fault cuts, and final requirement-to-proof audit. No old completed goal or token
allowance is resumed by this planning reconciliation. No production recovery,
shared service restart or uncertain effect replay is newly authorized.

## Approved closed-conversation follow-up | 2026-10-10

Operator approved reopening the exact saved conversation only when the sender
explicitly requests it. Default hold remains. Plan0138 is the bounded successor
for that behavior and its installed qualification; the older unconditional
no-resume passages below are historical for the opt-in case. Native scheduled
wake --resume-missing already exists, but agent-message integration and actual
closed-recipient completion must be proved separately. No stale mailbox authority
or uncertain effect may be replayed under this decision.

## Historical baseline at plan creation

Baseline at plan creation: f104c2f86b37ac548ba1f798aa0d65abd8d37322. Discovery, explicit
membership/capabilities, durable mailboxes, replies, acknowledgements, foreground
waits, scheduler/outbox foundations, receipt projection, retention and bounded
backup/recovery implementation already exist. Reuse them.

On 2026-10-04 the operator designated two real sessions in the root repository:

| Session | Actual thread | Demo result |
| --- | --- | --- |
| wakeA | 01a10876-c7cf-7ae1-ad99-e9d829994e45 | Sent request; waited for and read B's reply |
| wakeB | 01a10876-e53a-7322-bf68-ff43e9b2f2dc | Read request; acknowledged accepted; composed and sent reply |

One request `msg_02071e4c53c34984bd7561774edea49e` and one correlated reply
`msg_84da70ea168047249bb155004aa4c786` passed in 55.509 seconds from admission
to sender readback. Both identities were validated against the running shared
daemon; commands ran in the actual agents' tool contexts. Controller prompts
started their inbox work. Delivery was `inbox`, with notifications suppressed.
This is live manual-pull acceptance, not automatic delivery or durable suspension.

Evidence: [live demo receipt](../verification/0111-2026-10-04-wakeA-wakeB-live-round-trip.md).
The global installed 0.6.0 command still lacks A2A verbs. The demo used an isolated
wheel built from current main. Automatic A2A transport and generic receipt dispatch
remain unqualified. The demo bus is paused; the two user-owned sessions are idle.

## Historical execution decision | 2026-10-04

The operator rejected the custom Codex runtime dependency as unnecessary. Do not
activate the staged patch, replace the shared runtime, disable Codex updates or
restart the shared daemon for this plan. Note0007 is superseded. Its earlier
approval is not authority to continue the rejected activation path. The installed
official Codex0.160.0 package and updater settings remain unchanged.

Use the existing codex-wake Byobu/tmux wake mechanism for the next bounded probe.
It already supports waking idle sessions. The outstanding feature is connecting
message notifications and durable reply arms to that mechanism so that the
request/reply exchange requires no controller intervention after send. MCP reload
is not evidence of this behavior. Preserve exact identity/process binding, busy
and composer checks, cancellation, expiry, uncertainty and the M1-M4 acceptance
criteria. Do not bypass the existing A2A receipt dispatch fence merely to produce
a demo. Qualify the existing path and change only the Wake integration seam
required by an observed failure. A future runtime patch requires a separately
explained need and explicit operator direction.

Integrated source at that checkpoint:eb79e927fb227af3657d5b121aa17026294976d7 via PR211.
The retained patch and compiled package are inactive historical artifacts, not
a product prerequisite. Existing owning-client commands depend on that inactive
patch and do not constitute the selected stock-runtime transport. M1 now passes
on attempt2/3. M2 has live busy/draft/rename/move and expiry evidence but remains
PARTIAL. After the original three-attempt loop exposed offline admission failure,
PR211 repaired exact-thread resolution. Installed live admission and delivery to
the original recipient after explicit reconnect now pass. Cancellation was refused
by clock continuity; return delivery hit retained unread FIFO backlog. M3-M4
remain UNPROVEN. Verification0115 preserves original failures; verification0116
records repair and changed-source qualification. Both repair qualification slots
are consumed. Next packet must establish clock stability and reconcile the demo
mailbox before further acceptance. No unchanged extra trial, custom runtime
activation, automatic resume or shared-daemon restart.

## Scope and architecture

Deliver the existing product through four consecutive user-visible milestones:
automatic round trip, ordinary session safety, restart/suspension, and installation.
Use the existing mailbox as message authority and Wake as notification authority.
Do not create another broker, message database or receipt store. Notifications
carry an exact inbox retrieval pointer; peer bodies remain untrusted.

The next implementation seam is a qualified delivery adapter plus scheduler and
receipt-wake wiring. Resolve the installed runtime's actual capabilities first.
Use a supported exact-thread shared-daemon operation where its semantics protect
ordinary client work. Current idle/status metadata alone does not establish
composer ownership. If the existing runtime lacks the required binding, implement
an explicitly opted-in client/hook binding at the narrowest owning seam; do not
spend a succession of packets merely documenting its absence. Existing tmux
transport is eligible only after exact thread/client/process-generation binding
and composer safety are demonstrated. A queue operation that might run later is
not a substitute for these guarantees.

Keep notification delivery, recipient read, acknowledgement and reply as separate
states. Preserve current `held`/`uncertain` semantics across transport failures;
unknown effects are reconciled, never blindly replayed. A reply receipt is the
trigger for A's exact-thread resumption, not an instruction to start another agent.

## Milestones and acceptance

| Milestone | Feature work | Required live result |
| --- | --- | --- |
| M1: Unassisted exchange | Qualified adapter; dispatch existing notification jobs; recipient inbox workflow; reply receipt wake for sender | After setup, A sends one request and ends its turn. Idle B wakes, reads/acks and replies; idle A wakes and reads it. No controller prompt, body relay or foreground inbox-poll helper after send. |
| M2: Work safely in normal sessions | Gate delivery on exact identity and current client ownership; expose deferred/held reasons; honor cancel and expiry | Busy B is not interrupted; a human draft is unchanged; unloaded B stays pending without automatic resume. When B becomes eligible, the original exact recipient gets the message once. Rename/move cannot retarget it. Cancellation/expiry before dispatch prevents notification. |
| M3: Survive normal lifecycle | Persist sender receipt arm and recipient notification; reload authority on reconnect; recover leases and classify uncertain transport | Restart only the demo-owned worker, reconnect the same threads, and deliver a pending request/reply without new IDs, duplicate effects or lost arms. A stays suspended through the worker restart and resumes on B's actual reply. |
| M4: Usable installation | Ship CLI/workflow and service wiring through normal release path; expose setup/doctor/status; document the actual commands | Exact released installation performs M1 without temporary scripts or PYTHONPATH. A second explicitly enrolled root works; unenrolled root is denied. Installed rollback preserves readable messages/receipts and refuses unsupported state. |

M1 is the immediate critical path. Its first live probe must be able to fail on
missing delivery or wake-up, and its receipt must identify the actual sender,
recipient, request, acknowledgement, reply and both resumed turns. A handcrafted
firing record or a controller-generated reply cannot satisfy it.

For M2, repeat the smallest live scenario for each distinct guard rather than
building a broad synthetic matrix first. For M3, do not restart the shared daemon
or interrupt unrelated agent sessions. For M4, perform a bounded 30-minute owned
workload after the feature works: at most ten request/reply pairs, process/FD and
memory census before/after, no residual demo workers. Preserve the existing
verification0104 resource limits; freeze the installed baseline and thresholds
before running. This bounded soak does not imply production-scale qualification.

## First implementation packet

Owner: primary. Outcome: M1 passes on the operator-designated wakeA/wakeB threads.
Expected write surface: existing shared-runtime/transport adapter, injector,
scheduler/receipt dispatcher integration, agent workflow skill, and affected tests.
No mailbox schema or recovery change is planned unless a reproduced live failure
requires one. Inspect these seams with CodeGraph before choosing exact files.

1. Re-resolve wakeA/wakeB, installed identity, bus state and client bindings.
   Freeze one owned notification bus and exact opt-in permissions; resume only
   that healthy demo bus. Reuse the current identities if they still match.
2. Record a failing end-to-end notification/wake probe against the actual entrypoint.
   Identify the one blocking seam from observed behavior. Qualify or implement
   the transport's ownership contract before allowing its effect.
3. Connect existing outbox jobs to the qualified adapter. Install the bounded
   inbox/ack/reply workflow in B; arm A's durable exact-message reply wake before
   A suspends. Keep normal timers and other wake sources compatible.
4. Run one actual request/reply, observe both thread resumptions, and preserve
   runtime and mailbox receipts. Fix only demonstrated failures, then rerun that
   same behavioral probe within the bounds below.

Entry criteria: actual identity/binding, independent issued capabilities, owned
healthy bus, explicit notification opt-in, finite attempt bounds. Exit: M1 live
receipt passes, or a precise observed blocker and its smallest implementable
remedy are recorded. Controller prompting after send means M1 failed.

## Execution controls and authority

This request authorizes writing the successor plan, not starting a new autonomous
goal. The existing goal is paused at 867,188 tokens with its one-million ceiling.
This plan does not reset usage, review/rework counters, uncertain-effect history
or accepted findings. Carry them forward on an explicit goal continuation.

The operator explicitly authorized the preceding demo in wakeA/wakeB. These are
user-owned sessions in `/home/ecochran76/workspace.local/codex-wake`; do not delete,
archive or replace them. A subsequent implementation/live packet must name its
exact commands, notification permissions and effects. Routine in-scope source
work needs no extra ceremony; shared-daemon restart, global install/release and
additional roots have their own concrete execution boundaries. No business-system
operations or private real-world message bodies belong in demos.

One primary owner serializes M1-M4. No parallel lane is needed for M1's coupled
adapter and dispatch changes; later independent verification may be split with
explicit ownership. The same shared files have one writer.

Use at most three live attempts per milestone, one request and one reply per
attempt, with a 120-second delivery/reply deadline. No retry after uncertain I/O
until exact reconciliation establishes what happened. Stop an attempt at timeout
and preserve the first failure. At a local bound, reframe the verified blocker;
do not start an unrelated maintenance packet or reset the campaign's allowances.
Checkpoint after each live attempt and at least every 30 minutes of implementation.

At every checkpoint report: which live behavior passed, which failed, the current
installed/source identity, and the single next blocker. If two consecutive
implementation checkpoints produce no advance in the next behavior gate, stop
expanding code and revise the approach around that failing probe. Focused checks
cover changed seams; required hosted checks govern integration, not live claims.

## Deferred work and retained obligations

The earlier sequence put recovery-gap disposition and hold release ahead of
basic delivery. This successor reverses that priority. Existing damaged-source
recovery remains held; no production recovery or automatic replay is enabled.
Hold release, cross-generation processing-claim recovery, broader ancestry/fault
matrices and longer operational qualification remain explicit Plan0101/P63
obligations in verification0106. They do not block M1 on a new healthy bus.

No optional MCP facade, remote federation, broadcast, autonomous spawning,
new retention framework or additional backup design in this plan. Add hardening
only for a reproduced failure or a concrete acceptance requirement, with its
milestone effect stated. Preserve all previous failed receipts and accepted work.

## Definition of done

Close Plan0119 only when M1-M4 have attributable live/installed receipts, relevant
source changes are integrated, the normal agent workflow needs no controller
relay, and the documented install/rollback commands have been exercised. Demo
workers and temporary grants are cleaned up or explicitly retained; user sessions
and unresolved history are preserved.

Plan0101 remains the original campaign requirement record; issue181/P63 remain
OPEN until its outstanding obligations are separately reconciled and satisfied.
Do not close the full-system issue from this narrower feature delivery. This
successor owns execution sequencing, with no reduction of the original goal.

Memory discovery: skip; current canonical files and this turn's fresh live receipt
supply the decisions needed for this plan. Closeout disposition is recorded
separately; the plan is the restart-safe execution source.

## Execution checkpoint | 2026-10-04

User explicitly continued Plan0119 with working-product acceptance and a stop
before one million tokens. Execution worktree is
`/home/ecochran76/workspace.local/codex-wake-p63-feature-successor`, branch
`feat/p63-live-delivery`, based on34f6671. Origin/main remainsf104c2f.
Issue181 isOPEN; no open PR exists. Root checkout unrelated untracked note0003
is preserved. No delegated agents, live attempts, messages or notifications.

Read current policies and Plan0119. Re-resolved both exact demo threads through
the existing shared daemon: bothloaded,idle,expectedroot,canAcceptDirectInput=true.
Installed CLI/daemon remain0.160.0. Generated experimental protocol at
`/tmp/codex-wake-plan119-schema`: queue/add accepts threadId,input and
clientUserMessageId; queue/start accepts threadId and optional queuedSubmissionId.
Neither parameter schema supplies a composer/client ownership guard. Schema
absence alone does not qualify or disqualify every possible runtime seam.

Retrieved official release-mapped source revision
a956835d020762cb2b570053af06f643a11c0ecc beneath
`/tmp/codex-wake-plan119-runtime/codex-a956835d020762cb2b570053af06f643a11c0ecc`.
CodeGraph indexed the Wake worktree (188files,5851nodes,21907edges; fresh);
runtime source indexing/exploration surfaced the owning TUI event loop,
App::handle_event,submit_thread_op and composer_draft_snapshot.
Local rustc/cargo1.94.1 are present; compilation was not attempted.
File-searcher lookup waspartial/backend-degraded and did not locate a checkout;
this is not an exhaustive absence claim. Downloaded source is temporary.

M1-M4 remainUNPROVEN. No failing live notification probe or product code change
has yet been produced. Progress classification:blocker_reduction for current
identity and owning-seam discovery only; no live behavior advancement.
Next: implement the opted-in binding at the actual owning TUI seam and connect
existing MailScheduler dispatch/receipt path, then run the actual M1 probe.
Do not substitute bare queue/add,terminal screenshots or fixtures for binding.
No shared daemon restart,global install,client replacement or provider mutation
was performed. Source patches must be retained in Wake before using temp source
as a build input; qualify exact ownership,busy,draft,offline and uncertainty.

Budget: inherited867188 plus observed continuation121672 =988860 before
checkpoint writing. This is a conservative carried total,not an exact final
meter. Stop now with reserve under1000000; do not treat a fresh meter as zero.
User must explicitly resume or raise the ceiling before further execution.
Memory discovery:skip,current canonical evidence sufficient.
Memory disposition:not_durable;this startup investigation is transient and
adds no accepted product behavior or durable design decision.

## Implementation authority update | 2026-10-04

User resumed with ceiling1800000; inherited carried total996214 remains part
of the accounting. Previous checkpoint changed source authority and located
current runtime seams; no live acceptance passed. M1 remains the critical path.

Current release-mapped source demonstrates turn/start calls start_or_steer_turn;
therefore a read-only idle preflight cannot prevent steering when another turn
starts. Candidate patch adds a narrow turn/startIfIdle operation with existing
parameters/response and Core's atomic start_turn_if_idle, plus an opt-in TUI
Unix socket whose owning event loop checks draft/modal/pending-input/current
thread/root and offline state. Existing turn/start semantics remain unchanged.
Wake connects the existing MailScheduler to this binding with native bind-client,
dispatch and bounded worker commands. No mailbox schema change or new broker.
The patch is retained under runtime/codex with pinned upstream provenance and
a reproducible build helper; compilation and acceptance are still pending.

Only the owned candidate source/build and Wake worktree are mutated. No shared
daemon/client restart or global installation is authorized by this artifact.
Once the candidate is built and its concrete rollout is reviewable, resolve
any exact shared-runtime activation gate. No unqualified transport fallback.
Live attempts remain0/3; no notification or message was sent this continuation.

### Candidate receipt wiring and runtime boundary | 2026-10-04

The exact-message operator receipt allowlist cannot preauthorize an unknown
future message ID. Candidate `a2a delegate-receipts` instead independently grants
bounded observation for explicitly listed, notification-enabled sender actors.
Candidate `messages arm-reply` authenticates the current actor and registers its
own exact outgoing request in the existing Wake signal journal. No operator step
is required after send. This does not grant messaging or actor impersonation.
New configuration holds at most100 senders, pins wake root, bus and actor
generation, and is re-read on observation and dispatch. Generic receipt/tmux
delivery remains fenced. No mailbox schema or message store change.

The bounded native worker publishes its actual reader health, reconstructs reply
arms through the existing receipt source family, and releases the existing reply
notification only for a current exact firing arm. Cancellation, expiry and removed
delegations hold delivery. Actual submission evidence is recorded in the existing
mailbox attempt journal; interrupted arm bookkeeping is reconciled without resend.
Source fixtures prove these boundaries; they do not prove M1 or M3 live behavior.

Client binding also checks the actual server's home/provider namespace before
submission. Expired client event responders are dropped before any later effect.
The retained runtime patch and build hashes were updated and reproduced.

Plan0119 runtime activation gate is prepared in note0007 and explicit approval is
pending. Current policy0021 also requires deployment from an exact integrated
origin/main commit; source integration and hosted checks must precede activation.
No authority is inferred from compilation, local fixture results or a PR. M1-M4
remain UNPROVEN, live round-trip attempts0/3, actual runtime unchanged.

### Integrated source checkpoint | 2026-10-04

PR206 integrated candidate source08e82c3 as
origin/main835990a4ba31a1a774b5fa72332fe05db17b7b28. Hosted run37235883303 passed
both Python3.11 and3.12 release gates,895 tests each, including installed wheel
and existing compatibility/resource/recovery checks. Runtime source compilation
and fixture guards remain supporting evidence; M1-M4 are stillUNPROVEN.
Execution worktree remainscodex-wake-p63-feature-successor, now on
feat/p63-activation-gate from that exact integrated main. Source branch and refs
are retained. Verification0114 is the restart-safe activation checkpoint.

Fresh readback confirms wakeA andwakeB idle, correctIDs/root,directinputallowed;
installed shared daemon remains0.160.0 on its original standalone package.
Explicit activation approval is pending; no shared restart, client reconnect or
global install has occurred. Next action requires that approval, then the exact
bounded activation and one actual M1 request/reply attempt. Do not build more
supporting matrices while this concrete runtime gate remains unresolved.

### Activation approved; shared idle gate pending | 2026-10-04

The user's `approved` authorizes note0007's prepared shared activation and exact
client reconnect. Candidate package staged with verified SHA256 and rollback
snapshot; shared selection, settings and daemon remain unchanged. Fresh complete
shared inventory and repeated checks show unrelated active turns. WakeA/B remain
idle with original identities and empty composers. Do not restart across those
active turns or request this approval again. Execute the approved gate after
fresh complete all-idle readback, then perform the bounded M1 attempt. No live
round-trip was attempted; M1-M4 remain UNPROVEN.

### Operator correction: use existing wake transport | 2026-10-04

The custom-runtime activation path is superseded by the execution decision above.
The distinction is existing idle-session wake capability versus still-unproven
automatic mailbox/receipt integration. Source trace confirms existing tmux wake
prompt submission and process-bound routing; it also confirms an explicit A2A
receipt dispatch fence. No message, notification, restart or reconnect occurred
in this correction turn. Next packet targets the existing Wake integration and
one bounded automatic round-trip probe, retaining all acceptance obligations.

### Stock-runtime transport implementation | 2026-10-04

Native `a2a bind-tmux` captures the existing client PID/start ticks/boot ID and
exact home/provider namespace/thread/root. The existing notification dispatcher
uses that explicit binding without an automatic transport fallback. It checks
shared metadata for idle/direct-input eligibility and recognizes only the observed
empty Codex composer. Draft, modal, unknown UI, unloaded and changed-generation
clients are held. Paste uses the existing transport and records visible canonical
message-pointer evidence, not a fabricated server turn receipt. The same existing
reply-arm gate releases the correlated reply notification and reconciles completed
transport bookkeeping without resend. Generic A2A receipt injection stays fenced.

These are observed pre-paste checks, not an atomic server/composer transaction.
M2 requires live safety tests; source checks alone do not prove a human cannot
change input between the final check and paste. No stock runtime was modified.
Next gate: integrate this source after required checks, then one actual automatic
request/reply on the designated same threads.

### Live setup transport failure and correction | 2026-10-04

Before the first mailbox send, the existing paste runner left B's long setup
prompt folded in its composer; metadata remained idle and adapter deferred it as
composer_protected. A later setup-only Enter submitted that retained prompt. No
mailbox attempt occurred and no controller input followed a request send. This
is preserved as a setup transport failure. The product runner now uses tmux's
bracketed paste mode, a settle delay and one explicit Enter so burst detection
does not absorb submit keys. Source and hosted checks must pass before using
this correction for the actual automatic exchange.

### Observed host-clock hold | 2026-10-04

The old demo bus refused its stale clock checkpoint. A fresh demo-only bus for
the same threads/root also stopped after three empty worker ticks. Sampling
observed a backward wall-clock step of about2.7 seconds with monotonic time
advancing normally. Both buses and raw receipts are preserved; there were zero
messages and zero transport attempts. The old bus is paused. No host settings
or mailbox clock checkpoint were changed.

Keep the mailbox clock guard intact. The bounded worker may wait through a clock
hold only after an independently authorized journal read proves it owns no
dispatching or uncertain attempt. A pending effect instead stops for exact
reconciliation. Count committed submissions from the same journal so an error
after submission cannot expand the worker effect budget. This is a direct remedy
for the observed zero-effect worker exit, not relaxed expiry or replay policy.

### M1 attempt1: TTL rejected before admission | 2026-10-04

The actual wakeA native send returned operation_unavailable and stopped without
arming or retry. Read-only reproduction identifies operator-supplied `--ttl120`
as invalid; this CLI requires a duration unit such as120s. Authorized exact
journal reconciliation proves zero envelopes and zero transport attempts for the
original intent. This is M1 failure1/3, not a passed exchange. Preserve the agent
turn, native output and reconciliation. The zero-effect owned worker was stopped;
attempt2 retries the same intent key with120s and a fresh bounded worker. No
controller prompt followed an admitted request.

### M1 stock-runtime behavioral acceptance | 2026-10-04

M1 PASS on attempt2/3: actual requestmsg_c33d4cdf87544e138fedb286896fb9bb,
B read/accepted/replymsg_fe28d90d70c144ae8cec2a07f6c6ba77, automatic A read
receipt_c0308cf295f14ff089e7dade82c44488. Durable reply arm submitted; exactly
two transport submissions, same original threads/PIDs; worker exited normally.
No controller prompt/body relay/inbox polling after admission. Deadline proven
by90.576-second monotonic upper bound from BEFORE admission to actual A read;
wall receipt delta56.006 seconds is labeled separately. Verification0115 retains
exact receipts/turns, first failure and all setup/clock observations. Extra A
terminal ack failed claim_required; read criterion passed, terminal ack not claimed.
M2-M4 and wider campaign remain OPEN. Next packet is live session safety.

### Offline-admission repair packet

Owner primary, human accountability ecochran76, issue181. Branch
`fix/p63-offline-admission`, based on merged checkpoint PR210/main3bd0078.
No delegation: the CLI authorization and live qualification are sequential.
Public test seam: native `messages send`, real temporary mailbox, read-only
runtime boundary supplying an unloaded exact recipient. Red command:
`PYTHONPATH=src python3 -m unittest discover -s tests -p test_offline_message_admission.py -v`.
Before repair it returns the live `selection_error: session not found` symptom.
The selected repair allows only send's exact `thread:` selector to read stored
runtime metadata directly. Returned ID must match; namespace/root/enrollment and
cross-root policy remain enforced by existing mailbox admission. Enrollment,
tabs and other fuzzy selectors retain loaded discovery. No lifecycle request,
transport change, schema change or notification eligibility relaxation.

The old three-attempt M2 loop is closed, failures preserved. After exact merged
source installation, this changed-source packet permits at most two distinct
live qualifications: one offline cancellation and one pending exact-recipient
reconnect/delivery, each one request/at most one reply and120-second deadline.
No retry of uncertain effects without exact reconciliation. Owned worker custody
must survive observer failures, and only designated clients may reconnect.
M2 remains partial until these live results exist; M3/M4 remain separate gates.

### New goal continuation: remaining real acceptance

The user renewed execution of the four remaining gates with a fresh1100000-token
checkpoint ceiling; their Plan191 reference matches this Plan119's named gaps
and no Plan191 exists. Prior goal's counts and bounds remain historical, not reset
claims about failed tests. Current goal is active; track its own current meter.
Clock probe captured a2.29-second wall step; old store checkpoint drift is near
300 seconds. Preserve old journals and failed qualification. A fresh native,
explicitly enrolled store continuation-v2 separates this run from retained FIFO
history without resetting an existing clock checkpoint or weakening guards.

Primary executes serially. New bounded cases: live cancellation before dispatch,
clean reconnect automatic return, and full owned-worker restart/reconnect recovery;
at most two attempts per distinct case, one request/at most one reply per attempt,
120-second outcome deadline. A cancellation clock_anomaly may be retried once
only after native rejection and read-only exact-state proof establish zero effect;
no other error/effect retry. Stop or reframe failed bounded cases. Then complete
normal released installation, explicitly enrolled second root/unenrolled denial,
installed rollback, and30-minute owned soak with frozen existing resource limits.
The full objective remains open until every live/installed gate is proved.

### Current live checkpoint | 2026-10-05

Verification0117 records actual cancellation with zero transport attempts and a
clean reconnect automatic request/reply/read PASS. Verification0118 records a
failed restart setup with no managed reader, then a fresh corrected case: same
pending request/arm across native worker exit/new process, same original A/B
thread reconnects, one submitted request and reply, actual A automatic read in
109.313seconds. No further attempts in the bounded restart packet. Preserve the
first failure; second case corrected setup rather than replaying its keys.
M1 and these live lifecycle cases pass; M4 release/install, multiroot/denial,
installed rollback and30-minute owned soak remain open. No custom Codex or shared
daemon restart. Next slice: ordinary released installation and native service
wiring with frozen installed baseline, then the remaining installed/live gates.

### M4 release and installed acceptance packet | 2026-10-05

Owner primary, serialized branch chore/p63-v070-release, issue181. PR213's
evidence integrated at9ea38d7 after Python3.11/3.12 required gates passed.
Prepare Python CLI v0.7.0, actual native workflow documentation and bounded
user-systemd example. OpenClaw remains parked; neither installed plugin nor
gateway is upgraded or restarted. No Codex binary/custom daemon changes.

1. Validate release candidate locally and in required hosted CI. Integrate only
   through a merged PR; publish v0.7.0 at that exact origin/main commit. Two
   correction cycles maximum for this source/docs packet; unresolved failures
   end or reframe it without publishing an unqualified build.
2. Install the public tag using the ordinary user-scoped uv tool path. Preserve
   pre/post version, source identity and active supervisor/root readbacks. Only
   the already-active Codex Wake supervisor may restart to load the new package;
   no shared Codex daemon, OpenClaw gateway or unrelated service restart. Install
   an explicitly named demo-owned A2A unit from the shipped example and prove
   M1 with actual enrolled A/B actors, no PYTHONPATH or transport helper.
3. Prove an explicitly enrolled second real repository root and its actual
   owned Codex thread can exchange with root1; prove an unenrolled root is denied.
   New additional fixture thread/root is explicitly for this goal, never a
   replacement for original A/B. One request/one reply per case,120-second
   outcome bound, no ambiguous-effect retries.
4. Roll back a disposable normal installed copy to public v0.6.0. Preserve the
   A2A store and demonstrate old CLI refusal, then compatible reinstall reads
   the same messages/receipts. Include existing schema1-reader/schema2 refusal
   qualification, distinguished from v0.6.0's absent command surface. Do not
   downgrade the active live worker or store during the soak.
5. Freeze exact released CLI, store, owned unit/process baseline and thresholds
   before the30-minute run: duration1800, notification budget20, at most ten
   pairs, store<=10485760bytes, FD growth<=2, residual owned children0. Sample
   stable-worker FD/RSS after initialization and before exit; record start/peak/
   end RSS and freeze a64MiB RSS-growth ceiling before admission. Keep existing
   verification0104 resource limits; its synthetic30-second bound is separate
   from this requested real30-minute duration. Use four spaced live pairs at
   most unless evidence requires fewer; retain full elapsed worker duration.
   Operator setup may precede each request; no controller prompt/body relay
   after that request's admission. Stop on uncertain effects or resource limit.

Exactly one ordinary installation/public-tag proof and one30-minute soak are
planned, with one diagnosed zero-effect setup correction maximum. Retain all
failed receipts. Completion requires every installed/live result, not a release
tag, green CI or documentation alone. Track the current goal's1100000-token
checkpoint ceiling; preserve remaining gates if that boundary arrives first.

### Public installation and service failure checkpoint | 2026-10-05

PR214 required Python3.11/3.12 run37250697991 passed; integrated exact main
9144fb3ea0e0c6bd79907594b9040ac7a77ddce8 published as annotated v0.7.0.
Ordinary global uv installation records exact tag/commit and CLI0.7.0; public-tag
smoke passes. Existing Wake supervisor restarted to load it; four roots preserved,
stock Codex0.160.0/shared daemon/OpenClaw untouched. Disposable installed downgrade
v0.7 -> v0.6 -> v0.7 preserves mailbox bytes; old CLI refuses A2A; actual A reads
the existing reply with the same receipt after restore. Verification0120 records
these results and the following actual service failure separately.

Native owned service M1 PID91069 exited5/runtime_unavailable. Actual A's request
msg_f1500c1f16e244d7955f00422948f51d and arm were admitted, but journal proves zero
transport attempts, pending/unread state. The shipped unit lacked ~/.local/bin
in PATH; the manager PATH cannot find codex. Owned read-only systemd preflight
with explicit stable PATH succeeds without changing the existing daemon.
Next bounded correction: ship that environment fix as v0.7.1 through a merged
PR/required CI and ordinary tag install. Preserve v0.7.0 and failed receipts;
one diagnosed zero-effect setup correction, no ambiguous replay. Then released
service M1, enrolled root2/unenrolled denial and30-minute native soak. Full
objective remains OPEN; source/docs correction cycles have one remaining slot.

### Released native/multiroot acceptance and failed soak | 2026-10-05

Verification0121 records ordinary v0.7.1 at exact mainbec1005, released native
service M1 PASS77.85seconds, actual unenrolled denial and enrolled root2 automatic
exchange PASS71.08seconds. Original clients and stock runtime retained. The
30-minute soak failed after786.195835seconds: pair1 PASS82.02seconds; pair2
native B read rejected clock_anomaly before effect after one submitted
notification. No reply/read receipt or retry. Observer incorrectly stopped on
a file deadline and emitted invalid negative duration after manager timestamps
cleared; both raw errors and authoritative reconciliation preserved.

Close the original soak loop as failed. Next bounded packet has two steps: one
qualification observer correction (no restart on observation timeout; include
all native phase errors; preserve manager/process identity and valid duration),
then read-only clock diagnosis and one concrete bounded recovery decision. Do
not admit another soak until the failed intent/arm and FIFO state are reconciled
and actor clock-error handling has an inspectable120-second policy. No guard
weakening, host clock modification, checkpoint reset, or transport replay.
The full-duration soak remains mandatory; current goal remains active with its
1100000-token checkpoint ceiling. No implementation delegation.

### Bounded soak recovery decision | 2026-10-05

Read-only30-second host sample reproduced a2.278-second backward wall step;
no clock service/configuration change is authorized or performed. Current bus
checkpoint drift is about-100.95seconds, within the existing300-second guard.
The original failed request remains unread/submitted and is past its expiry;
retain it and let native expiration reconcile it before subsequent admission.
No manual backlog cleanup or notification replay may qualify this failure.

Installed v0.7.1 hermetic Mailbox qualification proves clock-rejected read has
zero receipt effect; after continuity returns, reading the same ID gives one
receipt, preserves expiry, and expired work cannot acquire a claim. Private
observer-correction/installed-read-recovery-proof.json and clock-sample.json
retain evidence; these are qualification, not live acceptance.

One successor full1800-second soak is permitted after observer corrections and
native expired-state reconciliation. Same installed v0.7.1, original A/B, four
spaced pairs,20 notifications maximum and all original frozen resource limits.
Each exact notified read permits at most one delayed same-ID retry after three
seconds ONLY on native clock_anomaly with reconciliation_required=false. Save
both results separately. No new send/notification/key or foreground inbox poll;
no retry on missing output, timeout, effect_uncertain, ack/reply rejection or
other error. Before work claim, native returned admission must remain accepted;
original expiry and120-second send-to-read bound are unchanged. A second read
rejection ends that exchange; native unit lifecycle follows actual authoritative
effect/process evidence, never an observer deadline alone. This is a changed
actor recovery packet; first failed soak remains FAIL. No further soak attempt
without another evidence-based reframe.

### Requested remaining-gate packet acceptance | 2026-10-05

Verification0122 audits every explicit current-goal gate: live cancellation,
clean reconnect automatic return, full normal owned-worker restart/reconnect,
ordinary released installation, actual multiroot/unenrolled denial and installed
rollback PASS. Successor native v0.7.1 soak ran1800.32296seconds on one PID/
invocation with four automatic pairs (88.38/92.01/96.74/92.09seconds), exactly
eight submissions, zero unfinished attempts, stable FD growth0, peak RSS growth
4259840bytes, peak store783105bytes, no residual owned children. Exact actor
notification turns completed; stock Codex0.160.0 and original A/B preserved.

Original failed soak and both successor observation/setup errors remain retained.
The partial-file observer error did not stop native work; same worker observation
resumed and actual pair3/4 receipts were reconciled. Manager cleared terminal
timestamps; independent matching native journal/start identity proves full
duration without replacing the original unknown-duration resource summary.
No clock guard/checkpoint modification, blind effect replay, daemon restart or
OpenClaw operation. Requested remaining-gate packet COMPLETE after final hosted
docs integration; broader Plan0101/issue181 and retained Plan0119 server-unloaded
qualification/deferred recovery obligations remain OPEN. Do not infer wider
acceptance or new recovery authority from this bounded packet.
