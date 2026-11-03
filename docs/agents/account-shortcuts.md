# Everyday account shortcuts

Plain `codex` remains the stock executable and default home. These commands use
registered private Wake account homes; completion setup creates no codex alias.
They are local client/confirmation conveniences over existing build/history
operations, not a second runtime or account database.

Select the root explicitly once (no credentials are copied):

```sh
codex-wake configuration default-root /path/to/private/wake-root
codex-wake open ecochran76
codex-wake open soylei
codex-wake resume ecochran76
codex-wake resume ecochran76 --last
codex-wake resume ecochran76 EXACT_UUID
```

The preference is private under `$XDG_CONFIG_HOME/codex-wake/shortcuts.json`
(or `~/.config/codex-wake/shortcuts.json`). Global `--wake-root ROOT` takes
precedence. These shortcut preferences do not change unrelated legacy command
root defaults. Completion uses the same preference unless explicitly overridden.
Open/resume select and pin registered build bytes internally; the existing launch
owner starts/attaches the matching managed daemon and refuses an incompatible
selected package. No automatic hot update, new model prompt, goal enrollment or
credential movement is introduced. Native exit status is preserved.

**Bare `codex-wake resume` retains its existing emergency-pause release meaning.**
An account argument selects conversation resume; mixing that with emergency
scope flags is refused. Invalid account shortcuts never fall back to unpausing.
Without a UUID/--last, native Codex presents that account's conversation chooser.
The saved-history read policy must authorize UUID/last discovery for that account.

## Skim recent conversations

```sh
codex-wake history recent --owner ecochran76 --limit 10
codex-wake history recent --owner ecochran76 --limit 10 --json
```

Recency uses native updated_at, or native created_at when updated_at is absent,
then a qualified rollout-file mtime fallback. JSON includes recency_source.
Results sort descending by activity and UUID for ties, before the bounded source
rollout reads. The latest N selection is not silently refilled with older sessions
when a selected history is unavailable or unsupported. Partial discovery and
holds remain visible. N is1–100; default10. Existing admission policies apply.
API/OAuth MCP/native MCP can use `history.search` with `owners`, `sort="recent"`
and `limit`; the CLI also accepts `history search --sort recent --limit N`.

## Copy the latest N to another account

```sh
codex-wake history import-recent --owner ecochran76 --destination soylei --limit 5
```

In an interactive terminal this saves a frozen preview, displays it and asks for
confirmation. Both selected account daemons must already be running for copies;
preview never starts them. Existing import support remains completed, idle,
goal-free legacy JSONL/schema5. Sources stay in place; destination conversations
get distinct UUIDs and no credentials, goals, grants or resource allowance.

For automation, preview first and use the returned batch ID:

```sh
codex-wake history import-recent --owner ecochran76 --destination soylei --limit 5 --preview --json
codex-wake history import-recent --batch BATCH_ID --yes --json
```

Noninteractive calls without --yes only preview. Retries reuse that frozen
selection, source revisions, destination pins and per-entry intent keys; newer
source histories cannot sneak into an approved batch. Repeated new batches for
the same source revision/destination home also reuse the original transfer intent
and return existing children, rather than duplicating copies. A changed source
revision or destination home generation represents a different transfer.

Results report copied IDs, discovery holds, unsupported histories and failed or
uncertain operations per entry. Unknown results stay in the existing operation
journal; retry queries that same intent and never blindly forks again. Partial
copy returns exit2, with successful children retained. Batch/intent manifests are
private under the selected root's controller-history-batches; no raw transcripts
or credential contents are included. Batch IDs are validated; symlinked or
unowned manifests are refused. API/MCP callers can orchestrate the same scoped
history.search/history.import operations; interactive batch confirmation and
local root preferences are explicit local-only conveniences.
