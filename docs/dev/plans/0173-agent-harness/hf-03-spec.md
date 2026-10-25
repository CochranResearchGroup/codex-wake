# HF-03: Semantic observation and bounded wait

State: OPEN
Owner: ecochran76 / primary coordinator
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/330
Base: 37a5cbb

## Outcome and decisions

Observe an exact enrolled managed agent without loading conversations, sending
input or inferring readiness from silence. The existing inventory's `ready`
means binding verified, not semantic readiness. Observations are read-only and
never confer operation permission or work acceptance.

Expose agents observe and agents wait through CLI and matching MCP tools. Both
use the same public observation owner. Query by managed agent ID; host-selected
runtime access stays outside model arguments. Defaults are configurable per
request: maximum observation age 30 seconds, wait timeout 60 seconds, polling
interval 1 second. Bound freshness to 0.1..300 seconds, waits to 0..300 seconds,
and polling to 0.05..5 seconds; reject nonfinite/bool inputs. Monotonic time owns
the wait deadline, wall timestamps qualify evidence freshness. Every source read
receives the remaining timeout; no read may start after the deadline.

## Evidence and supported states

Every result identifies the exact managed agent, runtime/conversation, semantic
state, source/evidence kind, observation time, freshness and reason. State
vocabulary: working, ready, awaiting-human, auth-required, disconnected, unknown.
Do not expose prompts, frames, credentials, socket endpoints or transcript text.

Codex uses existing read-only native metadata and runtime namespace identity,
verified process generation and complete exact-thread status. Active with no
flags means working; waitingOnApproval or waitingOnUserInput means awaiting-human;
idle with no flags means ready. Unknown flags/status combinations remain unknown.
An explicit notLoaded status is disconnected only after exact identity and
current process evidence; connection failure alone is unknown. There is no
qualified auth-required mapping yet: report that capability as unsupported.

Grok reuses its existing host-bound runtime and version-qualified observation
adapter. Only qualified empty-composer readiness maps to ready; draft/busy/unknown
frames, unavailable bindings and unsupported states remain unknown. Never infer
working or auth-required from arbitrary terminal text. Preserve host-bound
provenance instead of calling it native attestation.

Suppressed enrollment, identity/namespace/root/process mismatch, partial required
sources, future/stale timestamps or unavailable evidence always project unknown.
Only fresh identity-matching evidence can satisfy a wait, including a request to
wait for unknown. Wait returns matched, timeout or unknown explicitly. A zero
wait timeout returns timeout without starting a source read. Timeout retains the
last redacted observation; it never implies the requested state was reached.
Wait polls fresh state and may match on the initial observation; no prior-state
transition is required. This is state waiting, not an event-history stream.

## Acceptance and limits

Prove through public CLI/MCP and the shared observation seam that a ready/working
transition matches, stale/mismatched/partial/unknown evidence cannot become ready,
unknown runtime vocabulary is conservative, and deadline exhaustion is bounded.
Use provider-free protocol fixtures for actual native read-only metadata and
existing Grok qualification fixtures; no production state or provider turns.
HF-03 owns observation only, not interruption, recovery, wake registration or
new permissions. Existing delivery adapter behavior is not changed.
