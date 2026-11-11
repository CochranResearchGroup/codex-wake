# Plan0218 | One broad review and one TDD remediation

Frozen base: b6e93c2dada4eae08a869d569b5036defd2eaf39.
Frozen tip: 9c63b23d (all four child tickets closed before review).
Diff: `git diff b6e93c2dada4eae08a869d569b5036defd2eaf39...HEAD` at that tip.
Commits: f162b8fa,2ee87e63,8f87a6d8,17a73faa,54d3b0e5,1c72de30,9c63b23d.
Standards sources: AGENTS, runtime-proof, code-discovery, GLOSSARY and applicable
engineering/runtime/validation/testing policies. No CODING_STANDARDS or
CONTRIBUTING document was present. Spec source: frozen spec0218 / issue558 and
child issues559–562. No spec-source omission.

## Standards

Reviewer `/root/standards_review218` found no confirmed hard documented-standard
violation and one P2 ownership-hardening candidate. Copied async contexts retain
ContextVars: a second thread could be mistaken for the lease-owning thread and
bypass the OS lock in public poll_once. No current production carrying path was
established. Primary independently reproduced the public-interface exclusion
failure and adjudicated it `blocking` for the supported ownership contract.
Minimal correction binds the reentrant shortcut to both PID and thread identity.
No additional smell findings were accepted.

## Spec

Reviewer `/root/spec_review218` found one P1 candidate: a root changed to a
self-referencing symlink raises during coordinator path resolution before healthy
roots are admitted. This breaks stories6/8, root isolation and visible failure.
Primary reproduced it and adjudicated it `blocking`. Minimal correction reports
a rate-limited root-local setup failure and continues healthy-root admission.
No scope-creep finding was accepted.

## One bounded TDD remediation pass

One public regression at a time, observed red before changing implementation:

- `python -m unittest discover -s tests -p test_supervisor_scheduling.py -k invalid_root_path -q`:
  RED RuntimeError from the enrolled symlink loop; GREEN1 after containment.
- `python -m unittest discover -s tests -p test_monitor_ownership.py -k async_thread -q`:
  RED expected monitor_owned but got None; GREEN1 after thread-aware custody.

Use the declared Python3.12 check-env interpreter and PYTHONPATH=src. Exact red,
green and subsequent focused results are retained outside Git under
`~/.local/state/codex-wake/qualification/plan0218/remediation-*.log`.
The comprehensive run exposed a stale generated command-coverage artifact for
new supervisor.reconcile. Existing contract test was reproduced RED, the generator
refreshed one coverage entry, and all3 contract tests passed. This is validation
remediation within the same bounded pass, not a second review axis.

There is no second broad review or unrelated refactoring pass. Final verification
and installed-package qualification are recorded in the plan acceptance receipt.

Summary: Standards1 accepted P2 and Spec1 accepted P1; both corrected in the one
bounded pass, resolved; final focused61 tests pass on both Python3.12 and3.11, and the
corrected immutable installed wheel passes9 migration/recovery checks.
