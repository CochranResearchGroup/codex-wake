# App-server readiness installed rollout

Date: 2026-09-22
Issue: #156
Plan: `docs/dev/plans/0089-2026-09-22-app-server-readiness-installed-rollout.md`
Outcome: ACCEPTED

## Identity

- Planning PR: #157
- Planning head: `f9020609892717b974784ddfe9da31aba7d9e6aa`
- Canonical candidate source:
  `5aad4e0c4a44da0fd647d861cd2fd7bd73a55c9c`
- Candidate wheel SHA-256:
  `97f5e93d8322e33509b37433e24060af2eb9ad2237acdc212895a4b635da20a5`
- Rollback ref: `v0.5.2`
- Rollback commit: `99079e629a83c206f91f47455cd4691d484d6b34`
- Rollback wheel SHA-256:
  `db013caed98622e7d80719cb8b2a36f422d50a51e429bc43ce7ad5d215ba4c64`
- Installed tool root:
  `/home/ecochran76/.local/share/uv/tools/codex-wake`

Both wheels report package version `0.5.2`; source and installed file hashes,
not the unchanged version string, distinguish the candidate from the release
baseline.

## Pre-effect evidence

- Installed entrypoint: `/home/ecochran76/.local/bin/codex-wake`.
- The installed `app_server.py`, `supervisor.py`, `monitor.py`, and `service.py`
  hashes exactly matched the rollback wheel before mutation.
- `codex-wake-supervisor.service` was active and enabled at PID 1073 with start
  timestamp 2026-09-16 04:58:30 CDT.
- Supervisor unit SHA-256 was
  `b2b46c78462e52e176e415e02d928bb160d6f0e8f69b7e3aff6cd1ffb6fbcc23`.
- The codex-wake root registration was enabled and carried
  `dispatch.codex_cmd=/home/ecochran76/.local/bin/codex`.
- All four enrolled roots reported `active_total=0`, `pending=0`, and
  `firing=0` immediately before installation and restart.
- The baseline doctor result was supervisor-owned but incorrectly reported
  `codex_cmd_source=unit_environment`, reproducing the stale installed behavior.

## Validation before mutation

- Affected Python tier: 173 tests passed in 5.395 seconds.
- Exact supervisor regression with `ResourceWarning` promoted to error: passed.
- Comprehensive Python tier: 688 tests passed in 34.138 seconds.
- OpenClaw plugin provider-free tier: 12 tests passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- PR #157 hosted release gates: Python 3.11 and 3.12 passed.

No provider or live dispatch path was exercised by these checks.

## Mutation receipt

An initial attempt to invoke `python -m pip` in the uv-managed tool environment
exited before mutation because that environment intentionally has no `pip`
module. A complete hash and process readback confirmed the installed files,
PID, and service state were unchanged. The supported command then performed the
single replacement:

```text
uv pip install --python /home/ecochran76/.local/share/uv/tools/codex-wake/bin/python \
  --no-deps --reinstall <candidate-wheel>
```

uv reported one uninstall and one install, from the release baseline to the
local candidate wheel. The affected installed file hashes then exactly matched
the candidate:

| File | SHA-256 |
| --- | --- |
| `app_server.py` | `cabce5ce1a1b71dacb14a5323c2a76a327340797021d3f26b26657ddd88aba96` |
| `supervisor.py` | `fc8f37246a2d487cf3e5b90d82ef3fd77bab924557d4e73c9bbd2c70b19713c9` |
| `monitor.py` | `51c181c7b5c7bb926cc80f32bd137e60ac852f40ac8656ee3e8ebd70b3cc3558` |
| `service.py` | `f81b06bccc002f173e4ff246e52f0eb20b437fa8cd888b5858eba4e29b5b87e8` |

The exact supervisor dispatch regression passed under the installed Python
interpreter before service restart.

At `2026-09-22T11:08:54Z`, one explicit
`systemctl --user restart codex-wake-supervisor.service` replaced PID 1073 with
PID 3278. The new process started at 2026-09-22 06:08:54 CDT, remained active
and enabled, reported `NRestarts=0`, and retained the exact pre-effect unit hash.

## Post-effect evidence

- `supervisor status --json` reported four registered roots, all fresh and
  ready, with no remediation.
- The codex-wake root health was written by PID 3278 after the restart.
- From the enrolled repo path, `doctor --json` and `monitor check --json`
  reported:
  - `monitor_source=supervisor`
  - `monitor_ready=true`
  - `codex_cmd_source=supervisor_registry`
  - `codex_cmd=/home/ecochran76/.local/bin/codex`
  - `codex_cmd_ready=true`
- The repo-scoped `codex-wake-codex-wake.service` remained inactive and
  disabled.
- Every enrolled root remained at `active_total=0`, `pending=0`, and
  `firing=0` after restart.
- A first doctor assertion executed from the rollout worktree correctly derived
  that worktree's absent repo-service name and stopped on the test's wrong
  repo-service expectation. Re-running from the enrolled repo path passed every
  intended assertion; the supervisor evidence was already correct in both
  readbacks.

## Rollback and effect boundary

The rollback wheel was built and hashed before mutation and retained until all
installed-runtime postconditions passed. Rollback was not exercised because the
candidate was accepted. It remains reproducible from exact tag `v0.5.2` and
commit `99079e629a83c206f91f47455cd4691d484d6b34`.

Observed live effects were exactly one successful user-tool replacement and one
restart of `codex-wake-supervisor.service`. There was no wake dispatch, visible
turn, OpenClaw operation, enrolled-root change, wake-record rewrite, provider
mutation, package publication, release, other service mutation, or other-host
deployment.

## Hosted closeout gate stabilization

PR #158's first hosted run failed the same existing
`test_provider_timeout_runs_on_main_thread_and_fails_closed` assertion on
Python 3.11 and 3.12. The first request correctly returned
`VERIFICATION_UNAVAILABLE`; the second returned the fail-closed
`COMMIT_FAILED` result instead of the fixture's expected `COMMITTED` result.

The test had assigned a 50 ms absolute deadline to the complete second request,
including its SQLite commit. A closed-world harness injected 75 ms immediately
before that commit and deterministically reproduced the exact result. No stale
timer or database lock was involved: the runtime clears the prior timer in a
`finally` block, the first request never reaches the store, and requests are
serialized.

The correction changes only the test fixture: its deliberately slow provider
now sleeps for two seconds, while the runtime operation budget is 250 ms and
the elapsed-time ceiling remains below one second. This still proves a real
absolute provider timeout and same-runtime recovery, while leaving bounded room
for the successful request's durable commit under hosted scheduling variance.

Post-correction evidence:

- Injected 75 ms commit-delay loop: 10 of 10 passed.
- Normal exact test loop: 20 of 20 passed.
- `tests.test_github_webhook_runtime`: 11 tests passed.
- Comprehensive Python tier: 688 tests passed in 33.307 seconds.
- Plugin tier: 12 tests passed.
- Compilation and diff hygiene: passed.

No product source or installed-runtime artifact changed during this test-only
stabilization. The installed candidate remains bound to canonical source
`5aad4e0c4a44da0fd647d861cd2fd7bd73a55c9c` and its recorded wheel hash.
