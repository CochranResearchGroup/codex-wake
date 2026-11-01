# Final broad review and bounded TDD | #444

One broad review compared frozen15f247e against main base
`289bb97ecf8a0382089819e4c4119bc5462e48d0` using
`git diff 289bb97ecf8a0382089819e4c4119bc5462e48d0...15f247e46a05d3be9818d9da7c59546e7756e1c2`.
It covered67 changed files/104 commits. It began after455/456/457/453 acceptance
and closure. Standards ran in an independent agent; Spec ran separately in
primary because a second reviewer slot was unavailable. There was no review loop.

## Standards

Accepted blockingP2 S1: discovery/poll MCP schemas required `job_id`, while
the public dispatcher rejected it. This violated the public-surface validation
requirements of policies0006/0016. Integration `4ffc53e` removes that field for
these two operations. Existing job-specific verbs retain their identity field.
Actual tools/list schema validation failed RED before the fix; real MCP dispatch
and API-result parity passed GREEN afterward;14 upgrade-job tests passed.
No other material standards violation or baseline smell was established.

## Spec

Accepted blockingP2 P1: after registry selection committed but its controller
result was lost, public advance could return only a disabled/expired stop state,
while public reconciliation lacked the existing promotion observer. Plan0193
lines65/68 require durable outcome reconciliation without duplicate effects.
Integration `9d045b1` exposes `promotion_observe` through the same public owner.
It observes exact registry/package evidence without replay, new work or allowance
renewal. Terminal stop states and original budgets remain unchanged; nonterminal
promotion settles from actual evidence; an uncommitted intent remains held.
Public API test failed RED with invalid mode. GREEN tests inject filesystem
commit-loss, disable, expiry, interruption and an uncommitted intent, observing
actual public build selection and unchanged budgets/registry. The initial test
setup missing an import is retained separately and is not claimed as the RED.

## Validation and bounded remediation

Exactly one TDD findings pass addressed S1 and P1. Final source9d045b1:
`PYTHONPATH=src <checker>/bin/python -m unittest discover -s tests -p 'test_upgrade_*.py' -q`
passed93 tests on Python3.12.13 (46.029s) and3.11.15 (37.718s). Pinnedruff0.14.2
undefined-name checks and fresh sdist/wheel packaging passed. No second review ran.

Before those narrow findings fixes, source15f247e passed the canonical local
comprehensive profile:7 gates,2026 tests/1 expected skip,493.341s unit runtime,
including packaging. The first checker stopped at setup because development
dependencies were absent; that receipt remains retained. An isolated checker
with declared dev/MCP dependencies resolved setup before checks ran. The final
findings changes were verified by the affected public regression suite, lint
and packaging; the full2026 count is not represented as a full rerun of9d045b1.

Command: `<checker>/bin/python scripts/local_validation.py --repo . --runtime <checker>/bin/python --tier comprehensive --timeout 900 --test-temp-root /dev/shm --receipt <private-receipt>`.
RAM test temporary storage qualifies functional source behavior; separate
physical WSL package/account/history/promotion/rollback evidence is in
[native acceptance](native453-acceptance.md). Local Linux checks replace hosted
Actions per cost policy; only3.12 ran the full comprehensive profile, while both
supported Python versions ran the final affected suite. Native installed prefix
31f06f7/c13e793 and final source9d045b1 are distinct identified controller states;
final observational/schema fixes have public local tests, no production install.

Private review/adjudication receipt: testing/upgrade-bot444/primary/final-review-round1.json.
Native independent source review is separate from this final broad review.
Counts: Standards1 acceptedP2 resolved; Spec1 acceptedP2 resolved; review1/TDD1.
