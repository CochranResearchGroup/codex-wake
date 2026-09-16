# Source registry productization and installed compatibility

State: OPEN
Lane: P52-C4
Issue: #85
Branch: `feat/issue-85-source-registry-productization`
Target: `main`
Integration: `squash`

## Current state

At lane start, issues #82 through #84 were accepted on canonical main at
`e0d88620a7bfc9208b97dd29e420639d391c0ecf`. All four production source
families reconstructed through the immutable built-in registry while operator
readiness/support still derived source capability independently and the
internal extension procedure was undocumented.

Candidate `c4217b863d68f8e0cd803ed6990e2a6d53af5dac` now provides the shared
catalogue constructor, pure inventory, additive readiness/support projection,
focused coverage, and maintainer documentation. Validation passes 438 Python
and 12 plugin tests plus compilation and independent review with no findings.

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

The sole local installed attempt built and installed the exact `c4217b8`
wheel offline. Installed catalogue, readiness, support export, digest, and
zero-wake-root assertions passed. The harness then exited while rendering its
receipt because it referenced nonexistent `bytes_written` instead of the
documented `size_bytes`; installed fixture reconstruction had not yet run.
This consumed the local attempt and is not retried. Readback retained the wheel
and support hashes, confirmed no wake root, and cleanup moved the temporary
venv, wheel tree, and generated build artifacts to user trash.

The bounded replacement acceptance path is a checked-in provider-free smoke
script executed by each existing installed-wheel CI matrix job. It exercises
the same catalogue/readiness/support assertions plus fixture reconstruction and
temporary-root cleanup through the installed interpreter. This does not grant
a second local attempt or widen provider, dispatch, observation, installation,
release, or deployment authority.

## Next action

Publish the deterministic installed-wheel CI smoke, require both Python 3.11
and 3.12 release gates on the exact candidate, then record the failed local
attempt and successful CI replacement path in the verification receipt before
integration.
