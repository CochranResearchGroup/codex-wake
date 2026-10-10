# Native workflows: capabilities and migration

Native Codex owns ordinary messaging, conversation history, turn execution and
status. Wake adds persistent conditions, bounded follow-up expiry, uncertain
submission recovery and visible Byobu lifecycle. No custom Codex patch or
shared-daemon restart is required. Plan0127 qualifies official Codex0.162.1. Native execution requires a Wake0.9
reader for the selected root; an older live monitor holds schema4 even when its
legacy health status is ready.

| Capability | Native support | Compatibility retained |
| --- | --- | --- |
| Immediate ordinary message | Native Codex messaging tools | Tracked mailbox only when explicitly requested |
| Basic time/file follow-up | Exact UUID, queue acceptance, expiry, explicit same-thread resume | Classic --legacy-tmux or explicit app-server target |
| Network-authoritative deadline | Not qualified for the native namespace | Existing classic --network-time policy remains available |
| Advanced signals and tracked receipts | Replacement parity not qualified | Existing schema2 journal and mailbox contracts |
| Visible new/resume/reuse/close | Exact thread/attachment identity and guarded close | Explicit force preserves conversation and affected work |
| Ambiguous native submission | Exact evidence reconciliation or inspectable unresolved state | No automatic resend or transport fallback |

## Existing records and command callers

Native `attempts` counts durable submission intents. It increments once before
queue submission, including interruption before the external effect. Busy,
unavailable and expired work consumes no attempt; reconciliation never increments
it. This counter is not execution proof. Migration preserves historical counters
exactly, including earlier accepted candidate records with zero attempts.
Malformed native counters are held for inspection instead of reset or dispatched.

Existing schema1 tmux/app-server records, schema2 signal journals and schema3
network-time records retain their readers and recovery contracts. No bulk state
rewrite occurs on startup. Update classic basic command callers to explicitly
select `--legacy-tmux`, or use `native after|at|file` with an exact UUID. Options
must precede positional triggers/prompts. Do not convert tracked mailbox flows
into ordinary messages if their durable receipt contract is required.

Earlier candidate schema1 native records need explicit promotion before an old
scheduler is allowed near them:

```bash
codex-wake --wake-root ROOT native migrate WAKE_ID
codex-wake --wake-root ROOT native migrate WAKE_ID --apply
codex-wake --wake-root ROOT show WAKE_ID
```

The first command previews. Apply holds the lifecycle lock, saves the original
with file/directory synchronization, and changes only the schema version to4.
Prompt, status, nonce, uncertainty and exact target remain intact. A conflicting
backup refuses; inspect it rather than overwriting it. Repeat application is a
no-op. Migration never submits or cancels work. Keep the same root path when
restoring native uncertainty: the recorded prompt hash includes that path.

## Rollback and recovery

Stop the scheduler for the affected root before replacing its executable. Keep
schema4 records and their original copies; an older supported Wake reader holds
unknown schema4 unchanged. Pending work will not execute until a capable reader
is restored. Do not downgrade native records to tmux, replay uncertain effects,
restore earlier candidate-native schema1 state into an old active scheduler, or
delete historical state. Restore a capable installed reader to the same root,
inspect `show`, and use `native reconcile` for uncertainty before considering
any further action. No claim of exactly-once delivery is made.

## Evidence and limits

Plan0127 acceptance receipts distinguish source candidate, installed commands,
native turns, durable state and visible panes. Ticket0132 proves old-reader
hold, restored native execution and same-root uncertainty preservation with
owned disposable state. Candidate acceptance alone does not prove release,
global installation, arbitrary Codex-version support or network-time parity.

## Local versioned deployment

The qualified workstation uses user entrypoints pointing to an immutable0.9
installation under `.local/share/codex-wake/releases/`. The existing uv-managed
0.8 environment is retained for already-running project workers. Its package
manager listing describes that retained environment, not the current user
entrypoints. The deployment receipt records exact link targets and rollback.
A future uv tool install may reclaim user entrypoints; perform it against the
intended release and account for workers using the old environment. No automatic
upgrade of unrelated per-project units is claimed.
