# Explicit configured receipt observer

State: CLOSED
Lane: P63
Owner: primary
Parent: Plan 0101 / issue #181
Branch: feat/p63-receipt-authority
Target: origin/main
Integration: squash_pr

## Current State

PR #188 merged at ff37005b0271b631c5dffa2e1c630d241761826a after both
Python 3.11/3.12 release gates passed on e107ee39d467244def698d9336208144eced3631
in run 37154989267. Exact restore and guarded publication are integrated.
No production resolver or receipt daemon configuration exists. Issue #181
and Plan 0101 remain OPEN; the original handoff is preserved in its checkout.

This baseline paragraph records the starting state. The opt-in configured
observer is now locally accepted; verification 0101 records executable,
revocation, read-only, installed wheel and resource evidence. Hosted integration
and actual long-suspension acceptance remain separate.

## Scope and authority

One primary serialized packet adds an opt-in codex-waked receipt authority
file. It independently pins wake root, bus root/id, exact actor generation,
message and source instance, and an operator capability path. It is private,
nonsecret configuration; it never imports roots or credentials from an arm.
The operator explicitly delegates receipt inspection. The observer never
claims to be a live actor and never authenticates using fabricated runtime
metadata. Its mailbox transactions enforce SQLite read-only mode and cannot
send, acknowledge, reply, enroll, or modify the mailbox.

Write surface: a receipt-authority module, daemon wiring, focused tests,
README, parent plan, verification 0101, runbook and lane projection. No live
configuration is written; all acceptance uses synthetic temporary buses.

## Acceptance and non-goals

Without the explicit flag, cached receipt matches stay held. With a valid
independent grant, a fresh executable daemon can replay one receipt and
publish one durable no-dispatch firing across restart. Missing/malformed,
public/symlinked/oversized/copied-root configuration, wrong capability,
generation mismatch, and revoked grant must fail closed, including a runner
already holding cached evidence. Bodies and raw capabilities never appear
in output. Generic receipt delivery remains held as unqualified.

Actual agent suspension requires qualified exact-thread delivery and remains
a successor gate; registration or firing is not suspension acceptance. No
provider effect, live actor enrollment, service installation, release, or
new broad review allowance. This splits the configuration prerequisite from
the unqualified delivery gate rather than claiming both complete.

## Bounds and validation

Two implementation attempts, one targeted repair, 100 grants / 64 KiB config,
100 receipt replay rows. First red/green executable evidence within 30 minutes;
checkpoint after this packet. Focused tests, full Python suite, planning/diff
checks, and isolated installed executable proof. Inherit cumulative campaign
usage and earlier review limits. An unavailable goal meter does not reset them.

## Definition of done

The configured observer is locally qualified with exact source, revocation,
restart, read-only and no-dispatch evidence. PR publication/hosted integration
is a separate state. Full Plan 0101 and long-suspension delivery stay OPEN.

## Closeout

Transition: configuration absent -> locally accepted / awaiting hosted gate.
Progress classification: outcome_progress; executable production daemon wiring
now reconstructs exact receipt arms only with independently granted authority.
47 focused tests, 830 full tests, six installed tests; FD 5 -> 5 and children
0 -> 0. The next dependent packet is receipt arming and qualified suspension
delivery, preserving the current generic-dispatch hold until its own acceptance.
No inherited review allowance was reset and no subagent was launched.
