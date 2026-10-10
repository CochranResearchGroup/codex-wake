# Ticket0148 finite requirement matrix

Frozen2026-10-10; original verification0106 all32 requirement rows retained.
Earlier evidence keeps its recorded version/workload; source applicability and
raw locators must be qualified before acceptance. No green suite substitutes for
live authority. Original old failures/uncertainties remain unchanged.

| Row | Original requirement | Later receipt or bounded remaining cut |
| --- | --- | --- |
| R01 | Product: selected exact recipient, durable request, attributable retrieval/disposition and correlated reply | 0143 actual installed exchange;0147 actual claim context |
| R02 | P63.1 shared daemon/Byobu session selectors, ambiguity and shell refusal | 0094 discovery;0143 actual qualified owned tabs |
| R03 | Numbered authority rules 1-6: explicit membership, stable bus/namespace/thread key, sender runtime validation, exact selection, root/tab non-authority, invoking inbox | 0143 actual enrollment;0147 stale/wrong-root refusal |
| R04 | Runtime-issued client/PID/pane/namespace/freshness and composer binding before automatic TUI | 0142 native queue bypasses pane-effect requirement; active/human safety controls;0143 exact queued turns |
| R05 | Shared-daemon exact-thread operation with atomic busy/human-client safety; no silent stdio fallback | 0142 native queue_start receipt/source;0143 actual acceptance |
| R06 | Bus one mailbox authority, private owner-only SQLite/local root, capability/root identity, copied-store refusal | 0095/0104;0122 actual multiroot;0146 recovered actor/root fencing |
| R07 | CLI verbs send/inbox/outbox/show/read/ack/reply/cancel/wait/watch/reconcile, typed JSON/selector errors | 0095/0099;0143 real normal CLI;0147 reconcile fresh process |
| R08 | Body-file/stdin, machine keys, human announced key, kinds/TTL/delivery, body-hidden inspection, operator audit | 0095/0099;0147 body-hidden reconciliation/operator audit |
| R09 | Immutable envelope fields, UTF-8/digest/body limit, conversation/lineage, exact recipient FIFO/idempotency | 0095/0104;0143 exact original/result lineage |
| R10 | Reply permission/lineage, optional atomic ack and distinct reply keys; no implicit completed claim | 0095/0099;0143 request/result claims and completion |
| R11 | SQLite WAL/busy/schema/migration, corruption/disk-full, clock and ownership failure, commit-before-accepted | PASS F1 fault/interruption/writer controls and C1 compatibility |
| R12 | Separate admission/notification/recipient projections and honest semantics | 0143 exact separated state/native completed turns |
| R13 | Expiry/processing claim semantics, cancel before claim versus uncertain/too-late, append-only events | 0095/0096;0122 actual cancellation;0147 generation observation |
| R14 | Active/offline/unloaded recipients held, human draft/approval/foreign shell safe, no replacement thread | 0142 live admission safety;0145 notLoaded hold/opt-in same-thread |
| R15 | Canonical metadata-only notification, untrusted peer content, actual hook event boundary | 0142 canonical metadata-only native notification;0143 actual hook/prompt consumption |
| R16 | Dispatcher/recipient generation leases, FIFO/batch <=20, scan <=100, crash cuts, unknown never replayed | 0096/0104;0143 normal worker restart; PASS F1 interrupted/unknown controls |
| R17 | 32 KiB, 24h TTL, 1000 open/recipient, 100000 retained, 1 GiB, 10/min sender, 10/hour recipient, 3 actual attempts/backoff | 0104 bounded resource/load;0122 full owned soak;0143 current pair resource proof |
| R18 | Lineage max8, no self-send/reply authority cycles, no automatic spawn/reply loops, bounded rejection metadata | 0095 validators;0143 finite exchange; no autonomous spawning |
| R19 | Receipt source durable replay, exact arming, checkpoint/grant revocation, no recursive notification | 0100–0105 receipt grants/replay;0143 actual reply wake restored across owned restart |
| R20 | Foreground bounded receipt wait/watch, cancellation/timeout, correlated reply | 0099 bounded foreground;0143 actual unassisted automatic return |
| R21 | Body retention30d, pending/uncertain/active pins, preview/apply, finite dedup90d, compact tombstones | 0107 retention;0146 snapshot legacy bound preserving pins/history |
| R22 | Backup/restore same identity without concurrent activation, no conversation cascade deletion | 0108/0109/0110;0146 actual damaged recovery/disposition/release; PASS C1 version-linked recovery |
| R23 | Diagnostics source/backlog/lease/schema/capacity/uncertainty/retention, body-free output | 0097 diagnostics;0122 service;0143 installed owned worker |
| R24 | Resource process/FD cleanup, shallow shared clients, thresholds before soak | 0104–0106 bounded resources;0122 1800s owned soak;0143/0147 cleanup |
| R25 | Parent/subagent exact isolation and inherited pane refusal | PASS A1 actual disposable ancestry/process reparent/restart |
| R26 | P63.7 operations restart/reconnect/unloading/multiroot/service ownership | 0122 restart/reconnect/multiroot;0143 changed transport restart;0145 genuinely notLoaded saved path |
| R27 | Compatibility schemas1/2, older readers explicit reject, mailbox domain migration, staged rollout | PASS C1 actual old/new message-linked readers and restored claim |
| R28 | Rollback pause/no reset/no replay/no deletion, retained inspection | 0120/0122 exact recorded0.7/0.6 rollback;0146 actual0.11.2 schema2→3 refusal; PASS C1 current binary roundtrip |
| R29 | P63.8 docs/packaging/hosted CI/release/install readback | 0144 actual publication/global install;0149 final release/identity; hosted CI wait waived |
| R30 | Optional MCP facade | Optional; no obligation |
| R31 | Excluded cross-user/remote federation, broadcast, task allocation, arbitrary commands, external sends, autonomous delegation | Exclusions preserved; no task allocation/external sends |
| R32 | Full definition of done: actual two-agent, fault matrix, multi-root, resource, migration/rollback, hosted and release evidence together | OPEN parent0148 finite cuts +0149 original definition-of-done audit |

