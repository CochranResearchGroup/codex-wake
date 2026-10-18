# Token and time limits in the existing dev session

Codex Wake supervises the current native `/goal` without
moving to another tab or agent. Installation, host delegation and a running controller
are required. Host policy version2 lets native callers self-enroll without
per-session UUID grants. Check the installed version and controller receipt before claiming enforcement.

## Agent workflow

When the user supplies a token or time allowance, load this guide before heavy
work. Obtain your actual `CODEX_THREAD_ID` in a native shell, then call:

```json
{
  "caller_thread_id": "ACTUAL_CALLER_UUID",
  "token_limit": 1000000,
  "time_limit_seconds": 14400
}
```

Use `wake_goal_limits_set` with the user's actual allocation; these numbers are
an example, not defaults. Neither the tool nor a new goal grants a larger budget.
Read the full returned state. Proceed only when `state` is `armed` or
`checkpoint_requested`, the independent controller is fresh, and accounting is
qualified. `held`, `stopped`, `stop_unverified`, `winding_down` or a structured
error holds autonomous campaign work. It does not prohibit operator replies,
status inspection, bounded setup diagnosis, or checkpoint writing. Report the
reason and next action; do not repeatedly attempt enrollment or resume a held goal. Use `wake_goal_limits_show` with your actual caller ID to
reconcile a timeout or inspect enforcement. Do not retry with a different ID,
use a peer ID, or substitute CLI identity claims for native caller metadata.
With host delegation, enrollment binds the actual native thread/turn/call from
the private MCP connection. Optional `allocation_id` selects an existing host
objective; it cannot create another allowance. Successors use the same ID and
retain cumulative spend, original deadline and any stopping decision. An
ambiguous/missing allocation needs a concrete selection or host setup correction,
not a new per-session UUID grant.

The controller requests “stop work and write a restart-safe checkpoint” when
either 5% of tokens or 60 seconds remain. Optional `checkpoint_token_percent`
and `checkpoint_seconds` make explicit overrides; the receipt displays them.
Fractional `checkpoint_token_percent` values are supported, for example17.5
for a350k-token reserve in a2M-token allocation. Checkpointing consumes the
original allocation. If the session is idle, the
request remains pending until an exact active turn can receive it; it does not
launch a new model turn merely to checkpoint. At exhaustion the controller pauses
the campaign's native goal and interrupts only its captured work turn. Later
operator turns remain usable while the goal stays paused. Stop ownership persists
across controller reconstruction; a new operator reply is not adopted as work.

On loss of accounting qualification, the controller pauses campaign continuation
and requests checkpoint winddown. Status exposes `winddown_deadline`; the grace
is at most 60 seconds, the configured checkpoint reserve, and the remaining
original time allowance. No retry or re-enrollment renews it. At grace expiry,
only the captured campaign turn is interrupted. This does not extend a token or
time cap or authorize additional product work. If time/control cannot be safely
qualified, stop proof may remain unverified; report that uncertainty.

New enrollment counts fresh input plus output tokens by default, excluding cached
input. `token_accounting: "cache_inclusive"` is an explicit alternative. Receipts
show both totals and the selected basis. Counters begin at the original goal
start and include attributable delegated usage once. Re-enrollment preserves the
existing basis; legacy receipts retain their cache-inclusive basis until an
explicit basis change. Such a change re-evaluates the same complete history and
retains the previous accounting, time origin, generation and any stop latch; it
is not a reset or automatic resume. Replacing `/goal`, resuming, re-registering, restarting the
controller or changing context does not reset them. Re-registration may tighten
limits. Only an explicit user reset, recorded in a new host-approved allocation
generation, can reset counters/allocation. Do not invent a reset to escape a hold.

## Meaning and limits of the receipt

- `armed`: qualified sampled accounting and a fresh independent watcher were
  observed. This is not an exact token ceiling or a guarantee against watcher
  failure after the observation.
- `checkpoint_requested`: the reserve has been reached. Inspect the checkpoint
  delivery state; queued, acknowledged and uncertain are different outcomes.
- `winding_down`: campaign continuation is held; only checkpoint winddown is
  permitted until the recorded deadline. This is not armed work admission.
- `stopped`: native readback proves the goal is paused/absent and none of its
  captured work turns is active. A later operator reply can be active. Separately running delegated sessions,
  arbitrary tool processes and external services are outside this stop proof.
  Delegated usage is counted; `descendant_stop_verified` remains false.
- `held` or `stop_unverified`: continuation is not authorized by this receipt.
  Preserve the original allowance and report missing evidence or uncertain stop.

Token publication, polling, filesystem work and native RPCs introduce delay;
maximum token overshoot is unknown. Missing history, unsupported root forks or
referenced history, absent descendants, conflicting response identities, scan
bounds and unqualified time/accounting hold continuation. Never replace those
facts with discounted native goal display counters or zero prior spend.

Resource readiness is separate from native goal state. Receipts expose
`native_goal_status`; known paused, blocked, complete or native-limited goals can
have armed resource supervision without being resumed. Enrollment does not turn
an inactive goal active and does not turn a planned goal pause into resource
exhaustion. Existing resource stop latches remain in force, including legacy
unknown-state holds; recognizing a known state never clears a prior stop.

These are session-native controls. For kernel memory, swap, CPU and task limits,
use the separately approved [dedicated executor workflow](resource-limits.md).
Shared servers and unrelated sessions remain outside this controller's authority.

## Operator setup

Configure one private owned host policy and runtime root. For native callers,
prefer version2 host delegation. Each named allocation is one objective allowance;
its first enrollment fixes limits, accounting basis, time origin and deadline.
Subsequent callers share the ledger and may only tighten limits. Do not use one
default allocation for unrelated objectives. When multiple objectives exist,
provide explicit allocation_id or choose an intentional default. For example:

