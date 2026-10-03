# Session discovery and Byobu selectors

State: OPEN
Lane: P62
Parent: P63 / Plan 0101

## Current state

The command design is complete; implementation and acceptance remain pending.
Plan 0097 supplies exact-thread tmux routing and process-generation checks.
Existing `app candidates` scans saved rollouts and is not a live inventory.
A read-only host probe successfully queried the existing shared daemon through
WebSocket over its Unix socket with `thread/loaded/list` and `thread/read`.
Byobu window indices, window names, pane IDs, titles, and working directories
are available through tmux. All five session verbs now have an initial implementation; final installed
acceptance and remaining contract qualification are pending.

## Objective

Let humans and agents discover live Codex sessions and refer to them by Byobu
tab, while preserving exact thread identity and honest binding evidence.

## Scope and non-goals

Design five read-only verbs: `list`, `show`, `resolve`, `current`, and `watch`.
Discovery includes loaded daemon threads and running Codex TUI candidates;
shell-only panes appear only when explicitly requested. Saved history, mailbox
writes, delivery, steering, resume, archive, delete, and unload are outside this
slice. No permanent alias registry or wake-record schema migration is needed.
Discovery must not start a daemon, resume a thread, subscribe to a thread, start
a turn, or keep a session loaded. Implementation must verify the side effects
of each read method against the installed protocol.

## Command contract

| Verb | Purpose | Example |
| --- | --- | --- |
| `sessions list` | Inventory of loaded threads and TUI candidates | `codex-wake sessions list --json` |
| `sessions show REF` | Inspect one selection, evidence, and limitations | `codex-wake sessions show 16:mapocock` |
| `sessions resolve REF` | Obtain one exact identity with binding evidence | `codex-wake sessions resolve wake --json` |
| `sessions current` | Identify the invoking agent's thread and tab | `codex-wake sessions current --json` |
| `sessions watch [REF]` | Observe inventory/status/binding changes | `codex-wake sessions watch wake --duration 5m --json` |

All verbs support `--json`, `--app-server unix://[PATH]`, `--tmux-socket PATH`,
`--tmux-session NAME_OR_ID`, and a bounded `--timeout` (default 10 seconds per
source). Endpoints must refer to existing runtimes. Start with local Unix
transport; remote WebSocket authentication is separate work. Resolve default
endpoints through Codex's supported locator and current tmux context, not a
hard-coded host path or arbitrary filesystem scan.

### List

Default output columns: TAB, THREAD, STATE, BINDING, NAME, CWD. Display thread
IDs compactly, retaining full IDs in JSON and show. Include roots and subagents,
with parent ID and agent path where available; `--roots-only` hides subagents.
`--state active|idle|unknown` and `--cwd PATH` filter observations. `--all-panes`
includes ordinary shell panes explicitly labeled `not_codex`. `--limit` bounds
returned rows and reports truncation; it must not create false uniqueness in
resolve. Thread records contain an array of TUI attachments, since one thread
can be displayed in several panes; unbound panes remain separate rows.

### Show

Show the selected thread's full ID, source/runtime, parent relationship, name,
working directory, state and active flags, all observed tab attachments,
process generations, evidence timestamps, binding status, and source warnings.
Selecting a shell-only tab shows `not_codex`; it does not select another thread
in the same directory. No transcript or raw scrollback is read or displayed.

### Resolve

Return an exact thread ID plus a structured observation of how REF resolved.
Do not choose the first match, a recent thread, or a same-directory thread.
For tab selectors, require one unambiguous thread-to-pane match under Plan
0097's exact-thread metadata and process-generation rules. Label this
`metadata_matched`; it is the existing product's matching contract, not a
runtime-issued identity attestation. Candidate-only evidence is insufficient.
Two threads with identical title/cwd remain ambiguous even if only one appears
active. `--require-attested` requires a future runtime-issued thread-to-client
binding and fails as unsupported until that evidence exists.
A full thread selector can resolve identity without a TUI. A loaded thread is
not necessarily authorized or ready to receive input. A resolved observation
is not a delivery token: downstream actions must revalidate exact identity,
process generation, and transport safety immediately before acting.

