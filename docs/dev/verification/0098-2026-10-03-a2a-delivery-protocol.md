# Plan 0101 installed delivery protocol observation

State: INCOMPLETE
Parent: Plan 0101 / P63.5 / issue #181
Owner: primary
Source baseline: 625bb9c138bd3c13f5536ff92625a1d608da2850

## Current evidence

Read-only restart checks found clean canonical main at the source baseline,
equal to fetched origin/main. PR #186 is merged; issue #181 is OPEN.
The old checkpoint branch resolves to 21bed303b5fc0fb23318c517ccc7055862c3507e;
the catalog's f3050bd checkpoint describes the integrated foundation rather
than the latest branch tip. Reconcile custody before further integration.

Installed executable: codex-cli 0.160.0, resolved release binary under
`~/.codex/packages/standalone/releases/0.160.0-x86_64-unknown-linux-musl/bin/codex`.
SHA256: 12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad.

Ran `codex app-server generate-ts --experimental --out DIR` against that
binary. Generation completed successfully without launching an app server.
The generated TurnStartParams explicitly documents that turnTrigger is
ignored when the request steers an already-active turn. It contains no
idle-only compare-and-start precondition. ThreadQueueStartParams contains
only threadId and optional queuedSubmissionId. ThreadQueueAddParams contains
threadId, input, and clientUserMessageId. These schemas do not establish
atomic busy/composer safety or runtime-issued recipient/client binding.

Verdict: automatic delivery remains unqualified. No turn/start, queue/add,
queue/start, resume, notification, enrollment, or service mutation was issued.
Schema inspection cannot prove queue implementation semantics; inspect the
installed implementation before accepting or rejecting that alternative.

## Budget and next action

The resumed goal reports zero historical tokens. This is a new meter, not
evidence that the campaign allowance reset. The prior durable boundary is
625,906, with final paused usage still unverified. Preserve the 750,000
cumulative ceiling and the 700,000 working checkpoint threshold. Locate the
prior final goal receipt before committing to a larger proof. Two bounded
file-searcher requests timed out; neither establishes absence of that receipt.

Next packet: recover final budget accounting and inspect authoritative queue
implementation semantics. Freeze disposable identities and resource bounds
only if sufficient safety and allowance are established. Full campaign scope
and prior review/attempt bounds remain unchanged.

Graphiti discovery doctor reported degraded MCP ingress and persistence defect.
Memory disposition: unavailable; no authorized repository group or healthy
write path established, zero Graphiti writes.

## Continuation and accounting correction

The operator authorized continuation beyond the 700,000 working threshold,
retaining the 750,000 cumulative stop ceiling. Recovered the original goal's
paused tool receipt from session 01a0ff37-b363-7cb3-a424-d51835f538b1:
final tokensUsed **644,919**. The current session's paused receipt is **73,733**.
Thus the verified combined meter baseline is **718,652**, superseding the
699,639 minimum reported at the first continuation checkpoint.

The goal service still reports paused after the user's continuation message;
it cannot be resumed through update_goal. Track subsequent effort using the
current turn's transcript usage (input minus cached input plus output), rather
than treating that frozen goal meter as zero additional consumption.

Located the local Codex source checkout, commit
bdd282f3bbd55df3a869a5438519cd948c134d4d, dated 2026-06-27. Its turn processor
submits Op::UserInput; no ThreadQueueStart implementation was found in the
app-server/core search. This is not source qualification for the installed
0.160.0 binary: the installed package manifest gives version/target/layout but
no source revision. Do not use this mismatched checkout as runtime authority.

Remaining acceptance gaps are unchanged. Next meaningful delivery step needs
source provenance matching the installed queue implementation, or an equally
authoritative safe-operation contract. No effects are justified by the current
schema and source evidence. Preserve the completed observation without claiming
delivery acceptance or narrowing the full Plan 0101 outcome.

## Official release source observation

Read the official tag rust-v0.160.0 at peeled commit
a956835d020762cb2b570053af06f643a11c0ecc. The installed package manifest does
not include a source revision, so this is release-source evidence, not proven
installed binary provenance.

`codex-rs/app-server/src/request_processors/thread_queue_processor.rs` start
requires a loaded thread, calls the queue service, and rejects NotIdle or
PendingTriggerTurn with "thread already has an active or pending turn".
Its SHA256 is c5b6119ad7a5416b4b7b850e15a1f6c0024207975ff8dfa374578cae178698a4.
`codex-rs/ext/queue/src/service.rs` start takes a per-thread dispatch guard,
selects the specified queued ID, calls start_turn_if_idle, and deletes the
queued item only after Started. SHA256:
110253b6c2b74de1ad8610b347ac331479d4f09873a1c8f9793a6921438d6ae1.

The release test queue_start_while_active_returns_busy_and_preserves_the_queue
also shows the added item starts automatically after the active turn completes.
Therefore queue/add is not a passive mailbox operation. These observations
improve the busy-state evidence but do not establish composer ownership,
thread-to-client attestation, or installed provenance. Automatic delivery stays
unqualified. Source tests were inspected, not executed; no runtime queue effect
was performed.

Source locators: official openai/codex GitHub repository, the exact commit above,
app-server/tests/suite/v2/thread_queue.rs, queue processor and queue service.
