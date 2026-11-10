# Producer revisions and bounded publication

Base e5beb4c7, isolated fix/observer-publication-544. Root's process-cache TTL30 and
birth/deadline hooks are preserved. No formatter/cache files changed here.

## Revision contract

Trusted daemon observations now carry projection_revision and evidence_revision
on each resource and the whole snapshot. Projection tokens hash exact physical
identity, source availability/epochs, display status/value/reason and qualified
freshness, while excluding observation clocks and tick/cost counters. Changed
resource records are hashed at the producer; quiet ticks reuse their tokens.
Equivalent inventory refreshes keep the same projection token. Fresh observed
health/error/provenance records independently change evidence tokens, permitting
inspection updates without inventing a display change.

Each resource and snapshot also exposes projection_valid_until. Producer deadlines
handle future observation timestamps and expiry of visible error/health-warning
or legacy activity cues. Crossing a deadline recomputes derived display freshness
without fabricating new source evidence. Continuous qualified native activity has
no age deadline; a quiet running turn keeps its token. Absence of an error and
responsive health have no warning cue to expire. Static qualified type/name facts
retain their existing non-expiring semantics.

Physical presentation_source epoch/availability participates in resource identity,
so reconnects cannot reuse a prior namespace token merely because labels match.
Native updates and gaps invalidate exact affected resource revisions. Source errors
also participate in whole-snapshot revision. Caller mutation isolation remains via
the existing canonical JSON cache/fresh public decode.

## Publication and diagnostics

The existing monitor publishes changed projection OR evidence revisions immediately.
Unchanged full snapshots are written only at a heartbeat no slower than5seconds
or half stale_after, whichever is smaller. The wait is shortened to the publication
deadline when necessary. Missing/invalid legacy revision fields keep unconditional
publication. The ordinary owner heartbeat remains at its existing cadence,1second
by default. Bounded latest observer diagnostics (32KiB,64source summaries) live in
that small owner record, and status merges them for the matching live generation.
A quiet full snapshot therefore stays fresh while diagnostics remain current.
Status reads that downgrade stale/lost evidence strip trusted revisions so those
transformed records cannot reuse a prior daemon formatting token.

The per-resource/whole contract was frozen with formatter worker546 before code;
its consumer is a separate commit. These tokens grant no remote input authority.
The publisher preserves the1MiB snapshot and existing retained-operation limits.

## Focused evidence

The baseline real-daemon regression fails because unchanged snapshot mtime advances
on every owner heartbeat; the baseline native public regression lacks revision
fields (publication-red.txt). Final focused receipts list the exact selected tests
and Python identities. Source checks prove:

- Quiet and equivalent inventory refreshes keep projection stable while fresh
observed records change evidence revision.
- Native idle→running and source loss change projection; quiet running remains
stable across a simulated30second wall-clock advance.
- A real default-redacted terminal error's future qualification and age expiry
change projection while evidence remains unchanged.
- The actual private daemon advances owner writes/diagnostic ticks while full
snapshot mtime remains unchanged, then writes a fresh bounded heartbeat.
- Public publish_observation writes changed display/evidence immediately, before
heartbeat; stale status drops old trusted tokens.

An initial publication test sampled the first snapshot before its first owner-cycle
record completed; its readiness barrier was corrected to last_cycle_at before
measuring successive heartbeats. This was test setup, not a product retry claim.
Ruff F821/F822/F823 and whitespace checks pass. This packet does not itself claim
the full installed60second CPU/RSS gate; root combines producer and consumer and
retains that acceptance boundary in547. No live service was enabled or deployed.

Memory disposition: forbidden; no explicit memory-write request.
