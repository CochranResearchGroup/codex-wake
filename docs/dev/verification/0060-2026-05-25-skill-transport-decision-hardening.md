# Skill Transport Decision Hardening

Date: 2026-05-25

## Scope

Harden the tracked `codex-wake` skill so agents must distinguish live Codex
TUI/tmux wakes, Codex app-server wakes, and OpenClaw Gateway wakes before
scheduling delayed work.

This is a documentation and installed-skill synchronization slice. It does not
change wake-record schema, daemon dispatch behavior, plugin code, or the CLI.

## Changes

Updated:

- `skills/codex-wake/SKILL.md`
- `skills/codex-wake/references/use-cases.md`

The skill now includes a top-level `Choose Wake Transport` section with:

- target runtime classification;
- required target identifiers for tmux, app-server, and OpenClaw Gateway;
- delivery proof required for each transport;
- explicit warnings against using OpenClaw session keys as Codex app-server
  thread ids, app-server dispatch as current-TUI visibility proof, or
  `codex-waked --no-dispatch` as delivery proof;
- pre-schedule questions covering runtime, durable identifier, dispatcher,
  landing evidence, and missing-visible-turn follow-up.

The use-case reference now begins with `Choose Transport First`, including the
same decision matrix and negative examples before any trigger examples.

## Installed Skill Sync

Synced the tracked skill directory to:

- `/home/ecochran76/.agents/skills/codex-wake`
- `/home/ecochran76/.codex/shared/skills/codex-wake`
- `/home/ecochran76/.openclaw/skills/codex-wake`

Commands:

```bash
rsync -a --delete skills/codex-wake/ /home/ecochran76/.agents/skills/codex-wake/
rsync -a --delete skills/codex-wake/ /home/ecochran76/.codex/shared/skills/codex-wake/
rsync -a --delete skills/codex-wake/ /home/ecochran76/.openclaw/skills/codex-wake/
```

## Validation

```bash
git diff --check
```

Result: passed with no output.

```bash
rg -n "Choose Wake Transport|Choose Transport First|OpenClaw Gateway|app-server|TMUX_PANE|codex_wake_schedule|--no-dispatch" skills/codex-wake
```

Result: found the new top-level transport decision guidance and the existing
OpenClaw/app-server/tmux evidence guidance in the tracked skill.

```bash
diff -qr skills/codex-wake /home/ecochran76/.agents/skills/codex-wake
diff -qr skills/codex-wake /home/ecochran76/.codex/shared/skills/codex-wake
diff -qr skills/codex-wake /home/ecochran76/.openclaw/skills/codex-wake
```

Result: all three comparisons passed with no output.

```bash
openclaw skills info codex-wake --agent main --json
```

Relevant result:

- `filePath`: `/home/ecochran76/.agents/skills/codex-wake/SKILL.md`
- `eligible`: `true`
- `modelVisible`: `true`
- `userInvocable`: `true`
- `commandVisible`: `true`
- `disabled`: `false`

## Outcome

Pass. The tracked skill and all installed copies now differentiate tmux,
Codex app-server, and OpenClaw Gateway wake tasks at the top of the agent
guidance, and OpenClaw can still see and invoke the skill for agent `main`.

No live wake was dispatched in this slice because the requested change was
skill/documentation hardening and install synchronization, not runtime transport
behavior.
