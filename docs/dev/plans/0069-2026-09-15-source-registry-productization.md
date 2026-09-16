# Source registry productization and installed compatibility

State: OPEN
Lane: P52-C4
Issue: #85
Branch: `feat/issue-85-source-registry-productization`
Target: `main`
Integration: `squash`

## Current state

Issues #82 through #84 are accepted on canonical main at
`e0d88620a7bfc9208b97dd29e420639d391c0ecf`. All four production source
families reconstruct through the immutable built-in registry. Operator
readiness and support still derive source capability independently of that
catalogue, and the internal extension procedure is not yet documented.

## Objective

Make the accepted catalogue the side-effect-free authority for built-in source
inventory, expose that inventory additively through readiness/support, document
the deliberately closed internal extension procedure, and prove the exact
candidate wheel in one isolated provider-free, dispatch-disabled smoke.

## Scope and write surface

- Extend `BuiltinSourceRegistration` and `BuiltinSourceRegistry` only with
  immutable, bounded, side-effect-free introspection metadata/projections.
- Provide one production catalogue constructor shared by daemon reconstruction
  and operator introspection without importing daemon-owned runners into source
  family modules.
- Add an additive built-in inventory to `signal_readiness`; support export
  inherits the same projection through its existing readiness payload.
- Preserve every existing readiness/status/support field and meaning.
- Add focused registry, readiness, support, and daemon parity tests.
- Document the internal built-in extension procedure and closed security/
  authority boundary.
- Build the exact candidate wheel and run one isolated installed smoke from a
  temporary virtual environment and wake root.

## Invariants

- Catalogue inspection never calls a family factory, constructs a runner or
  provider client, reads GitHub/systemd/filesystem/process state, or creates
  runtime files.
- Inventory is deterministic, bounded by the closed catalogue, nonsecret, and
  derived from the same registrations used by daemon reconstruction.
- The daemon compatibility entry point, runner order, source semantics, public
  existing JSON/text fields, dispatch behavior, and persisted schemas remain
  unchanged.
- No arbitrary external registration, entry point, dynamic import, hot reload,
  or universal plugin ABI is introduced.

## Acceptance

- Focused tests prove pure inventory, catalogue/runtime agreement, additive
  readiness/support output, and zero factory/client construction during
  inspection.
- Comprehensive Python, plugin, compilation, packaging, planning, and required
  Python 3.11/3.12 CI gates pass.
- One exact wheel is installed into an isolated temporary virtual environment;
  provider-free catalogue inspection and representative fixture reconstruction
  pass with dispatch disabled and with exact cleanup/readback recorded.
- Parent #81 can close from canonical-main evidence with an empty active-lane
  catalogue and no P52 topic branch, issue, or pull request.

## Non-goals and effect boundary

No new source, provider or network read, provider mutation, live filesystem/
process/systemd observation, live dispatch, normal wake-root mutation, service
installation, global install refresh, tag, release, deployment, or arbitrary
external plugin loading.

## Ownership, model route, and bounds

The primary owns architecture, shared-schema decisions, Git/GitHub integration,
the exact installed boundary, and final acceptance. One bounded
`gpt-5.6-terra` medium worker owns implementation and focused tests in the #85
worktree. One fresh `gpt-5.6-luna` medium reviewer may perform the single broad
review-discovery pass. Nested delegation is disabled. Maximum implementation
attempts: two; maximum review repair cycles: one; installed attempts: one with
zero retries.

## Next action

Merge this plan checkpoint, create the exact branch from canonical main, and
publish the active-lane assignment before implementation starts.