### Current

Prefer an explicit runtime-provided `CODEX_THREAD_ID` and validate it against
the existing daemon. Environment inherited by a subprocess is a claim requiring
validation, not proof of its pane. Use tmux context to identify the invoking
pane, then apply the same matching rules as resolve. A parent agent's inherited
pane must not become a subagent's attachment. Conflicting thread/pane claims
fail visibly. Outside tmux, a valid thread can be returned with no tab. Missing
identity must not fall back to cwd or newest saved session.

### Watch

Poll read-only snapshots every 5 seconds by default (`--interval`, minimum
1 second); `--duration` defaults to 5 minutes. A positional REF is resolved
once to a thread ID. Continue tracking that ID across tab moves or renames;
never silently follow a replacement occupant of the original tab. Without REF,
watch the complete selected inventory. Emit JSONL initial snapshot followed by
`session_added`, `session_removed`, `status_changed`, `attachment_changed`,
`source_unavailable`, and `source_recovered` records, plus a terminal summary.
Source failure is not evidence of session removal. Ctrl-C exits cleanly. Never
subscribe, resume, or extend the thread's inactivity lifetime to watch it.

## Selector grammar and ambiguity

- `16`: window index 16 in the selected tmux session.
- `wake`: exact window name; no substring or fuzzy matching.
- `16:mapocock`: index plus expected exact name; both must match. This guards
  against index reuse or rearrangement and is not a persistent identity.
- `16.1` or `16:mapocock.1`: explicit pane index for a split window.
- `tab:NAME`: literal window name, including numeric-looking names. A period
  or colon in a name is literal with this form; use `pane:%ID` to disambiguate
  its split panes.
- `window:@ID` and `pane:%ID`: tmux object IDs scoped to the selected socket.
- `thread:FULL_ID`: full exact Codex thread ID; no prefix matching in v1.

Use `--tmux-session` for explicit tmux session qualification. Infer it from
current tmux context; outside tmux infer only if exactly one session exists.
Never search all tmux sessions and select the first. A window with multiple
eligible panes requires an explicit pane selector; no active-pane shortcut.
Duplicate names always produce an ambiguity error listing qualified choices,
even when one tab is a shell. For example, tabs `16:mapocock` and `27:mapocock`
require qualification. Tab numbers/names are human selectors; durable records
must store the exact thread ID and runtime location/generation separately.

## Observation and JSON contract

Use `schema_version: 1`, `observed_at`, `complete`, `sources`, and `sessions`
in inventory output. Per-source reports include endpoint, observation time,
availability, and bounded error code. Per-session fields include `thread_id`,
`name`, `cwd`, `source`, `parent_thread_id`, `agent_path`, `runtime_state`,
`active_flags`, `binding_status`, `attachments`, and `warnings`. Missing values
are null, not guessed. Attachments include socket, tmux session ID/name,
window ID/index/name, pane ID/index, client PID and start ticks, and evidence.

Keep three separate concepts:

- Runtime state: `active`, `idle`, `not_loaded`, `unknown`; preserve provider
  state/flags separately when the installed protocol adds new values.
- Binding: `metadata_matched`, `candidate`, `ambiguous`, `unbound`,
  `not_codex`, or future `attested`.
- Availability: source `available`, `unavailable`, or `unsupported`.

List can return useful partial observations while setting `complete: false`.
No unavailable source becomes an empty authoritative inventory. Observe only
runtime metadata; avoid prompt bodies, full transcripts, raw pane captures,
credentials, or arbitrary environment dumps. No persistent cache in v1.

## Exit and error contract

