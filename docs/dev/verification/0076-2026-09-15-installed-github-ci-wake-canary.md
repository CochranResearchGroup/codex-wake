# Installed GitHub CI wake canary retry 3

Status: VERIFIED

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

## Installed identity and pre-registration proof

- Built wheel SHA-256:
  `80e078ff7058b957c81bf2a4d434aacbc637057503797d8d3ecc9e32644336bb`.
- Installed `codex-wake` SHA-256:
  `a25b5961eec05b8a85b7e935942b7aaacf7a2680a92563d9b96a340e4c1d4ab9`.
- Installed `codex-waked` SHA-256:
  `a4224103f985e5961e79faeb2868ff793d498bb92b618fcbfbe1c6d25dbda77f`.
- Source configuration SHA-256:
  `52e7ffd83a817cf30c72fe50485a0b8ae18ecf86beea3d7020f27c67d2ab37ac`.
- Unit SHA-256:
  `a449d634bc1f3317556b92eb96b414e1953f5aa83b1110e798806f7c14d04c17`;
  drop-in SHA-256:
  `3bb71205b29dbd2f724f312b7508785a03a9f79d6804586fee5d557de797d1d4`.
- The credential file was owned by UID 1000, mode `0600`, and 65 bytes. The
  candidate service process held the same 40 credential bytes as the current
  authenticated GitHub CLI source, and its bounded Actions read returned HTTP
  200. The check was repeated after restart. No credential value or digest was
  printed or persisted.
- The candidate service started as PID 72634 and restarted as PID 73817. The
  wake record SHA-256 remained
  `6af9f0d602533250b25d693da6a72f42176b0b946da3f864e974c331f777de18`
  across that restart.

## Registration, occurrence, and dispatch

- Wake: `wake_d95aaa91211c4648ac540eda7906088b`; arm:
  `arm_wake_d95aaa91211c4648ac540eda7906088b`; journal:
  `bd2e6071ca4f435bb972922b2a914895`.
- Registration time: `2026-09-15T14:48:15Z`; terminal-proof anchor:
  `1789483695000000` microseconds; source configuration fingerprint:
  `fe3940a5553481c1e35eb5d2272c033cbd4d8e24dee14e352257d1aa131459fd`.
  Restart recovery was `source_replay`, with local sequence zero before the
  qualifying event.
- The ordinary pull-request workflow produced run `34984194234`, attempt 1,
  for workflow `CI`, exact head
  `5899a06cab2e97a36fc4db1cfe85a4d337230db9`. It was created at
  `2026-09-15T14:49:01Z` and completed successfully. Exact-attempt
  verification established the normalized terminal lower bound
  `2026-09-15T14:49:42Z`; provider `updated_at` was separately retained as
  `2026-09-15T14:49:43Z` and is not represented as completion provenance.
- Receipt `event_000000000001` used namespace
  `github.workflow_run.attempt.completed`, occurrence
  `1242753508:34984194234:1`, evidence reference
  `github:repository:1242753508:run:34984194234:attempt:1`, verification method
  `github-run-attempt-read`, local sequence 1, and evidence digest
  `02201ae99d32961e444f1a842e8f44bf256cb4e6e5de7e604dfb37762569cf8a`.
- The wake matched once at `2026-09-15T14:49:49Z` with token
  `match:wake_d95aaa91211c4648ac540eda7906088b:event_000000000001` and made
  exactly one dispatch attempt. The acknowledgement was observed and the
  submitted acknowledgement named session
  `01a0a02b-522a-7423-b7ee-e4d5f3a81efe`, turn
  `01a0a58a-fa01-7cf0-bca8-9ea4f6dc8a22`, and submission time
  `2026-09-15T14:50:08Z`.
- Visibility classification was `visible_prompt_observed` for exact pane `%33`:
  the pre-sample lacked the marker and the post-sample contained it. Raw pane
  text was not stored. The operator-visible resumed turn supplied the same wake
  ID and root, independently confirming delivery into the intended session.
- Source health was `GITHUB_COVERAGE_UNPROVEN`, the expected positive-only
  warning. The daemon cycle reported `checked=1 fired=1 failed=0 pending=0
  dispatched=1 submitted=1 requeued=0`.

## Archive and rollback

At `2026-09-15T14:51:15Z`, the submitted wake was archived with one attempt,
one receipt, one reservation, zero unapplied outbox entries, and visibility
`visible_prompt_observed`. The arm was tombstoned and lifecycle desired/applied
state became `archived` at revision 2.

The exact candidate service was then uninstalled. Its unit and drop-in are
absent, no candidate process remains, and the candidate runtime and build roots
were moved recoverably to the user's trash. The normal
`codex-wake-codex-wake.service` remained inactive and the global installation
remained version `0.5.2`. Retry 3 therefore proves the bounded installed
product outcome and stops the authorized retry loop; no fourth attempt is
allowed or needed.
