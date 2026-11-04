# Plan0200 single broad review

Frozen Wake tip: `85eeb7e720637c6ce1167020b11a8a67e5e20108` against
`171befbaf1be833f55eb0627c802e279cf0fbf35`; Bots tip
`763056b168db54a7a68b8d34b7595896e71cf384` against
`9ec0e7a5d8542d936f64b5409322c62393ebb694`.
One discovery pass; independent reviewer axes; no runtime/provider effects.

## Standards

No confirmed hard documented-standard violations. Candidate S1 is possible
Duplicated Code (judgement): direct CLI `local_control_commands.present` and
framed `local_control_client.output_frames` duplicate bounded polling, cursor
page draining, stop conditions and diagnostics. Primary verified their fallback
reasons differ for a known reasonless failed/cancelled turn: direct reports the
native outcome, framed reports output_incomplete.

Adjudication S1: **blocking for this bounded quality remediation**, priority P2.
This is an accepted architecture/diagnostic consistency improvement, not a hard
standards breach. Use one shared presentation loop, preserving transport writers.
Public-seam regression must prove a failed turn retains its cause across direct
and framed callers, with silent stdout and the same failure exit status.

## Spec

Independent review found no defensible missing requirements, scope creep or
incorrect implementation against the frozen spec and qualified harness contract.
No Spec candidates accepted. Headless Grok and its advertised unsupported exact
TUI health/cancellation/metering are qualified differences, not Codex exclusions.

## Remediation boundary

One bounded TDD pass for S1 only. Public silent-CLI native-failure test first
failed because framed diagnostics said output_incomplete, then passed after
moving bounded polling/page draining/diagnostics into one shared generator.
Direct and framed writers now consume that same generator. Focused critical
regressions passed33 tests on Python3.11 (66.769s) and3.12 (67.706s), including
actual Windows PowerShell fixture behavior. Ruff/generator/diff checks passed.
S1 is **resolved**. Final local CI passed:2052 unit tests plus one existing opt-in skip per Python
version,16 installed smoke commands per runtime and144 cached presentation cells.
One original intermittent PowerShell bootstrap failure remains unattributed;
successful continuation is not a source-fix claim. No second broad review
or additional provider intent is authorized by this remediation.

Exact red/green/critical-regression commands and log hashes are retained in
`~/.local/state/codex-wake/testing/plan0200/final-review/S1-remediation.json`.

Accepted findings: Standards1 (P2 judgement), Spec0 (none).