| Exit | Meaning |
| --- | --- |
| 0 | Complete successful observation/resolution, including an empty list |
| 2 | Invalid arguments or unsupported selector syntax |
| 3 | Selection not found in complete authoritative observations |
| 4 | Ambiguous selection, with candidate choices |
| 5 | Required source unavailable, unsupported, or incomplete |
| 6 | Selection found but cannot resolve to an eligible Codex identity |

JSON errors include `code`, `message`, `selector`, `candidates`, and source
warnings. Incomplete input cannot justify not-found or uniqueness. List output
may include partial rows with exit 5. Shell-only show succeeds with its explicit
classification; shell-only resolve exits 6. Successful resolving of an exact
thread ID requires a daemon read; history candidates are not a substitute.

## Implementation packets

1. Shared-daemon local transport and read-only loaded-thread discovery, with
   bounded framing, handshake, payload size, pagination, and error behavior.
   Reuse the existing app-server abstraction without altering stdio dispatch.
2. Tmux tab inventory, exact selector parsing, unique matching, and generation
   revalidation; retain Plan 0097 and Plan 0099 safety boundaries.
3. List/show/resolve/current CLI and stable JSON/error contracts.
4. Bounded polling watch and documentation; installed read-only acceptance.

One primary lane owns these dependent packets. No parallel worker is needed.
Do not reuse the ad hoc probe's hand-written WebSocket framing as production
transport; choose a maintained dependency or supported client after reviewing
package policy and compatibility. No implementation authority is implied by
this completed design artifact.

## Acceptance criteria

- Named tabs distinguish multiple threads in one repository.
- Duplicate names, split panes, title/cwd collisions, unavailable sources, and
  truncated inventories never produce a guessed recipient.
- Index-plus-name detects renames/reindexing; pinned thread identity survives
  tab moves, and a reused pane fails process-generation validation.
- A shell tab and a loaded headless/subagent thread are represented honestly.
- Current distinguishes the invoking thread from inherited parent context.
- Daemon absence, restart, pagination, and unknown status are inspectable.
- Watch preserves identity and emits changes without extending session life.
- Installed acceptance verifies reads cause no turns, resumes, subscriptions,
  prompt injection, or persistent registration, and releases client resources.
- Deterministic provider-free tests cover public CLI outcomes and JSON contracts.

## Definition of done

Design: this contract, roadmap lane, and dated runbook entry are coherent and
pass documentation hygiene. Implementation: all packets and acceptance above
pass, then update plan state with installed evidence. Design completion is not
runtime delivery or implementation completion.

## Implementation checkpoint | 2026-10-03

- Supported read-only locator: `codex app-server daemon version` reports
  socketPath. The owned control symlink is resolved only through this locator;
  explicit socket endpoints reject symlinks. No daemon start/restart occurs.
- Session inventory, exact selectors, current-thread validation, bounded JSONL
  watch, metadata-only output, and source-failure exits are implemented.
- Live metadata read resolved 17:wake and 7:mail-receipts; duplicate mapocock
  returned ambiguity. One-second pinned watch completed. These reads establish
  source behavior, not message delivery or comprehensive installed acceptance.
- Focused checks: 11 session tests and 10 shared reader tests pass. Existing
  CLI checks: 66 pass. Comprehensive suite: 733 tests, 36.459 seconds, no retries;
  run preceded the final locator/watch test additions and title normalization.
- Remaining P62 gates: exact unloaded-thread query semantics, status/protocol
  compatibility, complete generation/source-race qualification, installed
  package acceptance, and final documentation/CI checks.

## Discovery acceptance checkpoint

Local implementation qualification is recorded in verification 0094. The
existing-runtime probe and installed provider-free protocol/resource smoke
passed; hosted gates and canonical integration remain pending. Exact headless
selectors require only an available daemon; missing optional tmux is reported
in sources and complete=false without preventing an exact identity read. Tab
selectors still require complete sources. Unloaded identities are not resumed:
this installed runtime rejects metadata reads of unloaded threads. Discovery
reports absent live identity, rather than pretending history is a loaded target.
