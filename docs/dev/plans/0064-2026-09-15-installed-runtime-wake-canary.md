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
unit transition survives one controlled post-registration daemon restart and
produces exactly one bounded visible wake in the captured Codex tmux pane.
Archive and roll back all canary artifacts without changing the global
installation or normal wake root.

## Current state

Issues #59 through #62 are closed. Productization PR #77 is merged at canonical
`origin/main` commit `08447afdfe0384b23d73079e4579ca050dffe2c0`, with both
Python CI gates green. No P51 installed canary attempt has been registered.
Preflight, plan review, candidate build, isolated installation, and initial
runtime setup are complete. The first registration command failed closed before
writing a wake because the inactive target unit was not loaded in the user
manager; the isolated journal remains empty and no dispatch occurred. One
bounded pre-registration fixture repair, registration, transition, dispatch,
and rollback remain.

The candidate service lifecycle before this amendment comprised its initial
setup start and one fail-safe stop/start while waiting for the required hook
confirmation. Applying the fixture repair may consume one more
pre-registration stop/start. The recovery proof then consumes exactly one
post-registration restart. These are three total stop/start cycles after the
initial activation, with no fourth restart path.

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
- delayed transition trigger service:
  `codex-wake-p51-transition-20260915.service`
- delayed transition trigger timer:
  `codex-wake-p51-transition-20260915.timer`
- delayed transition command: `/usr/bin/systemd-run --user
  --unit=codex-wake-p51-transition-20260915 --on-active=20s
  /usr/bin/systemctl --user start codex-wake-p51-target.service`
- tracked sanitized receipt:
  `docs/dev/verification/0077-2026-09-15-installed-runtime-wake-canary.md`
- source instance: `p51-canary-unit`
- target state: `active`
- idempotency key: `p51-systemd-active-canary-20260915`
- dispatch bound: `max_attempts: 1`
- transport: current live tmux pane captured at registration

The visible tmux target is window index `34` (`wake`), containing internal pane
ID `%33`; both identifiers and `/dev/pts/38` are captured to avoid conflating a
window index with a pane ID.

The source archive is created from the exact canonical commit, so this receipt
branch and its plan do not alter candidate bytes. The candidate daemon uses
only the venv's absolute `codex-waked`, exact wake root, exact source tree as
working directory, one-second interval, and isolated `XDG_STATE_HOME`.

## Authority and exclusions

Authorized effects are one isolated venv/build, one named candidate daemon
service, one disposable same-user target unit, one named delayed transition
trigger, one systemd source configuration, one wake registration, one
hook-gate pause/resume already consumed, one pre-registration fixture-repair
restart, one controlled post-registration recovery restart, one target start,
and at most one tmux dispatch.

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
   and absence of the exact runtime root. The project hook is intentionally
   absent. Require `codex-wake hook user check` to report the user hook valid
   and installed, and require an active-pane `/hooks` review to show that user
   hook loaded; do not install a project hook.
3. Archive canonical commit `08447afd...` into the exact source root, build one
   wheel, record its SHA-256, create the venv, and install only that wheel.
4. Write the two exact user-unit files. The target is a benign oneshot with
   `RemainAfterExit=yes`; it starts inactive. The candidate daemon unit carries
   only an `After=codex-wake-p51-target.service` ordering reference to keep the
   exact inactive target loaded for the observer's fixed `GetUnit` call; this
   reference does not activate the target. Reload the user manager, start the
   candidate daemon, and prove unit PID/executable/root/environment, target
   `LoadState=loaded` with `ActiveState=inactive`, plus recent monitor, doctor,
   readiness, and empty-wake-root state.
5. Configure the exact target unit/source with the candidate CLI. Arm one
   `systemd-unit becomes active` wake with `--require-monitor`, the stable
   idempotency key, and `--max-attempts 1`; confirm inactive baseline, exact
   durable arm, zero attempts, and no match.
6. Restart only the candidate daemon while the target remains inactive. Prove a
   new PID recovered the same wake/source identity, zero attempts, and recent
   non-stale instance health.
7. Schedule the exact delayed trigger with the fixed absolute argv above. The
   generated transient timer may invoke only `/usr/bin/systemctl --user start
   codex-wake-p51-target.service`; inspect its unit properties before yielding.
   Product code receives no mutation method or command authority. The timer
   starts only the named target after this initiating agent turn ends. Then
   stop the turn; do not poll manually or create another wake.
8. On the resumed turn, inspect the original wake, signal state, occurrence,
   match, dispatch count, acknowledgement, target pane, and
   `visibility_result.classification`. Any ambiguity ends the attempt without
   retry.
9. Export bounded support/readiness/status evidence, archive the wake, extract
   the tracked sanitized verification receipt at the exact path above, commit
   and push that receipt before deleting its runtime source evidence, then
   stop/remove only the exact
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
- The target remains inactive while the active candidate service's exact
  ordering reference keeps it loaded; no product call loads, starts, or mutates
  the target.
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
- candidate-service activations: four total including initial setup, the
  already-consumed hook-gate resume, one fixture-repair activation, and one
  post-registration recovery activation
- candidate-service stop/start cycles after initial activation: three total;
  hook-gate pause/resume already consumed, fixture repair one, recovery proof
  one; no additional restart path
- review: one read-only plan/runtime-boundary review before mutation
- pre-effect repair: one bounded cycle; implementation defects require a new
  linked corrective issue and no canary registration
- checkpoint cadence: pre-mutation, service-ready, post-registration/restart,
  post-outcome, and post-rollback

Stop before creating the runtime root if it already exists, either unit name is
present, the candidate commit differs, the target pane is absent/dead, the hook
is not installed and loaded in the active pane, or global/normal state cannot
be captured. Stop before
registration if wheel/executable/service/root/config identities disagree,
monitor readiness is false, the target is not both loaded and inactive, the
wake root is not otherwise empty, or dispatch cannot be bounded to one. Stop
before transition if restart recovery, exact source health, pending state,
zero-attempt count, or target identity is ambiguous. After registration,
inspect and roll back the original record on any uncertainty; never create a
replacement wake.

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
