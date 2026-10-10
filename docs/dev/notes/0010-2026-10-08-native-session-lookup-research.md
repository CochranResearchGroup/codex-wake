# Native Codex session lookup research

## Scope and bound

Question: what built-in Codex tools discover existing sessions, and could Codex Wake reuse them for discovery or delivery?
Primary sources: installed Codex CLI help/binary, OpenAI's release-tagged source, and Codex Wake source. Output: this note. Stop after identifying the tool schemas, underlying requests, and material integration limits; no session messages, runtime changes, or implementation.

## Findings

- Installed CLI reports `codex-cli 0.162.0`. Its `agents --help` describes browsing sessions on the shared local app-server daemon. These commands were inspected without opening the interactive browser.
- The release defines the `codex_tui` namespace with `list_threads`, `list_archived_threads`, `read_thread`, `wait_threads`, and `send_message_to_thread`, among other task tools. There is no function literally named `session_lookup` in that specification. [Release tool schemas](https://github.com/openai/codex/blob/rust-v0.162.0/codex-rs/tui/src/dynamic_tools.rs#L74-L260).
- `list_threads` calls `thread/list`, returns up to 50 recent nonarchived threads, and does not accept a pagination cursor. Nonarchived does not imply currently running: summaries distinguish idle, notLoaded, systemError, and active. Summaries contain ID, title, preview, cwd, status, project ID, and update time; they do not contain tmux window/pane addresses. It is therefore useful discovery but not an exhaustive replacement for live-tab resolution. [List implementation](https://github.com/openai/codex/blob/rust-v0.162.0/codex-rs/tui/src/dynamic_tools.rs#L338-L389), [summary fields](https://github.com/openai/codex/blob/rust-v0.162.0/codex-rs/tui/src/dynamic_tools.rs#L1302-L1321).
- Native sending is more than discovery: `send_message_to_thread` reads the target, resumes it, registers it as a background task, and starts a turn with a delegated prompt containing the source thread ID. Its prompt is bounded to 1,000 UTF-8 bytes. Thus the earlier suggestion that built-ins only simplify lookup was too narrow. This is source evidence, not proof that native sending works for our independent live Byobu tabs. [Send implementation](https://github.com/openai/codex/blob/rust-v0.162.0/codex-rs/tui/src/dynamic_tools.rs#L683-L736), [turn submission](https://github.com/openai/codex/blob/rust-v0.162.0/codex-rs/tui/src/dynamic_tools.rs#L1227-L1255).
- Codex provides an MCP bridge for its TUI dynamic tools. Availability depends on the client connection; the current agent's callable catalog exposes neither `codex_tui` nor `codex_app` tools. Catalog absence does not establish product absence. [TUI MCP bridge](https://github.com/openai/codex/blob/rust-v0.162.0/codex-rs/tui/src/dynamic_tools_mcp.rs).
- Current released Wake discovery already consumes native app-server metadata directly: its read-only adapter permits initialize, thread/loaded/list and thread/read, requiring includeTurns=false. This is a different interface to native discovery, not an integration with the TUI MCP functions. Source inspected at Wake commit `6b822fad50209e217c79c6ab796b141c9f5258b2`. [Wake adapter](https://github.com/CochranResearchGroup/codex-wake/blob/6b822fad50209e217c79c6ab796b141c9f5258b2/src/codex_wake/shared_app_server.py#L26-L135).

## Recommendation and remaining evidence

Reuse native discovery where its coverage fits. Retain exact live-tab mapping for selectors such as `19:wake`. Before changing delivery, run a bounded native A-to-B-to-A experiment with two independent existing TUI sessions: verify recipient execution, ownership of the resumed session, UI synchronization, and automatic return to an idle sender. Compare that result with Wake's durable message, expiry, deduplication, and acknowledgment contract. Native sending is a plausible alternative transport; no claim that the Wake worker is inherently necessary follows from this research.

Validation: release-tag source fetched successfully and matched the installed CLI version; tool schemas and request bodies inspected. No native send or wake experiment was run. Existing unrelated untracked notes were preserved. Research conducted locally because discovery and synthesis shared the critical path.

Memory disposition: unavailable — no verified Codex Wake Graphiti group was established for this bounded research; findings remain in this source-cited note.
