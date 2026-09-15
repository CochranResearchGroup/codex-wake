# Systemd credential environment-file rendering correction

Status: VERIFIED

Issue: `CochranResearchGroup/codex-wake#45`

Source commit: `fc73e1460f35bbddb7f65cb2b8eca552590642d9`

Source tree: `1aa4209da64f53925d422f0c16ed4c139ab37e1a`

## Outcome

The service configuration now accepts only an absolute, parser-safe GitHub
credential environment-file path and emits that path literally in
`EnvironmentFile=`. Relative, whitespace/control, glob, quote, backslash,
systemd-specifier, directive-injection, parent-component, and double-root
forms fail before unit mutation. Rendering revalidates a directly constructed
`ServiceConfig`, so callers cannot bypass the builder's boundary.

The installed-host parser fixture and one disposable installed-candidate user
service both accepted the rendered directive. A key-name-only `/proc`
inspection proved that the environment file reached the service process. No
credential value, GitHub provider request, wake registration, dispatch, global
installation, release, or unrelated service was involved.

## TDD evidence

- RED: the parser-valid rendering tracer failed because the unit contained
  `EnvironmentFile="/tmp/.../github.env"` instead of the required literal
  absolute path.
- RED: relative input raised no error.
- RED: the grouped unsafe-path and direct-config mutation tracers produced 11
  failures before validation was added.
- GREEN: the four core service regressions passed.
- GREEN: the focused service and CLI selection passed 21 tests.
- Python 3.11 comprehensive: 349 tests passed.
- Python 3.12 comprehensive: 349 tests passed.
- OpenClaw plugin: 12 tests passed.
- Both JavaScript entrypoint syntax checks, Python compilation, and
  `git diff --check` passed.

The deterministic unit fixture invoked installed
`systemd-analyze --user verify`; it ran rather than skipping and returned zero
without the prior `EnvironmentFile= path is not absolute` diagnostic.

## Installed candidate smoke

- Candidate root:
  `/home/ecochran76/.local/state/codex-wake/p50-systemd-envfile-20260914`
- Build root: `/tmp/codex-wake-p50-systemd-build.20260914`
- Wheel SHA-256:
  `bc81d0e901788f50774e9bf79e4b6b6ca85636bf32605fedb53480a36294fe3c`
- Installed `codex-wake` SHA-256:
  `ae65b756beb79ac6c7db8b637015f4d81e2329a091f79ccdf719d891e8b25855`
- Installed `codex-waked` SHA-256:
  `4ddcfcf4870d59ae499ab8aac8773c3134e39cca951b02522b3f1ad8771e2c38`
- Unit: `codex-wake-p50-envfile-smoke.service`
- Unit SHA-256:
  `6793415612b53071ce65d63b91fc8c7dafd5ea902dfc03b9a4e9978e1252288c`
- Unit directive:
  `EnvironmentFile=/home/ecochran76/.local/state/codex-wake/p50-systemd-envfile-20260914/github.env`
- Credential file metadata: owner UID `1000`, mode `0600`, regular file, 48
  bytes. Its value was never printed or persisted in repository evidence.
- Service evidence: `ActiveState=active`, `SubState=running`,
  `Result=success`, `ExecMainStatus=0`, PID `356440`.
- Bounded process inspection: `credential_env_present=true`; only the variable
  name and presence result were inspected.

## Rollback proof

The installed candidate entrypoint uninstalled the exact service. Fresh
readback reported `inactive` and `not-found`; the unit was absent and no probe
process remained. The exact candidate and build roots were moved to user trash
for recoverability and are absent from their original paths. The normal global
`codex-wake` remains version `0.5.2` and was not refreshed.

## Acceptance boundary

This receipt verifies issue #45's provider-free correction and disposable
service smoke. It does not authorize or prove a replacement issue #37 canary.
The P50 plan still has `canary_retries_after_registration: 0`; a new wake or
live dispatch requires explicit operator authorization after this correction
is accepted on canonical `main`.
