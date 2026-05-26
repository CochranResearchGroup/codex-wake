# Live Product Smokes

Date: 2026-05-26

Plan: `docs/dev/plans/0043-2026-05-26-productization-completion.md`

## Scope

Record fresh live Codex app-server and OpenClaw Gateway wake smokes through the
P43 product smoke harness.

Both smokes used the real repo wake root:

```text
/home/ecochran76/workspace.local/codex-wake/.codex/wake
```

The root was monitor-ready through `codex-wake-supervisor.service`.

## Codex App-Server Smoke

Harness artifact:

```text
.codex/wake/smoke/0068-live-codex
```

Command shape:

```bash
python scripts/product_smoke.py \
  --wake-root "$PWD/.codex/wake" \
  --use-user-state \
  --expect-monitor-ready \
  --live-codex-thread-id 019e4814-febe-7fe3-b2b5-8f23ffe54b5b \
  --live-codex-path "$(command -v codex)" \
  --due-after 5s \
  --live-timeout 180 \
  --json
```

Result:

```text
wake_id=wake_20260526_130227_30c0
marker=CODEX_WAKE_PRODUCT_SMOKE_CODEX_20260526T130227Z
status=submitted
```

Wake-record evidence:

```text
transport=app-server
thread_id=019e4814-febe-7fe3-b2b5-8f23ffe54b5b
app_server_preflight.status.type=idle
dispatch_result.turn_id=019e6461-4566-7a40-83c7-02f8f5f57eb4
events=created,predicate_matched,dispatch_attempt,app_server_preflight,ack_observed
```

Post-smoke app-server status check:

```text
thread_id=019e4814-febe-7fe3-b2b5-8f23ffe54b5b
status_type=idle
session_id=019e4814-febe-7fe3-b2b5-8f23ffe54b5b
active_flags=
```

## OpenClaw Gateway Smoke

Harness artifact:

```text
.codex/wake/smoke/0069-live-openclaw
```

Command shape:

```bash
python scripts/product_smoke.py \
  --wake-root "$PWD/.codex/wake" \
  --use-user-state \
  --expect-monitor-ready \
  --live-openclaw-agent main \
  --live-openclaw-session-key agent:main:slack:channel:c0ahqqcg7j4 \
  --live-openclaw-workspace default \
  --live-openclaw-channel C0AHQQCG7J4 \
  --live-openclaw-path "$(command -v openclaw)" \
  --live-openclaw-deliver \
  --due-after 5s \
  --live-timeout 900 \
  --json
```

Result:

```text
wake_id=wake_20260526_130335_d7b5
marker=CODEX_WAKE_PRODUCT_SMOKE_OPENCLAW_20260526T130335Z
status=submitted
```

Wake-record evidence:

```text
transport=openclaw_gateway
attempts=1
openclaw_gateway_preflight.rpc_ok=true
dispatch_result.status=ok
dispatch_result.summary=completed
dispatch_result.run_id=codex-wake:wake_20260526_130335_d7b5
dispatch_result.session_id=f8d86ef1-76f0-49ef-97a0-05801ef3bad2
events=created,predicate_matched,openclaw_gateway_dispatch_attempt,openclaw_gateway_preflight,openclaw_gateway_dispatch_result
```

Slack/channel readback confirmed the marker:

```text
ts=1779800677.926499
timestampUtc=2026-05-26T13:04:37.926Z
text includes CODEX_WAKE_PRODUCT_SMOKE_OPENCLAW_20260526T130335Z
```

## Cleanup

Both live smoke records were archived after evidence capture:

```text
archived wake_20260526_130227_30c0
archived wake_20260526_130335_d7b5
```

Final repo wake-root status:

```json
{
  "active_total": 0,
  "terminal_total": 0,
  "archived_total": 23
}
```

## Known Gap

Live smokes are complete for source/current-wheel validation. P43 still needs
the version bump, tag, pushed CI, GitHub release, public-tag install smoke, and
user-scoped install refresh for `v0.5.0`.
