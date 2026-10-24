# Plan0173 | Default Own-Session Permissions

State: OPEN
Lane: P173
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/310
Owner: primary / ecochran76
Plan version: v1

## Objective and Authority

A verified session has appropriate access to itself by default. User explicitly
requested issue creation and diagnosis/fix, then clarified this permissions policy.
Scope: native-attested self-refresh configuration and admission on provisioned
host profiles; preserve separate effect scope, explicit denials, deadlines,
accounting, monitor ownership and cross-session restrictions. No allocation
renewal, unrelated lane edits or implicit shared-server authorization.

## Current State

Fresh branch fix/310-own-session-access at origin/main 7ef73b1. Root main and
other lifecycle worktrees are untouched. Issue310 is open and read back; overlap
with issue282 is recorded. Installed CLI is 0.19.1, source base is 0.20.0 candidate.
The MCP configuration failure reproduced twice on the actual session, and a
0.4-second CommandRunner regression reproduces the exact same error.

## Diagnosis

Ranked hypotheses shown before remediation: (1) exact-UUID allowlisting defeats
native self ownership, (2) incorrect MCP caller binding, (3) stale installation.
Host metadata resolves the actual caller; the installed profile already has
explicit effect-scope approval, but its two historical caller entries exclude
this session. Current origin/main retains that exact allowlist requirement.

## Acceptance and Execution

One primary-owned serialized lane. Independent fixture checks can run in parallel;
permission decisions, integration and runtime acceptance stay serialized.

- Red/green at the real MCP CommandRunner seam, followed by the original probe.
- New native callers can inspect and request their own approved refresh without
  policy-file mutation. Explicit caller denials and a default-off override win.
- Missing/conflicting native metadata, other-session targets, unapproved effect
  scope and malformed policy remain denied. CLI claims alone grant nothing.
- Queued self authority survives controller restart/revalidation, but revocation
  and profile changes stop effects. Existing fixed-intent fingerprints persist.
- Preserve emergency pause, checkpoint hash/workspace checks, expiry, resource
  proof and goal/accounting controls; add no provider calls to fixture tests.
- Focused and full relevant tests, independent authority review, source/runtime
  evidence, and truthfully separate deployment from source acceptance.

## Evidence

Red: PYTHONPATH=src <installed-python> -m unittest discover -s tests
-p test_session_self_permissions.py -v: exact configuration_unavailable refusal.
Live policy was inspected read-only; no production grants or refresh were changed.


## Source implementation and validation

Central permission resolution applies explicit entries before the default. The
host attests native identity and exact target, then dispatches a private bounded
child; the agent schema has no permission or attestation switch. Private queued
receipts retain the admission evidence for independent controller revalidation.
No policy registry, budget, objective or installed service was mutated.

The first in-process implementation failed independent review: a held emergency
lock bypassed the MCP timeout. Retained regressions for a held lock and FIFO
checkpoint went RED, then GREEN after restoring the bounded subprocess boundary.
Independent reviewer /root/review_self_access accepted this correction after
running both real blocking probes and checking authority/revocation paths.

Focused results: 11 own-session tests, 12 shared-refresh tests (including an
independent controller with native-self admission), and 4 public stdio MCP tests
PASS. Public transport identity is injected fixture evidence. The installed
0.19.1 service has not been upgraded, so the original live probe remains a
deployment acceptance gate. Full-suite result and PR tracked below.


## Review delivery

Draft PR311: https://github.com/CochranResearchGroup/codex-wake/pull/311.
Source checkpoint 6d99a4b30bda81de1e9a657950d0d0856551c942 pushed and remote
read back. Isolated wheel environment passes all 11 permission tests; the first
wheel run lacked declared MCP dependencies, corrected by installing the wheel's
[mcp] extra. No production install was involved. Final public stdio suite passes
4 tests after tool-description updates. Pinned Ruff, compilation, policy wiring
and diff whitespace checks pass. Full suite and Python3.11/3.12 PR CI pending.

Memory disposition: forbidden. Developer requires explicit user request for
memory writes; no such request occurred. A machine-readable no-write receipt
exists in user state under codex-wake-310/memory-disposition.json; no Graphiti
write was attempted.
