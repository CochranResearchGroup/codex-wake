# PR549 / issue548 release qualification

Operator authorizes PR, squash merge, deployment and worktree cleanup. Final
implementation commit: `e6e5d2b7033988ec2ab9d11befb6f24fbc937c4a`, based on fetched
`origin/main=fa2363c24bf921ecf0bd8390739e96041e620e8f`. Release version0.22.0.dev3.
Only CLI presentation adapters, explicit machine consumers, completion install,
version/docs and the preexisting Plan0214 header repair are included. Root
config/GLOSSARY/Plan0216 work is excluded.

## Local validation

Python3.12.13 full discovery in isolated XDG config/state:
`PYTHONPATH=src uv run --no-project --with 'websockets>=17,<18' --with 'dbus-next>=0.2.3,<0.3' --with 'jsonschema>=4.26,<5' --with 'mcp>=2.2,<2.3' python -m unittest discover -s tests -p 'test_*.py' -q`.
Ran2338 in656.162s, one skip and one setup error: the ephemeral dependency-only
interpreter had no adjacent installed `codex-wake` launcher. This is retained as
a failed initial run, not described as a passing full-suite run.

The affected public test
`test_controller_builds.PublicBuildAdapterTests.test_protected_build_launch_is_durable_across_api_and_mcp_retries`
passed against the qualified installed wheel using
`PYTHONPATH=src:tests /tmp/codex-wake-p217-release-installed/bin/python -m unittest ... -q`.
All remaining full-discovery checks completed without a failure. No product code
or assertion was changed to address the setup error; full discovery was not
repeated after environment correction.

Private installed0.22.0.dev3 wheel:18 CLI/completion tests PASS11.675s.
Python3.11 isolated focused selection:37 tests PASS15.733s (`test_cli_presentation`,
`test_shell_completion`, `test_completion`, `test_controller_accounts`,
`test_controller_operations`, `test_command_workflows`). Undefined-name Ruff,
policy wiring, active planning audit and whitespace checks PASS. Prior focused
and corrective history remains in `validation.md`.

Hosted CI skipped under cost policy; GitHub reports zero workflow runs for source
head e6e5d2b7. Full Python3.11 suite and Windows execution were not reproduced.
The test interpreter is CPython3.12.13 on Linux; shared-kernel resource variation
is not a provider/native-daemon qualification. No native daemon build is part
of this Python CLI release.

## Review, rollback and custody

`/root/presentation_review` independently reviewed published PR549's frozen
base/head and plan. Standards: no remaining blocker. Spec: no remaining blocker;
SSH errors, nested history and explicit stream diagnostics remain corrected.
Primary reconciled scope and published source head. The later evidence commit
contains documentation only.

Synthetic nine-launcher upgrade/rollback qualified using the previous complete
release and new private complete wheel. Old default JSON, new readable accounts,
restored old JSON and completion install/upgrade/rollback PASS. This exercise
uses isolated state, no credentials, native lifecycle calls or provider actions.
Working rollout will verify source/wheel/installed hashes and require every
changed Python member to be a CLI adapter or the shared presenter; native owner
code/binaries stay unchanged. Existing HTTP controller reports a stale identity
before rollout; its process state will be preserved rather than restarted.

Cleanup archived six clean inactive checkouts with verified live remote custody,
no open PR, no declared active lane/process cwd, and ignored cache-only content.
All six branches remain retained. Pruned50 absent administrative registrations
whose commits remain referenced. Active/native/observer/Plan0216, dirty and
unpublished trees are retained; source audit artifacts remain outside Git under
`~/.local/state/codex-wake/qualification/plan0217-20261110/`.
