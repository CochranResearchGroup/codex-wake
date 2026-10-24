# Prepare the0.20.0 multi-runtime candidate

State: OPEN
Ticket state: IN_PROGRESS
Owner: ecochran76
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/308
Lane: P172-REL
Branch: chore/0172-release-candidate
Base: cf1ca8a
Target: origin/main
Integration: squash_pr

## Outcome and authority

The user's “next” continues the integrated Plan0172 work into release preparation.
Prepare a versioned0.20.0 candidate and reviewable PR. No tag/public release,
package upload, production installation, grant/service mutation or new provider
input is authorized by this packet. Earlier candidate live tests remain historical
proof for the unchanged runtime implementation; version-only qualification must
not be called a new live provider test.

## Tickets and parallel ownership

| Ticket | Owner/surface | State | Blocking edge |
| --- | --- | --- | --- |
| REL-01 | primary: pyproject/package version, isolated build/install/CLI controls | DONE | none |
| REL-02 | /root/release_notes: release notes and README link only | DONE | none |
| REL-03 | primary: serial reconciliation, source/artifact comparison, PR/CI | IN_PROGRESS | REL-01 + REL-02 |

Two active agents, no nested workers. Separate worktrees from canonical main
cf1ca8a; primary owns shared plan/catalog/authority and integration. Worker branch
is docs/0172-release-notes. No unrelated original-main policy commits included.

## Acceptance

- [x] Aligned0.20.0 distribution and runtime versions; schema7/legacy reader boundary documented.
- [x] Notes preserve qualified versions/routes, independent work claims, default wait and explicit unsupported modes.
- [x] Build/install non-editably into a private candidate prefix; compare every source/installed module with the wheel.
- [x] Provider-free installed version/schema/CLI/MCP and wake-control checks pass with isolated fixture state.
- [ ] Primary reconciles worker packet, publishes coherent PR and records required matrix CI on exact head.

## Validation and stop rules

Use existing provider-free executable qualification scripts and existing version
reporting checks; no new shallow version tests. Target each focused check within
60seconds; installed protocol/control smokes within their existing bounds. CI
retains its conservative Python3.11/3.12 release-gates classification. Any artifact
mismatch, unexplained regression or changed runtime bytes beyond version metadata
stops qualification for review. Failed receipts are retained. A prepared/integrated
candidate is separate from published release and installed production authority.

Definition of done: a source-bound release-preparation packet with exact candidate
identity, reviewable notes, passing installed checks and required PR CI. Broader
Plan0172 remains open for separately scoped publishing/rollout and other runtimes.


## Local candidate result

Worker04e9ab7 accepted/reconciled asd7291e6 after source/notes review. Final wheel
4d1e243689bd85049af06061b3c52920755182baa08c9fd35f1d23eedf2d1c6f,
version0.20.0; all121 source/wheel/installed modules match. Final installed MCP
smoke PASS5.562s with32 tools and actual fixture claim/reply; wake controls PASS;
product smoke PASS. Preliminary clock_anomaly and retention-refusal samples stay
retained; no bypass or forced deletion. No new live provider qualification is
claimed. Required PR CI remains the integration gate.
[Receipt](../../evidence/plan0172/release-candidate-0.20.0.json).
