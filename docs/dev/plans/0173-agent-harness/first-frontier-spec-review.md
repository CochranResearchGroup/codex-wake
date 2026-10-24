# First frontier: specification and ticket review

State: APPROVED_AND_PUBLISHED; implementation not started
Owner: ecochran76
Work items: CW-HARNESS-173/HF-02, HF-07, HF-13

## Proposed vertical slices

| Existing ticket | Blocked by | End-to-end delivery | Specification |
| --- | --- | --- | --- |
| HF-02 | HF-01 design complete | Enroll one verified conversation, inspect its durable identity, suppress automatic re-enrollment after operator unenrollment, and recover the record through the same CLI/MCP policy boundary. | [Inventory](hf-02-spec.md) |
| HF-07 | HF-01 design complete | Approve a bounded brief, admit one assignment against its revision, and reconstruct that pin without silently adopting a changed brief. | [Task briefs](hf-07-spec.md) |
| HF-13 | HF-01 design complete | Register explicit wake ownership/startup policy, preserve it through recovery, and apply owner completion or capability admission with a durable observable outcome. | [Wake policy](hf-13-spec.md) |

These retain the existing ticket granularity. Each is one complete behavior,
including durable state, public callers and verification. No schema-only or
UI-only prefactoring ticket is added. If implementation evidence shows a slice
cannot fit one context, split by demonstrable behavior before beginning it.

## Public testing seams for review

- Inventory: existing session discovery/caller verification into shared CLI/MCP
  inventory handlers, with injected exact runtime evidence and disposable state.
- Task briefs: assignment admission and brief-management callers, with trusted
  authority fixtures and restart/revision races.
- Wake policy: wake registration through reconstruction and dispatcher admission,
  with injected clock, owner event and adapter; inspect effects and intent records.

Use the highest public caller seam for each feature. Additive leaf modules hide
consequential behavior; do not build a generic harness framework first. Real
provider sessions, host-policy changes and a machine reboot are unnecessary for
these source tests and are not granted by this review packet.

## Parallel ownership and integration

The three tickets have no mutual semantic prerequisite. HF-07 does not require
inventory adoption; HF-13 consumes exact opaque owner references and trusted
completion events, not a completed workflow VM. Shared hub/profile edits remain
with the primary; workers own disjoint leaves and focused tests. No workers have
been launched for this review packet.

Current origin/main was read at f96f4c8, including the accounting-timeout recovery
repair. Rebase implementation lanes onto a fresh readback, not this older planning
branch's source snapshot. [#310](https://github.com/CochranResearchGroup/codex-wake/issues/310)
owns default verified own-session access. HF-02 consumes its policy boundary;
this plan does not duplicate that repair. #282 remains operational self-refresh
scope and #270 remains prior enforcement investigation/history.

HF-13 declares startup policy now. HF-18/19/20 later qualify missing execution
paths; requesting unsupported startup returns a precise result. Shipping that
policy ticket does not mean full create/load/run execution already works.

## Review decisions

Confirm that the three public testing seams match the intended behavior, and
whether the existing three-ticket granularity/blocking edges should stand or be
merged/split. These are the review checkpoints required by to-spec (testing seam)
and to-tickets (granularity and blocking edges); they do not reopen the completed
product interview. All prior operator choices are carried forward.

After this review, publish the specs and reconciled ticket bodies to the canonical
GitHub tracker with the configured ready-for-agent label, retaining existing local
locators. Do not create a second copy of the 32-ticket backlog. Only these three
reviewed specs/tickets are in this bounded publishing slice. Creation and label
capabilities were checked for the explicit owned target, but no tracker mutation
has occurred in preparing this packet.

## Planning validation and limits

All three specs contain problem, solution, user stories, implementation/testing
decisions and non-goals. Existing ticket links point at their proposed spec.
Local link, policy-wiring and whitespace checks validate this documentation;
no runtime tests or implementation acceptance are claimed. Definition of done
for this packet is a reviewable specification and reconciled slice map; public
tracker publication follows the stated review, not another broad interview.

## Publication readback

Operator approved the seams and breakdown. Published #315 (HF-02), #316 (HF-07),
#317 (HF-13), each open with enhancement and ready-for-agent labels. No separate
parent issues were created. Shared hub edits remain serialized.
