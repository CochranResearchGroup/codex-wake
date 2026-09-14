# Plan 0055: Signal Readiness And Lifecycle Productization

Status: OPEN

Issue: `CochranResearchGroup/codex-wake#9`

Branch: `feat/issue-9-signal-productization`

## Outcome

Make the accepted filesystem and GitHub signal substrate supportable through
separate source and dispatch readiness, bounded evidence export, protected
journal lifecycle, compatibility tests, and disposable package acceptance.

## Current state

Issues #6, #7, and #8 are closed on `origin/main` at
`4169d7e1ea4f14144f493e934bfb14ce648adb05`. The signal journal and adapters
exist, but installed default source construction, source-specific readiness,
support export, lifecycle protection, and package-level signal acceptance are
not yet integrated. No live or installed runtime is authorized.

## Scope and acceptance

- Report signal capability and each configured source's health independently
  from target dispatch readiness in doctor, monitor, and product-readiness.
- Export a deterministic, size-bounded support artifact containing sanitized
  configuration/state/evidence and no raw provider payloads, secrets, or file
  contents.
- Protect active anchors, checkpoints, reservations, and evidence pins during
  retention and cleanup, with actionable repair diagnostics.
- Test schema migration and interrupted recovery, explicit downgrade behavior,
  and mixed-version supervisor/reader capability without weakening v1 support.
- Build a wheel and use disposable environments to verify clean install,
  upgrade, restart, source observation, resolution, inspection, export,
  retention, and retirement for filesystem and fixture-backed GitHub paths.
- Extend package and public-tag smoke definitions so the signal substrate is
  covered without enabling a source, creating a tag, or touching the installed
  user runtime.

## Non-goals and gates

No live GitHub access, public listener, secret provisioning, live dispatch,
installed-user-runtime mutation or cleanup, deployment, public tag, release,
or installation refresh. Provider and target readiness remain separate facts.

## Execution and ownership

Use one `gpt-5.6-sol` high implementation worker because lifecycle migration
and authority boundaries dominate this otherwise mixed mechanical slice. The
primary retains schema, authority, integration, and final acceptance. Run one
fresh `gpt-5.6-luna` medium read-only review after focused and disposable
package tests pass; allow one bounded repair cycle.

## Definition of done

Issue #9 criteria are satisfied by provider-free tests and disposable package
receipts, both release-gate jobs pass on the linked pull request, and the merge
and closure are read back from current `origin/main`. Every gated effect is
listed as unexecuted.
