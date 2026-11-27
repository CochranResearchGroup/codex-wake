# Pilot the private Bastion Wake network

Use this procedure for the #789 pilot with one dedicated conversation on
Bastion and one on Cooper. Use the same reviewed wheel on both owners.
The isolated qualification establishes rollout readiness. Persistent host
installation, ingress changes, dedicated conversation effects, and a
controlled Bastion reboot need an approved live rollout window.

## Before the rollout

Record the wheel SHA-256, both installed paths, the private HTTPS origin,
the native PostgreSQL service and database names, and the exact execution
scope for each conversation. Record the selected Cooper owner as normal
Windows, elevated Windows, or WSL. Use a binding that can verify its own
account, original conversation, and native receipt.

Confirm that both owners have qualified time, the existing local Wake
workers are healthy, and the test will use separate Wake roots. Record
current unrelated services before the maintenance window. Check with the
operator before rebooting Bastion if other workloads need coordinated
shutdown and restart.

Use the repo's Cooper service ingress procedure when allocating or changing
the private HTTPS route. The applied endpoint must forward the exact HTTPS
host to the connector's loopback HTTP listener. Restrict ingress to the
approved owner and peers. Use Bastion's identity-provider realm for the
Bastion-hosted connector. Confirm anonymous OAuth metadata and denied
anonymous Message and MCP operations with separate clients.

## Install and configure the owners

1. Install the reviewed wheel with its `mcp` and `postgres` extras into
   separate owner-controlled environments. Verify the version and hashes.
   Keep the local and hub databases distinct. Bastion uses native
   PostgreSQL with a boot-enabled service, dedicated roles, and private
   connection configuration. Use the OS service provisioning approved for
   that host.
2. Configure the Bastion connector with the reviewed HTTPS issuer, its
   loopback port, authorized identity-provider verifier, exact OAuth
   callback allowlist, and private hub DSN file. Grant only the selected
   peer IDs and conversation IDs in connector targets. The existing
   connector unit example runs the supported `connectors serve` command.
3. Enroll both exact peer IDs under the hub DSN and separately generated
   credentials. Give only that peer's credential to its owner. Configure
   each spoke worker with its own private PostgreSQL DSN, journal root,
   directory revision, and exact adapter. The Bastion owner also runs a
   spoke against the same hub API.
4. Pin management separately to local controller credentials and exact
   operation bindings. History and reversible tab management use the
   original owning controller. Windows-local psmux and WSL tmux must
   stay under their respective original owners.
5. Enable the hub and owner workers to start without a desktop login.
   Start only the pilot roots. Use the installed hub, speak the public
   endpoints, then compare the individual owner logs and PostgreSQL
   records. Verify with an approved OAuth client attached to the pilot.

See the connector example, [network message configuration](0268-network-messages.md),
and [live management configuration](../evidence/plan0268/788-live-management.md).
The connector example is at `docs/deployment/codex-wake-connector.service.example`.

For a Linux or WSL spoke whose user manager starts without a login, use a
dedicated service under that owner. Substitute the reviewed absolute paths.

```ini
[Unit]
Description=Pilot Wake network recipient owner

[Service]
Type=simple
ExecStart=RELEASE_PREFIX/bin/codex-wake wake-network-spoke --config PRIVATE_SPOKE_CONFIG run
UMask=0077
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
```

A management worker can use a oneshot service with
`RELEASE_PREFIX/bin/python -m codex_wake.wake_network_management --config PRIVATE_MANAGEMENT_CONFIG`.
A user timer with `OnBootSec=5s`, `OnUnitInactiveSec=2s`, and an explicit
`Unit` can schedule successive polls. Keep management and message units
separate so that an offline live operation never becomes a retained
Message. When the Cooper owner is native Windows, run the supported
commands in the approved native startup mechanism for that account and
elevation. Verify the selected mechanism before boot acceptance.

## Bind the Linux recipient

For the Bastion pilot, start the native stock Codex app server under the
approved owner and persistent Codex home. Use an explicit app socket in
an owner-private directory. Choose a dedicated saved background
conversation. The owner adapter pins the executable, profile and account,
checks the app-server process on the Unix socket, and resumes the exact
saved conversation after a restart. It checks the original UTC window
before submitting the background turn.

Write an owner-private request with `peer_id`, exact `thread`, `cwd`,
`home`, physical versioned `codex` executable path, `app_socket`, and
`tmux_socket`. Both socket paths are explicit and their directories must
belong to the owner. The terminal socket establishes whether a live pane
owns the conversation. An absent socket in a private directory permits
the saved background route. An attached or busy conversation holds the
message until the dedicated background route is available.

```sh
RELEASE_PREFIX/bin/python -m codex_wake.wake_network_native \
  --binding PRIVATE_BINDING enroll --request PRIVATE_REQUEST
```

Use this owner adapter argv for the exact Linux conversation in the spoke
configuration.

