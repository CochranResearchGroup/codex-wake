# Token and time limits in the existing dev session

This development-branch workflow supervises the current native `/goal` without
moving to another tab or agent. Installation, host grants and a running controller
are required. Source capability is separate from an installed release.

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
qualified. `held`, `stopped`, `stop_unverified` or a structured error means stop
and report the reason. Use `wake_goal_limits_show` with your actual caller ID to
reconcile a timeout or inspect enforcement. Do not retry with a different ID,
use a peer ID, or bypass missing host grants through the CLI.

The controller requests “stop work and write a restart-safe checkpoint” when
either 5% of tokens or 60 seconds remain. Optional `checkpoint_token_percent`
and `checkpoint_seconds` make explicit overrides; the receipt displays them.
Checkpointing consumes the original allocation. If the session is idle, the
request remains pending until an exact active turn can receive it; it does not
launch a new model turn merely to checkpoint. At exhaustion the controller pauses
the session's current native goal and interrupts its exact active turn.

Counters begin at the original goal start and include cached input and attributable
delegated usage once. Replacing `/goal`, resuming, re-registering, restarting the
controller or changing context does not reset them. Re-registration may tighten
limits. Only an explicit user reset, recorded in a new host-approved allocation
generation, can reset counters/allocation. Do not invent a reset to escape a hold.

## Meaning and limits of the receipt

- `armed`: qualified sampled accounting and a fresh independent watcher were
  observed. This is not an exact token ceiling or a guarantee against watcher
  failure after the observation.
- `checkpoint_requested`: the reserve has been reached. Inspect the checkpoint
  delivery state; queued, acknowledged and uncertain are different outcomes.
- `stopped`: native readback proves the goal is paused/absent and no active turn
  was observed. Arbitrary tool processes and external services may still exist.
- `held` or `stop_unverified`: continuation is not authorized by this receipt.
  Preserve the original allowance and report missing evidence or uncertain stop.

Token publication, polling, filesystem work and native RPCs introduce delay;
maximum token overshoot is unknown. Missing history, unsupported root forks or
referenced history, absent descendants, conflicting response identities, scan
bounds and unqualified time/accounting hold continuation. Never replace those
facts with discounted native goal display counters or zero prior spend.

These are session-native controls. For kernel memory, swap, CPU and task limits,
use the separately approved [dedicated executor workflow](resource-limits.md).
Shared servers and unrelated sessions remain outside this controller's authority.

## Operator setup

Configure a private owned policy file and runtime root. The exact caller grant
uses an existing absolute owned Unix endpoint and Codex home:

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

The caller UUID, limits and paths must be real approved values. Policy file mode
must be `0600`, and the runtime directory private (`0700`). Keep credentials and
raw transcripts outside tracked artifacts. A qualified trusted clock is required.
Host ceilings do not themselves enroll or reset a goal.

Run an independent managed process, then configure MCP:

```sh
codex-wake --wake-root PRIVATE_ROOT goal-limits watch --interval 1
codex-wake-mcp --wake-root PRIVATE_ROOT --goal-limits-policy PRIVATE_POLICY
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
