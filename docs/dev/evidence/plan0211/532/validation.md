# #532 terminal session UX and bot reuse

Source base e639397; core ensure prerequisite 648af92 cherry-picked as 6f52329.
Worker branch `feat/terminal-session-532`. No installed runtime was changed.

Public behavior: `tabs sessions list/show/...` renders a readable name/backend/state/tab count/health and activity table; `--json` retains structured transport results. Unobserved health/activity is explicitly marked. Ordinary workspace-scoped tab verbs accept `--session NAME_OR_ID` and `--server` qualifiers, preserving `--workspace`. Omitted selection infers exact TMUX socket and native session ID, otherwise selects a unique running candidate. Ambiguous human TTY commands offer a numbered picker. JSON and non-TTY calls return structured candidates and never prompt. Native API/MCP owners retain the portable noninteractive session operations.

The interview term bots names a role; the external launcher native name is `codex-bots`, also the helper default. An explicit name may select an independent destination. Existing external ownership metadata is preserved.

The portable `tabs sessions ensure --name codex-bots --defaults '{"argv":["/bin/sleep","300"]}' --json` is a directly usable authorized launch interface. `terminal_bot_session.ensure_bot_session(execute, argv=...)` supplies the same public operation for embedding clients; pass the host's authenticated operation client, or a local `operator_execute` closure. Commands apply only to new definitions; existing saved defaults and running processes are retained. No provider calls were made.

External launcher discovery used file-searcher before reads. Configured tenant source is `/home/ecochran76/workspace.local/grok-bots/codex-bots`. Its `src/native.mjs:329` `ensureBot(bot)` already creates/reuses dedicated `codex-bots`, checks service ownership, refuses duplicate owned bot windows and returns an attested existing binding before launch. New windows are created only for absent bots. This independent launcher was not modified or executed. The installed systemd unit executes `~/.local/share/codex-bots/current/src/main.mjs`; source identity is not installed equality proof. The Wake helper is an additional usable public seam, not a claim that this external launcher now calls Wake.

Validation (both passed, five tests each):

```
PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest tests.test_terminal_session_cli tests.test_terminal_bot_session
PYTHONPATH=src /tmp/codex-wake-p210-py311/bin/python -m unittest tests.test_terminal_session_cli tests.test_terminal_bot_session
```

Red evidence: bot public-seam test initially failed with one session instead of two before core ensure prerequisite was integrated. Native acceptance uses disposable private tmux servers and `/bin/sleep 300` only; exact pane IDs/PIDs remain unchanged after reuse with a different supplied command, and the default session remains unchanged. Fixtures kill only their private server. Current context is independently tested with two real private sessions. No hosted CI, Windows or production qualification. Local Python checks substitute for hosted CI; host OS is Linux/WSL, no Windows bridge qualification.

Memory disposition: forbidden — worker instructions explicitly prohibit memory writes.

Installed launcher readback: `current/src/native.mjs:518-556` independently confirms the same ensureBot ownership, duplicate refusal and attested reuse behavior; its exact tmux targets use `=codex-bots:`. Whole-file SHA256 differs: source `fe27ef7c0e694b361dab647e21d9c30185407928ceb24f6094c67c07ae2913ad`; installed `878486e37f835af077dbc31cbac435cdab8b50d5c64e988a63b0ad40cc6c5987`. This is bounded source inspection, not runtime execution or whole-file equivalence. No service was changed.
