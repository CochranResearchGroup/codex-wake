# Prevention439 review and bounded remediation

Base:5df7c811b4cd9b95a06d3ac4f6f92e84e3ec4f65. Reviewed head:204680c76254a2398ddce3211549c9dad341fb61, canonical PR445. Tickets440–443 were closed after integrated acceptance, before the single independent two-axis review. Primary adjudicated the two reports as one shared P2 blocker, not two distinct defects. No second broad review.

## Standards

Accepted P2: cleanup plans/results used default-mode exclusive creation, inheriting0644 under ordinary022 umask. Developer guidance requires private raw receipts; a0700 parent mitigates the exposure but is not guaranteed for every permitted output. No consequential baseline smell or other standard finding accepted.

## Spec

Accepted same P2: spec439 requires full receipts remain private. Both cleanup creation paths failed to enforce this themselves. Independent disposable public planning probes reproduced0644. Owner-only exclusive0600 creation now covers plan and result, retaining first-result preservation.

## One bounded TDD pass

Stable seam: actual cleanup plan/apply subprocesses against disposable Git worktrees, with the existing OS-census fixture substitution. The new test sets ordinary022 umask and observes actual plan/result file modes. Red test_plan_and_result_are_private_under_permissive_umask failed420!=384 (0644!=0600). Green uses one shared exclusive private-file creator; no real retained checkout was removed.

Exact red command: PYTHONPATH=src:tests <qualified-python312> -m unittest test_cleanup_worktrees.CleanupWorktreeTests.test_plan_and_result_are_private_under_permissive_umask -v. Private red log preserves the failure; its outer shell also ran tail, whose successful exit is not claimed as test acceptance. Final green command: PYTHONPATH=src:tests <qualified-python> -m unittest test_cleanup_worktrees test_summarize_receipt test_local_validation test_validate_candidate -q. Python3.12:22PASS39.641s. Python3.11:22PASS32.092s.

## Integrated acceptance and scope

Before the bounded privacy delta, exact source14b90c9 passed ten source-bound presubmit checks on Python3.12.13, pinnedRuff0.14.2, build1.6.1; source was clean and unchanged. Python3.11 combined public selection21PASS21.251s. Retained disposable three-case acceptance preserves denied HELD planning, actual successful plan/result/custody/peer outcomes, malformed planning first failure and corrected new receipt. Actual validation/cleanup summary outputs1087–2722bytes preserve original input. Profiles now include cleanup and summary public regressions. The comprehensive lane is documented, not claimed executed.

First failures remain private: census test injection initially read reset argv and was corrected before acceptance; initial packaging failed missing setup dependency and led to a public setup-tier regression; a silent-denial mutation was detected. Local timeout default600 reflects the previously observed350.623-second full suite rather than pretending300 was sufficient. Check setup installs nothing into the working environment.

Local presubmit evidence replaces hosted Actions. No provider/native/installed-wheel/live/plugin acceptance or production deployment is claimed. No actual historical checkout retirement, native publication, daemon installation, privilege expansion, service/process termination or governor activation occurred. Operator reference reviews and fresh process visibility are separate; a cooperative cleanup lock does not eliminate process-start races. All worker checkouts are intentionally retained as source/evidence anchors; future cleanup needs separate authorization and complete evidence.

Standards:1 accepted P2 resolved. Spec:1 accepted P2 resolved, same unique finding. Review1/1 and bounded remediation1/1; final source-bound verification and canonical ref readback govern completion.
