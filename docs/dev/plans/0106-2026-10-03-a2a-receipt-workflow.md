# A2A recipient disposition workflow

State: CLOSED
Lane: P63
Owner: primary
Parent: Plan 0101 / issue #181
Branch: docs/p63-delivery-qualification
Target: origin/main
Integration: squash_pr

## Current State

Mailbox and bounded foreground received/reply observation exist. Receipt signal
replay remains a library seam. Automatic delivery is unqualified. Release source
queue-start rejects active turns but does not establish composer/client safety.
The operator raised the cumulative campaign ceiling to 1,500,000; historical
usage carries forward. Prior known combined minimum is 745,116 plus closeout
and later effort. Checkpoint by 1,400,000 with margin before the hard ceiling.

## Scope and outcome

Expose bounded waits for attributable accepted, declined, completed and failed
receipts, in addition to received/reply. Preserve historical acceptance after
completion and query the journal independently of truncated display history.
Document the recipient workflow in the shipped skill, including peer trust,
intent reuse, claim/disposition semantics and unavailable automatic suspension.

## Non-goals

No notification effect, enrollment, actor spawning, service installation or
release. No claim that this packet qualifies long suspension or full Plan 0101.
Daemon receipt-source restore and exact safe dispatch remain successor gates.

## Work and validation

One serialized primary lane owns mailbox receipt lookup, CLI options and skill.
Two implementation attempts, one targeted repair; existing campaign review
discovery allowance is exhausted. No fresh broad review. Verify exact message
and participant authorization, historical receipts beyond display truncation,
wrong-condition timeout, and observation without read/claim or private bodies.
Run affected mailbox/CLI/signal tests and the full provider-free suite after
changes; installed fixture qualification remains separate from real agents.

## Acceptance and definition of done

Executable CLI waits return exact committed matching receipt IDs, reject
unauthorized observation and retain finite timeout. Skill commands match the
parser. Frozen protocol/source observations and budget authority are recorded.
Packet completion does not close P63.6 long-suspension acceptance or Plan 0101.

## Closeout

Implemented and verified the bounded foreground workflow. Verification 0099:
28 focused and 820 comprehensive tests pass; installed fixture closes 24 read
connections with zero child processes and runtime effects. CLI/skill agreement
verified. Long suspension, source restore and qualified delivery remain open
under the unchanged parent campaign. Integration remains separate from local
packet acceptance.
