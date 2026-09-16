# Installed webhook loopback qualification

State: OPEN
Lane: P53-C4
Issue: #107
Branch: `chore/issue-107-installed-webhook-canary`
Target: `main`
Integration: `squash`

## Current state

Canonical main `f4a5404889250050cf12cd3f11c810b78b8aad20` contains
the accepted bounded HTTP transport, durable signed-ingest runtime, and
supported product lifecycle. Issues #104 through #106 are closed, no webhook
service/unit or port-8820 listener exists, and the active-lane catalog is
empty. The user systemd manager is reachable but degraded by unrelated
pre-existing failed units, so acceptance is scoped to one exact unit/PID/socket
rather than whole-manager health.

Correction checkpoint `703134b084cb4852a4e95886ffdcd3d0f0e99f05`
replaces the initial runner after one independent drift review produced the
accepted finding ledger C4-R01 through C4-R08 below. Fourteen hermetic tests,
including a real in-process HTTP/store/restart/polling sequence, now pass;
comprehensive Python validation is 506/506 and the plugin tier is 12/12.
Compilation and diff hygiene also pass. The first attempted planning-audit
command used a nonexistent repo-local script and is retained as a failed
validation attempt; the actual selector-bundle active planning audit passed,
while the lane audit correctly remains stale until this correction checkpoint
is recorded. It has not been run with `--execute`: no wheel install, unit,
listener, provider access, ingress, polling, port-8820 bind, or dispatch
occurred. The one service attempt remains unconsumed. The next exact gate is
closed-world verification of C4-R01 through C4-R08, then a fresh live preflight.

## Accepted review ledger

- `C4-R01`: cleanup must use the product uninstall path with the same
  environment and unit directory, preserve the owner-only recovery root on any
  failed or incomplete stop, and prove inactive/disabled/MainPID-zero, no
  matching process, released port, and an unchanged failed-unit baseline.
- `C4-R02`: one valid text secret, UUID deliveries, frozen body, and frozen
  authoritative `WorkflowRun`/terminal proof must drive webhook and polling;
  only the post-restart delivery id may change.
- `C4-R03`: the wake root alone is isolated; every lifecycle/readiness/status/
  support command must resolve the real user-manager unit namespace.
- `C4-R04`: reachable `degraded` manager state with return code 1 is allowed;
  unreachable states fail closed and exact unrelated failed units are compared
  after cleanup.
- `C4-R05`: fixture installation must be an explicit fail-closed bootstrap
  before the installed listener entrypoint, with installed-interpreter
  preflight and a negative subprocess tripwire.
- `C4-R06`: the wheel is built from an exact clean candidate export/cwd, excludes
  qualification material, and binds commit, tree, wheel, executable, installed
  module, interpreter, and version provenance.
- `C4-R07`: bounded readiness before and after manual restart must prove a new
  positive PID/start identity, exact executable/command, loopback socket inode,
  and zero automatic restarts; terminal failure consumes the single attempt.
- `C4-R08`: polling must prove the exact source reconciliation, unchanged single
  occurrence, one logical wake/publication, zero dispatch/submission, staged
  evidence, configuration/unit identity, cleanup baseline/delta, and nonzero
  outcome for any incomplete packet.

## Objective

Build and hash one wheel from the exact candidate commit, install it only in a
fresh isolated environment, and prove the supported loopback listener service
end to end with provider-free signed fixtures, durable duplicate/restart and
polling convergence, installed readiness/status/support, and complete cleanup.

## Scope and frozen method

- Add one source-only `scripts/webhook_installed_smoke.py` runner with narrow
  tests. It is not packaged and requires an explicit execution flag.
- The runner exports the exact clean candidate commit, builds the wheel from
  that export, records its SHA-256, and installs it into a fresh temporary
  virtual environment. All configuration and lifecycle commands use the
  installed `codex-wake`.
- Use one fresh owner-only wake root, source instance
  `p53-c4-installed-canary`, canonical service name, `127.0.0.1:8820`, and the
  real user-systemd unit directory. Any occupied port, existing unit, foreign
  file, or unavailable user manager blocks before the install attempt.
