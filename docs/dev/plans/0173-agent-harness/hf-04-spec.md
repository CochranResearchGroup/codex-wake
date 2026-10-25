# HF-04 resource ownership specification

State: OPEN
Owner: ecochran76 / primary coordinator; implementation worker hf04
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/331
Base: 37a5cbb
Dependencies: HF-02 validated on base

## Frozen scope

Declare exclusive cooperative custody of one existing canonical directory tree:
worktree, build_prefix or install_prefix. Any ancestor/descendant overlap conflicts,
including across kinds. A managed-agent record names the owner; fresh host-verified
native or Grok binding evidence qualifies its current process generation. A claim
is an admission prerequisite, not an OS filesystem permission or interception of
arbitrary same-user writes. Existing pane/lifecycle locks remain separate.

A claim survives controller failure and stale/lost owner evidence. No timeout,
PID disappearance or output silence releases it. Release by the verified current
owner requires the expected generation; operator recovery requires that generation
and an explicit reason. Only an operator may transfer custody, to a currently
verified managed owner. Transfer increments the generation and fences old tokens.
Released records and attributable transition history remain inspectable.

## Public seam and acceptance

ResourceClaims exposes claim, inspect, guard, release and transfer. A guard verifies
active custody, exact owner/process generation, fresh binding and canonical resource
identity, and holds the serialization lock through the caller's mutation. CLI/MCP
check is a point-in-time diagnostic, not a transferable grant to a later mutation.

- Competing worktree/build/install claims refuse before changing ownership.
- Parent and child conflicts apply in either acquisition order and across kinds.
- Foreign or stale tokens cannot enter a guarded mutation (marker remains absent).
- Explicit transfer/release is attributable, fences prior generation, and leaves
  unrelated claims/resources unchanged.
- Reconstructed controllers retain active claims; stale owner cannot trigger
  automatic takeover. Unknown/malformed store versions hold without rewriting.
- CLI/MCP uses verified caller context; models cannot supply operator authority.
  Worker claims stay within their enrolled workspace. Operator allocation of an
  external prefix grants custody only, never mutation permissions.

## Validation and limits

Provider-free public module/adapter tests, real temporary filesystem and locks.
Runtime observation is injected at the existing provider seam. Parent owns shared
CLI/MCP wiring and final integration tests. No live provider input, installs,
existing operator-tab manipulation, automatic stale cleanup or generic lock daemon.

## Current state

Conservative defaults frozen under explicit implementation goal after optional
questionnaire opportunity. TDD implementation begins in isolated worker checkout.
