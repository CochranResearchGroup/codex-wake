# One formal review and one TDD remediation pass

Frozen range: ce1ad93eec437c1b4854dde2c9a174d5c5f94255...545ec79c522f669300b5434f72c68dc867479c8d. Both independent axes completed before primary adjudication. Review invocation1; remediation pass1 completed. No second review is planned.

## Standards

Accepted nonblocking P3: duplicated allocation/session accounting persistence in request_admission.py constructor and bind_listener; only construction validates private allocation ownership/mode. Verified against both hunks. Consolidate in the supervision owner, consistently qualify the state. Baseline Duplicated Code/Feature Envy judgment supported by architecture policy0014; no mandatory standards breach found.

## Spec

Accepted blocking P1: hard preflight returns gateway readiness after static host qualification failure; execute does not gate provider submission on current activation delivery. Verified inspect_host hard branch and bind_listener/execute. This violates preflight/activation requirements. Reopen353/354 until public-path regression passes. Actual rendering remains a separately qualified native/TUI fact, never inferred from a notice read.

Accepted blocking P2: execute starts the resource timer even when sync reports inactive; verified HTTPConnection and Timer both retain self.timeout. This violates deactivation semantics for requests dispatched after disable. Reopen352/354. Already-issued requests are a separate truthful boundary.

## TDD seams

- Public gateway execute/HTTP submission with native notice capability removed: catches unannounced hard-governed paid dispatch, not physical screen rendering.
- Public gateway HTTP response after durable operator deactivation and provider completion later than active timeout: catches stale timer/socket interventions; not an external provider qualification.
- Public bind_listener with an allocation made nonprivate: catches divergent persistent-state qualification; not filesystem atomicity against a hostile process.

Work vertically: one red regression, minimal green, then next finding. Exact commands/outcomes follow below.

Accepted findings: Standards1 P3; Spec2, highest P1.

## Red/green receipt

Runtime `/home/ecochran76/workspace.local/codex-wake/.venv/bin/python`, environment `PYTHONPATH=src:tests`, cwd integration worktree. Exact unittest commands:

- `python -m unittest test_governor_review_remediation.GovernorReviewTests.test_missing_current_activation_prevents_provider_submission`: red200 vs expected503 (`/tmp/governor-review-p1-red.log`), greenPASS (`/tmp/governor-review-p1-green.log`). A lost current native activation now withholds provider I/O and reports recovery controls.
- `python -m unittest test_governor_review_remediation.GovernorReviewTests.test_disabled_governor_allows_completion_after_its_former_timeout`: red502 vs expected200 (`/tmp/governor-review-p2-red.log`), greenPASS (`/tmp/governor-review-p2-green-final.log`). The first green attempt had an indentation error, retained at `/tmp/governor-review-p2-green.log`; it was corrected, not counted as a pass. The final regression waits for actual provider arrival before crossing the former timeout.
- `python -m unittest test_governor_review_remediation.GovernorReviewTests.test_listener_refuses_nonprivate_shared_accounting_state`: qualified redfailed-to-raise (`/tmp/governor-review-p3-red-qualified-final.log`), followed by three-regression greenPASS (`/tmp/governor-review-all-green.log`). Earlier fixture setup errors are retained in `/tmp/governor-review-p3-red*.log`; they were not defect detections. Qualified red temporarily restored only the old listener write block, then the owner helper was reinstated. Both constructor and listener now use supervision-owned persistence with the same private-state validation.

Affected selection `python -m unittest test_governor_review_remediation test_request_admission test_completion_reserve test_host_preflight test_governor_deactivation test_governor_visibility`:17PASS19.520s. The explicit selection is not the full suite. Pinned Ruff undefined-name checks and diff whitespace check PASS.

Actual native completion/control driver rerun: `PYTHONPATH=src python scripts/request_admission_native_acceptance.py --app-server /home/ecochran76/.local/share/codex-wake/native/345-b0ce988429/bin/codex-app-server --frontend /home/ecochran76/.codex/packages/standalone/releases/0.164.0-x86_64-unknown-linux-musl/bin/codex --output /tmp/governor-review-native-final --completion` PASS. Receipt `/tmp/governor-review-native-final/receipt.json`: activation rendered before guarded send, numeric limits visible, four guarded requests, implementation denial never forwarded, completion protected, original deadline/cap/history preserved, typed deactivation at zero with0external inference, final owned PID census empty. Funding fixture names remain separate from the actual formal review/TDD recorded here.

Full CI at pre-remediation da2f848: run40243924355 PASS3.11/3.12. Final-source successor CI remains required. No deployment or production-control changes. One formal review, one TDD remediation pass; all accepted findings addressed, no rejected or needs-evidence candidates remain.

Source-bound final presubmit runner PASS: `/tmp/governor-final-validation-receipt.json`, manifest `/tmp/governor-final-manifest.json`. Required axes: pinned Ruff, policy wiring and17 affected public-seam cases. This receipt binds the exact dirty candidate, runtime and inherited environment; logs remain outside Git. Final three review regressions separately3PASS3.546s.

Final fullCI run40244973786 at0a76bdf failed exactly one existing public spawn regression on each Python version:1723tests,1failure,1skip. The new static qualification guard changed the established reason from hard_admission_unsupported to hard_host_notice_unqualified. Integration correction preserves the existing public reason and exposes qualification_failure=host_notice_unqualified separately. Full failed log retained `/tmp/governor-final-ci-failed.log`; this is the same reviewed P1 fix, not a second review/TDD invocation. Dispatch remains blocked before effects. Successor CI required.
