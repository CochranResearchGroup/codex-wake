# Status Summary Dogfood

Date: 2026-05-20

Lane: P25

## Scope

Dogfood released `v0.4.7` `status --json` against the repo-local `.codex/wake` runtime using one short wake trigger.

## Installed Runtime Refresh

Command:

```bash
uv tool install --force --reinstall 'git+https://github.com/CochranResearchGroup/codex-wake.git@v0.4.7'
command -v codex-wake
codex-wake --help
codex-wake --wake-root .codex/wake status --json
```

Outcomes:

- Public tag resolved to `5aa3f61211a86ce4dc967ac6d76f25cdbe676bb7`.
- Installed `codex-wake==0.4.7`.
- Installed command path: `/home/ecochran76/.local/bin/codex-wake`.
- Installed help exposed `status`.
- Baseline `status --json` reported `active_total=0`.
- Baseline `status --json` reported existing historical terminal records: `cancelled=2`, `failed=1`, `submitted=1`.

## Baseline Readiness

Commands:

```bash
codex-wake --wake-root .codex/wake doctor --repo-root . --json
systemctl --user show codex-wake-codex-wake.service -p ActiveState -p SubState -p FragmentPath -p ExecStart --no-pager
```

Outcomes:

- Hook config existed and included `codex-wake-hook`.
- Hook runtime evidence had one older ack, `wake_20260519_104518_d191.submitted`.
- Repo-scoped service existed as `codex-wake-codex-wake.service`.
- Service was inactive/dead.
- Active shell had `TMUX_PANE=%202`.

## Dogfood Wake

Command:

```bash
codex-wake --wake-root .codex/wake after 20s -- 'P25 dogfood wake. First verify whether this wake has already been handled. If complete, report the evidence and stop.'
codex-wake --wake-root .codex/wake status --json
codex-wake --wake-root .codex/wake show wake_20260520_174316_9be6
```

Outcomes:

- Wake id: `wake_20260520_174316_9be6`.
- Wake path: `.codex/wake/pending/wake_20260520_174316_9be6.json`.
- Target transport: `tmux`.
- Target pane: `%202`.
- Due at: `2026-05-20T17:43:36Z`.
- Pending `status --json` reported `active_total=1`.
- Pending `status --json` reported `pending=1`.
- Pending `status --json` reported `earliest_next_attempt_at=2026-05-20T17:43:36Z`.

## Trigger Evaluation

Command:

```bash
sleep 23
codex-waked --wake-root .codex/wake --once --no-dispatch
codex-wake --wake-root .codex/wake status --json
codex-wake --wake-root .codex/wake show wake_20260520_174316_9be6
```

Outcomes:

- Daemon result: `checked=1 fired=1 failed=0 pending=0 dispatched=0 submitted=0 requeued=0`.
- No-dispatch mode was intentional to avoid pasting a surprise prompt into the active pane during this turn.
- Wake moved from `pending` to `firing`.
- Record event included `predicate_matched` with message `not_before due_at 2026-05-20T17:43:36Z matched`.
- Firing `status --json` reported `active_total=1`.
- Firing `status --json` reported `pending=0` and `firing=1`.

## Cleanup

Commands:

```bash
codex-wake --wake-root .codex/wake cancel wake_20260520_174316_9be6
codex-wake --wake-root .codex/wake archive wake_20260520_174316_9be6
codex-wake --wake-root .codex/wake status --json
python3 -m json.tool .codex/wake/archive/wake_20260520_174316_9be6.json
```

Outcomes:

- Wake moved to `.codex/wake/archive/wake_20260520_174316_9be6.json`.
- Archived record has `status=archived` and `previous_status=cancelled`.
- Archived record events include `created`, `predicate_matched`, `cancelled`, and `archived`.
- Final `status --json` reported `active_total=0`.
- Final `status --json` reported `archived=1`.
- Final `status --json` reported `earliest_next_attempt_at=""`.

## Hook Ack

`doctor --json` after dogfood still reported the latest ack as the older `wake_20260519_104518_d191.submitted`. No new P25 ack was expected because dispatch was intentionally disabled.

## Result

Pass. `status --json` was useful for supervising the dogfood wake without reading full records:

- pending was visible as `active_total=1`, `pending=1`, and a concrete earliest next attempt
- due trigger evaluation was visible as `pending=0`, `firing=1`
- cleanup was visible as `active_total=0`, `archived=1`, and no earliest next attempt

P25 is closed.
