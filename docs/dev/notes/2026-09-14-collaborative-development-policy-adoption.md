# Collaborative development policy adoption feedback

Date: 2026-09-14
Repository: `CochranResearchGroup/codex-wake`
Installed bundle: `v0.1.26`
Selected base profile: `repo-product-engineering`

## Adoption decision

Codex Wake adopted the `collaborative-development-workflow` module for the P48
event-driven wakes product lane. The repo retained its existing local issue,
planning, active-lane, Git, validation, subagent-governance, and model-selection
modules rather than replacing them with an unreviewed complete profile refresh.

Installation, wiring, and enacted behavior are distinct here. The installed
selector bundle supplies the module at `v0.1.26`. `AGENTS.md` now wires the
repo-local policy copy. Plan 0048, GitHub issue #2, branch
`docs/p48-event-driven-wakes-vision`, and the active-lane audit provide current
behavioral evidence; the pull-request closeout will complete the adoption
receipt.

## What worked

The module cleanly established a default issue-to-branch-to-pull-request flow,
one accountable coordination owner, explicit overlap handling, CI-backed
integration, bounded subagent fan-out, and evidence-based model calibration.
Those rules fit the planned filesystem and GitHub adapter lanes without
weakening the existing wake safety boundaries.

## Friction and ambiguity

Before adoption, `AGENTS.md` pointed to policy files `0021` through `0048` that
did not exist in this repo. The selector recognized substantial semantic policy
coverage and therefore recommended no missing modules, even though the new
collaborative-development module had not been concretely wired. The installed
selector's full source-layout test suite also expects catalog and module paths
that are absent from the downstream installed bundle; bounded downstream-safe
tests remain the usable verification surface.

The reusable upstream lesson is that selection and wiring checks should verify
that every generated policy path exists, and semantic alignment should not hide
a missing concrete module when the module is an explicit adoption target.
Downstream test packaging should either include its referenced policy-library
fixtures or label source-only tests so installed consumers can select valid
checks deterministically.

## Repo-local choices

Codex Wake keeps a `balanced` execution bias, a maximum of three concurrent
subagents, and nested delegation disabled by default. Those values reflect a
small Python product with shared persistence and dispatch invariants; they
should remain local unless broader fleet evidence supports another default.

The repo also preserves its explicit no-live-effect boundary: creating a wake
does not grant the resumed agent authority for repository, provider, tenant, or
runtime mutations. That product-specific rule belongs here even if a reusable
collaboration module continues to require explicit effect scope.

## Follow-up

Retain this note as the harvest locator for a future shared-policy change. The
local adoption is enacted for the P48 documentation slice; implementation-lane
effectiveness and model-cost calibration are not yet evidenced and must be
measured from accepted implementation samples before changing defaults.
