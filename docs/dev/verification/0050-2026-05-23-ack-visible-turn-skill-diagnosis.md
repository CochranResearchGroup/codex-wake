# Ack Versus Visible Turn Skill Diagnosis

Date: 2026-05-23

Request: diagnose reports that `codex-wake` says wake ack is triggering, but no
new turn is visible in the active TUI session.

## Runtime Evidence

Checked repo wake roots:

```text
/home/ecochran76/workspace.local/ragmail/.codex/wake
/home/ecochran76/workspace.local/graphiti/.codex/wake
/home/ecochran76/workspace.local/codex-wake/.codex/wake
```

Ragmail and Graphiti both had ack files and archived records with
`ack_observed`:

```text
ragmail wake_20260523_024420_9f2d: predicate_matched -> dispatch_attempt -> ack_observed -> archived
ragmail wake_20260523_013606_21dd: predicate_matched -> dispatch_attempt -> ack_observed -> archived
ragmail wake_20260523_003140_4c9e: predicate_matched -> dispatch_attempt -> failed -> requeued -> predicate_matched -> dispatch_attempt -> ack_observed -> archived
graphiti wake_20260523_004858_1699: predicate_matched -> dispatch_attempt -> ack_observed -> archived
```

Ack files recorded Codex session ids and turn ids, for example:

```text
ragmail wake_20260523_024420_9f2d -> session_id=019dc596-7543-7291-909e-f792ac300479
graphiti wake_20260523_004858_1699 -> session_id=019e3fbe-a697-7be2-83eb-4470c3bf51d6
```

Tmux pane inventory showed the expected live panes:

```text
%17 cwd=/home/ecochran76/workspace.local/ragmail
%13 cwd=/home/ecochran76/workspace.local/graphiti
```

Pane capture showed both target panes were busy Codex sessions. The evidence
supports this interpretation:

- Ack proves `UserPromptSubmit` ran for the wake prompt.
- Ack does not prove the operator saw a fresh, obvious turn in the pane being
  watched.
- If the target TUI is already active or interrupted, the prompt can be
  accepted and processed without looking like a clean new turn to the operator.
- If the wake targeted app-server, it may not appear in a live tmux pane at all.

## Skill Update

Updated `skills/codex-wake/SKILL.md` to say:

- ack proves Codex submitted the wake prompt in the target session, not
  operator-visible turn display
- operator-visible current-TUI wakes should schedule the daemon after the
  current turn stops
- agents should inspect target pane and ack evidence before claiming visible
  wake success

Updated `skills/codex-wake/references/use-cases.md` with:

- an operator-visible delayed wake pattern using `systemd-run --user`
- an `Ack But No Visible Turn` troubleshooting section
- commands to inspect wake records, ack files, pane inventory, and pane
  scrollback

Updated README with the same ack-versus-visible-turn distinction.

## Installed Skill Copies

Synced the updated skill into:

```text
/home/ecochran76/.codex/shared/skills/codex-wake
/home/ecochran76/.agents/skills/codex-wake
```

Confirmed installed copies match the tracked skill:

```text
diff -qr skills/codex-wake /home/ecochran76/.codex/shared/skills/codex-wake
diff -qr skills/codex-wake /home/ecochran76/.agents/skills/codex-wake
```

## Validation

Lightweight skill check:

```text
skill_visibility_guidance_ok
```

Repo checks:

```text
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
Ran 91 tests in 0.796s
OK

python -m compileall -q src tests
git diff --check
```

Wake root after diagnosis:

```json
{
  "active_total": 0,
  "terminal_total": 0
}
```

## Result

The tool appears to be doing what its current ack contract promises. The skill
was overclaiming what ack means. The updated skill now distinguishes
`ack_observed` from an operator-visible new turn and gives agents a safer
delayed-fire pattern for visible current-TUI dogfood.
