# Tab observation

`codex-wake tabs monitor-start` starts the existing single host monitor. It retains
one metadata-only tmux control client per selected session and passive native
Codex connections per endpoint. Byobu uses stock tmux; no patched Byobu is needed.
The default tick is one second. Status changes use cached attachment bindings;
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
