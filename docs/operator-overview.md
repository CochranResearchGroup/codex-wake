# Operator overview

`agents overview` is a one-shot terminal table; `--json` returns the same redacted
projection. It lists managed inventory only. It does not discover every agent on
the machine. Use `--limit` (1..100), `--timeout` (.1..30 seconds) and `--freshness`
(.1..300 seconds) to bound the scan. Each runtime read receives the remaining
monotonic budget; unread rows remain unknown. Truncation and incomplete semantic
reads mark `complete=false`, with CLI exit 3. Invalid/unavailable requests exit 2.

Workspace is the enrolled execution path. Repository/worktree identity is verified by a bounded local Git read with inherited
GIT environment removed. The canonical common directory and its device/inode identify
the repository; the canonical top level identifies its worktree. Failed or exhausted
reads remain explicitly unknown. Task IDs may be unassigned. Binding freshness and semantic
freshness are separate columns. Unknown/unsupported state is displayed with its
evidence timestamp, reason and capabilities. No completion or operation grant is
inferred. Prompts, frames, transcript bodies, credentials and host endpoints are
excluded. Existing inventory owner reads use a filesystem lock; the scan deadline
bounds runtime work but cannot preempt an externally held inventory lock.

`agents focus --managed-agent-id ID --bus-root PATH --operator-capability PATH`
switches the invoking existing tmux client to the exact existing session and selects
its window and pane. The invoking client is qualified from stdin tty and the live
client list; outside an interactive caller, pass `--client /dev/pts/N` for an exact
owned client tty. Missing, foreign or ambiguous clients hold the action. The command does
not start/resume a conversation, send input, open a shell, create a client or infer a client from a model-supplied role. It requires a verified local operator bus
capability and an active common permission policy allowing `workspace.navigate`
for that operator and exact conversation. Policy is rechecked immediately before
I/O. A denied or absent policy holds the action.

Focus requires a current enrolled binding, fresh exact native conversation
namespace/root/process evidence, complete live session sources, one attachment,
a canonical owned socket, and repeated exact pane/window/session/process identity.
Ambiguous, suppressed, stale, disconnected or changed evidence holds the action.
Grok focus is unsupported until an equivalent attachment navigation qualification
exists. MCP exposes overview and navigation-plan reads only; it cannot focus.

Source fixtures exercise a private tmux server, a disposable process named `codex`
and native protocol responses through the actual readers. They qualify local
command selection and redaction; they do not establish installed service or
production runtime acceptance. An actual PTY-attached client starts in another private session; readback proves
client session switching and pane selection without creating sessions. Shared
CLI/MCP registration belongs to integration.
