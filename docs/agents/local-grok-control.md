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

Creation retains two separate receipts: native `grok.create`, then a stable
`grok.load` activation derived from the original creation ID. Both IDs are bound
before activation I/O. The public response includes `readiness` with `ready`,
`state`, `creation_operation_id`, `load_operation_id`, and `reason`. Successful
native creation stays completed even if activation fails: the workflow returns
`created_not_ready` and preserves the original operation. Retrieve those IDs or
retry the same creation key; never manufacture a replacement key. An uncertain
load is reconciled only by native loaded-session listing, without replaying load.
Only `readiness.ready=true` means the created session is usable.
`control result CREATION_ID` exposes cached readiness without activation effects.
Successful readiness is retained and needs no new profile lookup on retry.

Use `control list --harness grok --profile disposable` to discover sessions loaded
in that exact owner. Select `grok:SESSION_ID`; the selector pins provider, native
agent instance, process generation, executable build, account home and profile.
After an owner restart, load an explicit persisted conversation with
`control load grok:SESSION_ID --harness grok --profile NAME --idempotency-key KEY`.
This uses the existing native `grok.load` owner with automatic same-user custody;
it does not create a session, submit a prompt or require a manual grant file.
The first request pins that fresh profile/process generation and explicit session.
Repeating its key returns the original completed or uncertain receipt, without
replaying load or rebinding a replacement process. A completed receipt remains
readable after the original profile disappears. Use a fresh key only for a
separately authorized new load intent, never to retry an unknown outcome.

Native session listing is window/owner scoped. It is not complete persisted
history discovery. A different owner or restarted process requires fresh identity.

Use the shared `control prompt`, `result`, `output`, `cancel`, `health`, and
`slash` verbs with the same harness/profile selection. Original operation IDs
route through retained custody without a new profile lookup. The four output
modes are `stream`, `transcript`, `final`, and `silent`. Live stream/transcript
chunks come only from correlated native ACP `session/update` notifications;
reasoning and user-message content are excluded. Native
`available_commands_update` notifications remain ordered transcript metadata with
native provenance and never become assistant stream text. Unknown native kinds
make retention explicitly partial. Historical partial receipts are not rewritten
when a later collector learns a known metadata kind. Retained cursors resume bounded
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


Oversized known metadata is losslessly represented by ordered
`grok/session/metadata_fragment` events within the existing 16 KiB per-event
limit. Group by `group_id`, order zero-based `part_index`, require `part_count`
parts, base64-decode each `data` field, concatenate raw bytes, verify `total_bytes`
and `sha256`, then decode UTF-8 JSON. Each raw piece is at most 8 KiB. The encoding
is canonical JSON with Unicode preserved; fragments may split a Unicode byte
sequence, so decode text only after concatenation. The reconstructed object is
the original native metadata event.

`occurrence_first_sequence` and the operation ID identify each occurrence;
identical repeated native events have distinct groups and the same content hash.
Normal cursors preserve fragment ordering and allow resuming a group across
pages. Metadata fragments never become assistant stream text. The 2 MiB total
and 2048-event retention limits remain unchanged: exhausted retention, missing
parts, or unknown native kinds remain explicitly partial. Historical partial
receipts are retained unchanged.
