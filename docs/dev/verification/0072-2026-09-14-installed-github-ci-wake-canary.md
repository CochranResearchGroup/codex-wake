# Installed GitHub CI wake canary: stopped before trigger

Status: FAILED_SAFE

Issue: `CochranResearchGroup/codex-wake#37`

Candidate commit: `a9716dd73fbd2a7fa9131bf570a31bb9a3b4f5e5`

Candidate tree: `4479c517a44cdcc0f4a64505d22b2cf9e7935649`

## Outcome

The first and only P50 installed canary registration stopped before the
selected GitHub workflow occurrence existed. The generated user unit rendered
the absolute credential environment-file path as a quoted value. The installed
systemd parser rejected it as non-absolute, the daemon process therefore had no
`CODEX_WAKE_GITHUB_TOKEN` environment entry, and source health recorded
`GITHUB_AUTH_UNAVAILABLE`. No receipt, match, dispatch attempt, hook
acknowledgement, or visibility result occurred.

The wake was cancelled and archived, the exact service was stopped and
uninstalled, and the drop-in, candidate root, credential file, venv, wake root,
logs, and build root were moved to the user trash. The plan's zero-retry bound
was preserved: no replacement wake or provider-triggering pull request was
created.

## Frozen identity

- Candidate wheel SHA-256:
  `7d07ed2f115ea6235bbe60aa49cfe0547634b49557ec7964de6369ddc255541a`
- Installed `codex-wake` SHA-256:
  `64608e16a492f02f015c301be296716db46dfbc2502425f8c94ea6aca4289784`
- Installed `codex-waked` SHA-256:
  `94e9b3a1f7a41adbe4916f415d0c54877a2eb3aec9133b13b0f950ec7faf7e9e`
- Source configuration SHA-256:
  `b0a571bd4bf45fd5e823e9ee73bd368d5fa8d0a4beacc2c006f76f07a8eb989e`
- Unit SHA-256:
  `827a70c3f598b91f76e811b726dbb4334a597116ada475824376ac37da0f325f`
- Isolation drop-in SHA-256:
  `25979ab3e10794ce3f4c7aee6c39228a2a4d04617dd7fe4a4e15e4298d99c7f1`
- Unit: `codex-wake-p50-github-canary.service`
- Initial daemon PID: `286772`
- Target: tmux pane `%36` on `/tmp/tmux-1000/default`
- Repository: `CochranResearchGroup/codex-wake`, numeric ID `1242753508`
- Workflow: `CI`, numeric ID `279450573`
- Ref: `refs/heads/chore/issue-37-installed-github-canary`
- Conclusion: `success`
- Source instance: `p50-github-ci`
- Credential reference: `CODEX_WAKE_GITHUB_TOKEN`; no credential value was
  printed, hashed into this receipt, stored in the wake record, or retained in
  the repository.

## Wake evidence

- Wake ID: `wake_09b5d91add724c5f8cb1ecb39ccec390`
- Arm ID: `arm_wake_09b5d91add724c5f8cb1ecb39ccec390`
- Idempotency key: `p50-github-canary-20260914`
- Registered at: `2026-09-15T03:30:27Z`
- Recovery: `source_replay`
- Anchor config fingerprint:
  `95d0c56289f52aa135c393e752aff75523b651dfb51d91799b5edf746c18f253`
- Anchor order: `1789443027000000`; local sequence: `0`
- Max attempts: `1`; observed dispatch attempts: `0`
- Journal checkpoint: absent; receipts: `0`; match reservations: `0`
- Source health at stop: `GITHUB_AUTH_UNAVAILABLE`, observed at
  `2026-09-15T03:32:22Z`, retry deadline `2026-09-15T03:32:52Z`
- Archived record: `status=archived`, revision `1`, no trigger match, no
  dispatch result, no acknowledgement, and no visibility result.

## Failure proof

Installed `systemd-analyze --user verify` reported:

```text
EnvironmentFile= path is not absolute, ignoring: "/home/ecochran76/.local/state/codex-wake/p50-github-canary-20260914/github.env"
```

A bounded `/proc/<pid>/environ` key-only inspection reported
`credential_env_present=false` and `xdg_state_present=true`. The credential
file itself was an owner-owned regular file with mode `0600`; its contents were
not emitted. The daemon remained active and recorded only pending checks, so
the failure is localized to unit rendering rather than GitHub authentication,
polling evidence, wake matching, or tmux dispatch.

## Rollback proof

- The wake was cancelled, then archived with zero attempts.
- The exact service reports `inactive` and `not-found`.
- The exact unit and drop-in paths are absent.
- The exact candidate and build roots are absent from their original paths and
  were moved to user trash for recoverability.
- A fresh `/proc` executable scan found no process using the candidate
  `codex-waked` executable.
- The global executable remains `/home/ecochran76/.local/bin/codex-wake` at
  version `0.5.2`; no global install, supervisor registration, workflow,
  credential, release, or unrelated service was mutated.

## Acceptance state

Issue #37 remains open and blocked on a product correction plus explicit
authority to revise the zero-retry canary bound. This receipt proves safe
failure and complete rollback; it does not prove a GitHub occurrence, match,
dispatch, acknowledgement, or operator-visible wake.
