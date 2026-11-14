# Persistent wakes: exact live restoration

`reopen_live` reuses a fresh, uniquely qualified exact-conversation attachment.
When no attachment exists, the existing `AgentResume` owner performs restoration:
its profile revalidation, common permissions, managed identity, durable intent and
uncertain-launch reconciliation remain authoritative. No fresh conversation or
background fallback is substituted. Opening a conversation with an active
background check waits rather than launching another client.

The local operator configures `WAKE_ROOT/wake-live-restore.json` as an owned private
file (0600), selecting existing private resume profiles and enrolled identities:

```json
{"version":1,"bindings":{"EXACT_THREAD_UUID":{"profiles":"/absolute/private/resume-profiles.json","managed_agent_id":"agent_EXACT_ID","profile":"last-confirmed"}}}
```

For recovery when the entire Byobu/tmux server is gone, the profile must include
its absolute `tmux_socket`, and the existing private `controller-tabs.json` must
already declare that exact socket as a tmux/Byobu workspace. The original client
generation must be confirmed gone, the pinned socket absent, native inventory
available, and no loaded/ambiguous owner present. The shared mode-presence observer
checks this evidence; incomplete connectivity alone cannot authorize restoration.
The existing `TerminalSessions` owner then ensures the declared session container
before `AgentResume` opens the exact conversation. Both operations retain durable
crash fences; an uncertain result never launches a replacement automatically.

The profile file is the existing `agents resume` configuration. It identifies the
harness, working directory, app-server endpoint, destination tmux/Byobu session,
timeout and optional Codex home. Update the binding/profile only from verified
runtime settings; neither the registration prompt nor model arguments may choose
this private host configuration. The selected configuration is read again for each
restoration and immediately before effects. The managed conversation, profile and
current native metadata must agree on identity and directory. A missing directory,
unsupported harness, unconfigured destination server, missing enrollment or
unqualified workspace move holds restoration; these are not reasons to substitute
another profile, directory, session or conversation.

The host mapping grants no permission. Dispatch supplies only its admitted frozen
permission context and original occurrence/deadline to the internal adapter.
`wake.new_tab` and the existing resume permission remain checked under current
common policy; they are rechecked before terminal commands. Existing task and
resource ledgers are preserved. An uncertain launch keeps its original durable
intent and is reconciled without another launch.

Source qualification for #613 uses `LiveWakeRestorer.prepare` and the real existing
resume owner, inventory and permission store. The missing-server check also uses
the real terminal-session owner and a temporary isolated tmux socket/container.
Native-reader and Codex-launch effects are replaced at their external boundaries;
no Codex/provider process or production tab is launched. The isolated server is
removed by exact socket after the check. This is not installed-runtime or
live-provider acceptance.
