# Releasing a recovered mailbox into fresh work

A recovered mailbox stays paused and held because its damaged source may contain
outcomes missing from the snapshot. Those outcomes remain unknown. This workflow
retains snapshot-era messages and receipts as operator history, fences their
notifications and processing, and permits only newly authorized work afterward.
It never resumes old work or claims that a missing outcome did not occur.

Use only the explicitly authorized recovered store and its newly issued operator
capability. `a2a recovery-status` reports the original recovery epoch, snapshot
SHA256, current hold, disposition and bounded revoked-actor metadata. Reasons
are private audit text: use a brief nonsecret explanation and a stable intent key.

```sh
codex-wake a2a recovery-status --bus-root "$RECOVERY_BUS" --operator-capability "$RECOVERY_OPERATOR" --json
codex-wake a2a dispose-recovery --bus-root "$RECOVERY_BUS" --operator-capability "$RECOVERY_OPERATOR" --recovery-epoch "$RECOVERY_EPOCH" --expected-database-sha256 "$SNAPSHOT_SHA256" --accept-missing-state-unknown --idempotency-key "$DISPOSITION_KEY" --reason 'Retain unknown history; begin fresh work only.' --json
codex-wake a2a release-recovery --bus-root "$RECOVERY_BUS" --operator-capability "$RECOVERY_OPERATOR" --recovery-epoch "$RECOVERY_EPOCH" --expected-database-sha256 "$SNAPSHOT_SHA256" --disposition-receipt "$DISPOSITION_RECEIPT" --json
```

Reconcile a lost response with status and the exact original key/commitment. The
same disposition returns its original receipt; a conflicting intent refuses.
Release likewise retains its original receipt. A damaged legacy fence or an
unreceipted hold-clear refuses. Release leaves the bus paused, existing roots
without grants and old actors revoked. Explicitly grant the intended roots and
rotate or enroll the intended actors before admitting a genuinely new intent;
configure exact notification bindings if wanted, then explicitly resume.

Operator message inspection reports `recovery.legacy=true`, `retain-unknown` and
`gap_unknown=true` for snapshot-era history. Original message projections remain
historical; they do not become new processing inputs under fresh credentials.
Retained legacy history counts toward storage limits, but not new open-work quota.
A later recovery has a new epoch and deliberate disposition; old audit receipts,
snapshots and quarantine remain retained.

Disposition upgrades recovered buses to bus schema3. Actual0.11.2 readers refuse
that schema. Ordinary schema1/2 buses remain supported; rollback does not downgrade
schema3 or delete history. Keep the qualified0.12 reader available for inspection.
Source/installed proof is in docs/dev/evidence/plan0146/. Production recovery or
release requires exact store-specific authorization; qualification used disposable
stores, fixed role-fixture time and zero transports, not UTC validation.

## Processing claims across actor generations

`codex-wake messages reconcile MESSAGE_ID --capability CAP --json` observes
committed metadata without acquiring mailbox time, changing expiry, reading the
body or granting another start. Processing reconciliation is separate from
notification uncertainty: `unclaimed`, `already_claimed`,
`held_for_original_claim`, or `known_terminal` backed by the exact recipient
receipt. A mismatched terminal pointer stays `held_for_exact_evidence`.
Original claim receipt/generation and current recipient generation are returned.
Rotation never transfers an accepted claim; a new generation cannot acknowledge
or complete the original work. Reconnecting alone does not create a new claim.
Operator reconciliation uses `--as-operator --operator-capability CAP` and commits
a bus audit receipt, with mailbox time explicitly `not_observed`.
