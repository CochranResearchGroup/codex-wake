# Source registry installed compatibility

Status: VERIFIED_WITH_RECORDED_LOCAL_HARNESS_FAILURE

Issue: `CochranResearchGroup/codex-wake#85`

Candidate commit: `bcfcfd5ec9b1b1c2b84879a4c89d0d526f17be22`

## Outcome

The closed built-in catalogue is the shared authority for daemon
reconstruction and additive readiness/support inventory. Exact installed-wheel
CI on Python 3.11 and 3.12 proved the four registrations, six ownership pairs,
one provider-free fixture reconstruction, no wake-root creation, and temporary-
root cleanup. No provider, source observation, dispatch, service/global install,
release, or deployment effect occurred.

## Local installed attempt

The one authorized local attempt used exact source commit
`c4217b863d68f8e0cd803ed6990e2a6d53af5dac` and offline `uv build`. It installed
`codex_wake-0.5.2-py3-none-any.whl` into a temporary virtual environment with
`--no-index --no-deps`.

Successful installed assertions before the harness exit:

- inventory IDs: `local-filesystem`, `local-process-exit`,
  `local-user-systemd`, `github-ci`
- readiness status: `ready`
- journal exists: `false`
- wake root exists: `false`
- support bytes: `2357`
- support SHA-256:
  `d6b83a3c83a107c42eaf293e743f165d9baa3b1e3a7c4c583195057a60b1d6fe`
- wheel SHA-256:
  `a1fcde0c46e984656aa7f72c8064d88a93a6a3578f4201402d9a76aefe33bf15`
- installed `codex-wake` SHA-256:
  `983974771208f34e5fb7864a992b71a13228a5653b71ead887e2000206720fca`
- installed `codex-waked` SHA-256:
  `f7676c77ea82b3091f6d546fd4c4010f2c1a2b2654001525c03db1df0b58defe`

The harness then raised `AttributeError` because receipt rendering referenced
`SupportExportResult.bytes_written` rather than `size_bytes`. Installed fixture
reconstruction had not run. The attempt was not retried. Readback confirmed the
wake root remained absent. The exact temporary tree plus generated `build/` and
`src/codex_wake.egg-info/` artifacts were moved to user trash and no longer
exist at their original paths.

## Deterministic installed CI replacement

PR #99 run `35044676538` installed the exact candidate wheel and executed
`scripts/source_registry_smoke.py` through each installed interpreter.

- Python 3.11: four expected registrations, six ownership pairs, readiness
  `ready`, journal absent, one fixture factory call, one restored runner, wake
  root not created, temporary root removed.
- Python 3.12: the same assertions and counts passed.
- Both jobs then completed the existing broader installed-wheel product smoke.

Support artifacts were 2,353 bytes in both jobs. Their hashes differed because
the sanitized payload includes each job's distinct temporary journal path; no
semantic field differed.

## Acceptance boundary

This receipt proves installed package compatibility for pure catalogue
inventory, additive readiness/support projection, provider-free fixture
reconstruction, and cleanup on Python 3.11 and 3.12. It does not prove provider
behavior, live source observation, dispatch, external plugin loading, service
installation, global installation, release, or deployment.
