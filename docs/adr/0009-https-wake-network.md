# Connect Wake peers over HTTPS

Use private HTTPS for the first production connection between Cooper and
Bastion. Keep the durable handoff contract already exercised over SSH.
A forwarded message keeps its identity, eligibility, expiry, and reply
link, and the receiving owner records the delivery receipt.

Use a hub-and-spoke model for the Wake network. The hub will present one
client-facing API and MCP endpoint and eventually host a dashboard. Peer
handoff and client access serve different callers and need distinct contracts.
Bastion is the first hub and also owns its local conversations. Cooper owns
its Windows and WSL conversations. The hub owns peer enrollment, recipient
lookup, client access, and durable custody of messages it accepts. The
receiving peer owns execution and its delivery receipt.

An offline peer's messages remain held at the hub until delivery or original
expiry. During a hub outage, peers continue local wakes and messages, and
network submissions wait. The first endpoint is private to Cooper and
approved operators. Peer handoff and client access use separate credentials.

Cooper initiates HTTPS connections to publish its recipient directory,
submit outbound messages, and pull work. Route by stable peer and
conversation IDs. Names are search terms, and ambiguous matches require
explicit selection.

The initial rollout covers one dedicated conversation on each host. Verify
messages, replies, and disconnect recovery in both directions through
Bastion. Schedule the dashboard after the initial rollout.

An operator enrolls each peer with a revocable credential bound to its
peer ID. Cooper can publish and pull only for its registered conversations.
Clients use separate OAuth scopes. The directory retains the last verified
identity of an offline recipient and marks it offline or stale. Exact-ID
sends may wait until the original expiry.

The hub reports acceptance after durable storage. The receiving peer
records custody before invoking the harness. Clients can distinguish held,
delivered, expired, and uncertain messages. Retries retain the original
message ID. Uncertain effects remain held for reconciliation.

Rollout acceptance requires a Bastion reboot, a Cooper disconnect, and
a reply in each direction. Verify that local wakes continue during a hub
outage and that reconnect preserves message IDs and receipts without
duplicate delivery.

The central API and MCP must let authorized clients manage the full set of
operations a spoke exposes. Spokes remain authoritative for their local
state and effects. Full management through the hub does not require copying
conversation history, terminal contents, or working directories into the hub.
Bastion provides one management gateway. It resolves the target and
forwards the request over the spoke-initiated connection. The spoke
enforces its local permissions, performs the operation, and returns
the result. A private tunnel may carry the traffic behind the gateway.

When a spoke is offline, the hub holds durable messages until their
original expiry. Live management operations return `offline` and
require a fresh request. The first rollout verifies messaging, history
lookup, and one reversible terminal action. The full spoke operation
catalog follows before the dashboard.

Revoking a peer blocks further pulls. Undelivered messages remain held for
operator review or original expiry. Re-enrollment under the same peer ID
can resume delivery under the original message IDs.

Bastion stores hub state in persistent PostgreSQL. The rollout includes a
backup and restore test. After restoring a backup that predates a delivery,
reconcile the message against the owning spoke's durable receipt before
retrying. Hold the message if the spoke cannot establish the outcome.
