# Plan 0262 | Autonomous upgrade owner port

State: BLOCKED
Owner: primary / ecochran76
Work item: #737
Integration branch: feat/issue-737-upgrade-owner. Base: ec412b151f82b76a70bd993e488eacc7c1b602f3.
Historical accepted source: PR #454 at ef156ba466f83e7adb692be248379f857c1157fe.

## Current State

Port the accepted durable upgrade owner to current controller authorization, release and package contracts. Preserve existing build operations and StableTime authority. The GitHub spec and ticket acceptance criteria govern scope. Working-host deployment and historical job replay are out of scope.

| Ticket | Blocked by | Owner | State |
| --- | --- | --- | --- |
| #738 Durable upgrade lifecycle | None | primary | validated, tracker closed |
| #739 Repair and qualification | #738 | repair739 | integrated source, blocked on installed acceptance |
| #740 Future-launch selection and rollback | #739 | pending dispatch | pending |

The primary owns lifecycle, discovery, public adapters and shared job schema. Repair owns source preparation, repair and qualification. Promotion owns selection, rollback and outcome reconciliation. Integrate serially. The integration worktree protects the existing primary edits and can retire after validated custody.

Acceptance requires public controller regressions, CLI and MCP parity, local checks on Python 3.11 and 3.12, and exact-package launcher acceptance in the dedicated test environment. Run one Standards and Spec review with one focused remediation pass. Tracker closure requires the corresponding accepted evidence.

## Lifecycle validation

The integration commit containing this section passed 30 tests per runtime on Python 3.11.15 and 3.12.13 with `PYTHONPATH=src:tests python -m unittest test_upgrade_jobs test_upgrade_discovery test_upgrade_storage test_upgrade_private_permissions test_controller_builds -q`. Ruff 0.14.2 passed `python -m ruff check --select F821,F822,F823 src tests`. Checks ran in isolated local environments with declared dev and MCP dependencies, without hosted Actions. These are source and public interface checks. Exact-package deployment acceptance belongs to the dependent slices.

Ticket #738 source and remote custody: `f660a4224141abe2f1c1269f0e4831bd4498b5cd`. The tracker readback confirmed CLOSED. Additional checks on that source passed 40 tests on each runtime with `PYTHONPATH=src:tests python -m unittest test_controller_build_authorization test_controller_portable_client test_release_driver test_release_build test_release_qualification test_upgrade_qualification test_measurements -q`.

Ticket #739 worker `/root/repair739` started from the validated #738 SHA. Its result and installed acceptance remain pending.

## Repair and qualification checkpoint

Worker base `f660a4224141abe2f1c1269f0e4831bd4498b5cd`, worker result `58ba21fdc133714d5b8402d80daf9778e911ce2d`, integration `b6f312a9dfa1d7efc71e853c0c99bde24fe19d69`. The worker checkout was removed after an exact remote readback and disposable cache cleanup. The current integration source passed 84 tests on each runtime with `PYTHONPATH=src:tests python -m unittest discover -s tests -p 'test_upgrade_*.py' -q`. Pinned Ruff passed with `python -m ruff check --select F821,F822,F823 src scripts tests .codex/hooks`. An earlier integration checkpoint built the sdist and wheel successfully using `python scripts/validation_build.py --outdir <private-output>`.

The presubmit planning audit reports the same three state metadata errors on the base and branch (plans 0259, 0260 and 0261). The 237-test controller selection had two failures. The controller-default test reproduces on the base. The Native MCP execution-state test passed unchanged in focused runs on both base and branch and remains an intermittent broader-suite failure. The full presubmit is unqualified.

Installed acceptance remains blocked. The dedicated UID1017 test user has a StableTime configuration and prior package assets but no existing upgrade policy binding a fresh sealed staged job to designated A/B identities. Disposable wsl-test has the historical package, policy and old stage receipt, with no dedicated StableTime client found. It returned to its original stopped state. The historical job was not replayed. Resume at #739 when a dedicated client and approved test identities are available. #740 and the single broad review and remediation pass remain pending.
