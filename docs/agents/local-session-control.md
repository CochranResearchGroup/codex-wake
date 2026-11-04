# Local session control from WSL and PowerShell

Start one same-user WSL controller:

```sh
codex-wake control server start
codex-wake control server status
codex-wake control remote list
```

The new control and self-limit commands use the saved shortcut default root, or
user-local state when no preference exists. Global `--wake-root ROOT` selects an
explicit root. Existing wake/admin commands retain their previous root rules.
Startup creates a private connection receipt automatically; no OAuth enrollment
or manual grants are required. The server is loopback-only. Public OAuth ingress
is a separate deployment surface.

## Prompt and retrieve

```sh
codex-wake control remote prompt thread:UUID 'Do this task' --mode stream --timeout 120 --idempotency-key my-task-1
codex-wake control remote output OPERATION_ID --mode transcript --cursor 0
codex-wake control remote result OPERATION_ID --mode final --timeout 120
codex-wake control remote cancel OPERATION_ID
```

`control list/resolve/prompt/output/result/cancel` are also available directly on
WSL, sharing the same operation owners and journal. `control remote` explicitly
uses the running server. Friendly names must resolve uniquely; exact thread UUIDs
avoid ambiguity. Discovery pins the owned native peer, account home, process and
socket generation. A restarted or replaced target is not silently retargeted.

| Mode | Caller output |
| --- | --- |
| stream | Live native response text |
| transcript | Ordered structured native turn, tool and telemetry events |
| final | The saved final answer, without the turn-event wrapper |
| silent | No normal stdout/stderr; actionable errors remain nonzero |

Without a mode, prompt returns a durable operation receipt. Explicit keys make
retries refer to the original intent; they never mean “submit another prompt.”
The remote clients generate a key before transmission when one is omitted.
Timeout returns124 and leaves work running. Uncertain delivery remains retained
and returns a nonzero status; never manufacture a new key to bypass uncertainty.
Output retention and cursor gaps are explicit; incomplete output returns3 rather
than pretending to be a full transcript. Hidden reasoning is excluded. A native
model's actual answer is returned faithfully, including punctuation.

## Windows PowerShell

Render the native client once to a Windows-accessible location:

```sh
codex-wake control powershell > /path/to/codex-wake.ps1
```

Then in PowerShell:

```powershell
& .\codex-wake.ps1 control list
& .\codex-wake.ps1 control prompt thread:UUID "Question Δ`nSecond line" --mode final --timeout 120
& .\codex-wake.ps1 control output OPERATION_ID --mode silent
```

The client privately captures its WSL connection bootstrap and sends UTF-8 JSON
directly to the same controller. It preserves native exit status and streams
output as frames arrive. `-Distro`, `-WakeCli` and `-WakeRoot` select an explicit
installation when needed. No bearer appears in command arguments or normal
output. The client controls WSL sessions; this is not native Windows tab control.

## API and local MCP

Use `POST /operations` with `operation` and `arguments`. The generated local
controller contract lists exact operation names, argument schemas and MCP names.
Set `Accept: application/x-ndjson` for incremental output frames; otherwise calls
return structured JSON and durable handles/cursors. API/MCP observation calls
are bounded; continue by cursor to retrieve later output without resubmission.

For a local MCP client, use the command `codex-wake control mcp`. It forwards to
that server and reads the private connection receipt itself. There is no token
to paste into MCP configuration. HTTP MCP is also available at `/mcp` for local
clients that read the private receipt through their own protected input channel.
The connection bootstrap command is pipe-only; do not publish its contents.

## Health, slash actions and voluntary limits

```sh
codex-wake control remote health thread:UUID
codex-wake control remote slash list thread:UUID
codex-wake control remote slash run thread:UUID /rename --idempotency-key rename-1
codex-wake control remote slash respond INTERACTION_ID 'New title' --idempotency-key rename-response-1
codex-wake self-limits show thread:UUID
codex-wake self-limits set thread:UUID --token-limit 20000 --time-limit-seconds 600
```

Health requires a fresh exact controlling-TUI loop acknowledgment; a reachable
daemon is insufficient. Unsupported, unavailable and ambiguous observations stay
explicit. `/status` and `/rename` have qualified native mappings. Bare `/rename`
returns a durable controller-owned interaction, not a claim to open a native popup.
Unsupported native pickers and unqualified asynchronous commands are rejected
before model submission. Commands are never inserted as ordinary prompt text.

Voluntary limits bind to the owned session automatically, inspect lifetime usage,
start enforcement and report actual engagement. They can tighten an allowance,
but cannot raise inherited caps or disable external enforcement. Ordinary
self-service does not require hand-written policy; an existing explicit host
policy remains authoritative when selected.

## Grok ACP sessions

Codex remains the default harness. Use `--harness grok` and, when needed,
`--profile NAME` for an owned headless Grok ACP session. Public `grok stdio-host`
creates the private profile, and `control create --harness grok` creates a session
without hand-written target or grant JSON. After an owned host restart,
`control load grok:SESSION_ID --harness grok --profile NAME` explicitly loads a
persisted conversation without creating another session. See [Grok workflow](local-grok-control.md)
for the exact bootstrap, loaded-session discovery, command interactions and native
capability limits. Retained operation handles select their original owner; result
retrieval does not change harness or require a fresh profile.
