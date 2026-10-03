# Webhook CI fixture diagnosis

State: CLOSED
Lane: P63
Owner: primary
Parent: Plan 0101 / issue #181; PR #188
Branch: feat/p63-receipt-restore
Target: origin/main
Integration: squash_pr

## Current State

Diagnose the two Python 3.12 failures in run 37148747612, job 111277982216.
Baseline 8dd07138661ca8b9b8e5ce913ce73ec5074a7a7c is unchanged. Preserve
the untracked fresh-agent handoff. The full post-reboot Python suite passed
824 tests in 34.167s; 100 ordinary focused iterations also passed. Neither
result erases the hosted failures.

The primary owns one serialized diagnostic/repair unit: two existing webhook
test modules and this plan plus verification 0100. No production runtime,
service, provider, installed identity, or integration change is authorized
by this diagnostic packet. Existing review allowances are inherited.

The local diagnostic/repair packet is now accepted. Verification 0100 records
exact red-before/green-after evidence, 29 focused tests and 824 full Python
tests. Hosted CI and integration remain unaccepted.

## Feedback loop and bounds

Ordinary reproduction: at most 100 paired iterations / 50 seconds, complete.
Controlled reproduction: at most three repeats per scheduling perturbation.
Delay the actual client half-close until a response is readable; separately
delay durable ingest by 300 ms. Both produced the exact hosted symptoms 3/3.
Remove each perturbation for the control. One implementation attempt and one
targeted repair, with focused checks and one full local suite on the final edit.
Checkpoint at the repair result; no automatic hosted rerun or merge.

## Acceptance and non-goals

Retain exact 503 ADMISSION, complete HTTP framing, one ingest and no queued
request. Ignore only ENOTCONN at the fixture half-close seam. Retain actual
main-thread POSIX deadline expiration, same-runtime recovery, fresh timers,
and reopened durable checkpoint proof. A slower successful journal must fit
inside a deliberately separate fixture margin; never narrow the production
deadline to provider work alone.

Existing regression assertions must go red before repair and green afterward.
Record causal probes and their limits in verification 0100. Production behavior
and deadline defaults stay unchanged. Hosted flake disposition, PR review,
integration, and full Plan 0101 acceptance remain separate gates.

## Definition of done

Bounded repair is locally accepted when both controlled reproductions pass,
focused modules and full Python suite pass, and original hosted failure
provenance and remaining hosted gates are explicitly retained.

## Closeout

Transition: active -> locally accepted / awaiting hosted gate.
Progress classification: blocker_reduction; both fixture sensitivities now
have reproduced causes and bounded regression coverage. Production behavior
was unchanged. Verification 0100 owns detailed evidence and original failures.
Next action: publish the coherent repaired checkpoint to PR #188 under its
existing integration workflow, then run hosted gates and the inherited review.
This packet performs no hosted rerun, publication, merge, or service effect.
