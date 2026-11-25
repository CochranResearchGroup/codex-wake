# Tab observation

`codex-wake tabs monitor-start` starts the existing single host monitor. It retains
one metadata-only tmux control client per selected session and passive native
Codex connections per endpoint. Byobu uses stock tmux; no patched Byobu is needed.
The default tick is one second. tmux metadata uses ordinary control notifications
plus periodic fixed metadata snapshots on that retained connection (one-second
fallback cadence, with ordinary event-triggered updates). Native
`refresh-client -B` wildcard subscriptions are not used: tmux3.4 can crash the
whole server if their timer encounters a closing client without a session.
Status changes use cached attachment bindings;
ordinary ticks do not spawn a Python inventory probe for every workspace.

```sh
codex-wake tabs monitor-status
codex-wake tabs monitor-status --json
codex-wake tabs monitor-stop
codex-wake tabs monitor-start --no-health --no-errors
codex-wake tabs monitor-stop
codex-wake tabs monitor-start --health --errors --health-interval 120 --error-interval 10
```

Activity, exact responsiveness and redacted visible-error checks are independent.
Use `--no-activity`, `--no-health` or `--no-errors` to disable a tier; omitted flags
retain saved settings. Stop before changing a running monitor's settings. These
same boolean and interval fields are available through the monitor-start API and
native/OAuth MCP schema. JSON remains the structured interchange format. Status
shows sources, epochs, fallback/unknown reasons, backlog, tier settings and costs.

A running turn is activity evidence; it does not prove that the TUI is responsive.
A quiet, connected source can retain its running state without inventing a stale
label. Source loss retains inspection details and marks dynamic evidence
unavailable. A reconnect or metadata gap requires a new baseline before changes
can establish state. Native status and saved metadata are never terminal input
ownership, transcript subscriptions, approval responses or model requests.

Loaded native metadata is rebaselined over the same connection at least every
30 seconds. An unknown thread status requests a coalesced refresh, rate limited
to once per second. New conversation discovery depends on metadata availability;
the two-second event target applies to an already qualified attachment. Unsupported
native feeds use bounded metadata polling for details; passive availability is
reported separately. Unsupported terminal backends retain bounded existing probes
and are not advertised as native event sources.

Fallback inventory normally reconciles every five seconds for active, changed,
unknown or unavailable panes. A fully bound native idle workspace with connected
presentation and native sources can reconcile every 30 seconds. Native events
still update cached activity on the one-second owner tick. Status reports the
selected interval, inventory age and reason; a slower inventory is not a health
claim. Every reused process tree is checked for live births and changed children.

Visible-error reads use bounded batches of only due panes. Failed reads remain
unknown and retain prior redacted positive evidence; they do not clear errors.
Raw screen text is transient and never enters the persisted observation snapshot.
Retained JSON snapshots use a faster decoder with a standard-library fallback
for legacy values. Stored values, canonical digests and strict finite-number
serialization stay unchanged.
The retained owner also lazily keeps one read-only formatting client per tmux
workspace. Its managed-option reads avoid repeated process launches; writes and
pane capture keep their existing path. Reader diagnostics appear separately in
`observer.formatting_reads`, never as activity evidence. Readers preserve session
environment and close on owner configuration replacement or stop.
Formatting consumes producer revisions, checks changed windows before writing and
uses a 20-second shared lease for dynamic cues. Unchanged sources renew every
10 seconds; failed renewals retry on the next monitor tick. Source changes still
project immediately. Loss of the lease removes uncertain cues while keeping the
selected palette and stable labels.

Background health checks run no faster than once per 60 seconds per exact client
birth/build; errors use their separate minimum five-second cadence when eligible.
Explicit monitor refresh remains a bounded one-shot operation. Observer sources,
cache and owned clients are closed with the monitor; no agent or tmux server is
terminated. Configuration identity changes rebuild the retained owner and sources.

The monitor supplies observations to formatting, routing and policy owners. A
monitor start alone does not enable formatting or create a routing rule. Formatting
rollback/reenable remain documented in [tab formatting](tab-formatting.md).

Qualification is recorded per exact source package. Private protocol tests do not
prove live native broadcast support, installed transport parity or resource gates.

## Inspect a destroyed tab

Search for the exact tab name through history. A search result lists each
retained binding separately when the name was reused. Use the owning account,
workspace and last observed time to select the intended binding.

```sh
codex-wake --wake-root ROOT history search --former-tab "amazon ads" --owner work --json
```

Each binding shows the last observed pane directory and observation time.
`last_known_presentation` records the last qualified observation of the tab.
An unavailable workspace preserves the previous evidence. A guest wall
timestamp is for display, as indicated by `observed_at_time_basis`.
Only exact Codex bindings observed with a verified pane and owning account
generation are retained. If the saved conversation becomes unavailable, the
binding and its last observed directory remain available. The monitor keeps
former bindings by default. To cap retained metadata, set
`CODEX_WAKE_FORMER_TAB_RETENTION_LIMIT` to an integer from 0 to 1000000 in the
monitor's environment before starting it. On qualified observations, it keeps
that many of the most recently observed absent bindings per host and
environment. Live bindings stay eligible for lookup. This setting does not
delete saved conversations.

For API and MCP, pass `former_tab` to `history.search` or
`wake_controller_history_search`. Send the returned `history_locator` to the
existing history read operation to retrieve saved activity. Search uses
account-level history observation authority, and reading content uses the
existing exact history read authority. Both operations leave a destroyed tab
closed. The local operator can remove one binding by its exact ID.

```sh
codex-wake --wake-root ROOT history forget-tab BINDING --bus-root BUS --operator-capability FILE --json
```
