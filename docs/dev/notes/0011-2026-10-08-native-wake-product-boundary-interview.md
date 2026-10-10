# Native Codex and Wake product boundary interview

Status: design interview in progress. First-frontier recommendations accepted by the user on 2026-10-09 ("agree al"). Subsequent recommendations remain unsettled; no implementation has begun.

Scope: define Wake's value across discovery, messaging, conditional follow-up, recovery, and visible tab lifecycle. No production changes during the interview. ROADMAP.md and existing plans retain execution authority. No new glossary or ADR is warranted until terms or decisions settle.

Evidence: prototype branch `prototype/native-session-lookup`, commit `3619e60`, `scripts/prototype_native_sessions/README.md`, proves native A→B→A with an idle sender in both native-created tasks and two independent TUI clients. Original panes reflected the exchange. This removes idle wake alone as a sufficient rationale for custom message injection. Research note 0010 records native API contracts; its earlier availability and untested statements are superseded by that prototype.

Installed Wake sessions commands currently support list/show/resolve/current/watch, not opening or closing tabs. Existing product includes scheduling, condition triggers, durable records, mailbox operations and transports. Presence of a feature does not establish that it must survive the product redesign.

## Decision tree and first frontier

1. Product scope: durable scheduler only, or scheduler plus agent workspace lifecycle? Recommendation: scheduler plus opening/addressing/closing visible tabs, while native Codex owns task execution and conversations.
2. Messaging contract: every direct message must enter Wake's durable mailbox, or direct native messages by default with durable workflows explicitly selected? Recommendation: native direct messaging by default; durable records for scheduled/conditional work and explicitly requested tracked exchanges.
3. Compatibility policy: preserve every existing implementation path, or permit evidence-backed retirement after replacement and migration qualification? Recommendation: permit staged retirement, preserving readable existing state and supported recovery throughout migration.

After these independent decisions settle, ask downstream questions about close semantics, pending work and restart behavior, client/version support, failure outcomes, capability selection, and migration acceptance. The design frontier is not empty. Do not silently treat recommendations as user answers.

## Accepted product boundary | 2026-10-09

All three first-frontier recommendations accepted: Wake owns durable scheduling plus visible tab lifecycle; ordinary messages use native Codex by default; redundant paths may be retired in stages after replacement and migration qualification. Native Codex retains task execution and conversation ownership.

## Second frontier | accepted 2026-10-09

User accepted all three recommendations ("yes all"): guarded close with explicit force preserving records; missing-target behavior explicit per workflow; reconcile uncertain submission before retrying and expose unresolved uncertainty.

4. Closing a tab: recommend refusing ordinary close while the agent is active or durable work targets it; explicit force-close preserves conversation and wake records and reports affected work. Force-close must not imply cancellation or archival.
5. Missing target: recommend keeping durable work pending for its exact thread until its expiry, with an explicit per-workflow option to resume that same thread. Do not create a replacement thread or visible tab automatically by default.
6. Uncertain submission after interruption: recommend recording uncertainty and reconciling native evidence before retrying. When reconciliation cannot resolve it, surface an explicit unresolved outcome instead of blindly replaying potentially completed work. This is a proposed contract, not an exactly-once delivery claim.

Next step: settle the second frontier, then qualify client support and migration criteria and refine one end-to-end workflow and the keep/simplify/replace/retire inventory. No production code, services, tabs, or messages are changed by this interview.

## Third frontier | accepted 2026-10-09

User accepted the recommendations with "ok go": explicit new/resume selection and attachment reuse; native-first delivery with explicit legacy selection; per-path retirement after runtime and migration qualification.

7. Opening: recommend explicitly selecting new conversation or resume exact existing thread, requiring a directory for a new conversation, and returning exact thread/tab identities. Reuse an existing attachment by default; creating a second attachment requires an explicit option. Do not silently select a recent conversation or create a worktree.
8. Delivery availability and busy recipients: recommend native-first delivery; when unavailable or recipient busy, retain durable work pending until expiry. Legacy transport is an explicit compatibility choice, never an automatic retry after uncertain native submission. Ordinary direct messaging reports failure instead of silently creating durable work.
9. Retirement qualification: recommend real native tests for idle and busy recipients, detached targets, client/daemon restart, uncertain submission, visible tab synchronization, and legacy-state migration/recovery. Retire each redundant path only after its replacement meets the corresponding contract; do not require unrelated capabilities to migrate simultaneously.

## Consolidated design boundary

Native Codex owns conversations, turns, ordinary messaging, and task status. Wake owns durable time/condition triggers, explicit tracked workflows, recovery visibility, and visible tab lifecycle. Tab labels resolve to exact thread identities; they are conveniences, not durable destinations. Closing a tab preserves conversation and pending records; archival and cancellation remain distinct actions. Native delivery is preferred; uncertain submission is reconciled rather than replayed blindly. Redundant transports may retire after their individual replacement contracts pass.

First implementation sequence: qualify native delivery from a background scheduler without depending on a live calling TUI; add exact new/resume tab lifecycle with guarded close; integrate one durable condition-triggered native submission; then qualify interruption/recovery and prepare staged retirement. The successful interactive native experiment does not prove unattended scheduler access to TUI-hosted MCP tools. This is an engineering evidence gap to investigate, not a question for the user.

Interface spellings, polling intervals, and bounded test organization are implementation choices. No new product questions remain for the bounded first slice. Confirm the consolidated understanding before implementation, per the grilling skill. This note captures interview evidence; a repo-native plan will become execution authority before behavior changes.
