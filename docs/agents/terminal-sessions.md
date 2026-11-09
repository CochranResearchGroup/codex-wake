# Named terminal sessions

A terminal session contains tabs; a tab contains panes and running processes.
Agent conversations have their own identity. A saved session may be empty without
keeping a native container or agent alive. Listing discovers native sessions before
adoption; editing adopts their settings without restarting existing work.

Use the installed command's help and [generated reference](command-reference.md)
for exact fields:

```sh
codex-wake tabs sessions list
codex-wake tabs sessions list --json
codex-wake tabs sessions create --name bots
codex-wake tabs sessions show --session bots --json
codex-wake tabs sessions open --session bots
codex-wake tabs sessions update --session bots --changes '{"name":"workers","description":"Batch work","labels":["automation"]}'
codex-wake tabs show --session workers --json
```

Names are scoped to a server. Add `--server SERVER` when needed.
Use `SERVER::NAME` in `--session` or `--destination`, and
`--tab SERVER::NAME:@N`, to qualify a name with the exact SERVER column value. Ordinary tab
commands accept `--session NAME`; omission selects the current tmux context when
unambiguous. Interactive terminals can choose among candidates; noninteractive
commands return structured candidates without waiting for input. Stable saved IDs
survive rename. Deleting and reusing a name creates a different identity.

Launch defaults use `--changes '{"defaults":{"cwd":"/absolute/path","argv":["/bin/sleep","60"]}}'`.
They apply to new launches, never existing tabs. A configured launch profile is a
separate authenticated launch choice; editing defaults grants no provider access.
Native Windows custom/profile launch remains unsupported without a qualified
launcher; no shell substitution is used. The separate codex-bots launcher owns its
named session reuse and must not restart or duplicate existing bots on reuse.

## Preview, apply and undo

```sh
codex-wake tabs relocate preview --destination workers --tab default:@3 --json
codex-wake tabs relocate preview --destination workers --filter harness=codex --pattern repository='*/project' --json
codex-wake tabs relocate preview --destination workers --group batch --json
codex-wake tabs relocate preview --destination workers --label automation --json
codex-wake tabs relocate apply --plan-id PLAN --json
codex-wake tabs relocate status --plan-id PLAN --json
codex-wake tabs relocate undo --receipt-id RECEIPT --json
```

Preview freezes exact tab/process identities, destination identity and category
revision. Apply rechecks them, preserving panes/processes and focus by default.
A group or label selects a category; saving it alone does not move tabs. Advanced
`--selection` JSON supports `all`, `any`, `not`, exact/pattern predicates and
explicit `{"field":"harness","unknown":true}`. Unknown or stale traits do not
match ordinary comparisons, including negated comparisons.

Inspect every per-tab outcome: batches can be partial, held or uncertain. Reconcile
with status before another intent; reuse the retained plan instead of blindly
replaying a missing response. Undo restores only tabs still in the resulting
placement; later manual moves are skipped. Successful manual movement and undo
hold automatic routing until explicitly resumed.

## Routing and deletion

Save a rule with `tabs routing save --name NAME --destination SESSION --selection
JSON`, optionally setting priority and stability seconds. Enable it explicitly
with `tabs routing enable --rule-id ID`; add `--include-existing` only when existing
matches should participate. The owned monitor starts for continuous routing.
Rules require stable observations; conflicting equal-priority destinations hold
rather than choose arbitrarily. `tabs routing status --json` exposes decisions.
`tabs routing pin`, `unpin`, `hold` and `resume` take an explicit `--selection`.
Resume releases a hold; it does not remove a pin. Holds survive process restart.

```sh
codex-wake tabs sessions delete --session empty-name --json
codex-wake tabs sessions delete --session old --destination workers --json
codex-wake tabs sessions delete --session old --terminate --json
```

Populated deletion requires an explicit drain destination or termination. A partial
operation retains the session and its outcomes. Confirmed deletion disables rules
targeting that saved identity; name reuse does not reactivate them. Retain the
plan ID to reconcile uncertain deletion.

## Transport and qualification boundaries

WSL-hosted tmux/Byobu supports same-server whole-tab relocation. Native psmux
session CRUD is qualified separately; cross-session moves between psmux servers
remain unsupported and are rejected before effect. Cross-host migration and
Windows-native service hosting are outside this workflow.

CLI, stdio MCP, authenticated HTTP API and OAuth MCP share the operation contract.
Remote mutations must use a fresh `expected_target` and `_request` envelope;
session/routing/relocation operations use the `@terminal-sessions` management
target, with grants scoped to its stable fields. Generation changes fence stale
intents. Existing resource grants do not become session-management grants.
Native PowerShell uses the portable controller client against that same authority.

Source tests, immutable installed-package acceptance and deployment are separate.
The #534 receipt records the exact wheel, private Linux/Windows prefixes, transport
calls and cleanup. It does not install or activate this version in production.
Existing long-lived clients need a deliberate reload only after a future approved
deployment; no reload is required merely because source tests passed.
