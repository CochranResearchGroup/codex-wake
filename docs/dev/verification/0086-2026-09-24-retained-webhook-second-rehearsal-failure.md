# Retained webhook second rehearsal failure

Date: 2026-09-24
Issue: #141
Plan: `docs/dev/plans/0091-2026-09-24-retained-webhook-rollout-second-successor.md`
Outcome: BLOCKED_ROLLED_BACK

## Frozen identity and qualification

- Canonical candidate: `3a53c0a8aca490928ef26a986b4584b2f688c7df`.
- Wheel SHA-256:
  `4010d4e64133533770ed835167ad22bd83df39ec7915b316a5b4a9fe8f3ca9ee`.
- Focused managed-webhook tier: 91 passed; comprehensive Python tier: 688
  passed; provider-free plugin tier: 12 passed.
- Compilation, diff/planning audits, isolated installed-wheel qualification,
  and the plan PR's hosted Python 3.11 and 3.12 gates passed.

## Corrected ordering and delivery

Fresh v4 identities, roots, unit names, HMACs, manifest, and counters were
used. One dry-run projected CREATE from an absent inventory. One apply created
hook `685357376` with exact active generation-2 readback while both services
were absent. The dispatch-disabled poller then established the managed-reader
capability, the wake was registered idempotently as
`wake_b069ee1528a84b16856fca4eb84b5de2`, and the listener first started only
after provider authority was active.

All five ingress paths rejected a correctly shaped unsigned workflow request
with HTTP 401. The one authorized rerun targeted main workflow run
`36089822519`, attempt 2, at exact candidate `3a53c0a`; both hosted Python
gates passed. GitHub's completed signed delivery `3844654355179372500`
returned HTTP 200, entered the journal, and the wake fired. Dispatch remained
zero. The earlier create-time ping failed while the listener was intentionally
absent and was not counted as delivery evidence.

## Polling blocker

The polling plane returned `GITHUB_POLL_BUDGET_EXHAUSTED` and managed health
remained `polling_fallback=UNOBSERVED`. The configured positive-only source has
`max_requests=200`; the workflow currently has 334 retained runs. The adapter
walks historical pages and exact attempts until complete pagination even after
it has found verified qualifying positive evidence. It therefore consumed its
bounded request budget before completing the scan. No polling cycle could be
claimed, so the plan's two-cycle gate failed and no retained owner started.

## Exact rollback and retained credential

Cleanup preview bound the exact owner, repository, hook, service, generation,
and desired fingerprint. One disable produced `DISABLED_PROVEN`; one delete
produced `DELETED_PROVEN`. Managed cleanup removed the listener; the exact
poller was uninstalled. Fresh readback reports zero matching hooks, zero v4
units, and no listener on port 8820. The rehearsal environment containing its
fresh HMAC was securely retired; the never-started retained environment was
preserved as evidence.

The durable repository-scoped read credential remains owner-owned with mode
0600 at `/home/ecochran76/.config/codex-wake/credentials/github-read-token`.
It was not printed, deleted, or revoked. Administrative material was never
stored in either long-running service environment.

Observed counters are:

- provider create/disable/delete: `1/1/1`
- provider update/redelivery: `0/0`
- explicit workflow rerun: `1`
- rehearsal install-start/stop-uninstall: `1/1`
- retained install-start/restart: `0/0`
- ingress mutation: `0`
- dispatch: `0`

## Required successor correction

Plan 0092 owns the successor. It must first prove through the public polling
interface that an individually verified qualifying positive may return without
claiming exhaustive negative coverage. No-positive incomplete scans must remain
bounded and degraded. Only a fully requalified fresh candidate may receive new
v5 rollout identities and effect counters.
