# Provider-free poll projection recovery

State: OPEN
Lane: P53-C4-v3
Issue: #107
Predecessor: Plan 0075 (`FAILED_SAFE`)
Branch: `chore/issue-107-installed-webhook-canary`
Target: `main`
Integration: `squash`

## Current state

Plan 0075's exact installed candidate `2cdfaf7` proved the service becomes
ready from an owner-only user-state root, survives a manual restart with a new
PID/start identity, and returns `COMMITTED`, `DUPLICATE`, and post-restart
`DUPLICATE` for the frozen signed occurrence. Its final provider-free poll
subprocess returned zero, committed no additional receipt, and reserved the
expected match, but strict convergence failed because its explicit
`SQLiteSignalModule` had no record publisher. Durable desired state became
`firing` while the firing projection remained pending.

The unit and matching processes are absent, port 8820 is freshly bindable, the
original receipt/root remain retained, and no provider, dispatch, or ingress
effect occurred. Independent read-only diagnosis accepted one exact correction:
construct the fixture module with `WakeRecordPublisher(root,
current_reader_capability(root))`, matching the product daemon's default open.

## Objective

Correct and prove the source-only provider-free polling projection, then accept
#107 from the retained installed-service evidence plus the repaired polling
proof and fresh cleanup readback, without repeating the service effect.

## Scope

- Test-drive publisher-bearing fixture construction and strict pending-to-firing
  convergence with exactly one receipt, one match, and zero dispatch.
- Preserve the injected local GitHub client factory and prove no production
  provider client path is reachable.
- Retain Plan 0075's original receipt and recovery root unchanged as failure
  evidence.
- Produce one sanitized verification artifact that separates retained service
  evidence, repaired source-only polling evidence, and fresh cleanup evidence.
- Complete issue #107 through its linked pull request and required CI if every
  acceptance axis is current.

## Non-goals and effect boundary

- No service install/start/restart, listener bind, loopback delivery, provider
  request, external ingress, wake dispatch, global install, release, deployment,
  or Cooper change.
- No rerun against or mutation of the retained Plan 0075 wake root or journal.
- No claim that later ambient user-manager failed-unit changes alter the exact
  contemporaneous before/after baseline in the retained receipt.

## Execution sequence

1. Add a failing focused test for publisher-bearing generated polling code and
   strict firing projection; implement only the accepted correction.
2. Run focused, comprehensive, plugin, compilation, diff, and planning tiers.
3. Obtain one closed-world independent verification of the publisher wiring,
   provider exclusion, dispatch absence, and evidence composition.
4. Publish the exact clean candidate and complete the issue-linked pull request
   after both required CI release gates pass.
5. Preserve the retained failed receipt/root and publish a sanitized verification
   artifact; do not repeat the installed service attempt.

## Acceptance criteria

- The explicit fixture module uses a current-process `WakeRecordPublisher` for
  the exact isolated wake root, matching the daemon default path.
- Provider-free polling retains one verified occurrence, creates one match,
  projects pending to firing, and reports one fired wake with zero dispatch.
- The injected local client remains the only GitHub read seam; production
  provider and live dispatch call counts remain zero.
- Retained Plan 0075 evidence continues to prove installed provenance,
  readiness, restart identity, three delivery results, unit/process removal,
  and its exact contemporaneous failed-unit baseline.
- Fresh cleanup readback proves the exact unit absent/inactive, PID zero, no
  matching process/listener, and port 8820 bindable. The private recovery root
  remains retained.

## Stop conditions

Stop on any mutation of retained evidence, provider-capable path, dispatch,
service action, dirty/unpublished candidate, inability to project firing with
the explicit publisher, or evidence that invalidates a retained service axis.
No service-effect retry is permitted by this plan.

## Definition of done

The repaired provider-free projection and retained service evidence jointly
satisfy #107; its pull request passes required CI and merges; canonical main,
issue closure, branch/worktree cleanup, and lane custody are reconciled; and
#108 becomes ingress-eligible.
