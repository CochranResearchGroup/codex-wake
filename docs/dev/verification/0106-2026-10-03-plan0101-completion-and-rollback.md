# Plan 0101 completion audit and installed pause rollback

Verdict: NOT COMPLETE. Parent Plan 0101 / issue #181 remains OPEN.
Baseline: ed973ba299a60124d0f5b56c5d0798d37f4944f9; original scope preserved.
This audit maps authoritative plan sections and requirement families to current
evidence and missing gates. Provider-free evidence never substitutes for a live,
service, release or same-thread acceptance claim.

## Installed pause rollback

Reproducible command: installed Python scripts/a2a_rollback_qualification.py
--cli /explicit/installed/codex-wake. Synthetic owned temporary bus and two actor
identities; two admitted messages, one metadata-only dispatch claim, zero transport
I/O. Thresholds frozen in Plan 0114: twenty seconds, CLI child ten seconds, FD growth
at most two, residual children zero; hosted wrapper hard watchdog thirty seconds.

The first horizon regression expected idempotency_expired but the existing API
correctly returned idempotency_horizon. Corrected the assertion, no runtime change.
Boundary at exactly ninety days preserves identity; one second later visibly
requires a new intent key. Seven operations tests pass on Python 3.12 (0.518s)
and 3.11 (0.573s).

Installed pause/status verifies dispatcher pause in fresh commands. Simulated
lease expiry and canonical reopen leave the previous claim uncertain, retain one
attempt and both envelopes, exclude the unknown claim from jobs, and refuse new
claims as paused. Recipient body/read receipt and sender retry identity survive
canonical reopens. Copied-root activation refuses bus_identity_mismatch. No binary
downgrade, backup activation, supervisor restart or live delivery was performed.

- Installed Python 3.12: {"accepted": true, "after": {"children": [], "fd_count": 5}, "backup_activation_qualified": false, "before": {"children": [], "fd_count": 5}, "binary_downgrade_qualified": false, "copied_root_denied": true, "elapsed_seconds": 0.404, "finite_dedup_horizon": true, "fixture_removed": true, "paused": true, "preserved": {"attempt_state": "uncertain", "attempts": 1, "envelopes": 2}, "real_delivery_qualified": false, "schema_version": 1, "synthetic": true, "thresholds": {"cli_timeout_seconds": 10, "dispatch_io": 0, "elapsed_seconds": 20, "fd_growth": 2, "messages": 2, "residual_children": 0}, "transport_io": 0}
- Source Python 3.11 with installed CLI: {"accepted": true, "after": {"children": [], "fd_count": 5}, "backup_activation_qualified": false, "before": {"children": [], "fd_count": 5}, "binary_downgrade_qualified": false, "copied_root_denied": true, "elapsed_seconds": 0.49, "finite_dedup_horizon": true, "fixture_removed": true, "paused": true, "preserved": {"attempt_state": "uncertain", "attempts": 1, "envelopes": 2}, "real_delivery_qualified": false, "schema_version": 1, "synthetic": true, "thresholds": {"cli_timeout_seconds": 10, "dispatch_io": 0, "elapsed_seconds": 20, "fd_growth": 2, "messages": 2, "residual_children": 0}, "transport_io": 0}

## Requirement and evidence ledger

