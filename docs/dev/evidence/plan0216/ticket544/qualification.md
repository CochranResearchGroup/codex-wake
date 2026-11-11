# Ticket 544 retained observer and lifecycle

Base branch: feat/observer-lifecycle-544; dependency ticket545 cherry-picked as
91c1d1ec (original5407b960). Root should cherry-pick this ticket's final commit only.

One persistent TabObserver now owns metadata feeds and a retained ControllerTabs
cache inside the existing single TabMonitor service. The default tick is1second;
metadata inventory fallback is5seconds. Native status deltas project already
qualified title/CWD/client-birth bindings directly without an inventory pass.
Passive-source continuity keeps quiet active conversations observed. Source loss
retains cached resources/details while making dynamic activity unknown and
source_available=False. Unsupported terminal backends retain isolated bounded
probes; unavailable passive native feeds retain bounded metadata polling details.
They are not misrepresented as continuous passive activity evidence.

Tmux/session and native source loops rotate fairly, as does fallback workspace
selection. Sources, frames, workspaces and batches are bounded. Configuration file
identity changes close owned feeds and reconstruct the retained owner. Epoch or
sequence gaps cannot apply deltas without a baseline. Stop closes owned feed
connections/clients; existing tmux servers and agent processes remain untouched.

Native baseline now includes the existing attachment matcher's required thread
name as bounded metadata. A new refresh_metadata operation rebaselines loaded
metadata over the same allowlisted connection every30seconds; unknown-thread
status requests a coalesced refresh limited to once per second. No resume,
subscription, prompt, approval response, daemon start or provider method exists.
New conversation discovery has separate latency from updates to known bindings.

Monitor-start accepts independent activity/health/errors booleans and intervals,
with --no-activity/--no-health/--no-errors CLI switches generated from the portable
schema. Health interval minimum60seconds, error interval minimum5seconds. Monitor
status is readable by default; --json preserves structured output. Generated
command reference was regenerated. Native/API/OAuth schemas use the same fields.
Status exposes source states/epochs, costs, backlog, tier settings, scheduler
counts, fallback count and unknown reasons.

## Evidence

- Public monitor-start regression first failed with unsupported tier arguments
before controls were implemented (behavior red).
- Focused selected tests (observer, monitor, native feed, portable contract,
format monitor and format autostart):21tests pass Python3.11.15 and3.12.13;
11.65/11.94seconds. Receipts python311.json/python312.json record exact selection.
The deliberately rejected CLI arguments printed by contract tests are expected.
- Real private tmux plus Unix-WebSocket fixture proves native binding, idle to
running projection without a new inventory pass, disconnect availability loss,
retained control-client PID and owned cleanup. System process-probe boundary
supplies synthetic executable metadata; no provider or live Codex session used.
- Native feed fixture additionally covers same-connection metadata rebaseline
ordering/epoch and bounded name metadata. Existing native burst fixture remains
within its two-second target; this is not installed public projection acceptance.
- Actual source CLI status printed readable inactive monitor output; --json
parsed to the same monitor status in a private empty controller root.
- Ruff F821/F822/F823 on changed Python files, generated reference --check and
whitespace checks passed. Final focused changed-behavior checks were rerun after
availability-status and server-metadata retention tightening.

This is focused adapter/lifecycle qualification only. Ticket547 owns the exact
installed package, real transport surfaces,100tab60second resource windows and
existing-host read-only measurements. No production monitor was enabled, no
formatting/policy/routing rule was created and no service deployment occurred.
Memory disposition: forbidden; no explicit memory-write authorization.
