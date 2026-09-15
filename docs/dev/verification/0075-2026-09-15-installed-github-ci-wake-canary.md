# Installed GitHub CI wake canary retry 2

Status: IN_PROGRESS

Issue: `CochranResearchGroup/codex-wake#37`

Candidate commit: `ee39ae1bbaf0af754e475dc79112a8787ad7f7ff`

Candidate tree: `44ccb26b9361d55000d6cbfc29f1fc224a66093c`

## Authorized boundary

This is the first of up to five newly authorized replacement attempts. It may
register one isolated wake with `max_attempts: 1`, cause one ordinary pull
request CI completion after the anchor and controlled service restart, and
make at most one live tmux dispatch. Success, ambiguity, identity drift, or a
failed restart-recovery check ends this attempt without a second registration.

The primary orchestrator owns all live effects. Every candidate CLI command
must use the candidate service's exact isolated `XDG_STATE_HOME`; registration
must also use `--require-monitor`.

## Frozen pre-registration names

- Branch: `chore/issue-37-github-canary-retry-2`
- Candidate runtime root:
  `/home/ecochran76/.local/state/codex-wake/p50-github-canary-retry-2-20260915`
- Candidate build root:
  `/tmp/codex-wake-p50-github-canary-retry-2-build.20260915`
- Wake root: candidate runtime root plus `/wake`
- Unit: `codex-wake-p50-github-canary-retry-2.service`
- Source instance: `p50-github-ci-retry-2`
- Idempotency key: `p50-github-canary-retry-2-20260915`
- Repository: `CochranResearchGroup/codex-wake`, numeric ID `1242753508`
- Workflow: `CI`, numeric ID `279450573`
- Ref: `refs/heads/chore/issue-37-github-canary-retry-2`
- Conclusion: `success`
- Credential reference: `CODEX_WAKE_GITHUB_TOKEN`; no credential value may be
  printed or persisted in repository evidence.
- Target: live Codex pane `%33` on `/tmp/tmux-1000/default`, subject to exact
  revalidation immediately before registration.

## Pending evidence

Wheel, executable, source-configuration, unit, drop-in, service PID, wake,
anchor, restart, workflow run, match, dispatch, acknowledgement, visibility,
archive, and rollback evidence will be filled only from exact readback. This
in-progress checkpoint claims none of those outcomes.
