# Disposable App-Server Dogfood Verification

Date: 2026-05-21

## Scope

Dogfood the released `v0.4.9` app-server wake path against disposable app-server threads.

## Installed Runtime

The user-scoped tool was refreshed from the public release tag:

```text
uv tool install --force 'git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.9'
```

Result:

```text
codex-wake v0.4.9
```

Local Codex CLI:

```text
codex-cli 0.131.0
```

The repo wake root baseline was tidy:

```json
{
  "active_total": 0,
  "archived_total": 6,
  "terminal_total": 0
}
```

## Thread-Start-Only Attempt

Created a disposable thread through local stdio app-server with `thread/start`.

Thread id:

```text
019e4813-b4da-7b80-9e45-03123c3eb57b
```

Immediate creation response reported an idle thread, but a fresh `codex-wake app status --json` invocation failed:

```text
codex-wake: app-server thread/read failed: {'code': -32600, 'message': 'thread not loaded: 019e4813-b4da-7b80-9e45-03123c3eb57b'}
```

A wake against that thread was registered:

```text
wake_20260521_010911_f2d9
```

Daemon result:

```text
checked=1 fired=1 failed=1 pending=0 dispatched=1 submitted=0 requeued=0
```

Wake failure:

```text
app-server thread/resume failed: {'code': -32600, 'message': 'no rollout found for thread id 019e4813-b4da-7b80-9e45-03123c3eb57b'}
```

Interpretation: `thread/start` alone does not create a resumable rollout for a later stdio app-server process.

## Persisted Disposable Thread Attempt

Created a second disposable thread, started one bootstrap turn, and waited for the thread to return to idle.

Thread id:

```text
019e4814-febe-7fe3-b2b5-8f23ffe54b5b
```

Bootstrap status sequence included active polling and ended idle:

```json
[
  {"type": "idle"},
  {"type": "active", "activeFlags": []},
  {"type": "idle"}
]
```

From a fresh app-server process, `codex-wake app status --json` found the thread but reported:

```json
{
  "status": {
    "type": "notLoaded"
  },
  "status_type": "notLoaded",
  "thread_id": "019e4814-febe-7fe3-b2b5-8f23ffe54b5b"
}
```

Registered a wake:

```text
codex-wake --wake-root .codex/wake app after 019e4814-febe-7fe3-b2b5-8f23ffe54b5b 1s -- 'P31 persisted disposable app-server dogfood. Reply with APP_SERVER_WAKE_DOGFOOD_OK and stop.'
```

Wake id:

```text
wake_20260521_011040_bd20
```

Daemon result:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0
```

Wake events:

```json
[
  {
    "type": "predicate_matched",
    "message": "not_before due_at 2026-05-21T01:10:41Z matched"
  },
  {
    "type": "dispatch_attempt",
    "message": "Starting app-server wake turn"
  },
  {
    "type": "app_server_preflight",
    "message": "App-server thread status is idle",
    "status": {
      "type": "idle"
    }
  },
  {
    "type": "ack_observed",
    "message": "App-server turn/start accepted wake prompt",
    "turn_id": "019e4815-eddb-79f2-a374-615bcd974284"
  }
]
```

The submitted wake was archived with `previous_status` set to `submitted`.

## Cleanup

Archived both P31 terminal dogfood records:

```text
codex-wake --wake-root .codex/wake archive wake_20260521_010911_f2d9
codex-wake --wake-root .codex/wake archive wake_20260521_011040_bd20
```

Final wake status:

```json
{
  "active_total": 0,
  "archived_total": 8,
  "counts_by_status": {
    "archived": 8,
    "failed": 0,
    "firing": 0,
    "pending": 0,
    "submitted": 0
  },
  "terminal_total": 0
}
```

## Outcome

Pass with an important constraint. The released app-server wake path works for a thread that has a persisted rollout: it resumes the thread, records idle preflight evidence, and accepts `turn/start`. A `thread/start`-only target is not resumable from a later stdio app-server process.

## Follow-Up

- Document that app-server wake targets must point to resumable threads, not bare `thread/start` shells.
- Consider changing `codex-wake app status` to offer a resume-backed status mode, because `thread/read` can report `notLoaded` even when dispatch can resume and preflight the thread successfully.
- Future dogfood should verify wake turn completion, not only `turn/start` acceptance.
