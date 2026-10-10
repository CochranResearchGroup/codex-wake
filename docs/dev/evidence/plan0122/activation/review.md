# Plan0122 activation review

Reviewed fixed implementation baseline7a4666a through the repaired native paths; canonical integration diff is b13e457...HEAD on feat/network-time-provider. Prior child implementation review remains in Plan0126 acceptance-review.md. Integration source/tests/scripts match e4f742b before the additional read-only guard repair; policy rollout86f18ba is deliberately excluded and remains in original main/source custody. One primary reviewer applied the two axes serially; no delegated reviewer is claimed.

## Standards

Sources: runtime/time policy0003, installed validation0006, testing0016, canonical integration0021, and prior child review. Time decisions remain adapter-owned, bounded and explicit; no system clock or old checkpoint reset is introduced. Schema migration/backup and unknown-client limits are documented. New live evidence is scoped to owned roots/threads; capabilities and peer bodies are not published. Busy waiting is bounded and does not retry a committed effect. Three real acquisitions are independently omitted at the inspection seam; those controls are not represented as actual provider outages.

Accepted blocking findings fixed with meaningful regression evidence: current Codex idle footer refusal, native worker outage exit, sender registration/evaluation guest-clock use, final tmux guest-clock expiry, network transaction contention, and read-only reply/transport time bypassing the persisted network regression fence. The last finding was demonstrated by an accepted900-second decision after a1000-second checkpoint; the helper now applies the same read-only check as mailbox writes and leaves the checkpoint unchanged. The core check is shared, avoiding duplicated continuity rules. UI test placement was corrected and separately replayed against the old predicate; its earlier collected-coverage claim is explicitly withdrawn.

Nonblocking backlog: host acquisition under a writer transaction serializes operations; the30-second wait can still fail closed under sustained contention. Removing that lock without widening expiry bounds needs its own measured design, rather than moving acquisition to an unbounded stale instant. Existing compact formatting/private internal seams are maintained; no speculative abstraction or unrelated cleanup was added. No unresolved blocking Standards finding remains in reviewed source.

## Spec

Plan0122 revision2 and issue224 govern activation. Stories1–8 map to child acceptance plus new third-provider omission controls, native worker outage recovery, reply/transport bounded-domain regressions, and actual candidate exchange. The fresh native exchange proves A admission/arm/turn end, B pointer/read/claim/correlated reply, automatic A pointer/read/digest verification, submitted arm, exactly two submitted transport attempts, and bounded worker exit. The earlier failed exchange is preserved separately; the controller did not intervene after admission in the accepted exchange.

Still-open acceptance gates: canonical PR/CI integration, stable installed identity and actual exchange on that installed release, final original-story matrix and rollback custody readback. These are blocking for parent completion, not missing candidate source changes. Authentication is explicitly plain NTP opt-in; NTS, unknown Netnod/PTB profiles, actual workstation reboot/suspend and historical guard repair are not claimed. Current Windows service is unhealthy and excluded. Existing legacy default behavior is retained.

Adjudication: Standards blocking source defects fixed; nonblocking serialization backlog retained. Spec has no observed unresolved source defect, but stable integration/installed acceptance remains blocking. Highest unresolved severity: Standards nonblocking, Spec blocking activation evidence.

## Final activation adjudication

All previously open Spec activation gates are now accepted: PR225 exact main edf2aea and both hosted gates, stable0.8.0 module identity, installed entrypoint workflow, each provider omission and actual stable native round trip, verified backups and real prior-reader refusal. All8 original stories are mapped in requirement-audit.md with fixture/live boundaries. No blocking Standards or Spec finding remains. Serialization and unauthenticated acquisition remain explicit nonblocking limits under approved scope. Successful transient worker units were garbage collected; final journal messages prove native bounded finish. Do not infer an exit code from default systemctl fields on a missing unit.

Memory disposition: unavailable. Current-goal machine-readable non-write receipt: `/home/ecochran76/.local/state/codex-wake/live-demos/plan0122-20261009/memory-disposition.json`; no reviewed Codex Wake target group exists and no write was attempted.
