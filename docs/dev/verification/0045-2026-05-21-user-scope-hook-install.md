# User-Scope Hook Install

Date: 2026-05-21

Request: ensure the Codex Wake `UserPromptSubmit` hook is installed at user scope.

## Result

Installed `/home/ecochran76/.codex/hooks.json` with the same `UserPromptSubmit`
handler used by the repo-local `.codex/hooks.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "codex-wake-hook",
            "timeout": 5,
            "statusMessage": "Checking wake trigger"
          }
        ]
      }
    ]
  }
}
```

This keeps the user-scope hook definition separate from the existing shared
Codex config and from repo-local hook trust state.

## Verification

Validated JSON shape:

```text
python3 -m json.tool /home/ecochran76/.codex/hooks.json
```

Confirmed the user-scope hook file and repo-local hook file are byte-identical:

```text
sha256sum .codex/hooks.json /home/ecochran76/.codex/hooks.json
0d073e43ce5580a3bbfb4948ef0b953c6dc4250ec89110910ba096223ea9ccb9  .codex/hooks.json
0d073e43ce5580a3bbfb4948ef0b953c6dc4250ec89110910ba096223ea9ccb9  /home/ecochran76/.codex/hooks.json
```

Confirmed the installed hook command self-filters non-wake prompts and exits
successfully:

```text
printf '{"prompt":"hello","cwd":"%s"}' "$PWD" | codex-wake-hook
rc=0
```

Confirmed Codex can parse the active config layer with the new user-scope
`hooks.json` present:

```text
timeout 10 codex debug prompt-input "hook config parse smoke"
rc=0
```

## Operator Note

Codex may still require `/hooks` review for this new user hook source before it
runs in an interactive TUI. In `/hooks`, it should appear under the user config
source rather than the repo-local project config source.
