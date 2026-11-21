# Plan 0262 | Autonomous upgrade owner port

State: OPEN. Owner: primary / ecochran76. Work item: #737.
Integration branch: feat/issue-737-upgrade-owner. Base: ec412b151f82b76a70bd993e488eacc7c1b602f3.
Historical accepted source: PR #454 at ef156ba466f83e7adb692be248379f857c1157fe.

Port the accepted durable upgrade owner to current controller authorization, release and package contracts. Preserve existing build operations and StableTime authority. The GitHub spec and ticket acceptance criteria govern scope. Working-host deployment and historical job replay are out of scope.

| Ticket | Blocked by | Owner | State |
| --- | --- | --- | --- |
| #738 Durable upgrade lifecycle | None | primary | validated, tracker closed |
| #739 Repair and qualification | #738 | repair739 | running |
| #740 Future-launch selection and rollback | #739 | pending dispatch | pending |

The primary owns lifecycle, discovery, public adapters and shared job schema. Repair owns source preparation, repair and qualification. Promotion owns selection, rollback and outcome reconciliation. Integrate serially. The integration worktree protects the existing primary edits and can retire after validated custody.

Acceptance requires public controller regressions, CLI and MCP parity, local checks on Python 3.11 and 3.12, and exact-package launcher acceptance in the dedicated test environment. Run one Standards and Spec review with one focused remediation pass. Tracker closure requires the corresponding accepted evidence.

## Lifecycle validation

The integration commit containing this section passed 30 tests per runtime on Python 3.11.15 and 3.12.13 with `PYTHONPATH=src:tests python -m unittest test_upgrade_jobs test_upgrade_discovery test_upgrade_storage test_upgrade_private_permissions test_controller_builds -q`. Ruff 0.14.2 passed `python -m ruff check --select F821,F822,F823 src tests`. Checks ran in isolated local environments with declared dev and MCP dependencies, without hosted Actions. These are source and public interface checks. Exact-package deployment acceptance belongs to the dependent slices.

Ticket #738 source and remote custody: `f660a4224141abe2f1c1269f0e4831bd4498b5cd`. The tracker readback confirmed CLOSED. Additional checks on that source passed 40 tests on each runtime with `PYTHONPATH=src:tests python -m unittest test_controller_build_authorization test_controller_portable_client test_release_driver test_release_build test_release_qualification test_upgrade_qualification test_measurements -q`.

Ticket #739 worker `/root/repair739` started from the validated #738 SHA. Its result and installed acceptance remain pending.
