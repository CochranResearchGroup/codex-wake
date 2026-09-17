# Managed webhook health, cleanup, and provider-free qualification

State: OPEN
Lane: P54-C3
Issue: #140
Branch: `feat/issue-140-webhook-health-cleanup`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0083-2026-09-16-managed-github-webhook-wakes.md`

## Current state

C1 and C2 are accepted on canonical `origin/main`. C3 is implementation-ready
at `f0fe41d746ff9ad9356fa031e5b16aedc76a63b7` and independently accepted. It
adds independent local/provider/delivery/polling/dispatch health, explicitly
armed exact-ID disable/delete, durable sanitized cleanup intent and tombstones,
runtime/reconcile/rotation fences, and a provider-free qualification.

Final validation passes 665 Python tests, 12 plugin tests, compilation, diff
hygiene, and a rebuilt isolated-wheel qualification. The qualification applies
fixture disable/delete, proves a production-adapter unit/PID/socket absence
census, and hashes retained product-path fixtures across cleanup. Rotation is
truthfully `preview_only`; no provider, service, secret, ingress, installed
runtime, release, or dispatch effect is authorized or performed. Canonical
acceptance still requires the issue-linked PR, hosted gates, squash merge,
issue closure, and `origin/main` readback.

## Objective

Deliver truthful independent health planes, exact-ID-only disable/delete,
retained bounded tombstones/history, sanitized support output, and a
provider-free installed qualification for lifecycle, rotation, fallback, and
cleanup with zero external effects.

## Scope

- Add a pure projection for local listener, provider object, provider delivery,
  polling fallback, dispatch, aggregate health, and separate cleanup eligibility.
- Preserve C1 inventory facts without inferring ownership or delivery;
  `dispatch` remains `NOT_INCLUDED` throughout C3.
- Define immutable generation-bound cleanup intent, plan, tombstone, and
  bounded history models containing no secrets, tokens, raw URLs/payloads/
  responses, or portable absolute paths.
- After C2 freezes, add a dry-run-first cleanup controller using the shared
  rotation fence and exact service/process absence seam.
- Disable/delete only an attributable exact hook and service, with durable
  intent, one armed mutation, independent readback, fresh unit/PID/socket
  census, and retained journal/wakes/checkpoints/history.
- Add sanitized CLI/support integration and provider-free installed
  qualification after #139 is accepted.

## Non-goals

- Automatic repair, redelivery, dispatch, polling reset, secret rotation or
  retirement, ingress changes, release, or live provider/service effects.
- Treating an exact provider object as delivery/secret proof or healthy polling
  as provider-mutation authority.
- Deleting without a prior proven disabled tombstone and local absence proof.
- Feeding raw provider responses or service output to the pure health model.

## Frozen contract

- Every health plane serializes separately. Healthy polling may make webhook
  trouble `DEGRADED`; it cannot make that plane ready or authorize mutation.
- C3-A always reports cleanup `NOT_AUTHORIZED`. Later integration may report
  `BLOCKED` or `ELIGIBLE_FOR_EXPLICIT_PLAN`, never execute from health alone.
- Cleanup verifies binding/hook, records intent under the shared generation
  lock, performs one explicitly armed mutation, reads it back, stops the exact
  service, and proves fresh absence before persisting a tombstone.
- Ambiguity becomes `UNKNOWN` and prohibits another mutation. Active C2
  rotation/rollback blocks cleanup and owns secret retirement.

## Execution graph

| Unit | Owner | Write surface | Exit condition |
| --- | --- | --- | --- |
| C3-A | standard implementation worker | new pure health module and tests | projection, codec, redaction, zero-effect tests pass |
| C3-B | primary | cleanup state/controller and shared joins | exact cleanup and tombstone tests pass |
| C3-C | primary | CLI/support and installed fixture | lifecycle/rotation/fallback/cleanup census passes |
| C3-D | independent reviewer | none | health and cleanup safety accepted |
| C3-E | primary | corrections, PR, receipts, canonical docs | local/hosted gates pass and #140 closes |

C3-A may run beside C2-A on disjoint files. C3-B/C3-C serialize through the
primary because they share C1/C2 state, lifecycle, CLI, and support surfaces.
No nested delegation is allowed.

## Validation

- Plane combinations prove webhook trouble plus healthy polling is degraded,
  polling failure remains visible, provider exactness is not delivery proof,
  and dispatch is always not included.
- Strict bounded codecs and projections reject permissive state, duplicate
  keys, secrets, tokens, reference names, and raw provider data.
- Cleanup fixtures cover absent/foreign/duplicate/collision/drift/unknown,
  intent-before-effect, one mutation, ambiguity, disable-before-delete,
  rotation fencing, and tombstone retention.
- Installed-wheel fixtures record fresh unit/PID/socket/root evidence and
  post-cleanup absence with zero provider and dispatch calls.
- Run focused and comprehensive Python, OpenClaw plugin, compilation, diff,
  goal/planning audits, independent review, and both hosted Python gates.

## Model allocation

Use one standard `gpt-5.6-terra` high-effort worker for the pure health module
and tests. The primary owns cleanup causality, shared integration, installed
qualification, GitHub custody, and final acceptance. An economical worker may
perform deterministic fixture checks after interfaces freeze; specialist use
requires a concrete unresolved ownership or cleanup-safety finding. Effective
allocation telemetry is unavailable.

## Acceptance criteria

- Health planes are independently truthful and cleanup eligibility remains
  separate from readiness and fallback coverage.
- Disable/delete affects only the exact owned hook/service, makes at most one
  armed mutation, and retains sanitized bounded history on success or uncertainty.
- Cleanup proves fresh provider/local absence while retaining journal, wakes,
  checkpoints, polling anchors, and accepted ingress.
- Installed provider-free qualification proves local behavior and zero
  provider/dispatch calls without claiming live delivery.
- Status/support contains no secret, token, raw payload, provider body, or
  secret-reference name.

## Definition of done

#140 closes only after #139 is accepted, this full provider-free path is
canonical on `origin/main`, the lane is reconciled, and no live provider or
target-dispatch effect occurred.
