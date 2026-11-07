# Native release driver design

State: OPEN
Work items: GitHub #480, #481, #482, #483, #484, #485
Authority: operator-approved interview decisions in the current conversation.

## Current State

Operator selected ticket publication and implementation after accepting all
design decisions. Implementation is now authorized; deployment remains separate. Existing account-build
workflow Plan0179 and its staging module remain authoritative for current behavior.
Plan0203 and the private native-modern-0167 receipts supply the initial acceptance
inputs. The efficient-cargo-builds skill supplies the build execution guidance.

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

Design a resumable release workflow over existing staging and native packaging
tools. No implementation, installation, service interruption, source integration,
paid hosted CI or publication is authorized by this interview artifact alone.
Existing session authorization and repository policies still govern those actions.

## Confirmation gate

All twelve interview recommendations were accepted; the operator then explicitly
authorized ticket publication and implementation. No additional
product decisions are pending; implementation details should follow the existing
command registry, staging module, Cargo Signal schemas and repository policies.
Exact command spelling is provisional until checked against the existing tree.

## Acceptance criteria and definition of done

Design is complete when the operator confirms a shared understanding covering
the full decision frontier. Record a buildable specification and implementation
work items in the subsequent explicitly selected flow. Implementation acceptance
must demonstrate complete package identity, no duplicate ambiguous jobs, selective
stage reuse and exact-artifact disposable qualification without working-host
installation. Claims of binary reproducibility require separate measured evidence.

## Evidence

- Existing staging: src/codex_profiles/upgrades.py, especially stage and _commands.
- Existing scope: docs/dev/plans/0179-account-build-workflow/spec.md.
- Prior release: docs/dev/plans/0203-2026-11-06-native-0167.md.
- Retrospective: user-scoped native-modern-0167/retro-20261106/report.md.

Memory disposition: forbidden for this closeout; no explicit memory-write request.
This plan remains the canonical working state.
