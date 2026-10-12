# Disposable lifecycle runtime probe — PROTOTYPE

This is retained experimental code, not a production controller or automated
acceptance suite. It observes real installed Codex0.162.1 and Wake0.13.1 through
an isolated app-server/CODEX_HOME and owned tmux session. Read the findings before
rerunning; private raw state must be retained, not overwritten.

Run `python prototypes/agent-lifecycle/probe.py setup` with a new absolute
LIFECYCLE_PROBE_ROOT. Other actions are `open [EXACT_UUID]`, `stage v2`,
`send EXACT_UUID PROMPT`, `quit OWNED_PANE`, `status EXACT_UUID`, `cleanup`.
Use an installed Wake Python with websockets for status. Before a second open,
reconcile private state/native thread and tmux inventory; never replay uncertain
creation. `open` uses installed Wake; native prompts use installed Codex queue.

The script's quit action requests a command; it does not prove exit. Observe
composer command acceptance, actual old PID exit and native readiness externally.
After `/new`, inspect thread/loaded/list for the fresh ID before queuing its
handoff prompt. Its first message makes persisted thread/list useful again.
Keep at most six short model turns and twelve minutes per live probe. Never use
production threads, change shared configuration, reset a goal or widen a budget.
Close exact owned tabs normally and verify the owned server/MCP/process tree exits.

The fixture links existing auth privately and never prints or commits it. Toy MCP
version is captured at process startup so stale connections are observable.
The initial v1 fixture intentionally retains the observed annotation omission;
stage a read-only annotation correction before reproducing the successful v2
call. A default same-root rerun refuses existing state instead of destroying it.