## Three bounded execution packets

A1: actual disposable thread ancestry and owned process reparent/restart. Exact
capabilities never inherit from a parent/pane, and original message/claim/receipt
arm cannot retarget to a child or replacement. At most one native fork without a
turn, then archive that owned artifact; no autonomous worker/delegated exploration.
Fork metadata must actually prove ancestry; absent relation is missing proof,
never labelled subagent acceptance. Process fixture uses owned OS children and
real PID/start identities.60s per control,120s packet, no queued task/notification.

F1: current installed public transaction/receipt/lease/recovery controls, including
before/after commit, writer lifecycle fence, actual corrupted source and exact
interrupted recovery reconciliation. Reuse source fault harnesses where sufficient;
required fresh-process controls use disposable buses.90s source/60s installed,
FD+2/children0, no real production faults/raw writer mutation.

C1:0.11.2→prepared0.12→0.11.2→prepared0.12 on same owned normal mailbox; exact
message/claim/terminal receipts preserved, current reconciliation restored. Old
reader explicitly refuses disposed schema3; held schema2 remains readable.
Use actual retained immutable old/current candidates; no live service/binary
activation.60s, child10s, reader bytes/identity/receipts unchanged; explicit CLI status audit separately retained, FD+2/children0.

WIP1, packets executed A1→F1→C1; two diagnosed attempts each maximum. Unknown
effect stops that case without replay. Missing runtime ancestry may be safely
reframed locally; no fixture promoted to actual ancestry. Parent0148 stays OPEN
until every original row and all three packets qualify, then0149 final release.

C1 first harness assumed CLI status is read-only; actual public status appends an
operator inspect_status audit. Preserve first failed hash assertion. Correction
pins bytes after each explicit audited status, before the non-mutating old/new
receipt reader. Identity/message/claim/terminal remain invariant throughout.

All three packets PASS; closeout.md supplies exact attribution. Final release
and original overall definition-of-done rows remain owned by0149, not waived.
