# Installed local-runtime systemd wake canary

Status: VERIFIED

Issue: `CochranResearchGroup/codex-wake#63`

Candidate source commit: `08447afdfe0384b23d73079e4579ca050dffe2c0`

## Outcome

The isolated installed candidate observed one exact current-user systemd unit
transition from `inactive` to `active`, recovered the pending wake through one
post-registration daemon restart, and submitted exactly one wake to the
captured Codex tmux pane. The hook acknowledgement and tmux visibility check
both succeeded. Raw pane text was not stored.

The first registration command failed closed before writing because the
inactive disposable target had been garbage-collected from the user manager.
The isolated journal remained empty and no dispatch occurred. The reviewed
pre-effect repair added only an ordering reference from the active candidate
service to the exact target, keeping it loaded without activating it. The
second command created the sole durable registration; it was not a replacement
for an existing wake.

The wake was archived before rollback. The sanitized receipt was committed and
pushed at `703e42d668b200bb3f5e8c251e2856439063237a` before the exact unit files
and runtime root were moved recoverably to user trash.

## Frozen installed identity

- Runtime root:
  `/home/ecochran76/.local/state/codex-wake/p51-runtime-canary-20260915`
- Wake root: runtime root plus `/wake`
- Candidate unit: `codex-wake-p51-canary.service`
- Target unit: `codex-wake-p51-target.service`
- Source instance: `p51-canary-unit`
- Target state: `active`
- Idempotency key: `p51-systemd-active-canary-20260915`
- Candidate version: `0.5.2`
- Wheel SHA-256:
  `eed659e3ae91a4e3544e0d32ca0ffc0c18eaadf82f3429d9d2c30dd6067a480a`
- Installed `codex-wake` SHA-256:
  `b1da4f8300a3de84da4d5247b2cf4ebe391e0aa969ff15a9da27434659513a1d`
- Installed `codex-waked` SHA-256:
  `d962db132d7b4e14bf887347ff221630383032afd0669793716854e0ea8d9908`
- Source configuration SHA-256:
  `5077860b47e95e991b96194979cb19f93d024cb7853c13ac7012ded5e77a72af`
- Repaired candidate-unit SHA-256:
  `0aac41158593de1508931fb9c6fe74f11e4156bef21aa02fae5bf1e098050411`
- Target-unit SHA-256:
  `134eca756bb852bbb8dd1502c916a9948fcac3c2cd6f9edcfba0a771780890ba`
- Bounded support export: 3,105 bytes, one included wake, zero omitted;
  SHA-256
  `421a4095d06b557c9724f2e7f2f1ab2fdb920206d91ce8c62b0a471a38b00b0d`

## Pre-registration failure and repair

- The first registration command returned
  `SYSTEMD_OBSERVATION_UNAVAILABLE` before publishing a wake.
- Readback showed zero total, pending, firing, submitted, failed, cancelled,
  expired, or archived records.
- The session bus, manager owner query, and candidate service were healthy.
  The fixed `GetUnit` call returned an error because the inactive target was
  not loaded. Product code did not call `LoadUnit` or acquire mutation
  authority.
- The plan amendment at
  `f1ed13a987766dcf5519486a1f0f9074b79131ad` added one fixture-only
  `After=codex-wake-p51-target.service` reference and required the target to be
  both loaded and inactive before registration.
- Independent reviewer `/root/p51_canary_plan_review` first returned
  `F-RESTART-01` because restart accounting was ambiguous. The amendment then
  recorded the full cumulative lifecycle and prohibited a fourth restart
  path. Closed-world re-review returned `PASS`. The requested route was
  `gpt-5.6-luna` medium; effective runtime model and allocation were not
  reported.
- Candidate service PIDs were: initial setup `55059`, hook-gate resume
  `14366`, fixture-repair activation `35066`, and post-registration recovery
  activation `37518`.
- After repair, the fixed backend resolved the canonical target with a
  64-character manager-generation fingerprint and read `active_state=inactive`.

## Registration and recovery

- Wake ID: `wake_ea9a12487da64c86bd2110430f517425`
- Arm ID: `arm_wake_ea9a12487da64c86bd2110430f517425`
- Journal UUID: `ba1fe97cd00944edaef30e911b9fa037`
- Registered at: `2026-09-15T20:50:38Z`
- Baseline state: `inactive`
- Recovery mode: `state_recheck`
- Manager-generation fingerprint:
  `91bf157e6c87fb320a1b9e6e0629e466420996c0303e448e5f0775ff6131244b`
- Target: tmux socket `/tmp/tmux-1000/default`, internal pane ID `%33`,
  visible window index `34` (`wake`), pane index `0`, tty `/dev/pts/38`
