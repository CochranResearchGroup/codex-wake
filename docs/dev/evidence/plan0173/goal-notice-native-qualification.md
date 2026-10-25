# Goal notice native/frontend qualification (#344, #345)

The local native development dependency is isolated from the shared daemon. It is
not an official Codex release, a general runtime upgrade, or broad native-suite
acceptance. The full watcher/enrollment/approved-renewal journey is a separate
integration acceptance owned by the primary coordinator and #346 worker.

## Native presentation seam

`thread/inject_items` alone cannot establish operator visibility: its raw history
items do not produce an ordinary frontend message. The dependency adds bounded,
exact-thread `thread/notice/append` and `thread/notice/read`. An append records a
`core/context` InternalModelContextFragment with source `external_supervision`,
a replayable agent display event, and the existing `item/completed` publication.
It never starts a user/model turn, changes a goal, or edits native usage counters.
Text is bounded to768 UTF-8 bytes; event IDs to128 ASCII bytes. Duplicate matching
IDs do not append or publish again; changed content refuses. Publication remains
separate from actual rendering and human reading.

Native behavior revision71620df88c3267760064af171bfd66f1264dfaaf (based on scoped
refresh development revision6115475dd95f6ffd525992bd5f98051d543a4c68) passed the
first public-RPC case, the254-case protocol gate and a stock-renderer snapshot.
This revision is superseded for the joined watcher journey because its older base
lacks response-level accounting. Its presentation evidence remains valid for the
unchanged presenter; it is not proof of accounting compatibility.

## Actual stock frontend evidence

Artifact root outside Git:
`~/.local/state/codex-wake/goal-limit-ux/345-native-render-final/`.
Actual stock frontend0.164.0 attached with `--remote unix://OWNED_SOCKET resume ID`
to the owned development server. `rendered.txt`, `busy-tool.txt` and
`reconnected.txt` retain the actual terminal capture. The parent owns the installed
Wake watcher journey; this fixture used explicit presentation data, labeled in its
receipt, and does not claim real external allowance enrollment.

- Notice rendered live, during an explicitly owned shell task, and once after a
  fresh frontend reattachment to the same conversation.
- Actual native readback retained model context independently of the terminal.
- A deliberately lost Wake/native append acknowledgement reconciled via actual
  native readback, retaining one append attempt instead of replaying the notice.
- A peer's native turns stayed unchanged. There were zero model/provider turns;
  the one explicit shell task was interrupted by its exact captured turn ID.
- Initial cleanup readback caught asynchronously exiting owned frontend children;
  `cleanup-followup.json` proves those exact remaining PIDs absent. The earlier
  `cleanup_incomplete` receipt is preserved rather than overwritten.

The initial setup attempts are retained separately: system Python lacked the MCP
WebSocket dependency; untouched native threads also deferred their rollout files.
The corrected fixture uses the declared installed dependency environment and the
notice read's session-header materialization, with no invented usage history.

## Accounting and caller compatibility prerequisite

The development base predates upstream response-level accounting even though the
shared installed0.164 runtime supports it. The actual joined fixture failed with
`first_usage_unavailable` after a genuine local mock response. Red evidence:
`~/.local/state/codex-wake/goal-limit-ux/346-native-journey-20261025T045000Z/attempt2/receipt.json`.

The bounded compatibility port follows upstream
5f79a92e3936274318d2122ae3244e5edd80dd1f, preserving exact response ID, provider
input/cached/output usage, thread/session/turn identity and canonical cumulative
record state. It emits the raw completion separately so absent usage remains
unknown. Root turn attribution is admitted only for the actual root session;
unproved descendant attribution leaves an unmatched raw completion and holds Wake
accounting rather than inventing lineage. Legacy remote compaction similarly
retains explicit missing response/usage evidence and cannot qualify accounting.
Local and v2 compaction use their actual response completions.

Ordinary private-stdio MCP calls also retain the actual runtime session ID and call
ID alongside native thread and turn metadata. Tool arguments cannot create those
fields. These additions restore the real session-facing qualification path; no
host grant, private policy or capability is copied or broadened.

Final native source, binary hashes, current test results and joined journey verdict
must be read from the integration ledger and final native manifest. They remain
pending until the authentic writer and actual MCP path pass their public seams.