```json
{
  "version": 2,
  "native_caller_binding": true,
  "default_allocation": "objective-289",
  "allocations": {
    "objective-289": {
      "app_server": "unix:///absolute/existing/codex.sock",
      "codex_path": "/absolute/path/to/codex",
      "codex_home": "/absolute/private/codex/home",
      "max_tokens": 2000000,
      "max_seconds": 21600
    }
  }
}
```

The host launches Wake MCP on its private native stdio connection with
`--goal-limits-policy POLICY --goal-limits-root ROOT`; the independent watcher
uses that root. Native Codex0.163supplies per-request metadata outside model
arguments. The adapter checks exact thread/session/turn/call identity before
admission. This trusts the host-owned local gateway; it does not authenticate
arbitrary public HTTP clients or isolate hostile code running as the same UID.
Do not expose this delegation adapter over an unqualified transport.

Version1 explicit caller policies remain compatible. Their caller grant uses
an existing absolute owned Unix endpoint and Codex home:

```json
{
  "version": 1,
  "callers": {
    "ACTUAL_CALLER_UUID": {
      "app_server": "unix:///absolute/existing/codex.sock",
      "codex_path": "/absolute/path/to/codex",
      "codex_home": "/absolute/existing/codex-home",
      "allocation_id": "user-approved-allocation-1",
      "max_tokens": 1000000,
      "max_seconds": 14400,
      "rpc_timeout": 5
    }
  }
}
```

Codex 0.163 publishes its `--listen` path as a rendezvous symlink. Provision
the physical owned Unix socket after verifying the private socket directory and
owned native process; an advertised alias is not an accepted endpoint for this
mode. Do not use strict-executor binding files to bypass that check.

Grants name an exact conversation UUID. A new conversation in the same tab or
CWD does not inherit a prior conversation's grant or allocation. Missing caller
grants return `caller_grant_missing` with no effect and the exact missing host
evidence. The current shared MCP path cannot mint a grant from a caller-selected
UUID, quoted prompt or checkpoint. Trusted caller and operator-request evidence
must be supplied by host admission tooling; agents cannot provision their own
authority. A missing grant holds campaign admission while operator interaction
and bounded diagnosis remain usable; `not_enrolled` means a grant was accepted
but the calling session has not yet registered limits. Neither condition is an
armed controller. Verify a renewal or continuation against its original authority
and accounting before provisioning; never copy an old UUID as the new caller.

The caller UUID, limits and paths must be real approved values. Policy file mode
must be `0600`, and the runtime directory private (`0700`). Keep credentials and
raw transcripts outside tracked artifacts. A qualified trusted clock is required.
Host ceilings do not themselves enroll or reset a goal.

Run an independent managed process, then configure MCP:

```sh
codex-wake --wake-root PRIVATE_ROOT goal-limits watch --interval 1
codex-wake-mcp --goal-limits-root PRIVATE_ROOT --goal-limits-policy PRIVATE_POLICY
```

The watcher must survive the calling agent's turn. An ordinary wake daemon or a
one-shot poll is insufficient admission evidence for this controller. Do not kill
the shared Codex server. Graceful watcher shutdown attempts native stop; abrupt
process loss cannot guarantee an action. Inspect process health and fresh status.

After an explicit user reset, change the host's `allocation_id` and approved
ceilings as authorized, then enroll again. The new generation takes a verified
response snapshot and a new time origin; old receipts remain historical evidence.
Changing endpoint/home is not a session reset or migration mechanism.

For CLI inspection use `goal-limits show --policy PRIVATE_POLICY
--caller-thread-id ACTUAL_CALLER_UUID --json` under the same `--wake-root`.
The MCP host, not its caller, owns these scope arguments.

Use `--goal-limits-root` for a separate private controller root when adding these
tools to an existing MCP configuration. This leaves other tools on their existing
wake root. Without this option, goal tools use the host `--wake-root`.

Delegated allocation ledgers live in `goal-supervision/allocations/` under the
private runtime root. Preserve them across restarts and handoffs. All enrolled
member histories are requalified, up to32members; unique native response IDs and
hashes prevent double charging delegated overlap. Missing or changed history
holds the objective. Stop latches and the first winddown deadline apply to every
successor while captured turn ownership stays per conversation. Self-enrollment
cannot renew an allocation or change its accounting basis; an explicit host
renewal is separate and must preserve prior history.

To authorize a scoped renewal, the host explicitly creates a distinct allocation
entry with `renews_allocation` naming the prior allocation. Changing IDs alone
does not authorize resetting the same caller. The renewed ledger starts at a
qualified response anchor and retains the previous ledger and finalized member
charges; later work is charged only to the renewed allowance. A boundary changed
after interrupted enrollment holds for reconciliation; do not retry with another
ID, alter the saved anchor, delete the ledger or invent another renewal.

For a first installation that must honor an already authorized renewal, the host
may set `initial_boundary` on its named allocation: `started_at` is the approved
UTC epoch, `token_accounting` is the explicit basis, and `reset_anchor` is the
qualified native response anchor recorded at that renewal. This field belongs
only to the private host policy; model tool arguments cannot provide it. The
controller requalifies original history, registers the boundary owner even if a
successor enrolls first, and charges post-boundary work without starting another
time window. Future/changed/unqualified boundaries hold before admission.
Version2policies may preserve a `callers` map for legacy explicit grants; those
callers retain their prior exact allocation and receipts. A requested different
allocation holds for qualified migration instead of silently using another one.
