# Public ingress certificate-race successor

State: CLOSED
Lane: P53-C5R1
Issue: #108
Branch: `fix/issue-108-public-qualification-retry-1`
Target: `main`
Integration: `squash`
Predecessor: `docs/dev/plans/0078-2026-09-16-cooper-webhook-ingress-publication.md`

## Current state

The qualification-only successor is accepted. Exact canonical candidate
`3a4dbd44af9231848b722fbc5127affe9412bdda` passed raw, local, Cooper-Host,
and public certificate-verifying HTTPS checkpoints in order with one frozen
occurrence, zero provider factory calls, zero dispatch calls, and leak-free
responses. Cleanup proved the exact unit/process/listener absent and removed
the successor root; a fresh OS census independently confirmed that result.
Verification 0079 records both the accepted receipt and the preserved first
failure. The public route remains durable and unchanged for #109.

The historical pre-successor state follows.

Plan 0078 consumed its one canary establishment and one bastion publication.
Raw, local, and Cooper-Host checkpoints passed; the first public TLS handshake
failed with `SSLError` and was not retried. The reviewed exact route is now
durable on bastion at commit `4e7bc6966870a592fc8b30c17889269e98134d0a`,
the route artifact SHA-256 is
`ffcb4efabc644d9da705e3369be043de28fe5c8f3b4850681e002ca2f5a68a64`,
and a read-only ACME-store inspection now finds the exact hostname certificate.

The failed canary unit is absent and a fresh `ss`/`lsof`/process readback proves
port 8820 and the process identity are clear. The failed root and external
receipt remain preserved. The immediate cleanup receipt was conservative:
`port_is_free()` bind-probed without server-equivalent address-reuse semantics,
so connected TCP teardown state could report false occupancy after uninstall.
One focused tested correction and one new qualification-only canary remain.

Checkpoint `046fbde773bdae3e74cc6cb76c5059110e4ffa31` now implements
the bounded correction. Shared C4 cleanup remains strict; only C5 opts into
server-equivalent `SO_REUSEADDR` port proof and classifies unrelated failed-unit
delta as noncausal evidence. Exact unit, PID, process, active-listener, and port
collision conditions remain blocking. Forty-nine focused installed/C5 tests,
compilation, and diff hygiene pass. Comprehensive validation, integration, and
the live successor remain.

The 541-test comprehensive tier passed on its first retained retry. Its first
run exposed an unrelated provider-timeout test that returned `COMMIT_FAILED` on
the second request; the exact test passed immediately in isolation and the
unchanged full suite then passed. This is retained as a pre-existing timing
flake observation rather than erased or attributed to the cleanup-only diff.
The plugin tier (12 tests), planning/goal audits, and closed-world successor
review also pass. Hosted CI and live execution remain.

## Objective

Correct the cleanup port-release proof without weakening real-listener
detection, integrate that correction through required CI, then run one fresh
provider-free canary through raw, local, Cooper-Host, and existing public HTTPS
routing. Prove the already-published route and provisioned certificate without
copying config, restarting either Traefik, mutating GitHub, or dispatching work.

## Authority and bounds

- This is retry 1 within the operator's earlier allowance of up to five retries;
  this plan authorizes only this one complete successor attempt.
- `c5_successor_canary_establishments: 1`;
  `public_qualification_attempts: 1`; no failed checkpoint is repeated.
- `external_ingress_publications: 0`; `traefik_restarts: 0`;
  `route_config_writes: 0`.
- `github_provider_reads: 0`; `github_provider_mutations: 0`;
  `live_dispatch_attempts: 0`; `global_install_mutations: 0`.
- The primary owns integration, live execution, acceptance, cleanup, and the
  issue disposition. One implementation worker may edit only the cleanup seam
  and its tests; one read-only reviewer may verify the frozen successor.
- The existing failed root is immutable evidence and is never reused.

## Scope

- Add one regression at the real cleanup port-availability seam that proves
  teardown/TIME_WAIT state does not masquerade as a live listener while a real
  listener still blocks the port.
- Apply the smallest server-equivalent availability correction shared by the
  installed qualification helpers.
- Run focused, comprehensive, plugin, compilation, diff, planning, and hosted
  CI gates before any new canary.
- Establish a fresh owner-only canary from exact canonical main and execute the
  existing ordered four-checkpoint runner unchanged apart from the accepted
  cleanup correction.
- Preserve a sanitized external receipt and publish a truthful #108 closeout or
  failed-successor disposition.

## Non-goals

- No bastion copy, Traefik restart, DNS, certificate, firewall, Authelia,
  inventory, renderer, Cooper, or route mutation.
- No GitHub webhook creation, provider request, live delivery, dispatch,
  release, tag, non-loopback bind, global install, or reuse/deletion of failed
  Plan 0078 evidence.
- No acceptance inferred from certificate-store presence alone.

## Execution sequence

1. Test-drive the cleanup availability invariant, including true-listener
   rejection; run focused and comprehensive validation and independent
   closed-world review.
2. Merge the correction through a linked pull request and both hosted Python
   gates. Re-anchor the active lane to the accepted implementation commit.
3. Re-read canonical Codex Wake and Cooper refs, bastion commit/config hash,
   certificate presence, exact route selectors, failed-unit baseline, unit and
   process absence, and port 8820 availability. Stop on route/config drift.
4. Prepare and start one fresh isolated canary. Execute raw, local,
   Cooper-Host, and public checkpoints once each in order. Do not write or
   restart ingress infrastructure.
5. Run cleanup once. Preserve the root on any uncertainty, then take a fresh
   OS socket/process/unit readback without upgrading an uncertain receipt to
   accepted evidence.
6. Publish the verification or failure artifact, reconcile Plan 0070, roadmap,
   runbook, issue, pull requests, branches, worktrees, and active-lane catalog.

## Acceptance criteria

- The regression fails under the old port probe and passes with the bounded
  correction; an actual listener remains detected as occupied.
- Canonical Codex Wake and the installed wheel agree, and the existing local
  and bastion route artifacts match their reviewed digests with no mutation.
- One fresh occurrence commits raw and is duplicate through local,
  Cooper-Host, and certificate-verifying public HTTPS; unsigned input is
  rejected and non-exact proxy selectors remain absent.
- Request/body identity and leak checks remain stable at all four checkpoints;
  provider factory and dispatch counters remain zero.
- Cleanup proves the exact unit, PID identity, process, and listening socket
  absent without treating ordinary connected-socket teardown as a listener.

## Stop conditions

Stop before the canary on dirty canonical sources, route/config/hash drift,
missing exact hostname certificate, occupied port, matching unit/process,
provider-capable fixture behavior, or any required infrastructure mutation.
After start, any failed checkpoint or cleanup uncertainty ends this successor;
preserve evidence and do not retry inside this plan.

## Definition of done

The cleanup correction is integrated through required CI; the one successor is
truthfully accepted or failed from durable evidence; the canary is absent with
a fresh OS readback; no ingress/provider/dispatch effect occurred; and issue
#108 plus all plan, roadmap, runbook, Git, and active-lane custody surfaces are
reconciled to the observed outcome.
