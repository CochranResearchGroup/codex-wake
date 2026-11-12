# Task governor controls

The governor journey is qualified on the Plan0220 integration branch in an
isolated Linux test user. Commands below require the matched native package.
See `docs/dev/evidence/plan0220/qualification.json` for exact source and installed
acceptance; working-account deployment remains separate.

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
preserves usage; reset preserves lifetime history. Extension, reset, disable and advisory changes resume only with `--resume`.
Use `codex-wake governor resume` for a separate explicit continuation. Model callers may activate or
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

Default native controls and the private controller read the locally owned Codex
MCP configuration's existing `--goal-limits-root` and `--goal-limits-policy`
binding. They use that governor rather than creating another under the general
controller root. Explicit isolated roots retain their own state. Model callers
receive the configured host policy through verified adapter context; it is never
an argument they can supply to increase authority.

Strict enforcement requires paginated native history, V2 task isolation and the
matched native guard capability. Legacy task isolation remains held with an
explicit unsupported reason. A watcher
heartbeat alone cannot prove fail-closed behavior after watcher termination. Old
native builds must report their limitation and offer an explicit advisory choice;
they must not advertise strict enforcement from backend tests alone.

The same-user private CLI bridge, including its PowerShell client, is an operator
entrypoint. Generic API/MCP calls retain their session/scoped authority. A
mutating remote CLI request receives its `--request-id` before transmission;
on disconnect retain that key to reconcile instead of submitting another intent.
Unavailable activation or incomplete requested continuation returns a held result
and nonzero CLI status. Observation can succeed while truthfully reporting that
no governor is enrolled.

Allowance admission uses the existing qualified host clock.
`codex-wake time inspect` reports its readiness. Failed clock or native capability
setup does not begin a task budget window.
