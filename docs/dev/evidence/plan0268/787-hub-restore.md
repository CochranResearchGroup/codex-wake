# Issue 787 hub backup reconciliation

Stop the hub and peer workers before restoring. Keep the restored hub
offline until the reconciliation command has committed. Restore into a
separate, empty PostgreSQL database and verify the selected DSN before
running the command.

```sh
python -m codex_wake.wake_network_restore \
  --config /private/restore.json --quiesced-restored-hub
```

Use a private JSON file with `hub` set to the original canonical HTTPS
origin, `network` containing the restored private `dsn_file` and
`stale_seconds`, and `owners` containing entries for each available
owning peer. Each entry has `peer_id` and the absolute path `journal`
to its original private `work.sqlite`. An optional `owner_dsn_file`
points to that peer's original private PostgreSQL DSN file. Preserve
ownership and read access for these inputs and keep the peer databases
separate from the restored hub.

The command first commits the restore marker, quarantines unresolved
inbound work, and disables every peer credential carried in the
backup. It then checks full immutable envelopes against the original
recipient journal. If the journal stopped at a submission intent, its
original local PostgreSQL attempt can establish the receipt. Prior
final evidence persists. Conflicting or missing authority remains held,
and original uncertain results remain terminal. A journal entry with
an ID absent from the older backup becomes a blocked ID rather than a
new dispatch. A newer admission known only to the lost hub and never
observed by an owner is outside the recoverable set. Retain separate
client/hub acceptance evidence when it is available.

Before opening traffic, reconcile the new peer roster from current
operator authority and explicitly enroll only the still-authorized
peers with fresh credentials. A restored enrollment is insufficient
to re-enable a revoked peer. The restored hub requires pull clients
that understand the restore allowlist. The recipient worker admits
only IDs enumerated by the current authenticated pull, including when
it has older locally retained messages. It leaves independent local
work alone. Re-run offline reconciliation with additional original
authority if a held record can later be resolved.

The isolated test restores an actual older PostgreSQL 17 custom-format
dump with `pg_restore`. Public peer HTTP confirms original receipts,
original timing, held custody, stale-credential refusal and blocked
resubmission of an owner-observed ID absent from the backup. The local
owner's driver count verifies no repeat effect. It uses a synthetic
native receipt driver and injected trusted-time observations. No
production host, peer, PostgreSQL instance or credentials were changed
by the qualification.

```sh
# Set CODEX_WAKE_TEST_RESTORE_DSN and CODEX_WAKE_TEST_RESTORE_CONTAINER
# to one disposable PostgreSQL instance with database creation authority.
PYTHONPATH=src:tests python -m unittest test_wake_network_restore
```
