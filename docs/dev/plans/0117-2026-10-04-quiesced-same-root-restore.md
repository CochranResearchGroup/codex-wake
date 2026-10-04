# Quiesced same-root restore

State: CLOSED
Lane: P63
Owner: primary
Branch: feat/p63-quiesced-restore
Target: origin/main
Integration: squash_pr
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/181
Depends-On: Plan0101; Plan0116

## Scope and bounds

Main1108be7 has accepted snapshot preparation, not activation. Add cooperative
lifecycle reader/writer fencing to every BusStore connection and explicit
same-root operator restore. Require original identity, private snapshot integrity,
paused state and exact non-audit canonical state equivalence before activation.
Preserve all subsequent audit events, authorities, unknown attempts and receipt
history. Refuse any post-snapshot canonical mutation; do not rewind revoked
actors, erase newer outcomes or imply recovery from corrupt source. SQLite
transactional backup restores into the existing canonical inode, avoiding a
second active store. No services or live roots are touched; fixtures only.

One serialized owner. Scope: BusStore connection lock, backup restore, CLI,
focused and installed fixture, CI/readme/evidence. Two work-unit attempts maximum;
inherited review/rework/discovery allowances persist. Reader lock wait1second;
copy and verification10seconds, files <=oneGiB, fixture20seconds. Cooperative
fencing applies only to upgraded BusStore clients. Old binaries/raw SQLite writers
must be stopped independently; no installed fleet quiescence claim is authorized.
No parallel worker requested.

## Acceptance and exit

Red fixture first. Prove actual same-root SQLite restore preserves canonical
identity, all state and newer audit history, remains paused, rejects concurrent
participating readers/writers and newer authority/receipt/body changes, and
retains snapshot/request evidence on interruption or completion-audit failure.
Use fresh installed CLI processes and both hosted Python versions. A passing
packet accepts only state-equivalent activation in disposable fixtures; full
corrupt-source recovery, real runtime/service and long-soak gates remain OPEN.

## Integrated bounded acceptance

PR202 source9d9cb867c1e0d737225609b2b3d63e4cee2ad34a passed hosted run
37224899191 on both Python versions, all871 tests and installed restore.
Squashfdc67e9c73839dd3794cc9f151e4bd78be794ff3; verification0109 accepted
only state-equivalent same-root activation and upgraded-client fencing. Full
corrupt-source recovery, old/raw-client quiescence, service/live/soak/release
remainOPEN. Source worktree clean, remote equal, ref retained.
