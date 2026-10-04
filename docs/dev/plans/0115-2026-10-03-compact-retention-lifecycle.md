# Compact mailbox retention lifecycle

State: OPEN
Lane: P63
Owner: primary
Branch: feat/p63-retention-lifecycle
Target: origin/main
Integration: squash_pr
Depends-On: Plan 0101; Plans 0113 and 0114
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/181

## Current state

Main 94e17a68e655d9e54ead6001704dc0ef453eb933 contains guarded body pruning,
independent projection acknowledgement and explicit ninety-day dedup refusal.
Envelope/state/receipt/outbox/attempt metadata remains indefinitely. A focused terminal-compaction fixture is being established; production
implementation has not started. The original campaign remains OPEN; its acceptance
ledger is verification 0106. This plan carries no new live authority or allowance.

## Scope and critical path

Add a compact terminal identity representation and bounded operator lifecycle
maintenance, coordinating explicit mailbox migration, participant reads, duplicate
admission, ancestry, receipt pins and storage recovery. One owner serializes schema,
read/write semantics and final installed acceptance. No parallel agents requested.
Expected write surface: a2a_mailbox.py, a2a_operations.py, a2a_cli.py, affected
scheduler/receipt adapters where schema contracts require, focused tests, one installed
qualification script and CI wiring, verification and parent campaign projection.

First freeze exact semantics from Plan 0101 before adding an API: thirty-day body
retention, ninety-day compact identity/dedup horizon, bounded pages, operator authority,
immutable attributable history and explicit behavior outside the advertised horizon.
Inspect existing receipt and foreign-key consumers before defining tombstone fields.
Do not silently delete a key then accept an old retry as a fresh intent. Do not remove
an ancestor required by a retained reply or collapse uncertain transport into success.

## Non-goals and authority

No actual agents, transport sends, provider/business effects, services, live roots,
or backup activation. No source or mailbox data outside disposable fixtures is changed.
Full restore, actual binary downgrade, real delivery, service/soak and release remain
separate campaign gates. Preserve root identity/copied-store refusal and old-reader
visible schema refusal. Preserve inherited review counters and failure history.

## Acceptance and validation

A focused deterministic fixture must distinguish full metadata from compact identity
while proving original message ID, sender/recipient authorization, digest, idempotency
fingerprint and receipt/correlation semantics. Establish the red-capable command before
implementation. Existing test_a2a_operations covers body pruning, projection pins,
late-reply invalidation and the exact ninety-day boundary; extend this seam rather
than adding overlapping tests. Its helper simulates publisher acknowledgement, so
installed qualification must use the production projection acknowledgement seam.

Prove preview/apply fingerprint consistency, stale-preview refusal, repeat maintenance,
active/unprojected/processing/uncertain pins, retained-reply ancestry, exact retry identity
through ninety days and typed old-intent refusal beyond. Migration must be explicit,
transactional, interruption-safe and visibly refused by the previous reader. Fresh
installed process reads and CLI envelopes must preserve typed failures and reconciliation
pointers. Measure physical SQLite recovery separately from logical row deletion and
retain resource/timeout bounds. Source focused checks plus final installed workload
and hosted Python 3.11/3.12 gates are required on the reviewed SHA.

## Definition of done

The lifecycle behavior satisfies the original retention contract, installed migration
and space-recovery evidence pass, code review and required gates pass, integration is
verified, and the completion ledger is updated without claiming unrelated live gates.
The operator resumed accounting with a new additional 500k allowance. The earlier
412,020-token checkpoint remains historical and does not consume or reset this
new meter. Checkpoint at a working 450k before the additional 500k ceiling. If
accounting cannot be resumed or this ceiling approaches, checkpoint
this packet without claiming accepted lifecycle behavior or resetting the ceiling.
