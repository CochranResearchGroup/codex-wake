# MR-01: exact open Grok qualification

Date: 2026-10-22
Verdict: NOT_QUALIFIED_AUTH_REQUIRED
Work item: CW-MR-172/MR-01
Branch: test/mr01-grok-qualification
Base: a2ef06c
Owner: primary agent / ecochran76

## Frontier and Authority

The user requested one primary ticket and one independent subagent per other
non-blocked ticket. At wave start only MR-01 was ready. Primary took MR-01;
MR-02–MR-06 remained dependency-blocked. No subagents were spawned, no extra
ticket was pulled forward, and reconciliation has no delegated result to trust.

The directive starts the ticket's documented two-recipient/six-submission/
five-minute disposable qualification. It does not authorize approving a new
login, changing credentials, touching production conversations or restarting a
shared leader. Existing authentication was used as available; no sign-in was
approved or completed.

## Installed Surface and Preflight

grok 1.0.40, build eb1a2256660d, stable. tmux is installed.
Read-only CLI help confirms custom leader sockets, explicit session UUIDs,
headless/stdio, permissions, tool restrictions and session controls.

An empty private workspace had zero hooks, plugins, MCP servers, LSP servers
and project instruction files in the actual inspect result. Global skill
discovery remained present; no skill, tool or model task was invoked.
Before launch, record existing Grok/tmux process IDs and process generations.
Use a private user-scoped evidence directory and short private temporary socket
directory. Keep raw terminal/auth evidence private and redact device codes.

## Reproducible Probe

1. Create a mode-0700 private run directory with an empty workspace, unique
   requested session UUID, private tmux socket and private Grok leader socket.
   Do not reuse a production socket or conversation.
2. Launch a real interactive TUI in a disposable tmux pane using:
   GROK_DISABLE_AUTOUPDATER=1 and a process-scoped GROK_CONFIG overlay with
   cli.use_leader=true and cli.auto_update=false.
   Grok arguments: --leader-socket <private-socket>, --cwd <empty-workspace>,
   --session-id <new-uuid>, --tools "", --permission-mode dontAsk,
   --no-subagents, --disable-web-search, --max-turns 1, --no-alt-screen.
   Add --sandbox read-only for the first sample. Extra rules restrict this
   disposable receiver to replying with a requested synthetic marker and forbid
   tools, file edits and messages.
3. Inspect the pane before any prompt. The first sample showed Sign in to Grok,
   so input was withheld. Its sandboxed window was retired.
4. Repeat one TUI launch without the sandbox flag, using another fresh UUID
   and the same private test leader scope. It also showed sign-in. No
   authentication action, prompt paste or Enter was performed.
5. Native observation: launch grok agent --leader --leader-socket
   <private-socket> stdio from the same private workspace. Send JSON-RPC
   initialize with protocolVersion=1, clientInfo naming this probe and client
   capabilities fs.readTextFile=false, fs.writeTextFile=false, terminal=false.
   Observe the response. On a second initialized connection send session/list
   with cwd set to the exact private workspace.
6. Do not call authenticate, session/new, session/load or session/prompt to
   manufacture a conversation when live identity is unavailable. Terminate
   the owned stdio clients. Kill only the exact test tmux session on its private
   socket. Identify the private leader via SO_PEERCRED and matching process
   generation before terminating that peer. Re-read OS processes afterward.

These are the actually exercised operations, not a new production launcher.
Input/protocol actions that could submit a conversation prompt were never reached.

## Observed Result

Both sandboxed and default-sandbox TUIs required interactive sign-in. This
discriminating sample does not support attributing the failure solely to the
explicit read-only sandbox. Requested UUIDs did not establish live conversation
identities.

Two native initialize responses advertised protocol version 1, session loading,
listing, resume and close. The workspace-scoped session/list returned zero
sessions, with conversations partial=false. This proves protocol availability,
not authentication, loaded-session control or delivery into an open TUI.

No conversation prompts, terminal input actions or native effectful requests
were submitted. Model execution, busy handling, an authenticated negative identity
case, receiver acknowledgment and A2A work receipts remain untested.
Input was deliberately withheld at sign-in; this is not a passing test of an
implemented production unknown-UI guard.

The live probe/teardown took 190.854 seconds, below its 300-second bound.
Two TUI launch attempts were used, below/equal to the two-recipient bound;
zero of six permitted conversation submissions were used. No automatic retries.

## Cleanup and Reconciliation

Test pane and private leader were retired by exact ownership/generation.
An initial post-teardown census saw one new transient Grok process; it was not
assumed safe to kill. The fresh final census showed zero introduced Grok/tmux
processes and preserved every pre-existing process generation.
No production-adapter edits, manual config/credential changes, shared-service
restarts or grant mutations were performed.
Synthetic/private probe evidence remains outside Git; no device codes are
published.

Sanitized machine receipt:
[mr01-auth-gated.json](../evidence/plan0172/mr01-auth-gated.json).
The native session-list result is complete for this workspace but empty; no
native or terminal delivery route is selected or qualified.

MR-01 is BLOCKED on interactive authentication. Its bounded negative observation
is complete; MR-02 is not unblocked merely because this probe ended.
After Grok sign-in is restored through its normal interactive workflow, rerun
MR-01 with a new bounded run ID before selecting a production delivery route.

## Documentation Validation

Check JSON parsing, required negative verdict/effect counts, budget and final
cleanup fields, relative document targets and Git whitespace. This packet changes
no production code and adds no implementation-mirroring tests.
The broader Plan0172 first-release criteria remain unexecuted.

Executed checks: receipt invariants PASS; 121 relative targets across the touched
documents PASS; whitespace PASS. Active planning audit retains the same four
Plan0166–Plan0169 header findings, with no Plan0172 finding. Plan0172 BLOCKED state,
Current State, lane and roadmap/runbook wiring pass. No broad runtime test suite
or live-delivery acceptance is claimed.

Upstream [configuration documentation](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/05-configuration.md)
informed the process-scoped overlay;
[agent integration documentation](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-shell/README.md)
describes stdio/ACP. Installed 1.0.40 responses, rather than current upstream
documentation, determine the protocol-availability verdict in this receipt.
