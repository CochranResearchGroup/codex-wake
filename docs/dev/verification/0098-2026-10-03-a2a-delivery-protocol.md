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
