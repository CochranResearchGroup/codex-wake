# Explicit receipt arming CLI

State: CLOSED
Lane: P63
Owner: primary
Parent: Plan 0101 / issue #181
Branch: feat/p63-receipt-arming
Target: origin/main
Integration: squash_pr

## Current State

PR #189 integrated at 75686bac66abd4be11cfbe865cb8918addfd0af5.
Independent observer grants restore receipt signals but no supported command
registers them. Full campaign and actual suspension/delivery remain OPEN.

## Scope and authority

One serialized primary packet adds explicit receipt arming through the existing
private observer grant. It writes only the selected Wake journal and records;
mailbox access stays read-only. No actor impersonation, grant creation, live
enrollment, provider effects or service installation. No parallel track.
Write surface: authority helper, a2a parser/handler, focused tests, README,
parent plan, verification and runbook.

## Acceptance and bounds

A fresh CLI creates a durable pending exact-message arm, repeating the same
idempotency key preserves its identity, changed intent conflicts. A fresh daemon
keeps it pending before a receipt and fires once after a committed fixture reply.
Expiry and missing/revoked grant fail closed. Command output omits bodies and
credentials. Isolated installed commands must exercise the same path.
Two implementation attempts and one targeted repair; replay/grants retain
100-row/64 KiB limits. First executable proof within 30 minutes. Carry campaign
usage, cumulative 2,250,000 ceiling and prior review ledger forward; no reset.
No active goal meter; do not invent an exact usage total.

## Non-goals and definition of done

Local arming prerequisite qualified with focused, comprehensive and installed
checks, then published for hosted gates. Actual agent suspension or delivery is
not accepted by a synthetic no-dispatch firing. Generic receipt dispatch remains
held. Close this packet at its bounded arming result, not wider campaign completion.

## Closeout

Local prerequisite accepted: four fresh-command scenarios, 25 focused tests on
Python 3.12 and 3.11, 834 comprehensive tests; four isolated installed-command
tests. Reader gate retained. Actual suspension/delivery remains unqualified.
No new review allowance, live effects or actor enrollment. Verification 0102
records initial failures, fixture correction and final evidence. Publication
and hosted integration are subsequent states.
