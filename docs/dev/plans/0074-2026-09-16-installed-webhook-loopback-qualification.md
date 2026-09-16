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

Source-only runner checkpoint `91797143c11b8a3563fc329111a267fdd8cdf4ef`
adds the explicit-refusal installed qualification runner and five hermetic
contract tests. Focused 5/5, comprehensive 497/497, plugin 12/12,
compilation, diff hygiene, and the active planning audit passed. It has not
been run with `--execute`: no wheel install, unit, listener, provider access,
ingress, polling, or dispatch occurred. The next exact gate is an independent
closed-world source review followed by the fresh live preflight specified in
this plan; the one service attempt remains unconsumed.

## Objective

Build and hash one wheel from the exact candidate commit, install it only in a
fresh isolated environment, and prove the supported loopback listener service
end to end with provider-free signed fixtures, durable duplicate/restart and
polling convergence, installed readiness/status/support, and complete cleanup.

## Scope and frozen method

- Add one source-only `scripts/webhook_installed_smoke.py` runner with narrow
  tests. It is not packaged and requires an explicit execution flag.
- The runner builds the candidate wheel, records its SHA-256, and installs it
  into a fresh temporary virtual environment. All configuration and lifecycle
  commands use the installed `codex-wake`; the service uses the exact installed
  `codex-wake-github-webhook` path.
- Use one fresh owner-only wake root, source instance
  `p53-c4-installed-canary`, canonical service name, `127.0.0.1:8820`, and the
  real user-systemd unit directory. Any occupied port, existing unit, foreign
  file, or unavailable user manager blocks before the install attempt.
- Configure the GitHub source and webhook listener and arm one GitHub completed
  wake through installed commands without contacting GitHub. Do not start the
  wake daemon.
- Provide an ephemeral, untracked `sitecustomize.py` only through `PYTHONPATH`
  in the owner-only service environment. It patches the installed listener's
  provider-attempt factory to a deterministic in-memory fixture. It adds no
  product flag, endpoint, alternate host, or packaged fixture path.
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
