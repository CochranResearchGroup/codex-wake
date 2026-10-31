# Diagnostic authority scope reconciliation (#425)

State: CLOSED
Owner: #425 diagnostic lane. Branch: fix/425-diagnostic-scope. Target: main.
Base: 5fcf2d65052c3316f84d821c6ff1d233e6746187. Governing specification: #420.

## Current State

The bounded source reconciliation is complete: accepted diagnostic behavior and
portable guidance are committed and source-validated. Canonical PR integration and
ticket closure remain with the #420 owner. Live native, installed-runtime and
working-account acceptance are separate gates and remain outside this closed scope.

## Scope and acceptance

Carry forward the parked diagnostic input's missing public CLI/MCP explanations
and portable skill guidance. A supervision refusal must retain its held admission
and distinguish independent manual-work authority, without granting, revoking or
renewing resources. Ambiguous native turns remain refused, with preserved history.
Governor control ownership, configured grants, accounting and stop latches remain
unchanged. Deployment, governor/service/session changes and account experiments
are excluded. Source validation is separate from installed/runtime acceptance.

The public seam is CLI diagnose plus native-context CommandRunner using the
existing isolated Unix-socket fixture; it checks reported authority and accidental
native mutation. The stdio MCP seam checks missing-grant guidance after the CLI
adapter. Neither seam proves live rendering or installed behavior.

## Input dispositions

- goal_readiness.py: accepted missing classification and explicit supervision-only
  authority notice/fields; existing engagement and effect ownership unchanged.
- goal_limits_cli.py: accepted retention of the shared notice when missing-grant
  guidance replaces next_action.
- test_goal_engagement.py and test_goal_limits_mcp.py: accepted public regressions.
- docs/governor-control.md: accepted pointer to packaged reference; existing
  control contract moved byte-for-byte into the new skill reference.
- skills/codex-wake/references/existing-goal-limits.md: accepted package-local link
  and scoped diagnostic guidance.
- untracked skills reference governor-control.md: accepted unchanged contract.
- historical untracked plan0179: preserved in #420 private custody, superseded for
  execution by this curated record. Historical installed-reference changes and
  separate native attachment observations are not current acceptance claims.

Original dirty checkout remains read-only and retained for the #420 owner's
custody/retirement verification. Private snapshots and logs remain outside Git.

## Local validation

The commands below use Python3.12 installed403 with candidate src:tests,
fresh HOME/XDG_CONFIG_HOME/XDG_STATE_HOME/CODEX_HOME, inherited CODEX_* cleared,
and CODEX_WAKE_STABLE_TIME_CONFIG empty. Native RPCs are fixtures.

- `python -m unittest test_goal_engagement.GoalEngagementTests.test_ambiguous_diagnosis_holds_supervision_without_deciding_manual_authority`:
  RED expected native_turn_ambiguous, observed setup_unavailable; GREEN 1 test.
- `python -m unittest test_goal_limits_mcp.GoalLimitsMCPTests.test_fractional_checkpoint_reserve_reaches_host_admission_without_a_grant`:
  RED missing manual-work notice after CLI override; GREEN 1 test.
- `python -m unittest test_goal_engagement test_goal_limits_mcp test_governor_deactivation test_governor_visibility test_governor_review_remediation test_goal_supervision`:
  PASS 54 tests, 14.571 seconds.
- `python -m compileall -q src tests .codex/hooks`: PASS.
- `ruff check --select F821,F822,F823 src scripts tests .codex/hooks`: PASS;
  available Ruff0.15.8 differs from hosted pin0.14.2.
- `python scripts/check_policy_wiring.py`: PASS.
- `git diff --check`: PASS.
- Copied complete skill to a temporary standalone folder; governor-control link
  resolved without repository docs: PASS.

Retained setup failures: default Python lacked websockets before behavioral red;
first focused selection named nonexistent test_goal_governance (44 real tests
passed), corrected selection above passed. No product repair inferred from these.
Hosted CI skipped under operator cost policy. Focused local checks cover the
changed public paths; no full-suite, live native, Windows or installed claim.

Definition of done for this lane is committed, source-validated accepted behavior
with per-input dispositions; #420 owns PR integration, shared trackers and final
protected-runtime readback. No activation or service mutation is part of this lane.
