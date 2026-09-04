# Cross-Root Wake Hook Routing

Date: 2026-09-03

Status: CLOSED

## Objective

Make delayed wake prompts self-routing so a prompt submitted from a different
repository, or after its record has been cancelled and archived, is resolved
against the wake root that actually owns the record.

## Current State

Tmux, app-server, and OpenClaw prompts now carry both `WAKE_TRIGGER_ID` and the
machine-readable absolute `WAKE_TRIGGER_ROOT`. The hook resolves explicit-root
prompts against their owning spool, searches retained archives, writes the ack
to that owner, and returns fail-closed terminal context for archived,
cancelled, expired, or failed records. Id-only prompts retain the legacy cwd
fallback.

The redundant tracked project hook was removed. Current hook readback reports
only the installed user hook and `hook_duplicate_install=false`.

## Scope

- Add a machine-readable absolute wake-root line to every canonical wake
  prompt transport.
- Resolve the hook against that explicit root, with current-directory fallback
  for prompts created by older releases.
- Search retained archive records and return a fail-closed terminal-state
  context for cancelled, failed, expired, or archived wakes.
- Write acknowledgments to the owning root.
- Cover the observed cross-repository, archived-after-paste sequence with
  focused regression tests.
- Remove the duplicate project hook while retaining the user hook.

## Non-Goals

- Do not resume, recreate, or mutate the completed P0133 wake.
- Do not change wake-record schema version 1 or copy original prompts into the
  canonical transport prompt.
- Do not alter retry timing, predicate evaluation, or transport identity.
- Do not modify the unrelated app-server active-writer plan or its broader
  implementation beyond the one prompt-construction call needed here.
- Do not release or publish a new package version in this plan.

## Work Units

1. Add failing unit tests for explicit-root parsing, cross-root lookup,
   archived terminal handling, and transport prompt construction.
2. Implement prompt routing and terminal handling in the critical path.
3. Run focused tests, then the repository presubmit suite and planning audit.
4. Remove the redundant project hook, verify the user hook remains installed,
   and record terminal evidence here.

The work is serialized under one owner because prompt construction and hook
resolution form one protocol boundary and the existing worktree has unrelated
in-flight edits. No subagents are used.

## Acceptance Criteria

- Tmux, app-server, and OpenClaw canonical prompts contain
  `WAKE_TRIGGER_ROOT=<absolute path>` without containing the original wake
  prompt.
- A receiving session in another repository finds the record in the explicit
  owning root and writes its acknowledgment there.
- An archived or cancelled wake returns explicit terminal context instructing
  the agent not to resume the task.
- Legacy id-only prompts retain current-directory fallback behavior.
- A missing explicit-root record does not create a misleading acknowledgment
  in either repository.
- Focused hook, injector, app-server, and OpenClaw tests pass.
- Broader presubmit and planning validation pass, or any pre-existing unrelated
  failure is recorded precisely.
- Exactly one user-scoped wake hook remains installed on this workstation.

## Definition Of Done

The source behavior, regression tests, and installed hook configuration all
match the acceptance criteria; validation results are recorded; the plan is
marked `CLOSED`; and no unrelated dirty worktree content is changed.

## Implementation Result

- `src/codex_wake/injector.py` emits the owning root in canonical tmux and
  app-server prompts.
- `src/codex_wake/openclaw_gateway.py` emits the same machine-readable field
  while retaining its human-readable root and record-cwd context.
- `src/codex_wake/hook.py` accepts only absolute explicit roots, resolves all
  active status directories plus `archive/`, avoids misleading acknowledgments
  for missing explicit-root records, and distinguishes resumable from terminal
  context.
- `.codex/hooks.json` was removed because the same hook remains installed at
  user scope.
- The unrelated dirty app-server active-writer changes were preserved; this
  plan changed only its canonical-prompt call.

## Validation

- Red proof: focused collection initially failed because
  `extract_wake_root` did not exist.
- Focused: `PYTHONPATH=src pytest -q tests/test_hook.py
  tests/test_injector.py tests/test_app_server.py
  tests/test_openclaw_gateway.py` passed, 39 tests.
- Presubmit Python: compileall plus `PYTHONPATH=src python -m unittest
  discover -s tests -p 'test_*.py'` passed, 180 tests.
- Plugin: `npm --prefix plugins/openclaw-codex-wake test` passed, 12 tests;
  both plugin JavaScript entrypoint syntax checks passed.
- Planning: active planning audit passed before closeout.
- Packaging: a wheel built successfully with SHA-256
  `280ae44a5477bae8cefba7c786f2e1575f960d13931c944497255027680c8bdc` and
  passed the isolated product smoke. Live Codex/OpenClaw checks were skipped
  because no live target ids were supplied; tmux remained correctly classified
  as `manual_only`.
- Installed-wheel replay: wake `wake_20260904_004759_22ca` was created,
  cancelled, archived, then submitted to the built hook from a different cwd.
  The hook wrote its ack only in the owner root and returned
  `status=archived, previous_status=cancelled` with `Do not resume`.
- Hook configuration: project hook absent, user hook installed,
  `hook_installed_scopes=user`, and `hook_duplicate_install=false`.

The user-scoped executable remains the public `v0.5.0` install. This plan
validated the repair from an isolated wheel but intentionally did not replace
the public install with an unreleased dirty-worktree build.
