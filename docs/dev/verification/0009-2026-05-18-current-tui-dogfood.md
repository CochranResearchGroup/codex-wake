# Current TUI Dogfood

Date: 2026-05-18

## Scope

Dogfood `codex-wake` from the active Codex TUI session instead of a disposable pane. The target was the current tmux pane exposed to the session.

## Commands

```bash
codex-wake doctor
codex-wake service install
codex-wake after 45s -- "Dogfood wake for the current Codex TUI session. Verify the wake predicate is true, run codex-wake list, report whether this pane was resumed by the daemon, then stop."
codex-wake list
codex-wake show wake_20260519_030204_9085
codex-wake service stop
codex-wake service status
```

## Evidence

- Current pane: `%202`
- Current tmux socket: `/tmp/tmux-1000/default`
- Wake id: `wake_20260519_030204_9085`
- Predicate: `not_before` due at `2026-05-19T03:02:49Z`
- Service: `codex-wake-codex-wake.service`

The daemon injected the canonical prompt into the current TUI pane:

```text
WAKE_TRIGGER_ID=wake_20260519_030204_9085
Resume the scheduled wake task.
```

The wake record events showed three dispatch attempts to pane `%202`, then a terminal failure:

```text
dispatch_attempt attempt 1: Pasting canonical wake prompt into tmux pane %202
ack_timeout attempt 1: ack timeout
requeued attempt 1: Wake requeued after 300 seconds
dispatch_attempt attempt 2: Pasting canonical wake prompt into tmux pane %202
ack_timeout attempt 2: ack timeout
requeued attempt 2: Wake requeued after 300 seconds
dispatch_attempt attempt 3: Pasting canonical wake prompt into tmux pane %202
ack_timeout attempt 3: ack timeout
failed: Maximum dispatch attempts reached
```

Final status:

```text
ID                                  STATUS  PREDICATE   NEXT
wake_20260519_030204_9085           failed  not_before  2026-05-19T03:08:18Z
```

The service was stopped after the retries:

```text
name=codex-wake-codex-wake.service
active=inactive
enabled=disabled
```

## Result

Partial pass.

The tmux target capture, daemon predicate handling, current-pane injection, retry behavior, max-attempt failure, and service stop behavior all worked against the live TUI session.

The ack path did not complete in this already-running TUI session. No `.codex/wake/acks/wake_20260519_030204_9085.submitted` file appeared, so the daemon correctly treated the wake as unacknowledged and failed closed after three attempts.

The likely operator action is to run `/hooks` in this TUI session and trust/review the current `.codex/hooks.json` entry that executes `codex-wake-hook`, then repeat a short current-pane wake. `codex-wake doctor` can confirm hook config presence, command availability, and the trust caveat, but it cannot prove that the active Codex TUI session has already accepted the hook.

## Follow-Up

- Keep `codex-wake doctor` wording explicit that hook config validity is not equivalent to active-session trust.
- Repeat this smoke after `/hooks` review in the same TUI pane.
- Consider adding an operator runbook step named "current TUI dogfood" that starts with `/hooks` before scheduling the wake.

## Repeat After Hook Review Attempt

A second current-pane wake was scheduled after the operator requested hook review:

```bash
codex-wake service install
codex-wake after 20s -- "Second current-TUI dogfood after hook review. Verify codex-wake list and report whether the ack path submitted this wake, then stop."
sleep 55
codex-wake show wake_20260519_031211_5457
codex-wake service stop
codex-wake cancel wake_20260519_031211_5457
```

Evidence:

- Wake id: `wake_20260519_031211_5457`
- Target pane: `%202`
- Predicate due at: `2026-05-19T03:12:31Z`
- The canonical prompt landed in the active TUI pane.
- No `.codex/wake/acks/wake_20260519_031211_5457.submitted` file appeared.
- The service was stopped, then the still-firing wake was cancelled to prevent a future retry when the service is restarted.

Final status:

```text
wake_20260519_031211_5457 cancelled not_before 2026-05-19T03:17:31Z
```

Result: injection still passes, ack still fails in this current TUI. The operator reported that the hook was not visible in the `/hooks` list. That means the active TUI had not loaded this repo hook source, so hook trust review was not available from this session. A chat message containing `/hooks codex-wake-hook` is not sufficient evidence that the interactive hook review flow ran.

## Repeat After Locating UserPromptHooks

The operator later clarified that the hook was visible under the `UserPromptHooks` group rather than the `codex-wake-hook` command name. A third wake was scheduled:

```bash
codex-wake service install
codex-wake after 20s -- "Third current-TUI dogfood after confirming UserPromptHooks. Verify codex-wake show for this wake, report whether status is submitted and ack exists, then stop."
```

Evidence:

- Wake id: `wake_20260519_033023_e611`
- Target pane: `%202`
- The wake did not paste into the pane.
- The daemon repeatedly requeued because `.codex/wake/locks/tmp_tmux-1000_default__202.lock` already existed.
- The lock contained PID `3672992`, which was not a live process.
- The wake was cancelled after the service stopped.

Result: no ack-path conclusion. The run found a stale pane-lock bug before injection. The fix is for `PaneLock` to remove dead-PID or malformed lock files before acquiring the lock.
