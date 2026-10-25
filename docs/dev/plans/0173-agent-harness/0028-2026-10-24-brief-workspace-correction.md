# Exact revision workspace authorization

State: OPEN
Owner: ecochran76 / primary implementation agent
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/328
Branch: fix/328-brief-workspace
Base: 37a5cbb
Target: origin/main
Dependencies: None

## Current State

Issue filed and read back. MCP regression reproduced cross-workspace admission
before the fix. Shared store now checks the host-verified workspace against the
selected or pinned revision while holding the task transaction. Inspection
fails closed when any returned revision is outside that workspace. Source
validation completed at the focused seams; draft PR #329 awaits CI and
integration. Release remains separate.

## Scope and non-goals

CLI and MCP worker authority carries the verified workspace to the shared owner.
Cover new admission, explicit selection, original-pin retries, pin retrieval,
inspection and proposal. Operators and scoped controllers retain existing
rights. No persisted schema changes, launches, permission grants, releases or
unrelated refactoring. Issue 328 owns outcome and acceptance.

## Seams and evidence

- Public MCP CommandRunner.call: catches native workspace authorization and
  latest/explicit selection, inspection and pin/retry access. Native workspace
  evidence is injected; this does not prove a live app-server connection.
- Public CLI task_briefs_command: catches selected/pinned revision authority,
  denied inspection and same-workspace success. Host authority is injected;
  existing capability authentication remains covered by existing tests.
- Existing task-brief store/lifecycle/handoff suites protect continuity and
  operator/controller compatibility. No live provider calls.

Red: PYTHONPATH=src python -m unittest discover -s tests -p test_harness_callers.py
failed before implementation with revision 2 admitted by caller in workspace A.
Green: same command passed 7 tests. Additional CLI regression was checked against
a disposable baseline source copy carrying only the additive authority field:
latest/explicit admissions, inspection and foreign pin all failed expectations.
That counterfactual check supplements the initial red; it is not another
pre-implementation cycle.

Focused: PYTHONPATH=src python -m unittest discover -s tests -p 'test_task_brief*.py'
passed 14 tests on Python 3.11 and 3.12. Harness caller selection passed 7 on both.
Undefined-name check and git diff --check passed. Broader handoff selection ran 62 tests with two preflight readiness failures;
both passed on isolated retry and on the unchanged baseline. Preserve these as
flaky results, not a clean broader pass. Spawn selection passed 27 tests. The
initial test_agent_lifecycle filename selection matched no tests and is not
counted as evidence. Required CI runs separately on PR #329.

Delivery: https://github.com/CochranResearchGroup/codex-wake/pull/329
Implementation checkpoint: 75789bd (remote readback matched). No integration
or release claim. First-failure logs retained in user-scoped issue-328 evidence.

## Definition of done

Issue acceptance proved at the named seams, source committed on its isolated
branch and published for integration review. The issue remains open until the
intended integration target contains the validated change. Production install
and provider behavior are not claimed.
