# Plan0267 stock and Wake Codex mailbox commands

Issue [#778](https://github.com/CochranResearchGroup/codex-wake/issues/778)
covers ordinary tab language in stock Codex and native mailbox slash commands
in Wake Codex. Both routes use the existing Wake mailbox and terminal-owner
interfaces.

## Fresh stock Codex

The disposable run used stock Codex 0.171.0, executable SHA-256
`b76a027d6b210f9a8da7aaf321dd235c700f0ef7a794d4a5314b9af6c134f0f0`,
with a fresh home, an installed copy of the Wake skill and the real stdio MCP
server. Approval was scoped to the two Wake tools used by the fixture.
The actual model context contained the Wake skill's ordinary-tab guidance.
The loopback fixture supplied deterministic tool choices to the stock
Codex code-mode runtime.

- A named-tab status question resolved the exact live project-reviews
  conversation.
- A request addressed to the agent in that named tab admitted a durable
  inbox message. The bound recipient read the same original message ID
  and body through its own Wake actor capability.
- A second tab with the same name produced an ambiguity result containing
  multiple candidates.
- After removing the duplicate and destroying the original tab, an ordinary
  restore request used the same approved launch profile, retained intent and
  exact saved UUID. The resolved receipt showed one new-window effect and
  the original conversation's CWD.

There were 11 loopback requests and no external model calls. The retained receipt is
`/home/ecochran76/.local/state/codex-wake/issue-778/stock-runtime-result.json`,
SHA-256
`d8de6d90e9219953eef6971e827258c4bda1946f5abbb12a304786e4e8d892ad`.
The first restoration assertion expected `tab_ready`. The supported receipt's
final state is `resolved` after readiness. Later runs asserted the exact
typed state, thread and effect. The final fixture used StableTime-backed
mailbox time after the legacy WSL clock interrupted one run.

The Wake source passed 65 local tests from `test_tab_targets`,
`test_tab_targets_mcp`, `test_a2a_mailbox`, `test_a2a_reply_wake`,
`test_wake_live_restore` and `test_command_contract`.
Evidence is retained at
`/home/ecochran76/.local/state/codex-wake/issue-778/wake-focused.log`.

## Wake Codex

Native sources start from the qualified Wake Codex 0.171 revision
`691605707cb31e41d1082230d70e3449ee9cf526`. The native composer adds
`/message`, `/reply` and `/dnd`. The command dispatch uses the actual current
conversation and existing mailbox capability. It supplies message text on stdin
and displays Wake's receipt through a thread-scoped native UI result.

The candidate source is `ca0782cfc0d8a0f2008b2f6d8eb727557e5ed664`.
The Wake repository retains both the Git bundle and an exact-reconstruction
patch. Verify the bundle and use `git apply --cached --unidiff-zero` from the
qualified base if reconstructing from the patch. The [source manifest](
../../../patches/codex/0267-native-mailbox-slash.json) records exact prerequisites,
tree and artifact hashes. Native source custody is independent of the Python
Wake service package.

The preliminary native package from `7d06c7823694b105d8c76c41f9a70f9fa028a093`
passed in the private fixture. Two actual Wake Codex TUIs attached to the
same private native app-server and used separate actor capabilities. The
sender addressed `project reviews` with a stable delivery key, and the
recipient found and read the same mailbox message. The recipient replied
with a new message linked to the original. The sender read the same reply
ID. Hold, bounce and clear changed the recipient's setting in PostgreSQL.
A duplicate tab name rendered `ambiguous_target` with candidates and added
no outbox message. The slash operations triggered zero model requests.

The first fixture attempts hit an incomplete TUI startup and an omitted
StableTime client setting in the pane. The qualified run waited for the
real native readiness display and passed the dedicated user's clock
configuration. Retained preliminary receipt SHA-256
`a811e563ad374bad8c938162ac4d948725928611506237623b7d19766e9c7f54`.

Using the same preliminary package, the native UI attached successfully
through the published Unix socket alias but returned `runtime_unavailable`
from the first slash send. The recipient's inbox stayed empty. Recorded
SHA-256 digests are
`50de161f6c3afbf6ad2614d3f4dc742ac9fad1be88ecd31453d76b47c1869186` for the
fixture result and
`802ce30abcb9527cfb17a73c284e0fc37eead83f76aca619ff7982f3d84b7c30` for the
TUI capture. The candidate canonicalizes the current conversation's alias
before presenting its runtime identity to Wake.

The final source built locally with Rust 1.99.1 and
`cargo build --locked --offline --profile dev-small --bin codex
--bin codex-code-mode-host --bin codex-exec-server --bin bwrap`.
Cargo Signal build `job-20261125T054702Z-6b580d11fc79` exited zero.
The maintained package assembler produced `0.171.0-wake778.2` for Linux
x86-64 GNU. All six files matched the installed copy under test UID 1017.
The inventory SHA-256 is
`36f4ec5c7a19aebb54fe342bb0f5cae2d4e1ce71143b0e0a9e195f0a336523a3`.
The installed `bin/codex` SHA-256 is
`18004c00b8a94786709feef90dd961b488a27315d79cfbe249ee47dac33411ea`.

The same native TUI journey passed through the published alias. The final
fixture reused the existing Wake service CLI with the private app-server,
tmux socket, StableTime client and disposable PostgreSQL database. It confirmed
send, recipient inbox and body reads, reply correlation, hold/bounce/clear,
and the ambiguity receipt with no added outbox message. The run made two
localhost seed requests and zero slash-command model requests. The final
process census found no owned fixture app-server, clients or tmux process.

The retained result is
`/home/ecochran76/.local/state/codex-wake/issue-778/native-final-runtime-result.json`,
SHA-256
`3cb75bbccdee9774d544a24a83180c5d70410b603776326c689c01250a71986a`.
The complete package and artifact inventory are retained under the same
private state directory. This was a side-by-side feature qualification
under the test user. Working-account updater, rollback and installation
are separate release qualification.