- Before restart: pending, attempts `0/1`, candidate PID `35066`, target
  loaded/inactive, exact-instance source health `SYSTEMD_READY`.
- After restart: the same wake and arm remained pending at attempts `0/1`,
  candidate PID was `37518`, the target remained loaded/inactive, and fresh
  exact-instance source health returned `SYSTEMD_READY`.

## Transition, match, and dispatch

- The named transient trigger was
  `codex-wake-p51-transition-20260915.timer` and its paired service. Its fixed
  command was `/usr/bin/systemctl --user start
  codex-wake-p51-target.service`.
- The trigger service exited successfully and its transient units were
  collected. The exact target remained `active/exited` with result `success`
  when the resumed turn verified the predicate.
- Receipt ID: `event_000000000001`; local sequence: `1`.
- Match token:
  `match:wake_ea9a12487da64c86bd2110430f517425:event_000000000001`
- Matched at: `2026-09-15T20:51:59Z`
- Verification: `verified` by `user-manager-state-recheck`
- Observed attributes: previous state `inactive`, current state `active`,
  transition `true`, reason `periodic`, and the same manager generation.
- Evidence reference:
  `systemd:user:codex-wake-p51-target.service:91bf157e6c87fb320a1b9e6e0629e466420996c0303e448e5f0775ff6131244b`
- Evidence digest:
  `a97ddff71c18a593649b71398d7740d80b24375ee0c45856825d489ed81dedb6`
- Record status before archive: `submitted`; attempts: `1/1`.
- Event sequence: `created`, `predicate_matched`, one `dispatch_attempt`,
  `ack_observed`, and `tmux_visibility_checked`.
- Acknowledgement submission time: `2026-09-15T20:51:59Z`; session
  `01a0a02b-522a-7423-b7ee-e4d5f3a81efe`; turn
  `01a0a6d7-4027-7483-979d-92baae392ac0`.
- Visibility classification: `visible_prompt_observed` for pane `%33`.
  The bounded pre-capture lacked the wake marker and the post-capture contained
  a new marker. Privacy classification was `raw_pane_text_not_stored`.
- The user-supplied resumed turn carried the same wake ID and exact isolated
  wake root, corroborating delivery into the intended session.

## Archive and scoped readiness

- The archived status reported one archived wake, zero active wakes, zero
  terminal wakes outside the archive, and one
  `visible_prompt_observed` classification.
- The signal arm had already been tombstoned after the verified match, with
  lifecycle desired/applied state `submitted` at revision `2` and no blocked
  outbox operation before archive.
- Hook readiness reported one acknowledgement, the exact latest wake ID,
  `active_session_loaded=observed_ack`, and one installed user hook with no
  duplicate project hook.
- Monitor readiness reported the exact candidate service active and matching
  the isolated wake root. Signal readiness reported the compatible journal and
  no active arms after submission.
- Aggregate product readiness was `blocked` only by unrelated app-server and
  OpenClaw Gateway checks. Those transports were outside this tmux/systemd
  canary and are not represented as acceptance failures.

## Rollback proof

- The candidate service was stopped before the target. Both exact unit files
  and the validated runtime root were moved to user trash, so the removal is
  recoverable.
- Fresh user-manager readback reports the candidate, target, transition
  service, and transition timer all `not-found`, `inactive`, and `dead`.
- A fresh `/proc` census found zero processes whose command line referenced
  the exact runtime root or any named P51 canary unit.
- The global installation remains `codex-wake 0.5.2`; executable SHA-256
  values remain:
  - `codex-wake`:
    `e04c4dc59c1feb4bfb824012e4cefce3ab70342e1f56d19b4a63b72cc164ecea`
  - `codex-waked`:
    `209507af842573172a3a08c57b2b50467562fe433a3e0254b61d88e9fda9514a`
  - `codex-wake-hook`:
    `ac253bf57ea37ddc6250233b68e692442adde4fd84ca74ab2f2d54fdef99eadf`
- The normal repo wake root is unchanged at zero active and 23 archived wakes.
  Its repo service remains loaded, disabled, inactive, and dead.
- The user supervisor remains loaded, enabled, active, and running with the
  same three enabled roots. The isolated canary root was never enrolled.
- No global install, normal wake root, supervisor registry, credential,
  provider, release, deployment, or unrelated process/service mutation
  occurred.

## Acceptance boundary

This receipt proves one installed, restart-correct, read-only user-systemd
state-transition wake through exact observation, match, dispatch,
acknowledgement, and visible tmux delivery. It does not claim unseen transition
replay, exact transition time, system-manager access, unit-control authority in
product code, provider behavior, a global installation refresh, release, or
deployment.
