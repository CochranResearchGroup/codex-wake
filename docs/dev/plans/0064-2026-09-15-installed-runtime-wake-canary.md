# Installed local-runtime wake canary

State: OPEN
Lane: P51-C5
Issue: #63
Branch: `chore/issue-63-runtime-wake-canary`
Target: `main`
Integration: `squash`

## Objective

Install the exact accepted P51 candidate into an isolated virtual environment
and named user service, then prove one exact configured current-user systemd
unit transition survives one controlled daemon restart and produces exactly one
bounded visible wake in the captured Codex tmux pane. Archive and roll back all
canary artifacts without changing the global installation or normal wake root.

## Current state

Issues #59 through #62 are closed. Productization PR #77 is merged at canonical
`origin/main` commit `08447afdfe0384b23d73079e4579ca050dffe2c0`, with both
Python CI gates green. No P51 installed canary attempt has been registered.
Preflight, plan review, candidate build, isolated installation, runtime setup,
registration, transition, dispatch, and rollback remain.

## Source selection

Select `systemd-unit becomes active` because the live current-user session-bus
and manager-generation boundary carries higher residual installed risk than the
fixed `/proc` process observer. This canary proves one positively observed
inactive-to-active transition only; it does not claim unseen transition replay,
unit completion, process exit status, or exact transition time.

## Exact identities

- candidate source commit: `08447afdfe0384b23d73079e4579ca050dffe2c0`
- runtime root: `/home/ecochran76/.local/state/codex-wake/p51-runtime-canary-20260915`
- wake root: runtime root plus `/wake`
- venv: runtime root plus `/venv`
- archived source/build root: runtime root plus `/source`
- receipt staging: runtime root plus `/receipts`
- candidate daemon unit: `codex-wake-p51-canary.service`
- candidate unit file: `/home/ecochran76/.config/systemd/user/codex-wake-p51-canary.service`
- disposable observed unit: `codex-wake-p51-target.service`
- disposable unit file: `/home/ecochran76/.config/systemd/user/codex-wake-p51-target.service`
- delayed transition trigger: `codex-wake-p51-transition-20260915`
- source instance: `p51-canary-unit`
- target state: `active`
- idempotency key: `p51-systemd-active-canary-20260915`
- dispatch bound: `max_attempts: 1`
- transport: current live tmux pane captured at registration

The source archive is created from the exact canonical commit, so this receipt
branch and its plan do not alter candidate bytes. The candidate daemon uses
only the venv's absolute `codex-waked`, exact wake root, exact source tree as
working directory, one-second interval, and isolated `XDG_STATE_HOME`.

## Authority and exclusions

Authorized effects are one isolated venv/build, one named candidate daemon
service, one disposable same-user target unit, one named delayed transition
trigger, one systemd source configuration, one wake registration, one
controlled daemon restart, one target start, and at most one tmux dispatch.

No global tool refresh, normal repo wake-root mutation, supervisor enrollment,
credential change, provider call or mutation, public ingress, system-manager
access, arbitrary product D-Bus call, unrelated unit/process action, release,
tag, or deployment. Product code remains read-only toward systemd; the canary
owner's explicit `systemctl --user start/stop` actions control only the named
disposable target.

## Execution graph

1. Publish and independently review this plan; merge the coordination ledger
   that closes #62 custody and registers P51-C5.
2. Capture global installed identity, normal wake status, supervisor/service
   state, current tmux target, hook readiness, existing named units/processes,
   and absence of the exact runtime root.
3. Archive canonical commit `08447afd...` into the exact source root, build one
   wheel, record its SHA-256, create the venv, and install only that wheel.
4. Write the two exact user-unit files. The target is a benign oneshot with
   `RemainAfterExit=yes`; it starts inactive. Reload the user manager, start the
   candidate daemon, and prove unit PID/executable/root/environment plus recent
   monitor, doctor, readiness, and empty-wake-root state.
5. Configure the exact target unit/source with the candidate CLI. Arm one
   `systemd-unit becomes active` wake with `--require-monitor`, the stable
   idempotency key, and `--max-attempts 1`; confirm inactive baseline, exact
   durable arm, zero attempts, and no match.
6. Restart only the candidate daemon while the target remains inactive. Prove a
   new PID recovered the same wake/source identity, zero attempts, and recent
   non-stale instance health.
7. Schedule the exact delayed trigger to start only the named target after this
   initiating agent turn ends, then stop the turn. Do not poll manually or
   create another wake.
8. On the resumed turn, inspect the original wake, signal state, occurrence,
   match, dispatch count, acknowledgement, target pane, and
   `visibility_result.classification`. Any ambiguity ends the attempt without
   retry.
9. Export bounded support/readiness/status evidence, archive the wake, extract
   a tracked sanitized verification receipt, then stop/remove only the exact
   trigger, target, service, unit files, runtime root, and associated processes.
10. Prove exact rollback and no global/normal-runtime drift, close the plan and
    P51 ledgers, pass CI, merge the receipt PR, close #63, and re-read canonical
    `origin/main`.

## Acceptance criteria

- Candidate commit, wheel hash, venv executables, service unit/PID, isolated
  state, source config, target unit, wake root, tmux target, wake/arm IDs, and
  attempt bound form one attributable identity.
- Registration observes a nonmatching inactive baseline. One controlled daemon
  restart recovers the same pending identity with zero attempts before the
  target transition.
- The delayed owner-controlled target start yields one verified observation,
  stable occurrence identity, one match, exactly one dispatch attempt, hook
  acknowledgement, and `visible_prompt_observed` in the captured pane.
- Evidence includes only bounded fingerprints, allowlisted state/health codes,
  observation times, counts, hashes, and locators. It excludes raw D-Bus
  payloads, secrets, prompt body, raw pane text, and unrelated unit/process
  data.
- The terminal wake is archived and every exact canary service, unit, trigger,
  process, runtime/build root, source config, and target is absent afterward.
  Global installed identity, normal wake root/service/supervisor, credentials,
  and unrelated runtime state remain unchanged.

## Bounds and hard stops

- installed canary attempts: one; retries after registration: zero
- live dispatch attempts: one; wake `max_attempts`: one
- daemon restarts: one before transition
- review: one read-only plan/runtime-boundary review before mutation
- pre-effect repair: one bounded cycle; implementation defects require a new
  linked corrective issue and no canary registration
- checkpoint cadence: pre-mutation, service-ready, post-registration/restart,
  post-outcome, and post-rollback

Stop before creating the runtime root if it already exists, either unit name is
present, the candidate commit differs, the target pane is absent/dead, the hook
is not installed, or global/normal state cannot be captured. Stop before
registration if wheel/executable/service/root/config identities disagree,
monitor readiness is false, the target is not inactive, the wake root is not
otherwise empty, or dispatch cannot be bounded to one. Stop before transition
if restart recovery, exact source health, pending state, zero-attempt count, or
target identity is ambiguous. After registration, inspect and roll back the
original record on any uncertainty; never create a replacement wake.

## Rollback

On success or failure, preserve sanitized evidence first. Cancel a still-pending
wake or archive a terminal wake. Stop/reset/remove only the named transition
trigger, target unit, and candidate service; remove their exact unit files and
reload the user manager. Verify their units and PIDs are absent. Remove only the
validated exact runtime root after its required receipt has been copied into
the tracked verification artifact. Do not mutate the global installation,
normal wake root, supervisor registry, or unrelated process tree.

## Next action

Publish this plan checkpoint, perform one independent pre-effect review, and
advance canonical active-lane custody before any installed mutation.
