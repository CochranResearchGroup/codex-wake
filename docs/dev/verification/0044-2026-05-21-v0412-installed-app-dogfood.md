# v0.4.12 Installed App Dogfood

Date: 2026-05-21

## Scope

Dogfood one app-server-targeted wake through the refreshed public `v0.4.12` installed runtime.

## Preflight

Installed runtime:

```text
codex-wake==0.4.12
```

Initial wake root:

```text
active_total=0
terminal_total=0
archived_total=8
```

Validated repo-local app-server candidates:

```text
codex-wake app candidates --cwd "$PWD" --validate --only-idle --json --limit 3
```

Result: three repo-local candidates returned `validation: resume_ok` and `status_type: idle`.

Selected candidate:

```text
019e4814-febe-7fe3-b2b5-8f23ffe54b5b
```

This was the disposable `codex-wake`-originated candidate, not the active TUI-originated candidate.

## Wake Registration

Created the wake from the installed CLI:

```text
codex-wake --wake-root .codex/wake app after 019e4814-febe-7fe3-b2b5-8f23ffe54b5b 2s -- 'P35 installed v0.4.12 app-server dogfood. Report APP_DOGFOOD_V0412_OK and stop.'
```

Wake id:

```text
wake_20260521_125018_24fb
```

Created record:

```text
status=pending
predicate.type=not_before
target.transport=app-server
target.endpoint=stdio://
target.thread_id=019e4814-febe-7fe3-b2b5-8f23ffe54b5b
```

## Daemon Dispatch

Ran the installed daemon once after the predicate was due:

```text
sleep 3
codex-waked --wake-root .codex/wake --once --ack-timeout 10
```

Result:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0
```

Submitted record evidence:

```text
status=submitted
attempts=1
app_server_preflight.status.type=idle
dispatch_result.thread_id=019e4814-febe-7fe3-b2b5-8f23ffe54b5b
dispatch_result.turn_id=019e4a96-6aef-7b50-9acb-6ac384fa12b4
events=created,predicate_matched,dispatch_attempt,app_server_preflight,ack_observed
```

## Cleanup

Archived the dogfood record:

```text
codex-wake --wake-root .codex/wake archive wake_20260521_125018_24fb
```

Archived record evidence:

```text
status=archived
previous_status=submitted
archived_at=2026-05-21T12:51:23Z
```

Final wake root:

```text
active_total=0
terminal_total=0
archived_total=9
counts_by_target_transport=app-server:3,tmux:6
```

Service state was unchanged:

```text
Id=codex-wake-codex-wake.service
ActiveState=inactive
SubState=dead
UnitFileState=disabled
Result=success
NRestarts=0
```

## Result

Pass. The refreshed public `v0.4.12` installed runtime created a durable wake record, evaluated the due predicate, dispatched through app-server, recorded submitted wake evidence, and archived the dogfood record. No active or terminal wake records remained.
