# Wake network message custody

Use a private PostgreSQL database on the hub and a separate owner database
and journal for each spoke. The hub stores the original immutable Message.
Only the owning spoke executes it. Its receipt is authoritative for the
effect. A hub acceptance receipt confirms storage under the original ID.

## Client API and MCP

An OAuth grant permits messaging only for its explicit peer and any narrower
conversation. The send operation requires `control`. Status requires
`observe` and the original sender grant. Reply bodies also require
`content.observe`. No transcript is copied to the hub.

| HTTPS POST | MCP | Required arguments |
| --- | --- | --- |
| `/network/v1/messages/send` | `wake_network_send` | `id`, `peer_id`, `conversation_id`, `body`, `expires_at_micros` |
| `/network/v1/messages/status` | `wake_network_message_status` | `id` |

Supply a caller-generated lowercase UUID for `id`. Both
`not_before_micros` and `in_reply_to` are optional. Use absolute UTC
microseconds for eligibility and expiry. Resubmit the original unchanged
request after a lost response. If the original ID names different contents,
the hub returns HTTP 409. Status distinguishes `hub_accepted`,
`owner_admitted`, recipient holds, `submitted`, `uncertain`, `expired`,
and policy bounce. Only a submitted receipt confirms an effect.

## Spoke operation

Peer-authenticated message requests use POST under
`/network/v1/peers/{peer_id}/messages/`. The operations are `send`,
`pull`, `receipt`, and `status`. Directory publication remains a PUT to
`/network/v1/peers/{peer_id}/directory`. An exact peer credential is
required at each exchange.

The spoke reads a private owner configuration file. Create the journal
directory before starting the worker.

```json
{
  "root": "/private/wake/spoke",
  "peer_id": "cooper",
  "origin": "https://wake.example",
  "credential_file": "/private/wake/spoke-token",
  "owner_dsn_file": "/private/wake/local-postgres",
  "directory": "/private/wake/directory.json",
  "bindings": {
    "04317f37-680a-4a9c-b141-3b3175932f49": {
      "namespace": "codex:account",
      "argv": ["/private/wake/bin/qualified-owner-adapter"]
    }
  }
}
```

The optional `ca_file` points to the local certificate authority for the
private endpoint. `directory.json` contains the peer's revision and exact
published recipients. The adapter receives one existing Message JSON frame
over stdin and returns the ordinary pinned owner transport receipt.
The optional binding namespace applies local recipient policy and FIFO to
the same exact recipient used by other Message delivery paths. An absolute
argv list alone uses the stable directory conversation as the local key.

Run the existing installed console with `codex-wake wake-network-spoke
--config CONFIG run`. For a single pass use `tick`. The local `send
--request FILE` command stages the original request along with
`sender_conversation_id`, which must be a locally owned and published
conversation. For replies to a peer, target the original peer and its
source conversation. For replies to an OAuth client, provide the
original `in_reply_to` and set `peer_id` and `conversation_id` to JSON
null. The original client can read the correlated reply through status.
`status ID --inbound` reads local recipient custody. `status ID` reads
outbound custody and linked replies when the hub is available.

An unavailable hub leaves outgoing work in the local journal. A
disconnected or unauthorized pull holds network inbox work while unrelated
local work continues. The spoke records local authority before invoking the
recipient adapter, and records the exact outcome before reporting it. A
dropped receipt response retries only the receipt. An unresolved effect
keeps the original ID fenced.
