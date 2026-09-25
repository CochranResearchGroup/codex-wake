# Retained webhook rollout rehearsal failure

Date: 2026-09-24
Issue: #141
Plan: `docs/dev/plans/0090-2026-09-22-retained-webhook-rollout-successor.md`
Outcome: BLOCKED_ROLLED_BACK

## Frozen identity and qualification

- Candidate commit:
  `919fd2affd88216e1b3fc5359e6c175899921797`
- Candidate wheel SHA-256:
  `ca72e92173e49f4f9351d92a591b437ba386f72163d4dbd11ba59641bf571080`
- Isolated runtime version: `0.5.2`.
- Focused managed-webhook tier: 91 tests passed.
- Comprehensive Python tier: 688 tests passed.
- Provider-free OpenClaw plugin tier: 12 tests passed.
- Compilation, diff hygiene, and installed provider-free qualification passed.
- A fresh repository-scoped read credential read the repository and Actions
  workflow runs while GitHub denied webhook-administration access, proving the
  intended separation from the administrative provider credential.

## Ingress and local runtime

The checked-in cooper ingress inventory validated without changes. Before the
listener started, raw loopback was absent and the local, cooper-host, bastion,
and public routes returned backend-unavailable responses. After the listener
started, all five paths reached the exact callback and rejected an unsigned
request with HTTP 401. The route remained exact `POST /github/webhook`; no
ingress mutation occurred.

Fresh rehearsal and retained roots used new owner identities, HMAC generations,
service names, and private environment files. The rehearsal listener bound
only `127.0.0.1:8820`; its poller was active with dispatch disabled. The
retained services were never installed or started.

## Provider effect and failure

The rehearsal dry-run projected exactly one create from an absent inventory.
One apply created GitHub hook `685323162`, event `workflow_run`, with exact
provider readback. No update or redelivery occurred.

The listener had been started before that create so GitHub would have a live
callback. Its runtime therefore captured the pre-create `UNMANAGED` binding.
The successful provider reconciliation changed the durable binding to `ACTIVE`
generation 2. Runtime admission intentionally requires its captured binding to
equal the current durable authority; the mismatch makes the admitted generation
set unavailable and fails closed. GitHub's ping and two workflow-run deliveries
therefore received HTTP 503. No delivery entered the journal, and provider
delivery remained unproven.

The frozen natural-delivery deadline expired without a new main-branch run.
The one authorized workflow trigger reran main workflow run `35758727705` as
attempt 2. Python 3.12 passed; Python 3.11 failed the timing-sensitive
`test_provider_timeout_runs_on_main_thread_and_fails_closed` assertion. The
workflow conclusion was `failure`, so the success-only polling predicate could
not converge. The trigger ceiling was exhausted and no retry was attempted.

## Exact rollback

Cleanup preview bound the exact owner, repository, hook, service, generation,
and desired fingerprint. One disable produced `DISABLED_PROVEN`; one delete
produced `DELETED_PROVEN`. Independent GitHub inventory then returned zero
hooks. The managed cleanup removed the rehearsal listener unit, and the exact
poller unit was uninstalled separately. Fresh readback reports both units
absent and no listener on port 8820.

Both fresh HMAC environment files and the local read-credential file were
securely retired after provider and service absence was proven. The token must
also be revoked at GitHub by its owner; local deletion cannot revoke a GitHub
credential. The old failed-attempt roots remain preserved as prior evidence.

Observed counters are:

- provider create/disable/delete: `1/1/1`
- provider update/redelivery: `0/0`
- workflow trigger: `1`
- rehearsal install-start/stop-uninstall: `1/1`
- retained install/start/restart: `0/0/0`
- ingress mutation: `0`
- dispatch: `0`

## Required successor correction

Do not resume this effect packet. A successor must use fresh owner identities,
credentials, HMAC generations, roots, units, and counters. It must either:

1. reconcile the provider object before starting the listener, accepting that
   the create-time ping may fail while the callback is not yet live; or
2. explicitly authorize exactly one post-create listener restart before any
   qualifying workflow delivery.

The successor also needs a fresh workflow-trigger bound and must preserve the
same zero-dispatch, no-redelivery, exact-cleanup, and ingress-read-only defaults.
The retained owner must not start until a new rehearsal proves signed delivery
and at least two fresh polling cycles.
