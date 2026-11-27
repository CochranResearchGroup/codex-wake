# Issue 789 rollout readiness

The isolated run used a private TLS listener, independent PostgreSQL
databases for the hub and each spoke, and separate stock Codex homes and
Unix sockets. It used a loopback inference fixture and injected test time.
The operator-facing pilot procedure is in the
[private network rollout guide](../../plans/0268-network-rollout.md).

## Installed hub and spokes

The wheel built from `c77a981c` had SHA-256
`83ec23aa81e77e3b3537fd11dec5cfac8d2c36ee7373b40acb45f75122f7f9d8`.
The directory, message custody, outage and revocation, older PostgreSQL
dump reconciliation, and live management suite passed from that installed
wheel. The management run used a dedicated real tmux server. Peer custody
exercised real TLS. The management regression exercised public OAuth HTTP
and MCP through ASGI.

A separate isolated run used the installed spoke CLI to submit four
Messages through the TLS hub to two actual stock Codex 0.172.0 app servers.
Both directions retained the original request and linked reply. Each
receiver confirmed one local attempt, one native receipt, and one
completed turn in its original conversation. A separate fixture OAuth
consent typo interrupted combined discovery after those receipts passed.
OAuth discovery and receipt readback passed in the installed network suite.

## Linux native recipient restart

The native-adapter wheel had SHA-256
`77c8e5aab22726d8b702e447b6f581830663e9ffd3c43a2b192a7d70b7b6d791`.
The installed adapter enrolled one saved stock Codex conversation and
reused the same binding with a new app-server process. It held a message
for the wrong peer before loading the saved conversation. It then recovered
thread `01a21e96-e6a5-7373-b30c-c0472f3aa7cc` and accepted Message
`b908283c-5543-46d3-8eb8-e800c8fd6bb1` with its original expiry.
The stock transcript contained one matching input and one completion under
native turn `01a21e98-4eca-79a3-98d7-a6548f8e65cb`. The private binding
remained byte-identical across process generations.

The initial isolated session enrollment returned a held status before any
delivery. A second isolated attempt enrolled the already saved
conversation and completed the restart case above.

## Live authority

Read-only preflight confirmed that Bastion has a lingering user manager,
its PostgreSQL system unit is absent, and its Minecraft port has an
active listener. Cooper's normal Windows SSH route has native psmux and
Python. Ask the operator to approve persistent rollout, the private HTTPS
origin, the exact Cooper execution scope, and the Bastion maintenance
window. Boot, disconnect, restore, and gateway acceptance must be repeated
under those live bindings. The isolated run made no production changes.
