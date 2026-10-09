# Plans0123–0126 implementation and acceptance audit

Review baseline: `36de0b0` (the approved tickets). Inspection/fallback commit: `a1a7aaa`. Mailbox and wake integration follow on feature/network-time-consensus. Exact source bytes and installed wheel identity are preserved in `candidate-identity.json`; the final commit includes this review and its receipts. All task changes are isolated in `/home/ecochran76/workspace.local/codex-wake-time-prototype`. The original main checkout and its unrelated untracked notes were preserved.

## Requirement-to-evidence audit

| Plan / requirement | Implementation and proof |
| --- | --- |
| 0123 executable inspection and all candidates | `time inspect` CLI → packaged host acquisition → normalization → selection; `plan0123/first-live-inspection.json`, cached readback and current installed acceptance. Four operators visible, CF/NIST admitted, Netnod/PTB explicitly excluded. |
| 0123 admission/authentication/NTS | `plan0123/qualification.md` records plain-NTP opt-in, first-party scale references, numeric bounds, NIST rate/backoff and failed bounded mature Chrony NTS spike. Authentication has not been qualified; no silent downgrade. |
| 0123 age/identity/fault boundaries | Host QPC, host/guest boot IDs, collection generation, request nonce, per-user lease and rate cache. `test_time_inspection.py` exercises malformed/replayed/delayed/stale/foreign identity and missing interop; `test_time_provider.py` covers duplicate operators, ties and outages. Owned host cache controls additionally prove corruption and counter/frequency anomalies fail closed. |
| 0124 healthy fallback and priority | Inspection adapter validates W32Time synchronization evidence, source, age, dispersion and offset; core requires consistency with all remaining usable network evidence. Network quorum overrides Windows; ties cannot be broken by Windows. Core and inspection tests cover health loss, conflict, outage and recovery. Real installed observation records this host's stopped W32Time as excluded, not as an observed working fallback. |
| 0125 uncertain creation and immutable deadlines | Schema-3 mailbox `send` returns retryable `time_uncertain` before admission when acquisition is unavailable. Existing public mailbox creation accepts relative TTL, not an explicit-deadline argument; stored explicit envelope expiry is never recomputed. Successful retry of an interrupted commit retains identity and expiry. Absolute wake creation separately preserves supplied fractional deadlines. |
| 0125 inspection/cancellation without anchor reset | Metadata show/list/replies avoid time acquisition and expiry. Operator inspection and uncertain cancellation record NULL UTC with explicit status; cancellation suppresses notification without fabricating recipient transport evidence. Outage and fresh-process tests exercise these paths. |
| 0125 effect holds and automatic recovery | Mailbox expiry uses lower bound; read/ack/reply and scheduler jobs/claim/publication hold a deadline inside the interval. Provider outage is retryable. Tests resume the same stored deadline after fresh evidence, without an operator checkpoint rewrite. Lease creation uses upper and lease validity uses upper bounds. |
| 0125 migration, faults and compatibility | Explicit operator migration to schema 3 requires quiescence, accepted network consensus and an intact legacy guard. Initial consensus becomes a persisted regression fence. Tests cover refused anomalous migration, successful migration preserving existing envelope/checkpoint/FKs, backup actual version, interrupted commit, concurrent duplicate admission and fresh-process metadata inspection. Boot/round exclusion is proved at the real acquisition/selection seam, not invented in the mailbox. State contract documents backup/no-loss rollback. |
| 0126 installed workflow | `scripts/network_time_acceptance.py` runs only with installed imports in an isolated virtualenv. Real entrypoints create/persist/poll/show/cancel a wake; migration and mailbox inspection cross process boundaries. Temporary target IDs identify fixtures; daemon is `--no-dispatch`. `installed-acceptance.json` preserves prompt, unchanged predicate and result. |
| 0126 uncertainty, restart and sleep | `test_network_wakes.py` proves pending boundary, outage hold, fresh sleep-length advance, unchanged deadlines, cancellation race and direct-dispatch gate. Acquisition/core tests prove Windows-health loss, tied groups and host/guest boot exclusion. These are deterministic fault inputs and process restarts, not an actual workstation reboot/suspend. |
| 0126 release and rollback | Version 0.8.0, schema document, README and `docs/dev/release-notes/0.8.0-network-time.md` describe opt-in, old-reader limits, migration, backup and rollback. No production install/migration/dispatch or host action occurred. |

## Standards review

Reviewed the complete diff from approved-ticket baseline through current implementation, plus the new modules, installed harness and persistence tests. Acquisition remains separate from deadline selection; callers inject only a trusted acquisition seam. New persisted domains require explicit policies/versioning. Legacy mailbox continuity/recovery authority remains intact. Cancellation and wake dispatch share lifecycle locking, with reacquisition/re-read before effects. Backup verification reads the actual persisted schema. Tests use disposable state and default regression remains hermetic; network and host controls are explicit opt-in scripts.

