# SSH conversation views

An SSH view gives one registered Windows or WSL conversation a presentation in the other environment. The source owns the local tmux or psmux window. The destination owns the Codex conversation and receives messages through its usual Wake owner.

Use a private source configuration with the installed `codex-wake` command.

```sh
codex-wake ssh-views --config /path/to/source.json inspect
codex-wake ssh-views --config /path/to/source.json recover existing
codex-wake ssh-views --config /path/to/source.json recover resume
codex-wake ssh-views --config /path/to/source.json recover background
```

Use `existing` to reopen the source view for a destination conversation the app server still reports as idle or active. Use `resume` to also allow the destination to open its saved conversation when the receiver configuration authorizes that action. Both use SSH to present Codex directly through the source terminal. `background` leaves the current presentation alone and makes no SSH request. The destination owner's original message receipts still establish delivery.

Prepare the paired configurations using the exact target records from the two registered execution owners. Both files use `version: 1`, a shared `view` identifier, the original `source` and `destination` target records, a local `registry` path, and the destination `conversation` with `namespace`, `thread_id`, and canonical `cwd`.

- The source uses `role: "source"`. Its `terminal` specifies the local multiplexer `executable`, `session`, window `name`, numeric `index`, source `cwd`, and either the tmux `socket` or the psmux `namespace`. Its `receiver_argv` runs the installed destination command through `codex-wake ssh-views --config <destination-path>`. The source uses the registered SSH destination and executable. An optional private `ssh_config` selects an existing SSH configuration.
- The destination uses `role: "destination"`. Its `harness` specifies the absolute Codex executable as `codex`, a running local app-server `endpoint`, the original `codex_home`, and the canonical `cwd`. A loopback WebSocket endpoint that requires a bearer can specify its private `token_file`. Set `allow_saved_resume: true` to permit saved-conversation presentation. The normal Windows receiver requires the registered normal account.

The source reports a hold if the original position contains an unrelated window or the destination cannot confirm the pinned conversation. A source window receipt describes the local presentation. Consult the destination owner for harness execution and delivery receipts.
