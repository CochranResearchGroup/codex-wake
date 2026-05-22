# Codex Wake Skill

Date: 2026-05-22

Request: determine whether a `codex-wake` skill exists and develop use cases
agents can use to schedule their own wake cycles.

## Result

No existing `codex-wake` skill was found in:

- `/home/ecochran76/.codex/shared/skills`
- `/home/ecochran76/.agents/skills`
- this repo

Added a repo-local skill:

```text
skills/codex-wake/SKILL.md
skills/codex-wake/agents/openai.yaml
skills/codex-wake/references/use-cases.md
```

The skill covers:

- durable wake records instead of model memory
- hook and doctor preflights
- delay, absolute-time, marker-file, file-change, and process-exit wakes
- daemon/service choices
- wake prompt idempotence
- ack/status/archive closeout
- duplicate project/user hook caveat

The use-case reference includes:

- CI or test babysitting
- long build or indexing job
- external artifact appears
- periodic self-check
- staged migration
- current TUI dogfood
- app-server wake
- cleanup or closeout wake

## Installed Skill Copies

Installed the same skill files into user skill roots:

```text
/home/ecochran76/.codex/shared/skills/codex-wake
/home/ecochran76/.agents/skills/codex-wake
```

## Validation

The bundled skill validator could not run in the current Python environment
because `yaml`/PyYAML is not installed:

```text
ModuleNotFoundError: No module named 'yaml'
```

Performed a lightweight structural check instead:

```text
skill_structure_ok
```

Confirmed tracked skill files:

```text
skills/codex-wake/SKILL.md
skills/codex-wake/agents/openai.yaml
skills/codex-wake/references/use-cases.md
```

Line counts:

```text
104 skills/codex-wake/SKILL.md
129 skills/codex-wake/references/use-cases.md
7 skills/codex-wake/agents/openai.yaml
```

Confirmed installed files:

```text
/home/ecochran76/.codex/shared/skills/codex-wake/SKILL.md
/home/ecochran76/.codex/shared/skills/codex-wake/agents/openai.yaml
/home/ecochran76/.codex/shared/skills/codex-wake/references/use-cases.md
/home/ecochran76/.agents/skills/codex-wake/SKILL.md
/home/ecochran76/.agents/skills/codex-wake/agents/openai.yaml
/home/ecochran76/.agents/skills/codex-wake/references/use-cases.md
```

## Notes

Future installer work could expose a command to install the skill from the repo
into the configured user skill roots. For now, the repo-local skill is tracked
and the current machine has installed copies.
