# Issue 383: Windows, WSL, terminal and Grok capability research

Date: 2026-10-29. Owner: ecochran76; delegated research lane `wayfind_platforms383`.
Canonical question: [#383](https://github.com/CochranResearchGroup/codex-wake/issues/383), decision map [#381](https://github.com/CochranResearchGroup/codex-wake/issues/381).
Wake source baseline: `0ab5a3a302a948ea658dc6af3e19219c73cc4296`.
Planning evidence only; no provider calls, credentials, infrastructure changes or installed-runtime acceptance.

## Scope and stopping rule

Question: which native mechanisms can support host-owned execution/state, authorized clients anywhere, symmetric Windows/WSL control, explicit presentation operations and correlated durable conversations? Read current first-party documentation/source only; stop once each platform, presentation, transport, identity, correlation, health and durability axis has a documented fact or explicit gap. Research skill and agent-reach GitHub routing applied. Supplied map and current repository records suffice for this lane; no advisory Graphiti recall was needed. No nested workers.

Upstream snapshots inspected through GitHub: `psmux/psmux` **1ba25a7f04b8f43656313dadd6c2b5350ee71b3b**, `psmux/psmux-plugins` **1e4d684754ec7f176de48560515661bc9ecd93bc**, `xai-org/grok-build` **2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8**, `openai/codex` **6174d05a6a17255dda97be686072eee00c4a1bc9**. These establish current source capabilities, not availability in deployed binaries.

## Compact capability matrix

| Surface | Verified native capability | Controller adapter or remaining gap |
| --- | --- | --- |
| Windows → WSL | `wsl --list --verbose`, explicit distribution/user execution [W1] | Persist host + Windows owner + distribution + Linux user + runtime-home identity; discover actual installations |
| WSL → Windows | Windows `.exe` interop and redirected pipes [W2] | Explicit executable, quoting, environment/path translation and authority checks |
| Remote Windows/Linux | OpenSSH remote commands; PowerShell SSH sessions [W3,W4] | Admission, durable request ledger and execution ownership; SSH connection identity is not provider identity |
| Byobu | tmux/Screen presentation enhancement; detach/attach via backend [T1] | Backend/socket/pane discovery; no provider completion or reboot-continuity proof |
| psmux | Native ConPTY, detached per-session server; structured control mode [T2,T3] | Bind pane generations to agent identity; framing acknowledges terminal commands, not model answers |
| Codex | JSON-RPC app-server; current source supports stdio/Unix/WebSocket; experimental daemon [C1,C2] | Version-specific capability negotiation, provider/account scope and durable bridge reconciliation |
| Grok Build | ACP stdio/WS server, sessions, headless correlated results [G1–G3] | Installed-version qualification; exact open-TUI concurrent input and independent health contract unresolved |
| xAI provider API | Responses IDs, retrieval, continuation and bounded storage [G4] | Coding runtime/tool execution, CLI session identity and durable flow controller are separate concerns |

## Windows/WSL and remote topology

Microsoft documents enumeration of installed/running distributions and selection of distribution/user; Linux can invoke Windows executables with `.exe` and mix redirected I/O. This supplies bidirectional process-launch primitives, not a unified cross-environment session registry. Explicit identities must avoid default-distribution/default-user drift. Shared filesystem reachability does not establish shared account authority. [W1,W2]

OpenSSH has clients and servers for remote management; Windows availability/configuration depends on OS installation. PowerShell SSH remoting supports Windows/Linux where SSH and PowerShell are configured. These offer authenticated remote launch channels; neither source establishes application-level exactly-once requests or agent conversation ownership. [W3,W4]

WSL systemd support does **not** itself keep the WSL instance alive. An always-on controller in WSL therefore needs a separately specified host startup/liveness contract. This note does not authorize changing it. [W5]

Feasible topology alternatives, with no selection:

| Topology | Native foundation | Tradeoff to resolve |
| --- | --- | --- |
| Windows owner, WSL execution adapter | `wsl.exe` dispatch, explicit distribution/user | Windows owns durable requests; Linux runtime homes and credentials remain scoped to that environment |
| WSL owner, Windows execution adapter | `.exe` interop, Linux service management | Must establish Windows boot/WSL liveness and Windows-side process ownership |
| One host controller, distinct environment workers | Local interop plus authenticated remote execution | More explicit identities and routing; one authority ledger must avoid duplicate dispatch |
| Host-local controller on every registered machine | SSH or application channel | Federation/admission and reconciliation required; client disconnect must not transfer work ownership |

These are architectural inferences from launch/transport primitives, not supported Wake configurations.

## Presentation lifecycle and stdio limits

Byobu enhances tmux/Screen organization; backend selection matters. Pane/window/session names are presentation locators. Closing or reattaching a terminal is separate from provider conversation resume. [T1]

The exact psmux project is **psmux/psmux**, a Rust native Windows ConPTY multiplexer, not an MPEG program-stream muxer or a similarly named npm package. Its architecture documents one detached server per session, multiple clients, loopback TCP and per-session key material under the user home. Pane processes belong to the server. `-C`/`-CC` provide framed command responses and notifications. These enable structured presentation operations, but terminal output still requires a runtime-specific completion/correlation contract. [T2,T3]

psmux documents detach/reattach persistence and separate resurrect/continuum plugins for reboot restoration. The resurrect plugin saves layouts, directories and selected commands; replaying a command is a new process, not restoration of in-memory agent execution. Restarting one must be an explicit policy intervention with conversation recovery checks. [T4]

Stdio belongs to a launched child/channel; a second client cannot simply open another copy of its stdin. A broker or remote launch channel must own initialization, serialization, approvals, event fanout, backpressure and reconnect reconciliation. Use non-PTY transport for machine JSON; keep terminal rendering separate. This is a proposed adapter consequence, not a native guarantee.

Current Codex source recognizes stdio (default), Unix socket and WebSocket listen transports. Its experimental daemon documents machine-readable lifecycle commands, SSH-oriented remote use and Linux/macOS/Windows support. Windows requires a suitable non-elevated host permitting detached children; automatic attachment has an AF_UNIX path-length constraint. Shared clients inherit the daemon environment; per-client environment isolation is explicitly absent. Do not project these current upstream capabilities onto Wake's stock/modded installed builds. [C1,C2]

Bounded transport alternatives: (a) SSH-launched stdio bridge, with channel loss and process lifetime reconciliation; (b) SSH forwarding to a host-local socket/WebSocket service, preserving server ownership while clients reconnect; (c) authenticated application WebSocket/HTTP gateway, requiring separately specified admission, TLS, authorization and replay rules; (d) current upstream Codex experimental daemon/remote-management path, pending version and authority qualification. None selects a production transport.

## Grok: runtime versus provider

First-party **Grok Build** source is distinct from third-party Grok CLIs and xAI inference. Its agent-mode guide documents ACP JSON-RPC over stdio, WebSocket serve with secret authentication, state across client reconnects and shared-leader options. ACP exposes initialize, session/new, session/load, session/prompt and streamed session/update; x.ai extensions cover filesystem, terminals, session operations and authentication. Discover actual methods from initialize rather than assume every release has all extensions. This is an alternative to terminal injection. The documentation's always-approve examples are not a recommendation or authorization to bypass approval. [G1]

Sessions are persisted under GROK_HOME, with authoritative conversation updates and UUID identities. `--session-id` creates; `--resume` resumes. Title selection is ambiguous compared with exact IDs. Documentation calls concurrent same-ID operation best-effort: neither saved history nor a shared leader proves safe simultaneous external control of an already-open TUI. Headless JSON/streaming-json returns sessionId, requestId and terminal result/end information; submission, completion and returned answer can therefore be modeled separately. [G2,G3]

Authentication supports cached browser/OAuth credentials, device flow and API keys with documented precedence. Account replacement/hot reload affects subsequent requests; a controller needs account-generation binding and explicit scope, not credential replication. MCP connectivity snapshots and process reachability are partial observations, not agent progress guarantees. No stable independent health endpoint/SLA was established by the reviewed Grok guides. [G1,G5]

xAI Responses supports response IDs, stored-response retrieval and continuation, with new responses retained for 30 days. The reference marks background processing as compatibility-only, currently unused. These APIs do not establish a Grok Build conversation or attachment to its tool executor. Durable flows need their own host ledger and recovery semantics beyond provider retention. [G4]

## Evidence gaps and next qualification packet

Resolve installed stock/modded Codex and Grok version-to-capability mapping; native Windows Grok support for the selected build; exact leader/TUI ownership and concurrent-update semantics; server health versus stalled-turn observations; cancel/timeout and uncertain-send recovery; restart/reboot resume without duplicate model/tool work; environment credential/account generation; registered-host admission and allowed-client scope. No experiment is implied. The next specification should state required semantics and mark unsupported parity explicitly before any separately authorized acceptance packet.

Memory disposition: **forbidden** — this research lane permits a cited repository note only; the primary owns reconciliation and any qualified memory closeout.

## Primary sources

- [W1: WSL basic commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)
- [W2: Windows/WSL interoperability](https://learn.microsoft.com/en-us/windows/wsl/interop)
- [W3: Windows OpenSSH](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh-overview)
- [W4: PowerShell SSH remoting](https://learn.microsoft.com/en-us/powershell/scripting/learn/remoting/ssh-remoting-in-powershell)
- [W5: WSL systemd lifetime](https://learn.microsoft.com/en-us/windows/wsl/systemd/)
- [T1: Ubuntu terminal multiplexers](https://ubuntu.com/server/docs/tools-byobu/)
- [T2: psmux architecture](https://github.com/psmux/psmux/blob/1ba25a7f04b8f43656313dadd6c2b5350ee71b3b/docs/architecture.md)
- [T3: psmux control mode](https://github.com/psmux/psmux/blob/1ba25a7f04b8f43656313dadd6c2b5350ee71b3b/docs/control-mode.md)
- [T4: psmux resurrection](https://github.com/psmux/psmux-plugins/blob/1e4d684754ec7f176de48560515661bc9ecd93bc/psmux-resurrect/README.md)
- [C1: Codex transports](https://github.com/openai/codex/blob/6174d05a6a17255dda97be686072eee00c4a1bc9/codex-rs/app-server-transport/src/transport/mod.rs)
- [C2: Codex experimental daemon](https://github.com/openai/codex/blob/6174d05a6a17255dda97be686072eee00c4a1bc9/codex-rs/app-server-daemon/README.md)
- [G1: Grok ACP/agent mode](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-pager/docs/user-guide/15-agent-mode.md)
- [G2: Grok sessions](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-pager/docs/user-guide/17-sessions.md)
- [G3: Grok headless mode](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-pager/docs/user-guide/14-headless-mode.md)
- [G4: xAI Responses API](https://docs.x.ai/developers/rest-api-reference/inference/responses)
- [G5: Grok authentication](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-pager/docs/user-guide/02-authentication.md)
