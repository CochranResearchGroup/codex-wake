# Held damaged-source recovery

State: CLOSED
Lane: P63
Owner: primary
Branch: feat/p63-held-recovery
Target: origin/main
Integration: squash_pr
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/181
Depends-On: Plan0101; Plan0116; Plan0117

## Scope and authority

Main0ec0690 accepts only state-equivalent restoration of a readable store. Add
explicit recovery using independently supplied operator capability and a reviewed
snapshot database SHA256, under cooperative exclusive lifecycle fencing. Caller
must acknowledge unbacked-state uncertainty. Preserve original main/WAL/SHM in a
private quarantine; do not inspect/repair/delete the damaged files. Recovered
mailbox retains snapshot IDs/digests/receipts/unknown intent, stays paused with a
persistent recovery hold, rotates operator authority and fences every old actor.
Bus schema2 makes prior readers refuse the recovered authority epoch. Mailbox
schema2 is unchanged. A fresh operator capability is published privately, never
printed. No automatic replay/resume or gap reconciliation is inferred.

An interrupted filesystem transition has a durable private intent marker before
any original file moves. Normal connections refuse while it exists. Explicit
reconciliation finishes only exact inode-bound original/staged transitions and
refuses ambiguous replacements. No destructive rollback, overwrite or deletion.
The quarantine includes an attributable external completion receipt. The old
source may contain newer unavailable outcomes: gap remains unknown/held, not
reported as absent or recovered. No release-hold workflow in this packet.

## Work units and bounds

Primary serializes recovery module, bus schema/hold guards, snapshot version
compatibility, CLI, tests, installed fixture, CI/docs/evidence. No independent
worker lane. Two implementation attempts; inherit review/rework/discovery limits.
One marker, one new quarantine, at most three original source files. One GiB per
file, copy/validation10seconds, lock wait1second. Installed fixture30seconds,
CLI child10seconds and hosted watchdog40seconds. ResourcesFD+2/children0/transport0.
No real actors/services/production bus or shared-root recovery is authorized.

## Acceptance and terminal condition

Red-capable fixture first. Prove damaged canonical file recovers snapshot rows
without original file loss, same canonical root/bus ID, fresh authority, old
operator/actor/cached authority and old readers refused, held resume/dispatch,
and inspection under new operator. Wrong hash/operator/root/version/corrupt
snapshot and concurrent upgraded connection refuse before source moves. Prove
interruption at move/publication cuts leaves normal readers blocked and explicit
reconciliation attributable and repeat-safe. Preserve all original artifacts and
never infer completion from prepared image alone. Actual installed fresh-process
recovery/reconciliation plus hosted3.11/3.12 required. Close only held recovery;
live/service/soak/release and operator gap reconciliation remain campaign gates.

## Image finalization reframe

Initial transformation produced a committed validated image but same-connection
WAL checkpoint failed. Consuming the mode pragma did not fix it; targeted probe
showed no open transaction. Split the serialized work into committed image
transformation and fresh-connection WAL finalization, with no source movement
until cold-file validation. This is a local tactic change after the first unit
failed its finalization gate, not a reset of cumulative review/discovery bounds.
Preserve failed probes; remove tagged instrumentation before qualification.

## External authority anchor

A private root anchor records current recovery operator digest/epoch outside the
possibly damaged SQLite file. Existing roots bootstrap from their independent
root operator file. Successful recovery atomically publishes a fresh anchor;
old operator secrets cannot start a second recovery. A pending intent binds its
original approval digest, permitting explicit reconciliation of that already
approved transition. Recovered bus schema2 requires matching external anchor
before normal connections. New backups record actual bus schema1/2. Reusing an
old snapshot with newly rotated operator authority is refused; create a current
qualified backup under the fresh operator. No bypass of revoked authority.

## Final bounded acceptance

PR204 source928effef29648d1c082e94ef6c482b073cab5ffd passed run37227096598
on Python3.11/3.12, all882 tests and installed recovery/reconciliation plus
actual old-reader refusal. SHA-fenced squashef59ca2b34397c24a192dc36ef57f6e165a47cfa.
Verification0110 ACCEPTED_BOUNDED_HELD_RECOVERY. Source/authority retention and
held recovery are qualified; gap disposition/release and full campaign remainOPEN.
Source branch retained clean/remote-equal. No actual service or live effects.
