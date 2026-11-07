# Native release driver design

State: CLOSED
Work items: GitHub #480, #481, #482, #483, #484, #485
Authority: operator-approved interview decisions in the current conversation.

## Current State

Six tickets (#480–#485) are implemented, integrated, validated and tracker-closed.
Integration branch: feat/native-release-driver-0204; last code commit7f87ac4.
One Standards/Spec review and one bounded TDD pass resolved four distinct blockers.
28 release,19 MCP and191 controller tests passed. Actual PowerShell/WSL/REST/MCP
and real UID1017 native acceptance passed using the verified retained0.167 package.
Source was subsequently merged through PR486 as5fd4aeb and deployed to the
versioned Wake prefix recorded in deployment.json. No native recompilation or
working-account daemon restart occurred. Broad-suite/Python3.11
coverage is not claimed; the validation receipt retains the harness timeout and
baseline diagnosis. Worker branches/worktrees retain recoverable custody.

Acceptance: [native/public receipt](../evidence/plan0204/acceptance.json).
Final checks: [validation](../evidence/plan0204/validation.json).
Deployment/rollback: [receipt](../evidence/plan0204/deployment.json).
Review: [one-pass adjudication](../evidence/plan0204/review.md).
Execution custody: [ledger](0204-execution-ledger.json).

## Settled decisions

- First slice targets Codex mod builds; this is not a generic build framework.
- Extend the existing build command tree with prepare, build, qualify, status and
  resume operations backed by the same implementation for CLI, API and MCP.
- Use Cargo Signal for bounded diagnostics and retained full logs.
- Demonstrate verified artifact reuse, interruption recovery and disposable runtime
  qualification with retained 0.167 inputs.
- Working-account installation remains a separate explicit action.
- Resume automatically invalidates affected stages when inputs change and reuses
  verified unaffected results. Reconcile uncertain worker outcomes before retrying.
- Select conservative parallelism from available memory and competing builds,
  allow explicit overrides and retain selected limits in the manifest. Serialize
  expensive stages sharing a build directory.
- Include explicitly requested cleanup with preview and inactive-target checks;
  normal builds preserve caches. Failed preflight prevents cleanup. Protect
  qualified packages and rollback artifacts.
- Prepare accepts pinned upstream and retained mod revisions, creates an isolated
  worktree and attempts integration. Conflicts retain a recoverable worktree and
  pause before building; existing working branches remain untouched.
- Prepare generates the manifest automatically. Durable private user storage
  holds manifests, logs and receipts; subsequent commands accept the run ID.
- Compact results are the default, with JSON, progress events and bounded
  diagnostics available consistently across CLI, API and MCP. Full logs stay on
  disk and are retrieved only when requested.
- Build execution initially runs in WSL. WSL and PowerShell clients can start,
  inspect and resume runs through the same service; native Windows compilation
  is outside the first slice.
- A build run operation orchestrates pinned source preparation, build and
  qualification, stopping at a qualified package. Individual stage operations
  remain available. Installation and cleanup require explicit requests.
- Acceptance includes changed-input invalidation, interrupted-job reconciliation,
  complete package inventory, output controls and cleanup refusal tests, plus
  real disposable 0.167 qualification. Reuse verified artifacts where possible
  and report which stages actually executed.

## Scope and non-goals

Implement a resumable release workflow over existing staging and native packaging
tools. The operator explicitly authorized tickets, implementation, delegated
workers, review and bounded remediation. The later operator instruction explicitly authorized main-branch merge and Wake
package deployment. Native package replacement, account-daemon restarts and paid
hosted CI remain outside this deployment.

## Confirmation gate

All twelve interview recommendations were accepted; the operator then explicitly
authorized ticket publication and implementation. No additional
product decisions are pending; implementation details should follow the existing
command registry, staging module, Cargo Signal schemas and repository policies.
Exact command spelling is provisional until checked against the existing tree.

## Acceptance criteria and definition of done

The six approved tickets meet their named acceptance conditions on the integration
branch and are closed with provider readback. Review and remediation ran once each;
all four accepted blockers have red/green regression evidence. Retained package
reuse, job reconciliation, selective rebuild, complete inventory, output controls,
cleanup refusal and exact-artifact disposable qualification are verified. This is
repeatable orchestration; bit-reproducible native binaries are not claimed.

## Evidence

- Existing staging: src/codex_profiles/upgrades.py, especially stage and _commands.
- Existing scope: docs/dev/plans/0179-account-build-workflow/spec.md.
- Prior release: docs/dev/plans/0203-2026-11-06-native-0167.md.
- Retrospective: user-scoped native-modern-0167/retro-20261106/report.md.

Memory disposition: forbidden for this closeout; no explicit memory-write request.
This plan remains the canonical working state.
