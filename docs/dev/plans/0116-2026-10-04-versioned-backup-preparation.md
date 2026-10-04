# Versioned backup preparation

State: OPEN
Lane: P63
Owner: primary
Branch: feat/p63-backup-recovery
Target: origin/main
Integration: squash_pr
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/181
Depends-On: Plan 0101; Plan 0115

## Scope and current state

Main fe42507 has schema2 retention and copied-root refusal but no operator
snapshot format. Serialize one bounded packet: paused snapshot via SQLite online
backup, versioned private manifest, explicit read-only verification using
independently supplied original operator authority. Retain identity, complete
receipts and uncertain attempts. No credential files exported; token digests
and bodies remain private inside the snapshot. No service, live actor, restore
activation, automatic replay or downgrade. An older backup can resurrect revoked
capabilities or erase newer receipts; activation requires a separate authority
and write-fencing contract. The campaign remains OPEN.

## Work units and bounds

Primary owns a2a_backup.py, CLI wiring, focused tests, installed qualification,
CI smoke, README and evidence. No independent delegation needed on this serialized
API/format contract. Two implementation attempts maximum; inherit one review/rework
cycle and prior discovery allowance without reset. Checkpoint after this packet.
SQLite copy and verification bounded to ten seconds and one GiB per file. New
snapshot directories only; preserve incomplete evidence rather than overwrite.

## Acceptance and exit

Run a red-capable snapshot roundtrip fixture before implementation. Prove
paused/operator gates, consistent WAL snapshot, exact schema/identity/hash,
integrity and foreign keys, private permissions and no symlinks, rejection of
partial/corrupt/unsupported/different-authority backups, source state unchanged
except attributable audit events. Completion-audit failure preserves snapshot
and request pointer. Verification never activates the backup or changes its
canonical root. Installed fresh-process CLI qualification and hosted3.11/3.12
checks required. Close only on that bounded axis; full recovery remains OPEN.
