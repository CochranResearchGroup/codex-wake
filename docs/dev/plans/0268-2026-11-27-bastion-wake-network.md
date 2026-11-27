# Plan 0268 | Bastion HTTPS Wake network

State: OPEN
Owner: primary integration agent
Spec: https://github.com/CochranResearchGroup/codex-wake/issues/783
Work items: #784 through #790

## Current State

The [execution ledger](0268-execution.json) records the tracked ticket graph
and verified changes. The integration branch combines current main with the
qualified Plan 0267 branch so the network reuses durable message custody.

## Scope and acceptance

Build the private Bastion HTTPS hub and its outbound Cooper spoke. Use the
public HTTPS protocol and OAuth API/MCP to verify discovery, custody, replies,
restore, and live spoke controls. One dedicated conversation on each host
qualifies the production pilot after separate rollout approval. Full catalog
parity follows its own ticket. Dashboard work, public access and central
transcript replication are outside this plan.

## Peer enrollment and directory

Set `wake_network` in the hub OAuth connector policy with a private absolute
`dsn_file` and `stale_seconds` (1 through 3600). The PostgreSQL database is
controlled by the hub. Enroll a peer using the installed Python environment
and `python -m codex_wake.wake_network --dsn-file PATH --peer-id ID
--credential-file PATH`. Use an independently generated high-entropy
credential in an owner-private file. The command also replaces a credential
for the same identity without changing its accepted directory.

Through private HTTPS, the peer sends `PUT /network/v1/peers/{peer_id}/directory`
with its credential and a monotonic directory revision. An identical revision
can refresh the current directory. To rename or remove a recipient, publish a
new revision while retaining its stable conversation ID for a rename. The
payload has `revision` and `recipients` containing `conversation_id` and
`name`. Clients separately grant OAuth `observe` for authorized targets. An
explicit `peer_id` in the target grants that peer, and a `conversation_id`
can narrow it further. An existing local-only target grants no network access. Query with OAuth
`POST /network/v1/recipients` or MCP `wake_network_recipients`. Optional
filters are `peer_id`, `conversation_id`, and `name`.