| Plan requirement | Current authoritative evidence | Remaining verdict/gate |
| --- | --- | --- |
| Product: selected exact recipient, durable request, attributable retrieval/disposition and correlated reply | verification 0095/0099; installed a2a_mailbox_smoke.py and capability service API | Synthetic workflow accepted; actual two-agent round trip missing |
| P63.1 shared daemon/Byobu session selectors, ambiguity and shell refusal | verification 0094 and 0103, sessions.py fixtures; current installed read-only observation below | Named recipient example not currently resolved; live discovery acceptance incomplete |
| Numbered authority rules 1-6: explicit membership, stable bus/namespace/thread key, sender runtime validation, exact selection, root/tab non-authority, invoking inbox | a2a_identity.py/a2a_bus.py, test_a2a_bus.py and test_a2a_cli.py; verification 0095 | Provider-free guard coverage; live named enrollment missing |
| Runtime-issued client/PID/pane/namespace/freshness and composer binding before automatic TUI | verification 0098/0103; metadata_matched is explicitly weaker | Automatic delivery unavailable; no attestation proof |
| Shared-daemon exact-thread operation with atomic busy/human-client safety; no silent stdio fallback | official release mapping/queue source in 0098/0103 | Queue add is effectful; safe ownership contract and adapter acceptance missing |
| Bus one mailbox authority, private owner-only SQLite/local root, capability/root identity, copied-store refusal | bus/mailbox code and tests, verification 0095/0104 | Synthetic accepted; production multi-root rollout separately gated |
| CLI verbs send/inbox/outbox/show/read/ack/reply/cancel/wait/watch/reconcile, typed JSON/selector errors | messages_cli.py parser and handlers; 0095/0099 installed smoke, hosted full suite | API available and fixture exercised; real-agent workflow gate remains |
| Body-file/stdin, machine keys, human announced key, kinds/TTL/delivery, body-hidden inspection, operator audit | messages_cli.py/body_input, mailbox tests and 0095/0099 | Provider-free evidence; no private-body fixture or peer authority escalation |
| Immutable envelope fields, UTF-8/digest/body limit, conversation/lineage, exact recipient FIFO/idempotency | mailbox schema/transaction implementation, 0095/0104 | Provider-free accepted; actual workflow and restart acceptance separate |
| Reply permission/lineage, optional atomic ack and distinct reply keys; no implicit completed claim | test_a2a_mailbox.py, 0095/0099 and installed smoke | Synthetic accepted |
| SQLite WAL/busy/schema/migration, corruption/disk-full, clock and ownership failure, commit-before-accepted | test_a2a_bus.py, test_a2a_mailbox_faults.py and 0095 | Provider-free fault proof; operational backup/recovery and installed migration matrix incomplete |
| Separate admission/notification/recipient projections and honest semantics | 0095/0096/0099/0106 preserve independent states/receipts | Live notification and attributable actual recipient acceptance missing |
| Expiry/processing claim semantics, cancel before claim versus uncertain/too-late, append-only events | mailbox and scheduler fault/race tests; 0095/0096 | Provider-free accepted; live cancellation boundary not qualified |
| Active/offline/unloaded recipients held, human draft/approval/foreign shell safe, no replacement thread | sessions/injector generic safety fixtures; A2A dispatch held | A2A live busy/draft/offline/unknown matrix unavailable |
| Canonical metadata-only notification, untrusted peer content, actual hook event boundary | scheduler body-free projections, installed smoke and foreground workflow skill | Automatic notification/hook adapter acceptance missing |
| Dispatcher/recipient generation leases, FIFO/batch <=20, scan <=100, crash cuts, unknown never replayed | 0096 and scheduler/fault tests; 0104/0106 | Provider-free accepted; live transport crash/reconciliation acceptance missing |
| 32 KiB, 24h TTL, 1000 open/recipient, 100000 retained, 1 GiB, 10/min sender, 10/hour recipient, 3 actual attempts/backoff | defaults in mailbox/scheduler; bounded limit/rate tests and 0104 workload | Configured constants/fixture behavior verified; production installed load/soak not qualified |
| Lineage max8, no self-send/reply authority cycles, no automatic spawn/reply loops, bounded rejection metadata | mailbox validators and bus tests, body-free diagnostics | Provider-free evidence; no excluded product effect introduced |
| Receipt source durable replay, exact arming, checkpoint/grant revocation, no recursive notification | 0100/0101/0102/0105 and installed nine-case projection gate | Local seams accepted; actual long suspension remains gated on delivery |
| Foreground bounded receipt wait/watch, cancellation/timeout, correlated reply | 0099 and installed foreground smoke; messages_cli.py bounded polling | Synthetic accepted; actual agent waiting/suspension unqualified |
| Body retention30d, pending/uncertain/active pins, preview/apply, finite dedup90d, compact tombstones | 0097/0105/0106/0107; PR197; hosted run37176278799 | Bounded logical compaction, ninety-day retirement, expiry projection pins, explicit migration and physical recovery accepted; actual service/soak remains separate |
| Backup/restore same identity without concurrent activation, no conversation cascade deletion | copied-root refusal in 0104/0106; retained canonical store/receipts | Actual versioned backup activation/recovery not qualified |
| Diagnostics source/backlog/lease/schema/capacity/uncertainty/retention, body-free output | operations.py and 0097 installed doctor; source/signal diagnostics | Available metadata proof; live supervisor/source maintenance acceptance missing |
| Resource process/FD cleanup, shallow shared clients, thresholds before soak | 0104/0105/0106 deterministic bounded workloads and census | Bounded fixture acceptance; long-running/live soak missing |
| Parent/subagent exact isolation and inherited pane refusal | identity/discovery fixtures, 0094/0095/0099 | Real disposable ancestry/reparent/restart packet missing |
| P63.7 operations restart/reconnect/unloading/multiroot/service ownership | 0101/0102 daemon restart fixtures, 0104 canonical process reopens, 0106 pause | Actual same-thread recovery/unload and supervisor installation gate missing |
| Compatibility schemas1/2, older readers explicit reject, mailbox domain migration, staged rollout | generic product_smoke.py and mailbox schema tests; isolated wheel installed | Message-linked versioned upgrade/downgrade recovery matrix incomplete |
| Rollback pause/no reset/no replay/no deletion, retained inspection | installed pause contract above, unknown attempt and finite horizon preservation | Pause axis accepted; old/new binary and actual backup compatibility not qualified |
| P63.8 docs/packaging/hosted CI/release/install readback | README, installed wheel gates; PRs182-193 integrated | Final release publication, chosen supervisor installation and rollback readback missing |
| Optional MCP facade | Explicitly optional in Plan 0101 | Not a required deliverable; no new facade introduced |
| Excluded cross-user/remote federation, broadcast, task allocation, arbitrary commands, external sends, autonomous delegation | Public product surfaces inspected; notification/peer bodies do not add capabilities | Preserve exclusion; no authorization expansion |
| Full definition of done: actual two-agent, fault matrix, multi-root, resource, migration/rollback, hosted and release evidence together | Evidence remains separated above | NOT COMPLETE; never mark achieved from current green suite |

