# Plan0150 — Policy routing and governance-context pilot

State: CLOSED
Workflow: DONE
Owner: primary / ecochran76
Lane: P72
Branch: chore/policy-context-pilot
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/237

## Scope

Reconcile nonexistent AGENTS policy pointers, preserve existing policy bodies,
wire a bounded policy-maintenance gov_policy profile, and add a deterministic
wiring/inventory/hash guard to existing CI. Canonical Markdown remains authority.

## Non-goals

No policy-library upgrade, product behavior, wake, service, release, global MCP
change, broad rollout, or assertion of measured total-token savings. Other task
kinds continue canonical reading; this first profile is policy-maintenance only.

## Acceptance criteria

- Every AGENTS policy pointer exists and every local policy is wired exactly once.
- Installed read-only MCP discovers current profile at the exact root; canonical
  fallback reads succeed. First/context-lost use hydrates all selected sections.
- Current, changed-source, missing/added-file and out-of-scope controls qualified.
- Hashes, section choices, action facts, and citations are checked; reuse verifies
  freshness only while the exact consumed packet is retained.
- CI runs the mechanical check; a missing-pointer regression fails locally.
- Record source/version, availability, limitations and adoption feedback.

## Definition of done

Focused checks pass, governed PR integrated, root main clean; issue closed only
from final integration and receipts. Pilot admission is distinct from measured
host efficiency; no total-token saving claim without paired host measurements.

## Current State

Implementation and qualification merged by PR238 at
fbc3d0275f0e46b41180706adf615e6ce3771bae. All local acceptance criteria pass;
root main read back before this terminal documentation slice. Pilot host-token
economics remain explicitly unmeasured; no broader profile or efficiency claim.
Issue237 closes from final terminal metadata integration.

## Bounds

One primary, one profile, two correction attempts per qualification seam, one
consolidated review. Checkpoint on qualification or integration; no subagent.
