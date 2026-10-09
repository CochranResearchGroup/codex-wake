# PROTOTYPE: native session discovery and idle reply wake

Question: can stock Codex 0.162.0 deliver A→B→A through native tools when A ends its turn before B replies, including independent existing TUI clients?

Verdict: **PASS for both tested topologies.** No Codex Wake delivery, mailbox, time provider, or worker participated. No production code changed.

## Evidence

| Topology | Sender A | Recipient B | Result |
| --- | --- | --- | --- |
| Native-created tasks | `01a11eb1-6fdc-7273-8368-d0f53cb2045f` | `01a11eb1-57f6-7380-9c61-f047662a8858` | A ended; B delayed; native reply started a new A turn |
| Two independent TUI processes | `01a11eb2-6bc0-75b2-ac35-951e563449c1` | `01a11eb2-6c3e-76e2-b2d1-50a88c1a8a4c` | Same, with reply and completion visible in original panes |

Independent A's sending turn `01a11eb2-c946-73f3-adab-4ca4cfe39e31` completed at server timestamp 1791516404. Its receiving turn `01a11eb3-4912-77c3-9774-a327f30b5711` started at 1791516428 and completed at 1791516430, returning `INDEPENDENT_20261008_RECEIVED`. Thus A was idle before the reply; it did not remain in a polling turn. These timestamps are ordering evidence from the same server, not a clock-accuracy claim.

Both native sends appear as completed `codex_tui.send_message_to_thread` calls in the attached structured readbacks. The original independent TUI panes show the delegated messages and final tokens. The dedicated tmux socket was used only to host and inspect clients, never to paste test messages. Client PIDs before cleanup: A 58936, B 58941.

`independent-idle.json` preserves the observed idle state before the reply. Actor JSON files preserve native `read_thread` results; pane text files preserve visible UI transcripts. Only disposable test actors were read. Native `list_threads(limit=50)` also returned both independent IDs, but full discovery output was not retained because it contained unrelated session metadata.

## Reproduce

From this checkout, run `python scripts/prototype_native_sessions/run.py start`, then `status` until both fresh IDs and READY tokens appear. Use native `send_message_to_thread` to instruct A to native-send to B, with B delaying 20 seconds before native-sending back to A. A must finish immediately after sending. The exact successful instructions and tool arguments are retained in the JSON files. Observe idle A before the reply using `wait_threads`, then read both threads and capture both panes. Run `stop` to terminate only the dedicated socket's clients. Use fresh IDs; do not send to the archived historical actors.

Replay the saved evidence with `python scripts/prototype_native_sessions/verify.py`. Replay validates the retained result; it does not execute another live exchange.

## Decision and limits

Native discovery and native thread sending should be the first integration candidate on clients exposing these tools. The experiment disproves any blanket claim that idle-session wake requires a custom notification worker. Wake's live tab selectors and durable message contracts are separate capabilities; their need should be decided individually.

The experiment covers two successful exchanges on one workstation and one shared app server, with idle recipients and short prompts. It does not qualify concurrent sends to busy recipients, restart recovery, expiry, deduplication, acknowledgment guarantees, unavailable clients, cross-host delivery, or every Codex version. The independent clients were ordinary tmux-hosted TUIs; existing unrelated Byobu tabs were not touched. No production replacement was implemented.

Source contract: [OpenAI 0.162.0 tool schemas and implementation](https://github.com/openai/codex/blob/rust-v0.162.0/codex-rs/tui/src/dynamic_tools.rs). Research context: `docs/dev/notes/0010-2026-10-08-native-session-lookup-research.md` in the original checkout. This prototype branch is the primary runtime evidence; it supersedes that note's earlier statement that native sending was untested or unavailable in the current catalog. Tools became available in the subsequent turn.

Memory disposition: unavailable — no verified project Graphiti group; this committed experiment preserves the findings.
