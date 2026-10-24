# One review and one bounded TDD remediation pass

State: REMEDIATED; final integration/check authority is PR326
Fixed point: f96f4c8244529e8b4e8e4206202d4a1e91084a52
Reviewed tip: bf911469e0de5492e86c12ce260cd1739e62770a
Review began after verified closure of #315, #316 and #317.

## Standards

Reviewer: /root/review_standards. Primary accepted two blocking candidates:

1. P1: native caller identity/task delegation was sufficient to manufacture
   owner completion, violating runtime-governance completion provenance. The
   public MCP reproduction accepted active-turn metadata without a terminal
   runtime or operator event. Fixed: MCP reconciles the exact previously recorded
   operator completion; caller identity cannot mint terminal evidence. Explicit
   operator CLI completion remains supported. Automatic completion evidence is
   not fabricated from idle state or an approved task brief.
2. P2: completion swept matching schema8 records without classifying them and
   could cancel an unknown base version or rewrite an unknown policy version.
   Fixed: classify the locked current record and preserve held raw bytes.

No smell-only candidate was accepted. No source edits were delegated to reviewers.

## Spec

Reviewer: /root/review_spec. One candidate duplicates Standards2: unknown-version
records must hold without rewriting. Primary accepted it as a blocking normative
compatibility/provenance violation, even though that axis did not demonstrate
unauthorized delivery. No other implementation/spec divergence was confirmed.

## Single TDD pass

Stable seams: public CommandRunner.call for owner completion; public CLI
owner-complete for unknown-version preservation. Disposable roots; no provider,
model, installed production or global policy effects.

Cycle1 red: `.venv/bin/python -m unittest discover -s tests -p
 test_harness_callers.py -q` failed because active caller metadata returned
completed. Minimal fix separated explicit operator evidence from MCP identity;
green6 tests. The test also proves exact operator-event reconciliation succeeds.

Cycle2 red: `.venv/bin/python -m unittest discover -s tests -p
 test_wake_policy.py -q` failed both unknown-base and unknown-policy byte-preservation
cases. Minimal fix skips classified holds under the wake lock; green8 tests.

Both commands pass on Python3.11 and3.12. Native-intent recovery18 passes;
undefined-name and whitespace checks pass. No additional broad review is run.
Only accepted findings and critical regression/CI gates are verified afterward.

The installed CI smoke exposed a second historical32-tool assertion in wake-control
qualification. It is updated, like the A2A installed smoke, to require named
capabilities and unique tool names instead of an obsolete tool count.

Summary: Standards2 accepted (highest P1), Spec1 accepted duplicate (P2);
all accepted blockers remediated in one bounded TDD pass.
