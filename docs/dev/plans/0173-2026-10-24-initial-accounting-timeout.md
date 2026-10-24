# Plan0173 — Refuse initial scan timeout without a durable stop

State: CLOSED
Branch: fix/usage-scan-recovery
Target: main

## Current State

An initial delegated enrollment verified the original history, then its subsequent
allocation accounting scan exceeded the two-second bound. Enrollment persisted a
stop receipt and the controller paused the goal. A later observation qualified,
but the retained stop prevented continuation. The operator explicitly requested
repair; the exact singleton runtime was recovered under locks after qualified
nondecreasing accounting, same-boot time, current grants, fresh controller and
remaining-budget checks. Original caps, deadline, charges and first-stop evidence
were preserved. No renewal or additional allowance was created. Private repair
receipts remain outside Git. The installed controller subsequently reported armed,
qualified accounting and an active native goal.

## Scope

A first enrollment whose accounting fails specifically because of scan timeout
must refuse admission before publishing a caller stop receipt. Its allocated
boundary remains retryable with the original deadline. Existing enrolled
campaigns retain their accounting-loss winddown, stop latches and budget rules.
Other malformed or unqualified history is not reclassified as transient timeout.
No automatic stop recovery, counter reset, deadline extension or broader controller
upgrade belongs to this change.

## Evidence

Public enrollment regression failed before the fix: expected refusal was absent.
The fixed explicit-caller and delegated-allocation paths prove that a timeout
leaves no caller stop, then qualified enrollment succeeds with original charges
and deadline. Controller/accounting tests preserve established-campaign failures.
Runtime profiling of both installed versions currently completes in approximately
0.3 seconds; the original transient slowdown itself was not reproduced. The
confirmed defect is initial enrollment turning that failure into a durable stop.

Source acceptance and installed delivery are separate: this source patch is not
an installed MCP/controller upgrade. No shared client restart is needed to recover
the exact affected runtime. Merge/release status follows the associated PR.


## Delivery

Preventive fix merged through PR313 after both Python release gates passed.
Patch version0.20.1 prepares the user-requested local controller/MCP installation.
The source fix refuses initial timeout admission; it does not clear existing
stops or claim to repair unrelated native observation failures. Installed
readback, maintenance handover and client refresh remain independent gates.


Installed readback (2026-10-24): pinned0.20.1 from f59d3be526f76cbd1651f103f394388ec2dc68aa passed61 focused tests from the installed package. Supported maintenance handover reached `replaced`; controller process and all CLI entrypoints point to the new release. All five existing receipt authorities and stop latches were preserved, with nondecreasing counters. Existing shared MCP connections are a separate idle-only reload gate pending scope authorization; fresh stdio startup is verified separately. Deployment receipts and before/after runtime snapshots stay in the user-scoped operator-repair directory outside Git.
