# Build usable live agent-to-agent messaging

State: OPEN
Lane: P63
Owner: primary integration lane
Branch: feat/p63-activation-gate
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

## Current state

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

## Current execution decision | 2026-10-04

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

Current integrated source:835990a4ba31a1a774b5fa72332fe05db17b7b28 via PR206.
The retained patch and compiled package are inactive historical artifacts, not
a product prerequisite. Existing owning-client commands depend on that inactive
patch and do not constitute the selected stock-runtime transport. M1-M4 remain
UNPROVEN and actual automatic round-trip attempts remain0/3.

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
