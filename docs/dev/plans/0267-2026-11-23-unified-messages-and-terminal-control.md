# Plan 0267 | Unified messages and terminal control

State: OPEN
Owner: primary integration agent
Spec: [GitHub #766](https://github.com/CochranResearchGroup/codex-wake/issues/766)
Work items: #767 through #780
Source audit baseline: `70ff3585`

## Current State

The agreed specification is in implementation on `feat/plan0267-unified-messages`.
The [execution ledger](0267-execution.json) records ticket ownership, integration
commits, validation receipts, and remaining gates. Live acceptance and deployment
require their own authorization.

## Goal

An operator can speak naturally about their tabs and agents from stock Codex,
Wake Codex, or ChatGPT through the external OAuth MCP connector. Those clients
use the same Codex Wake operations and receipts as the CLI. Wake coordinates
durable messages and restores or inspects exact conversations across WSL
tmux/Byobu, native Windows psmux, and SSH views between them.

## Domain model

- A **message** addresses an exact recipient and has a stable ID, sender,
  payload, eligibility trigger, original expiry, delivery policy, and optional
  response request. Send-now messages are immediately eligible. A wake uses a
  time or event trigger. A recurring schedule produces a distinct message per
  occurrence, with a retained relation to the schedule and its original due
  time.
- A **conversation** is the persisted harness session and its owning execution
  environment, account, and workspace. A **terminal attachment** presents it.
  One conversation can survive loss of a terminal attachment.
- A **reply** is a message related to the original message and sender.
  Acceptance, execution, acknowledgment, work claim, and reply remain distinct
  evidence. Preserve the existing A2A distinction between a request for work
  and a notice. Retain replies in the original sender's Wake inbox. A
  requested wake on reply targets the exact sending conversation under its
  current delivery policy. ChatGPT can retrieve the reply through OAuth MCP
  after the originating tab closes.
- A **placement** records the desired terminal session, tab name and slot.
  The observed terminal generation and native window/pane identifiers identify
  a live attachment. A title or slot can be reused by a different conversation.
- An **execution owner** is the registered host, environment, and execution
  scope that owns the conversation and its durable delivery effects. A
  **presentation owner** owns the terminal attachment and its placement.
  These roles can be on opposite sides of SSH.

## Delivery contract

Use one delivery decision and receipt path for immediate A2A messages, wakes,
and replies. Keep existing callers and durable records usable throughout the
change. The decision evaluates original eligibility and expiry using StableTime
where required, then exact recipient state, permissions, DND, startup policy
and harness capabilities.

- An attached idle recipient can receive immediately. An active recipient can
  queue, bounce, or receive an explicitly authorized exact-turn interruption.
  Ordinary sends wait until idle or expiry. An explicit idle-only send
  bounces immediately. Deliver waiting messages individually, oldest eligible
  first, preserving each expiry and reply correlation. Stock Codex admits one
  at a time. An authorized interruption may take precedence over ordinary
  queued messages.
- A detached or dormant recipient can require an existing attachment, resume
  in the background, or recover a visible tab and the original harness.
- The Codex Wake database owns session message data and settings, including
  do-not-disturb. Key DND to the exact conversation in the owning execution
  scope. All views of that conversation share the setting across tab closure,
  restoration and reboot. Delivery reads the current setting when deciding
  whether to proceed. The receiver chooses hold or bounce for ordinary
  delivery. The sender may request an immediate bounce instead of waiting.
  DND supports an optional expiry and can always be cleared manually.
  A normal interrupt request respects DND.
- DND does not take the execution owner offline. Inspection and reconciliation
  continue. The operator or a Wake controller acting under explicit delegated
  policy can override DND for one exact recipient and message or operation.
  A DND override waits for idle by default. Interrupting an active turn
  requires a separate explicit request, authority, and exact-turn evidence.
  The operator may request both in one command. The receipt records the
  authorizing principal or policy, the exact target, and the resulting effect.
  The original expiry and identity rules still apply.
- A future delegation may grant a bot such as Chief of Staff DND override for
  named recipients or a defined scope. The grant follows the verified bot
  identity. It does not include interrupt authority unless that authority is
  also granted. Wake checks delegation at delivery time, including revocation.
- Waiting in Wake and admission to a harness queue have separate receipts.
  Stock Codex should retain pending messages in Wake and submit when idle.
  Use receiver-side expiry, interruption, and richer queue semantics where
  supported and qualified. Surface the actual capability and outcome.
  For an ordinary queue request, Wake may hold until stock Codex is idle.
  An explicit interrupt or deadline-aware harness enqueue requires that
  capability. When unavailable, report it and preserve any existing hold.
- A transport failure after possible admission remains uncertain. Reconcile the
  original message and effect before any retry. Cross-owner handoff preserves
  the message ID, recipient, original expiry and correlated reply destination.
- Before harness admission, cancellation removes the message from delivery
  eligibility. After admission, report cancellation only with positive
  removal evidence. If the turn started, report that state. An explicit turn
  interruption is a separate operation.
- Redirecting a bounced message requires an explicit new recipient. Create a
  new message ID linked to the original. Preserve the original recipient's
  delivery and reply history.
- Reuse a verified live conversation, including a loaded idle conversation
  whose frontend disappeared. Recovery preserves the account, harness,
  workspace and execution scope. Reuse a vacant original slot, follow the
  existing matching-idle-shell policy, and preserve unrelated occupants.
  Record actual placement and identify automatically restored tabs.

### Operator example

1. The operator asks their dot to prompt a session. Wake can return that the
   exact session is busy and report whether the message was held or bounced.
2. The operator asks for an interrupting message. Wake can return that the
   recipient is on DND and report the message's disposition.
3. The operator says to send the message and ignore busy and DND. The client
   submits both the interrupt request and the DND override through Wake.
   Resolve the exact session and reuse the pending message ID if it was held.
   If it bounced, link the new authorized send to the prior attempt.
   An uncertain prior submission must be reconciled before another send.
   Report the interruption and delivery outcomes separately. If escalation
   fails, keep any original held message under its original policy.
   Cancellation is a separate action.

## Windows, WSL, and remote ownership

- On Cooper, Windows Wake comes up first and coordinates boot recovery.
  Windows owns Windows-native harnesses, history, CWD, psmux attachments and
  delivery. WSL Wake owns corresponding Linux harnesses, history, CWD,
  tmux/Byobu attachments and delivery. External Wake servers can route to a
  registered destination owner through the same message contract.
- Model normal Windows and elevated Windows execution separately. Verify the
  actual account and elevation behind the `Cooper-win` and `Cooper-win admin`
  SSH routes. Elevated restoration retains the original privilege level and
  requires an active, authorized elevated executor.
- In an SSH view, the source multiplexer owns placement. The destination owns
  the harness and presents it directly through SSH. This workflow never starts
  or attaches a destination tmux or psmux. Closing the source tab reconnects
  the view only when visible recovery is requested and the remote conversation
  survives. Otherwise the delivery policy applies with the view closed. If the
  harness also exited and recovery is allowed, the destination resumes the
  saved conversation in its original execution scope.
- Each active owner can serve its own clients independently. When both run,
  callers can see one scope-filtered inventory. An inactive owner is reported
  unavailable, with last known facts labeled by observation time.
- Windows Wake can durably accept WSL-bound messages, including from ChatGPT,
  while WSL is stopped. Report that the message is waiting for WSL. When a
  message becomes eligible, Windows can start the registered WSL distribution
  if auto-start is enabled for it. WSL reconciles its own wakes and owns final
  delivery. Normal Windows, WSL and elevated Windows activation are independent.
  Ordinary messages wait for the separately activated elevated executor.
  Recipient policy governs tab and harness recovery within an active scope.

### Cross-owner custody

- Windows retains forwarding custody until it confirms that WSL durably
  accepted the same message ID. After a lost receipt, inspect or repeat the
  same handoff. WSL deduplicates admission and owns any harness effect.
- A pending message remains pinned to its original execution owner unless an
  explicit verified transfer preserves conversation identity and outstanding
  delivery state. Renaming a tab, reconnecting a view, or copying history
  does not redirect work.
- Offline status reads use timestamped cached metadata. Read saved content
  through the authorized owning history reader. A status query leaves the
  owner stopped unless the operator requests a fresh check and activation
  policy permits it.
- Qualify Cooper normal Windows and WSL in both directions, including SSH
  presentation. Qualify the elevated route independently next, then reuse
  the same acceptance contract for external Wake servers.

### Shared PostgreSQL store

Cooper runs PostgreSQL on Windows, independently of WSL. Windows owns
startup, backups and recovery. Windows Wake waits for database readiness
before accepting messages into the shared store. Cooper uses the
native Windows service so it can start at boot independently of Docker and
WSL. Other hosts may use a container when it meets the same startup and
recovery requirements.

PostgreSQL stores messages, replies, settings, receipts, and current and former
tab bindings, including the last observed pane CWD. Full harness transcripts
remain in the owning account's history store. Wake services expose authorized
reads through their operation interfaces, including ChatGPT through OAuth MCP.

Windows Wake coordinates boot and ingress. Each execution owner retains a
local delivery journal and remains the sole authority for its harness effects
and recipient settings. The owner can commit settings locally during an outage
and publish its revision when connected again. Remote settings requests wait
for the owner to confirm them.

Introduce the shared store one execution scope at a time. Verify imported
records before switching writes. Preserve existing message and schedule IDs,
deadlines, reply correlations and uncertain delivery outcomes. Reconcile
uncertain outcomes under the original identity.

If the shared store is unavailable, WSL can continue local work using locally
committed records and authoritative local settings. New cross-owner traffic
waits durably. If current recipient policy cannot be established, hold new
cross-owner delivery and overrides. Recheck settings and original expiry
after recovery. Windows reports shared ingress unavailable until PostgreSQL
is ready.

A remote settings request carries the owner revision it was based on. If
the owner committed a newer revision during the outage, retain the owner
revision and report a conflict. The operator can reapply the request against
the current revision. After database restore, hold new delivery for each
affected scope until its local delivery journal is reconciled. Preserve
submitted and uncertain outcomes.

### Linux-only deployment

On a single Linux host, Linux Wake combines ingress, boot coordination and
local execution ownership. PostgreSQL can run as a native system service.
Wake's shared ingress becomes ready after PostgreSQL is reachable. The
Linux execution scope reconciles its local journal and resumes eligible
deliveries when the account and recovery capabilities are ready.

An operator can configure boot activation for the service or login activation
for a session-bound scope. A boot-enabled owner may recreate its configured
tmux/Byobu session for visible terminal recovery when that configuration
works without desktop login. Desktop-bound scopes wait for their required
user session. A tmux client can attach later to a recovered terminal session.

On several Linux hosts, the registered receiving host owns harness effects
and local recovery. Hosts can share a Wake ingress and PostgreSQL store
within one deployment. Independently operated Wake servers exchange
messages by the durable handoff contract. PostgreSQL placement does not
change which host owns a conversation.

Use a disposable WSL distribution or Linux container for early Linux-only
functional checks. Run PostgreSQL, Wake and tmux in the isolated environment
with the Windows Wake owner absent. Verify message admission, DND, delivery
deduplication, tab restoration and restart of the owned processes. Use
StableTime for operations requiring qualified time, and disclose any injected
clock or provider used by a fixture.

Bastion is the native Linux acceptance target. Qualify native service startup,
database readiness, boot without a desktop login, local journal reconciliation
and one delivery after recovery. Disposable environments can establish
functional and process-restart behavior. Actual host boot requires a separately
authorized native boot test. A Bastion deployment or restart is outside this
draft's authority. Qualify Linux-to-Linux handoff after single-host acceptance.

## Management and history

- Expose session and tab discovery, creation, rename, focus, movement and
  ordering, formatting, inspection, content read, input and close. Expose
  harness launch, pause/interrupt where supported, saved resume and capability
  inspection. Qualify supported operations per terminal backend.
- Resolve natural-language tab references through Wake before acting. Clarify
  ambiguous names or positions before acting. History queries can return both
  current and former bindings with dates. Teach stock Codex agents this convention
  through their Wake setup. Wake Codex should offer message, reply and DND
  slash commands. CLI and MCP remain usable through both harnesses.
- ChatGPT's external OAuth MCP client should offer the same protected
  session/tab/harness and message operations. Distinguish metadata reads,
  history content reads, input, lifecycle and elevated authority. A metadata
  update includes current or last observed status and timestamps. A content
  summary uses authorized saved history. A requested agent report uses a
  correlated message and reply.
- After destruction, a former tab lookup resolves through the last verified
  binding to the exact saved conversation. Return the last observed pane CWD,
  the conversation workspace when different, and the latest saved activity.
  Retain name reuse as a separate binding. A read leaves the tab closed.
  By default retain the former-tab binding as long as the saved conversation,
  subject to a configurable limit and explicit forget. If history is gone
  and tab metadata is still retained, report that metadata and its observation
  time.

## Existing, deepen, develop

| Existing foundation | Deepen or develop |
| --- | --- |
| Durable A2A mailbox, reply correlation, work claims, wake scheduler and runtime adapters | Consolidate delivery decisions and receipts behind one message interface. Add DND and common busy policy. |
| tmux/Byobu tab recovery, psmux bridge and prior tab-management qualification | Share restoration semantics and qualify the psmux tab-loss and full-server-loss journeys independently. |
| Tab metadata observations and scoped saved conversation history | Develop former-tab resolution and last-known CWD provenance. Reuse existing history reads. |
| Host/environment registration, scoped SSH routing, external OAuth MCP protected catalog | Develop Windows-native Wake ownership and activation, SSH attachment links, durable delivery handoff, and protected external messaging. |
| CLI, stock Codex stdio MCP and protected controller surfaces | Deepen natural-language resolution and parity. Add Wake Codex slash commands and qualify actual ChatGPT dispatch. |

## Acceptance and done

1. Submit an immediate message and a timed wake to the same recipient. Prove
   matching idle, active, queue, bounce, DND, expiry and reply behavior.
   Demonstrate stock Codex waiting and qualified Wake Codex queue capabilities.
   Verify that ordinary interruption respects DND, authorized intervention can
   reach the exact recipient during DND, and a DND override alone cannot
   interrupt an active turn.
2. On both tmux and psmux, create a tab and conversation, retain a wake, destroy
   the tab only, and verify the same conversation receives one delivery.
   Repeat with a busy detached turn, original slot vacant with later tabs,
   matching idle placeholder, unrelated occupant, and terminal-server loss.
3. Boot Windows with WSL stopped. Exercise enabled and disabled WSL auto-start,
   WSL-only and Windows-only operation, interruption during handoff, and
   recovery after both owners return. Preserve message IDs and deadlines.
4. Run both SSH directions and the normal and elevated Cooper routes. Close
   only the outer tab, then test remote harness loss separately. Verify direct
   destination harness presentation, exact identity and privilege, and no
   destination multiplexer activation.
5. In actual connected ChatGPT and fresh stock Codex, use ordinary tab language
   for status, management, send/reply and scheduled recovery. Exercise Windows
   and WSL recipients in both directions and show correlated outcomes.
6. Change a test tab's CWD, complete a recognizable turn, and destroy the tab.
   From ChatGPT, resolve the former tab and report its observed CWD and latest
   saved activity without recreating it. Repeat after the name is reused.
7. Qualify Linux-only behavior in a disposable environment, then verify
   single-host native Linux service activation and boot recovery on Bastion.
   Verify that no Windows Wake service is required.

Done means the agreed journeys have evidence at the public entry points,
existing callers remain compatible, and unsupported capabilities are visible.
No migration, rollout, or host changes are in scope for this draft.

## Implementation and qualification order

1. Route one direct message and one timed wake through the same PostgreSQL-backed
   delivery model. Keep existing commands and stores usable throughout staged
   cutover. Verify the original identity, expiry, and receipt for both cases.
2. Exercise the shared contract in disposable Linux with Windows Wake absent.
3. Qualify Bastion's native single-host boot and Cooper's normal Windows and WSL
   routes independently once the shared contract is available. A Bastion boot
   test requires separate authorization.
4. Qualify elevated Windows and other cross-host routes after the corresponding
   normal routes pass.
