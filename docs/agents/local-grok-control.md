# Grok local session control

The supported Grok mode is a headless ACP session in one explicitly owned native
stdio host. It does not control arbitrary open Grok TUIs. Use the same local
controller CLI/API/MCP operations with `harness=grok` and an explicit profile when
more than one profile exists. The default harness remains Codex.

Start a foreground owner in a separate terminal, with an existing native account
home and an empty or explicitly chosen workspace:

```sh
codex-wake --wake-root "$WAKE_ROOT" grok stdio-host \
  --profile disposable --account local --binary "$GROK_BINARY" \
  --home "$HOME" --cwd "$WORKSPACE" --ready-file "$READY_FILE"
```

The owner writes its private profile automatically. Provider authentication stays
inside Grok's existing native store; Wake does not copy credentials or perform a
new login. Keep this foreground host running while controlling its sessions.
`control create --harness grok --profile disposable --idempotency-key KEY`
creates a session through the existing retained Grok owner, without manually
writing target JSON or grants. Repeating the same key returns the original
creation. A different profile cannot replace its target.

Use `control list --harness grok --profile disposable` to discover sessions loaded
in that exact owner. Select `grok:SESSION_ID`; the selector pins provider, native
agent instance, process generation, executable build, account home and profile.
Native session listing is window/owner scoped. It is not complete persisted
history discovery. A different owner or restarted process requires fresh identity.

Use the shared `control prompt`, `result`, `output`, `cancel`, `health`, and
`slash` verbs with the same harness/profile selection. Original operation IDs
route through retained custody without a new profile lookup. The four output
modes are `stream`, `transcript`, `final`, and `silent`. Live stream/transcript
chunks come only from correlated native ACP `session/update` notifications;
reasoning and user-message content are excluded. Retained cursors resume bounded
history. A detached collector owns the original request when a caller disconnects.
Collector loss means unknown work, not permission to submit it again.

The qualified slash adapters are `/status` (`session/load` metadata) and `/model`
(`session/set_model` followed by exact native model readback). A bare `/model`
returns a durable choice handle: `interaction_id` equals its parent `operation_id`.
Submit a negotiated model ID through `slash respond`, or cancel before responding
for no native effect. Presentation is `controller_interaction`, with
`native_popup=false`; no terminal typing or model prompt substitutes for a command.
The response key is immutable. An uncertain model response is reconciled by exact
readback without replay. Other advertised native commands remain unsupported by
this adapter until separately qualified.

Exact TUI-loop health, exact-turn cancellation custody and exact resource metering
are unsupported. Health never grants recovery. A cancellation request cannot stop
an unrelated later turn. Existing retained final answers remain retrievable, and
unknown outcomes remain unknown. Native metadata, protocol fixtures and genuine
provider acceptance are separate evidence boundaries.
