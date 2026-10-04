# Delivery runtime provenance and live-test boundary

Parent: Plan 0101 / Plan 0111 / issue #181
Baseline: 9c3bbe8d89c421bddd6e6a5f2d8573d14acee6a1.

## Current installed identity

Read-only `codex --version`: codex-cli 0.160.0. Executable resolves to
/home/ecochran76/.codex/packages/standalone/releases/0.160.0-x86_64-unknown-linux-musl/bin/codex.
Official release API target: a956835d020762cb2b570053af06f643a11c0ecc,
tag rust-v0.160.0. Official source:
https://github.com/openai/codex/releases/tag/rust-v0.160.0.

One bounded download of codex-x86_64-unknown-linux-musl.tar.gz from the release
matched the API asset SHA256:
306865417d4ee7a927785852910a527f41e1e159add390ac5ae3accb67d44a13.
The extracted executable and installed executable both SHA256:
12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad.
Thus installed executable identity matches the official release asset. The
release names the exact source revision above; this is authoritative release
mapping, not an independent reproducible-build or cryptographic build attestation.

Retrieved exact-source thread_queue_processor.rs through the official repository
API at that revision; SHA256 matches verification 0098:
c5b6119ad7a5416b4b7b850e15a1f6c0024207975ff8dfa374578cae178698a4.
The idle queue-start rejection is source-qualified against this release mapping.
It does not establish exclusive composer/client ownership. Queue add remains an
effectful operation that may start a turn automatically; no queue operation issued.

## Read-only runtime observation

Shared managed daemon process existed (PID 5083). The bare source Python probe
reported SharedSourceError/ModuleNotFoundError due to absent WebSocket dependency;
it is not evidence of a broken or unavailable daemon. The isolated installed
wheel environment successfully connected and read metadata for 15 loaded threads,
without turns/history. It exposed status and canAcceptDirectInput; those fields
alone do not authorize an effect or prove the client's composer is empty.
No existing idle thread was designated disposable by this packet.

Temporary download and metadata evidence: /tmp/codex-wake-p63-provenance.
No transcript bodies, credentials, queue/start, turn/start, resume, notification,
enrollment, service mutation, provider effect or process kill performed.

## Concrete live acceptance packet to authorize

Use a new private bus `p63-live-acceptance` and two disposable roots beneath
/tmp/codex-wake-p63-live-acceptance/{sender,recipient}, with dedicated sender and
recipient threads named `p63-acceptance-sender` and `p63-acceptance-recipient`.
Never reuse existing production threads or roots. Both must be explicitly chosen
and identified from the current shared daemon before enrollment. Explicitly
select whether delivery is manual pull or a qualified adapter; a manual result
cannot satisfy automatic delivery acceptance.

Maximum effects: one request, one recipient retrieval/acknowledgement, one
correlated reply and one sender retrieval; 120-second timeout; no external tools
or business-system effects. Capture mailbox/notification/recipient projections
separately; refuse on missing runtime identity, generation, busy/queued/draft or
ownership evidence. No automatic retries on uncertain delivery. Record OS process
and descriptor census before/after; preserve accepted records and receipts;
remove only owned temporary test state after attributable cleanup is established.

This is a prepared boundary, not execution authorization or live acceptance.
The objective remains the full Plan 0101, including busy/restart/multiroot/resource,
migration/rollback and release gates. Current automatic delivery remains unavailable
until composer/client ownership or an authoritative supported safe-operation
contract is established. Do not replace this requirement with a synthetic firing.
