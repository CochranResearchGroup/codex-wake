# Plan 0056: Signal Work Model-Routing Calibration

Status: OPEN

Issue: `CochranResearchGroup/codex-wake#10`

Branch: `chore/issue-10-model-calibration`

## Outcome

Produce a bounded, evidence-linked routing calibration from the representative
signal work already frozen by Plan 0049, and retain the balanced defaults
unless the available samples support a narrower change without inference.

## Current state

Plan 0049 froze adapter implementation, fixture construction, and fresh
independent verification as the three task families before execution, with a
six-unit ceiling and cumulative repair accounting. Plans 0052 through 0054,
Git history, test receipts, review findings, and agent closeouts now provide
the available completed samples. Effective-model and measured allocation
counters were not exposed and must remain explicitly unknown.

## Frozen comparison window

- Workload identities: issue #6 filesystem adapter and fixtures; issue #7
  GitHub polling adapter and fixtures; fresh independent reviews for #6 and #8.
- Requested routes: implementation on the recorded standard or specialist
  model/effort; verification on `gpt-5.6-luna` medium.
- Topology: one exclusive writer plus primary reconciliation; one fresh
  read-only reviewer; no nested delegation.
- Quality floor: accepted issue criteria, both Python release tiers, plugin
  tests, no unresolved blocking finding, and no gated live effect.
- Accounting window: lane-registration commit through accepted feature commit,
  including failed tests, reviewer findings, repairs, primary intervention,
  rebase, and validation. Git elapsed time is a labeled wall-clock proxy only.
- Stop/promotion: at most six units and two per family; fewer than three valid
  comparable families or missing causal/allocation evidence yields an honest
  inconclusive result and retains balanced defaults.

## Scope and acceptance

- Extract exact sample identities, requested/effective route, context,
  topology, outcome, defects, interventions, elapsed proxy, and allocation
  availability from durable evidence.
- Keep retries, repair, replacement, and primary reconciliation in each sample.
- Separate observed facts from inference; do not attribute concurrency time or
  shared-account consumption to a model.
- Recommend a repo-default change only if the frozen promotion rule is met. Any
  such change is a separate serialized issue and pull request after #9.
- Preserve primary ownership of architecture, shared schemas, authority,
  integration, and final acceptance.

## Non-goals

No new model runs solely to improve the result, no widened sample, no policy or
default mutation in this branch, and no provider, dispatch, install, deploy,
tag, or release effect.

## Execution and definition of done

Use `gpt-5.6-luna` medium for bounded evidence extraction and comparison, with
deterministic Git/test locators. The primary validates every locator and owns
the conclusion. The issue is done when a compact calibration artifact covers
all frozen fields, states validity honestly, and its documentation-only pull
request passes CI and merges.
