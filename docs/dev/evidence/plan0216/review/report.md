# Single broad review — pass 1

Frozen source afd0061f, base fa2363c24bf921ecf0bd8390739e96041e620e8f.
Independent reviewers /root/review_standards216 and /root/review_spec216.
Diff and commit list are adjacent. No second broad review is authorized.

## Standards

S1, P2, **blocking**: observer inventory hands work to ControllerTabs.execute,
which creates a fresh ten-second deadline. Root verified observer.py:381 and
controller_tabs.py:112. This violates the bounded/fair work contract and plan
budget precedence; retain the caller deadline through the inventory seam.

## Spec

P1, P1, **blocking**: native activity rebinds by home basename and thread alone,
not exact original source. Root verified tab_traits.py native target contains
full home/home generation/peer/socket generation while observer.py:411 loses it.
Spec requires namespace/replacement fencing. A different same-basename home with
copied thread must never supply an existing attachment's activity.

P2, P1, **blocking**: deadline-skipped rows are directly retained, counted as
represented, then can be timestamp-renewed from native cache. Root verified
observer.py:366–422. Spec requires skipped/overloaded work unknown/degraded.

Accepted: Standards 1 (highest P2); Spec 2 (highest P1). No rejected, backlog or
needs-evidence findings. One bounded TDD pass addresses these three findings.
Existing-host lack of a natural native transition remains an explicit limit,
not a fixture pass or a new review finding.
