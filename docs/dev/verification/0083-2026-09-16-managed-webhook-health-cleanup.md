# Managed webhook health and cleanup acceptance

Date: 2026-09-16
Issue: #140
Feature PR: #149
Canonical commit: `b0d4a8517f6075e1b848d94a5aa471010cecba46`
Accepted feature tip: `f0fe41d746ff9ad9356fa031e5b16aedc76a63b7`

## Accepted outcome

- Health projects listener, provider object, provider delivery, polling
  fallback, and dispatch independently. Provider failure does not suppress
  locally observable health, and health never authorizes cleanup.
- Cleanup is preview-first and explicitly armed. It binds one exact owner,
  repository, hook, service, generation, and fingerprint; records intent before
  one mutation; reads back independently; and retains bounded sanitized
  tombstones and ambiguity state.
- Disable and delete are fenced against concurrent listener enablement,
  generic reconciliation, secret rotation, and runtime admission.
- Local absence requires stopped/disabled unit state, zero unit PIDs, an empty
  cgroup or exact process census, and no IPv4 or IPv6 listener on the managed
  port. Both supported executable and module launch forms are recognized.

## Validation evidence

- Comprehensive Python tier: 665 tests passed.
- OpenClaw plugin tier: 12 tests passed.
- Python compilation and Git diff hygiene passed.
- Active planning, goal-contract, and exact active-lane audits passed.
- The isolated candidate wheel ran the provider-free qualification from its
  installed package. Fixture disable/delete each ran once; the production
  absence adapter returned `PROVEN_ABSENT`; retained journal, wake, checkpoint,
  and polling fixtures under the wake root were unchanged; all external-effect
  counters were zero.
- Independent specialist review accepted the final tree after reproducing and
  closing listener-lock recursion, owner-scope, health-coupling, process-census,
  and retention-fixture findings.
- Custody PR #148 passed hosted run `35177281729` and merged as
  `2d6d573c1aaedff957896a3a9ea6c678f4914647`.
- Feature PR #149 passed Python 3.11 and 3.12 on hosted run `35177389023`,
  squash-merged as the canonical commit above, and closed #140.

## Authority boundary

The qualification used injected provider and local mutation fixtures plus a
read-only production absence adapter. Rotation was `preview_only` and lifecycle
execution was `not_included`. No live provider, service, secret, ingress,
installed-runtime, release, redelivery, or dispatch effect occurred. C4 #141
requires a fresh explicit retained-activation gate.
