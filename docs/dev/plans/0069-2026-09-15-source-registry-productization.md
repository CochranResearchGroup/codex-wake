# Source registry productization and installed compatibility

State: CLOSED
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

Candidate `bcfcfd5ec9b1b1c2b84879a4c89d0d526f17be22` is integration-ready in
PR #99. It supplies pure catalogue inventory, additive readiness/support
projection, maintainer documentation, and a provider-free installed-wheel
conformance gate. Focused, comprehensive, plugin, compilation, planning,
independent review, and Python 3.11/3.12 CI gates pass.

PR #99 squash-merged at canonical
`2929d934f34ccf9e27eaa28e910a5a6a5e6ada8d`, closing #85. The implementation
worktree and local/remote topic branches were removed after clean readback.

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

## Installed-attempt disposition

The sole local installed attempt built and installed exact candidate
`c4217b863d68f8e0cd803ed6990e2a6d53af5dac` offline. Catalogue, readiness,
support export/digest, and zero-wake-root assertions passed. Receipt rendering
then referenced nonexistent `bytes_written` instead of `size_bytes`, so the
process exited before installed fixture reconstruction. The attempt was not
retried. Readback retained exact hashes and cleanup moved the temporary venv,
wheel tree, and generated build artifacts recoverably to user trash.

Candidate `bcfcfd5` adds a checked-in provider-free smoke to the existing
installed-wheel CI jobs. Both matrix jobs reconstructed exactly one fixture
runner, reported the four built-ins and six ownership pairs, created no wake
root, and removed the temporary root. This deterministic replacement path did
not grant another local attempt or any provider, observation, dispatch,
installation, release, or deployment authority.

## Next action

None for this lane. Parent #81 may close after the final empty-lane projection
is accepted on canonical main.
