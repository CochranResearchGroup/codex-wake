# Task governor controls

The new governor journey is under implementation in #570 (Plan0220). Commands
below describe the integration branch; this document is not an installed-runtime
qualification receipt.

Inside a qualified existing Codex session:

```sh
codex-wake governor status
codex-wake governor activate --token-limit 100000 --time-limit-seconds 1800
codex-wake governor extend --add-tokens 50000 --resume
codex-wake governor reset
codex-wake governor disable
```

Use an explicit `thread:UUID` selector outside the current session. `--json`
returns the full status. New task windows begin at successful activation; waits
count against elapsed time. Task and shared allowances both apply. Extension
preserves usage; reset preserves lifetime history. Extension/reset resume only
with `--resume`; disable never implicitly resumes. Model callers may activate or
tighten their own limits, but cannot increase, reset or disable operator ceilings.

The modded harness's `/wake governor` opens the corresponding direct operator
controls. Its persistent strip separates enforced/advisory/disconnected/disabled/
limit-reached states with text and subdued meters. Missing accounting is unknown,
not zero. Lost enforcement pauses affected work and offers repair or explicit
advisory operation. Native UI support requires the qualified modded build; stock
Codex is unchanged.

Machine surfaces use `local.governor.*` on the same-user control server and
`governor.*` on the OAuth controller, with `wake_governor_*` MCP tools. Native MCP
binds model actions to the verified current caller. Remote operations require an
explicit task selector and its scoped grant; increasing/resetting/disabling also
requires authenticated owner/admin authority. JSON authority flags are rejected.