```json
[
  "/path/to/release/bin/python",
  "-m",
  "codex_wake.wake_network_native",
  "--binding",
  "/private/wake/native-binding.json",
  "deliver"
]
```

For a Cooper Windows psmux pilot, use the existing Windows recipient binding
under that execution scope. A Cooper WSL owner can use the Linux adapter
with its own approved profile, socket directory, journal and worker units.
The gateway separately authorizes terminal operations through the owning
controller.

## Execute the live acceptance

| Step | Evidence to retain |
| --- | --- |
| Discover both conversations from the authorized client | Exact peer and conversation IDs, approved scopes, availability, and denial for a grant that targets a different conversation. |
| Send and reply in each direction | Original IDs, due/expiry timestamps, `in_reply_to` links, and one exact recipient receipt and completed turn per Message. Confirm no sender attempt. |
| Stop only the Cooper pilot spoke | Keep a due Message pending with its original ID. Verify a live management request reports offline and produces zero owner effects. Run one independent Cooper local wake during a hub outage, without switching its local database or adapter. |
| Resume the same Cooper owner | Verify one retained delivery and one expired case with zero delivery attempts. Issue a fresh management operation after reconnect. |
| Reboot Bastion with operator assistance | Stage one wake with zero attempts. Record old and new boot IDs, PostgreSQL and owner service start times, one confirmed retained delivery, and the first login time. Check that boot services and the original conversation were available before a login. |
| Read former history through the gateway | Read the pilot conversation's last known working directory and most recent activity through the authorized owner. Verify a history-only grant cannot perform terminal mutations. |
| Apply and reverse one pilot tab rename | Use two fresh operation IDs and exact window observations. Verify the owner and native window ID before and after both changes. |

Limit probes to the two approved pilot conversations. A missing
effect receipt requires owner reconciliation under the original ID. Keep
the original expiry when assessing a held record.

## Verify a backup and recover

Take a private custom-format PostgreSQL dump of the pilot hub before the
selected delivery. Complete the delivery and record the issuing owner's
receipt. For the restore exercise, stop admission and peer polling, then
restore the dump into a distinct empty database. Use reviewed local
PostgreSQL service entries or equivalent private connection configuration.

```sh
pg_dump --format=custom --file=PRIVATE_PILOT_BACKUP --dbname=service=wake_hub_pilot
pg_restore --exit-on-error --dbname=service=wake_hub_restore PRIVATE_PILOT_BACKUP
```

Run the offline reconciliation with the original owner journals and
optional owner DSNs. Follow the exact restore config and roster procedure.
Verify the restored hub reports the same submitted receipt without sending
the payload again. Keep a record without positive owner evidence held.
Keep the active hub database separate from the restore destination.
[Hub restore and reconciliation procedure](../evidence/plan0268/787-hub-restore.md)

If the pilot must stop, quiesce admission and the dedicated worker units,
retain the private hub and owner journals and their original IDs, and
disable only the allocated private ingress. Confirm the pre-existing local
Wake configuration and unrelated workloads by reading their startup and
status records. Keep production rollout open until the independent boot,
disconnect, bidirectional, restore, and gateway receipts are recorded.

## Native time and managed private ingress

Native Linux owners can use the synchronized kernel UTC interval for Wake
network operations. They hold when synchronization is lost. WSL keeps
using StableTime. An explicit StableTime configuration remains authoritative
and a failed configured service holds the operation. Native UTC carries no
StableTime elapsed-counter claim.

The installed Fleet Receipts 0.1.0 catalog handles Tailscale sign-in and
prerequisite inspection. It does not expose Tailscale Serve maintenance.
Bastion protected Fleet enrollment is tracked in
https://github.com/ecochran76/fleet-receipts/issues/203. The Serve
maintenance follow-up needs a broker operation that inspects, plans, applies,
and reads back one approved private route, preserving unrelated Serve
entries and keeping public Funnel disabled. Capture the exact host, endpoint,
upstream, before/after state, and route-specific rollback receipt. Do not
use unrestricted SSH or administrator execution as the managed maintenance
implementation.

The operator applied the dedicated Tailnet-only Serve route. From Cooper,
the route passed certificate verification and served OAuth discovery for the
exact issuer and resource. Anonymous MCP and peer requests returned 401.
Fleet Receipts tracks the managed route operation in
https://github.com/ecochran76/fleet-receipts/issues/219.

The installed persistent spokes exchanged an original message and linked reply
in each direction. Each incoming pilot delivery produced one native Codex
input and completion on the allocated receiving thread. During a controlled
Cooper spoke stop, the hub held a new message and Cooper's local wake completed
independently. Restarting the same spoke delivered the held message exactly
once with its original expiry.

Native Bastion web OAuth initially rejected authorization because it required
a StableTime elapsed counter. Commit `5426e547` uses bounded native UTC for
external OAuth on synchronized native Linux without a StableTime configuration.
An explicitly configured StableTime service and WSL keep their existing time
paths. Ten focused OAuth tests passed. Live consent, gateway management, and
reboot evidence remain open at this checkpoint.