- Configure the GitHub source and webhook listener and arm one GitHub completed
  wake through installed commands without contacting GitHub. Do not start the
  wake daemon.
- Provide an ephemeral, untracked bootstrap only through the owner-only service
  environment. The exact installed interpreter must explicitly install and
  verify the deterministic provider-attempt fixture before invoking the exact
  installed listener entrypoint; bootstrap failure exits before either the
  listener or provider path. It adds no product flag, endpoint, alternate host,
  or packaged fixture path.
- Exercise real loopback signed HTTP through the installed service: first
  delivery `COMMITTED`, identical delivery `DUPLICATE`, stop/start, then a new
  delivery identifier for the same durable occurrence `DUPLICATE`.
- Use the isolated environment's installed Python/library to run a provider-free
  polling batch over the same armed signal and prove no second logical wake.
- Record only sanitized hashes, identities, status codes, counts, projections,
  and cleanup evidence. Never record secret values, the raw environment file,
  payload, provider credential, or fixture sidecar.

## Non-goals and effect boundary

- No GitHub request or mutation, public ingress, non-loopback bind, target
  dispatch, daemon start, normal wake-root mutation, global install, release,
  deployment, or Cooper change.
- No product test mode, fixture CLI flag, generic provider injection, alternate
  endpoint, or relaxation of source/service/secret/journal authority.
- The packet permits one service install/start attempt and no automatic retry.
  A failure retains sanitized evidence and proceeds directly to cleanup and
  replan.

## Execution sequence

1. Re-read current policy and verify canonical commit, issue state, empty lane
   overlap, user-manager reachability, absent exact unit, and free port 8820.
2. Implement the source-only runner test-first. Unit tests own default refusal,
   exact-target preflight, secret redaction, bounded subprocesses, and cleanup
   on every exit.
3. Run focused and comprehensive tests, plugin tests, compilation, diff hygiene,
   and planning audits. Obtain one independent closed-world review.
4. Build/hash/install the exact wheel and complete all non-effect setup before
   consuming the one installed-service attempt.
5. Execute install/start, readiness/status/support, signed commit/duplicates,
   restart, polling convergence, and exact readback once.
6. In `finally`, uninstall the unit, verify inactive/disabled/no MainPID, release
   port 8820, census processes, remove temporary roots/environment/fixture/logs,
   and confirm unrelated runtime state is unchanged.
7. Publish sanitized receipt, pass required CI, merge, close #107, reconcile
   plan/lane custody, and only then begin #108 with the ingress skill.

## Acceptance criteria

- The receipt binds canonical commit, wheel hash, installed executable hashes,
  interpreter, isolated root, exact source/unit, loopback tuple, and unit text
  hash without retaining secrets.
- Installed configuration, service status, readiness, and support agree on the
  exact enabled source and service owner.
- Real signed loopback responses are `COMMITTED`, delivery replay `DUPLICATE`,
  and post-restart occurrence replay `DUPLICATE`; polling convergence creates no
  second logical wake and dispatch remains absent.
- Restart readback proves a new service PID owns only 127.0.0.1:8820.
- Cleanup proves the exact unit absent/inactive/disabled, no matching process,
  port 8820 released, temporary roots removed, and pre-existing unrelated
  failed units unchanged.
- Focused/comprehensive/plugin tests, compilation, planning audits, independent
  review, and required Python 3.11/3.12 CI pass without erasing failures.

## Stop conditions

Stop before installation if the exact unit/path or port already exists, the
manager is unreachable, build/install/config/arm evidence is incomplete, the
fixture would enter the wheel, or any provider/dispatch path is possible. Stop
after any install/start failure, retain sanitized evidence, perform cleanup,
and replan without retry. Stop on secret output, non-loopback ownership,
unexpected PID/socket, duplicate logical wake, incomplete cleanup, or unrelated
runtime mutation.

## Definition of done

One exact installed service packet is accepted and fully cleaned up, PR and CI
close #107 from sanitized evidence, branch/worktree/lane custody is removed,
and #108 becomes eligible for one exact Cooper ingress publication through the
required ingress skill.
