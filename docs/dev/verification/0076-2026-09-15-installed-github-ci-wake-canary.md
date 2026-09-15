# Installed GitHub CI wake canary retry 3

Status: IN_PROGRESS

Issue: `CochranResearchGroup/codex-wake#37`

Candidate commit: `99338719d61fe189c3e0030e36f07b5d83e5dfc6`

Candidate tree: `2b80409b40975d92f22664cc673c3af177fcd1f9`

## Authorized boundary

This is the third replacement retry and the second of up to five newly
authorized attempts. It may register one isolated wake with `max_attempts: 1`,
cause one ordinary pull-request CI completion after the anchor and controlled
service restart, and make at most one live tmux dispatch. Success, ambiguity,
identity drift, or failed restart recovery ends the attempt without another
registration.

Every candidate CLI command must use the service's exact isolated
`XDG_STATE_HOME`; registration must use `--require-monitor`. Before
registration, the service-process credential must be byte-equal to the current
authenticated GitHub CLI credential and a bounded Actions read must return HTTP
200. Only equality, length, and status may be reported; neither value nor a
digest may enter output or repository evidence.

## Frozen pre-registration names

- Branch: `chore/issue-37-github-canary-retry-3`
- Candidate runtime root:
  `/home/ecochran76/.local/state/codex-wake/p50-github-canary-retry-3-20260915`
- Candidate build root:
  `/tmp/codex-wake-p50-github-canary-retry-3-build.20260915`
- Wake root: candidate runtime root plus `/wake`
- Unit: `codex-wake-p50-github-canary-retry-3.service`
- Source instance: `p50-github-ci-retry-3`
- Idempotency key: `p50-github-canary-retry-3-20260915`
- Repository: `CochranResearchGroup/codex-wake`, numeric ID `1242753508`
- Workflow: `CI`, numeric ID `279450573`
- Ref: `refs/heads/chore/issue-37-github-canary-retry-3`
- Conclusion: `success`
- Credential reference: `CODEX_WAKE_GITHUB_TOKEN`
- Target: live Codex pane `%33` on `/tmp/tmux-1000/default`, subject to exact
  revalidation immediately before registration

## Pending evidence

Wheel, executable, source-configuration, unit, drop-in, service PID, wake,
anchor, restart, workflow run, match, dispatch, acknowledgement, visibility,
archive, and rollback evidence will be filled only from exact readback. This
in-progress checkpoint claims none of those outcomes.
