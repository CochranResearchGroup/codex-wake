# LOCAL-P213 | Formatting throughput and STALE regression

State: OPEN
Ticket: LOCAL-P213
Owner: primary
Priority: P1
Branch: fix/tab-format-performance
Dependencies: none
WIP limit: one

## Problem and bounded outcome

Operator rejected colors and sluggish updates with widespread STALE labels on
42tabs. Production formatting rolled back; original effective values for42windows
verified, monitor stopped. Diagnose and reduce native option roundtrip overhead;
preserve inherited/explicit baseline, linked-window holds and manual style policy.
Do not reenable production formatting or change the palette without preview.

## Acceptance

A private42window public controller enable/rollback must complete without partial
results and fewer than500tmux process launches (old1728). Multiline literal option
values and exact rollback remain intact. Existing formatting/linked/manual/expiry
checks pass. Record wall-clock timings separately from deterministic processbudget.
No model/provider work, global theme edit or production formatting activation.

## Feedback and predictions

Original private42window loop succeeds unloaded but costs6.907s enable/2.903rollback;
onewindow0.374/0.158s. Native process budget assertion red at1728launches. Ranked
predictions: native per-option spawn cost dominates; repeated statewrites contribute;
20second TTL expires under cycle delays. Change only native batching first.

## Current state

Source throughput fix validated:1728→275 nativeprocesses;42window formattingbudget
red3.859s→green1.143s after consolidating durable saves with original baselines
persisted before writes.25focused3.12checks and3focused3.11checks pass. See
plan0213/diagnosis.md. No production deployment/reactivation. Remains OPEN for
installed loaded-host observation qualification and user-visible palette/plain
preview. Memory forbidden: no explicit memory-write request. Prior current runtime
receipts sufficient; Graphiti historical lookup skipped for this bounded incident.