## Current named-selector observation

Installed read-only `sessions resolve 17:wake --json --timeout 5` resolved current
thread 01a10388-a110-7990-8d45-1aa263c2ef68, runtime_state active, binding_status
metadata_matched. This is discovery evidence only, not effect authority.
`7:mail-receipts` returned code6, selection has no unique Codex identity. The command
sequence captured JSON verdicts; later shell success is not the recipient's success.
No enrollment, transcript/turn read or live send. Prepared disposable scope in
0103 remains pending; existing idle sessions cannot be substituted silently.

## Next actions and control

Preserve full Plan 0101 and cumulative allowances. Next independent ready unit:
compact tombstone/lifecycle qualification and versioned rollback preparation.
Actual live round trip, service and release cannot be claimed from those units.
A named disposable response is required before dependent live work; elapsed time
is not approval. Checkpoint by 450k, stop before current goal meter reaches500k.
Memory discovery skipped because current canonical sources suffice; durable graph
write unavailable without an authorized repository group.

Retention successor update: Plan 0115 CLOSED / verification 0107 accepts the
bounded retention/migration axis after PR 197 integration at 8414adc0. This
supersedes the earlier missing-compaction statement only. Full restore, actual
old-binary downgrade, live delivery, service/soak and release remain unproven.
Next packet: versioned backup/restore preparation under original identity and
concurrent-activation requirements, using owned provider-free fixtures first.

## Versioned backup preparation after PR200

Verification0108 / Plan0116 accepts paused SQLite online snapshots and read-only
version/schema/identity/integrity/authority verification, including preserved
uncertain intent and committed WAL. Both hosted lanes passed864 tests and
installed workloads. This reduces the backup-format gap only. Verification
requires the original readable bus and always refuses to qualify activation;
corrupt-source recovery, preventing revived old actor authority and preserving
later receipts during activation remain unqualified. No full acceptance claim.