Findings fixed during implementation/review:

- Schema-3 backup manifests incorrectly reported schema 2: focused backup regression reproduced it before the manifest/verification fix.
- Wake cancellation during acquisition could be overwritten by firing: controlled public poll regression failed before lifecycle locking and re-read.
- Direct dispatch lacked the network time gate: added a boundary regression and independently checked deadline/uncertainty before transport.
- Whole-second parsing lost supplied fractional absolute deadline precision: failing preservation/early-fire control drove precise parsing in creation, polling and dispatch.
- Initial network activation did not establish the first regression fence: failing test drove persisted initial consensus.
- Guest wall time still controlled network-record archive/retention: failing public archive/cleanup control drove accepted upper/lower bounds.
- Reply metadata inspection still called expiry with absent time: regression reproduced a store-unavailable error, then passed with time-independent projection.
- Malformed host cache could reacquire immediately and cache writes were non-atomic: collector now persists a bounded error marker with flushed atomic replacement. The first owned-host control exposed PowerShell's empty backup-path coercion in `File.Replace`; corrected to an owned unique backup path, then all host controls passed. Counter/frequency regression rejects the collector rather than admitting fresh Windows fallback after elapsed-authority failure.

Some additional fault assertions passed against already implemented behavior. They are coverage, not claimed red/green cycles. Initial command invocations missing PYTHONPATH and an incorrect test import failed at harness setup; corrected before observing the meaningful archive assertion failure. No external effect was retried ambiguously.

## Spec review and remaining limits

All child acceptance criteria are supported by the mapped evidence within their explicitly isolated, non-live scope. The sequential ownership lane completed inspection/fallback first; shared mailbox/wake integration code and its disposable installed harness were developed together to test their seam, rather than representing the harness as a separately accepted prerequisite. Plans0125/0126 close together after this review and passing final gates.

Only two operators are currently admitted. An outage of either generally holds network effects unless healthy, consistent Windows fallback qualifies. Netnod/PTB are visible candidates, not functioning extra fallbacks. NTS is unresolved; the explicit policy trusts unauthenticated packets and cannot establish hostile-network canonical UTC. Bounds assume the documented short-term QPC engineering drift envelope and reject leap announcements/unsupported NTP era; arbitrary hardware calibration is not proved. Inspection's `production_ready: false` describes lack of automatic production admission; it does not silently authorize rollout when a schema-3 opt-in exists.

No actual suspend/reboot, real session resume transport, live guard repair, production store migration, production package upgrade or unattended service rollout is qualified. Older unmanaged daemons must be quiesced before schema-3 roots are used; this candidate cannot retroactively fence arbitrary old binaries. Current unknown-version readers hold records. Parent Plan0122 remains open for production activation/authentication/additional-source qualification; the four implementation tickets are bounded candidate work.

## Validation receipts

Final comprehensive result and installed candidate outcome are recorded in `validation.json`. Commands:

```
PYTHONPATH=src python -m unittest discover -s tests
uv build --wheel --out-dir /tmp/codex-wake-time-wheels
uv pip install --python /tmp/codex-wake-time-candidate/bin/python --reinstall /tmp/codex-wake-time-wheels/codex_wake-0.8.0-py3-none-any.whl
/tmp/codex-wake-time-candidate/bin/python scripts/network_time_acceptance.py --output docs/dev/evidence/plan0126/installed-acceptance.json
PYTHONPATH=src python scripts/network_time_cache_acceptance.py --output docs/dev/evidence/plan0126/cache-corruption-control.json
```

Full logs remain at the /tmp paths recorded in validation.json. Durable compact receipts retain outcomes and identity; private capability files and raw secret-bearing logs are not published. No actual host restart or production transport tests ran.

## Review adjudication

Standards axis: three accepted blocking findings (backup schema truth, initial persisted regression fence, atomic/fail-closed cache) are fixed and verified. Spec axis: five accepted blocking findings (cancellation race, direct-dispatch gate, fractional deadline, archive retention, outage reply inspection) are fixed and verified. No blocking finding remains open. Highest accepted severity on each axis was blocking; current unresolved severity is none. Dense formatting and repeated policy literals are nonblocking maintainability backlog, not a reason to claim an architectural cleanup occurred. The source registry's disabled candidates and failed NTS spike are explicit qualification limits rather than missing child requirements.

Memory disposition: unavailable. Machine-readable non-write receipt: `/home/ecochran76/.graphiti-openclaw/state/closeout-memory/20261009T014226Z-remember.json`; no reviewed Codex Wake Graphiti target group exists in established context, and no Graphiti write was attempted.
