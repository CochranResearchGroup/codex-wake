# CLI output

Use ordinary commands for readable terminal output:

```sh
codex-wake accounts list
codex-wake accounts resolve soylei
codex-wake daemons list
codex-wake builds list
codex-wake history search --help
```

Account lists show account names, aliases and home directories in aligned columns.
Other lists use tables; details use labeled fields. Empty lists and failed commands
explain the outcome. The same human defaults apply when output is redirected.
No ANSI color, pager or terminal-width dependency is required.

For scripts, add `--json` to the leaf command:

```sh
codex-wake accounts list --json
codex-wake accounts resolve soylei --json
codex-wake builds list --json
```

JSON preserves the complete structured envelope, including exact target/generation
pins. Human output hides protocol envelopes and generation metadata. Do not parse
human table columns or labels as a stable interface. Existing scripts that parsed
unflagged JSON must select `--json`; command exit statuses are unchanged.

The shared presentation applies to accounts/stores/configuration, controller
inventory, builds, daemons, health, history, migration, hosts, tabs, flows,
flow-sessions, recovery, notices, structured Grok operations, common operations,
base control commands, task briefs, agent inventory/observation/resume, resource claims, attention,
work acceptance, background jobs, goal renewal and permissions. Existing specialized
human views (native account login/status, terminal sessions, operation answers and
older wake commands) retain their presentation. Build workflows also accept their
existing `--output json` form.

Explicit stream/transcript modes, `operations stream`, SSH receiver frames,
controller remote/API/MCP payloads and stdin permission frames keep their structured
protocols. Presentation changes do not alter dispatch, authorization, generation
checks, wake scheduling, runtime ownership or provider effects.

An already running shell uses the next installed CLI invocation; shell completion
still refreshes through the supported build/install workflow. Working-host package
installation and daemon/native build qualification remain separate from source and
private-wheel validation.
