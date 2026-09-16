# Installed webhook PrivateTmp successor qualification

State: OPEN
Lane: P53-C4-v2
Issue: #107
Predecessor: Plan 0074 (`FAILED_SAFE`)
Branch: `chore/issue-107-installed-webhook-canary`
Target: `main`
Integration: `squash`

## Current state

Plan 0074 consumed its single service-effect attempt at exact candidate
`da28deee19a99be8db9e08276383ec5344722a30`. The installed unit started but
systemd returned `203/EXEC` before listener execution because `PrivateTmp=yes`
made the host `/tmp` bootstrap path unavailable inside the unit namespace.
Cleanup is accepted and complete: the unit is absent/inactive/disabled with
MainPID zero, port 8820 is free, no matching process remains, and the six-unit
unrelated failed baseline is unchanged. The sanitized receipt is
`/tmp/codex-wake-p53-c4-service-effect-1.json`.

The source qualification, candidate wheel, managed-reader provider exclusion,
PID/start census, and external stage receipts remain valid. Only the disposable
execution-root placement and missing service-effect stage locator require
correction. No second service effect is permitted until that correction is
test-driven, validated, published, and freshly preflighted.

Checkpoint `710c001b5873552c0b85618c8506ca742b9f127a` implements the
source-only correction. It creates owner-only roots beneath the resolved user
state qualification directory, rejects relative state paths and paths resolving
beneath `/tmp` or `/var/tmp` (including symlink aliases), and stages every
service/delivery/poll effect boundary in the external receipt. Validation passes
25 focused tests, 517 comprehensive Python tests, 12 plugin tests, compilation,
diff hygiene, and active/goal planning audits. Narrow independent review
accepted the root selector, effect-stage ordering, and cleanup regression; no
systemd, provider, dispatch, or ingress effect occurred. The successor service
attempt remains unconsumed pending publication and fresh host preflight.

## Objective

Run one successor installed qualification from an owner-only disposable root
under user state that is visible to the supported `PrivateTmp=yes` unit, while
preserving every Plan 0074 provider, dispatch, identity, cleanup, and evidence
guard.

## Scope

- Add a source-only execution-root selector under
  `${XDG_STATE_HOME:-$HOME/.local/state}/codex-wake/qualification/` and prove
  owner-only custody. Do not change product service hardening.
- Keep the exact wheel export/build/install, isolated XDG application state,
  explicit no-source-runner managed-reader bootstrap, disabled-first source
  ordering, installed CLI lifecycle, loopback-only listener, frozen signed
  fixture, restart, polling convergence, and cleanup contracts from Plan 0074.
- Stage `service_install_start` before the effect and every subsequent service
  phase externally so a terminal failure remains locatable after safe cleanup.
- Permit exactly one successor service install/start attempt. No automatic
  retry follows any post-install failure.

## Non-goals and effect boundary

- No product runtime change, service sandbox relaxation, non-loopback bind,
  provider request/mutation, external ingress, wake dispatch, global install,
  release, deployment, or Cooper change.
- No reuse of the failed Plan 0074 execution root, wake identity, wheel, unit,
  fixture, or temporary environment.
- No weakening of `PrivateTmp`, source authority, secret custody, journal
  authority, cleanup census, or the failed-unit baseline comparison.

## Execution sequence

1. Test-drive the user-state root selector and effect-stage receipt; run the
   focused, comprehensive, plugin, compilation, diff, and planning tiers.
2. Obtain one narrow independent verification of the PrivateTmp/root fix and
   critical cleanup regression only.
3. Publish the exact clean candidate and re-read unit absence, port freedom,
   process absence, manager state, failed units, branch/tree, and remote tip.
4. Run the source-only qualifier once. Treat reaching service installation as
   consuming the successor attempt.
5. Preserve the sanitized receipt and fresh host cleanup census regardless of
   outcome. Do not retry a consumed failed attempt.
6. On acceptance, publish the verification artifact and complete #107 through
   its pull request and required CI. Only then make #108 ingress-eligible.

## Acceptance criteria

- The disposable execution root and executable/bootstrap paths resolve under
  the declared owner-only user-state qualification directory, not `/tmp`.
- Installed provenance binds the exact clean commit/tree/wheel/module and all
  entrypoints before the service effect.
- The supported unit becomes ready on exactly `127.0.0.1:8820`; installed
  readiness/status/support and PID/start/socket identity agree.
- Signed delivery results are `COMMITTED`, `DUPLICATE`, and post-restart
  `DUPLICATE`; provider-free polling adds no logical wake; dispatch remains
  absent.
- Cleanup proves the unit absent/inactive/disabled, MainPID zero, no matching
  reader/listener process, port released, temporary execution root removed,
  and the unrelated failed-unit baseline unchanged.
- The external receipt retains every completed setup, reader, arm, service,
  delivery, restart, polling, and cleanup stage without secrets.

## Stop conditions

Stop before service installation on any dirty/unpublished candidate, existing
unit, occupied port, matching process, unreachable manager, provenance gap,
provider-capable path, `/tmp` execution path, or incomplete preflight. After
service installation begins, any failure consumes the one successor attempt:
perform cleanup, retain evidence, and do not retry.

## Definition of done

One successor installed-service packet is accepted and fully cleaned up; #107
passes required CI and closes through its PR; branch/worktree/lane custody is
reconciled; and #108 becomes eligible for the required ingress skill.
