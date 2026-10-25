# Seven-feature source review and bounded remediation

Fixed point: ff5911775eb54965454e664556fc96d53c5d3584.
Frozen head: fe5e8b61330e088ba21f24f06867ab624516995e.
Command: `git diff ff5911775eb54965454e664556fc96d53c5d3584...fe5e8b61330e088ba21f24f06867ab624516995e`.
Twenty commits,52 files,6035 additions and11 deletions; nonempty diff verified.
Specs: hf-05/08/14/16/18/21/27-spec.md and original numbered tickets.
Standards: AGENTS.md, relevant policies0001/0003/0004/0005/0006/0014/0016/0017/0021,
pyproject.toml and the full Fowler smell baseline supplied independently.
No CONTRIBUTING.md or CODING_STANDARDS.md exists. Reviewers were read-only,
independent /root/final_standards and /root/final_spec; no nested delegation.

## Standards

S1, `nonblocking_backlog`: possible Duplicated Code in private atomic publication
in guarded_interactions.py, tab_organization.py and background_jobs.py. Primary
confirmed the repeated flush/fsync/replace/directory-fsync shape. Validation/size
and ownership differences are real. This is a heuristic maintenance opportunity,
not an evidenced documented-standard violation. Defer extraction to a separately
specified retained-behavior change; no broad refactor in this repair pass.
No blocking standards candidate was reported or accepted.

## Spec

F1, `blocking`, P1, HF08/#335: work_acceptance.evaluate rechecked permission per
verifier but pin/artifacts only before the loop, and omitted final pin revalidation.
Confirmed against hf-08-spec.md requirements to validate before each effect and
invalidate evidence if scope changes during verification. A real approved verifier
changing an artifact or removing the task-brief directory allowed a later marker
command to execute; pin loss in the final verifier could publish acceptance.
Repair: exact pin and artifact snapshot before each verifier, stop with unknown on
change, and revalidate pin with final snapshot before receipt publication.

F2, `blocking`, P2, HF08/#335: missing frozen verifier executable raised outside
the infrastructure exception boundary, losing the typed unknown evaluation receipt.
Confirmed by deleting an approved executable after a successful evaluation.
Repair: executable hashing belongs inside the same infrastructure failure boundary
as process startup. Public inspection retains the new unknown original receipt.

Both findings reopen #335 until repaired source passes. No unverified candidate
is treated as a finding. No second broad review was run.

## One TDD remediation pass

Stable seam: WorkAcceptance.define/evaluate/inspect with real task approval,
real resource claim and real bounded verifier processes. It proves invalidation,
no later effect under stale scope, and typed retained results; it does not claim
hostile same-UID isolation or daemonizing verifier support.

Cycle1 red: `PYTHONPATH=src:tests <qualified3.12>/python -m unittest test_work_acceptance.WorkAcceptanceTests.test_verifier_scope_changes_stop_later_effects_and_invalidate_publication`.
Red receipt /tmp/frontier-remediation-red1-corrected.log; green same command
/tmp/frontier-remediation-green1.log. Initial test cleanup error retained separately
in /tmp/frontier-remediation-red1.log; corrected before product change.
Cycle2 red: same invocation with test_missing_frozen_executable_retains_unknown_receipt,
/tmp/frontier-remediation-red2.log. Green selection test_work_acceptance plus
real attention/job-await callers, /tmp/frontier-remediation-green312.log and311.log.
An initial test asserted a nonexistent receipts-list field; corrected to the public
original_receipt field; this was test repair, not a concealed product failure.

Summary: Standards1 accepted nonblocking heuristic (highest maintenance opportunity);
Spec2 accepted blocking defects (highest P1), both addressed in the single TDD pass.

The first3.11 combined13-test run hit owner_unqualified during the multi-effect
regression; its original claimant timestamp was reused. Retained first result in
/tmp/frontier-remediation-green311.log. The isolated diagnostic passed and the
same combined selection passed13/5.243s on diagnostic repeat. Do not erase or
label that first result clean. The regression now obtains a fresh observed_at
before each evaluation, matching the actual caller's fresh-observation contract;
final focused validation is recorded separately. This is bounded fixture timing
correction, without weakening the production30-second qualification fence.
