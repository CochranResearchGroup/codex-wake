# Issue 788 live management qualification

The hub exposes POST endpoints under `/network/v1/management/` for
`history/search`, `history/read` and `tabs/rename`, with matching
`wake_network_history_search`, `wake_network_history_read` and
`wake_network_tabs_rename` MCP tools. Each requires the exact hub grant
target with host, environment, peer ID and conversation ID. The peer
must be enrolled and have published the conversation in its directory.
Search requires `history.observe`. Reading saved records adds
`content.observe`. Rename requires `control`.

A spoke can poll with
`python -m codex_wake.wake_network_management --config /private/path.json`.
The operator-owned file contains the HTTPS `hub` origin, `peer_id`,
`wake_root`, `peer_token_file`, `controller_token_file` and `bindings`.
The binding keys are stable conversation IDs. Values map the full
network action name to local controller arguments. For history search
pin the former name and permitted account list. For history read pin the
account and native thread. For rename pin the workspace, current expected
target and exact window ID. The peer rechecks the local controller
grant and the live request deadline when its controller authorizes
the effect. A reverse rename uses a new request and a fresh observation
of the window. The spoke command is a single poll for a supervising
owner to invoke. Keep local controller credential renewals under that
owner's existing OAuth procedure.

Live slots exist only in the hub process, while the authorized caller
and a peer poll can rendezvous. PostgreSQL continues to own enrollment
and the directory. A missing poll yields `offline` and creates no
work. Claims and start acknowledgments are one-use. A spoke must receive a
start acknowledgment before entering its local controller. The hub
withholds start after caller withdrawal, while a missing completion
after start yields `uncertain` and the original operation ID for owner
inspection. Timed OS waits schedule checks, and trusted time determines
expiry. An expired request cannot start or accept a completion. A hub restart loses the
live slots. No restore process replays them.

The integration test exercises OAuth code and PKCE, public HTTP routes
and Streamable HTTP MCP via ASGI, against isolated PostgreSQL and a
temporary, real tmux socket. It checks an absent former tab's last
observed working directory and reads the actual saved synthetic record
through the local history controller. Control and content scopes are
separate, and a host-only grant receives no remote operation authority.
The first rename is applied in tmux with its completion withheld.
The client records uncertainty. A fresh request restores the original
name and reports success. The expired first receipt cannot be reused.
The fixture used a local clock injection for deterministic time
qualification. No production hub, certificate, grant or pane was used.

```sh
# Set CODEX_WAKE_TEST_NETWORK_DSN to an isolated PostgreSQL connection.
PYTHONPATH=src:tests python -m unittest test_wake_network_management \
  test_wake_network test_external_oauth_connector
```
