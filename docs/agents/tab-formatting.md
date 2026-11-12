# Tab formatting

Wake can decorate owned Byobu/tmux and native Windows psmux tabs from one WSL
controller. It preserves your tab names, placement, conversations and processes.
Plain `codex` remains stock Codex. No model request is needed to draw a tab.

## Everyday commands

Use your remembered controller; no `WAKE_ROOT` environment variable is needed.
List workspaces, then select one ID or unique label:

```sh
codex-wake tabs list
codex-wake tabs format status --workspace WORKSPACE
codex-wake tabs format enable --workspace WORKSPACE
codex-wake tabs format inspect --workspace WORKSPACE
```

Enable, resume and re-enable ensure that the existing single tab monitor is
running for the selected controller when persistent policy permits it. They do
not restart an incompatible legacy monitor or any agent. A startup failure is a
partial result with actionable monitor details. Rollback leaves this shared
monitor running while keeping the selected workspace disabled. Inspect it with
`codex-wake tabs monitor-status`; `tabs monitor-start` is also available explicitly.
Defaults are a
five-second interval, bounded probes and a ten-second whole-cycle budget.
These are scheduling targets, not a promise that every workspace updates in five
seconds under load. An isolated forty-tab tmux acceptance run completed successive
cycles in roughly seven seconds. Unavailable/over-budget observations report
partial results and do not extend freshness.

Labels show harness/build, profile when known, activity and your existing name.
`CX` is stock Codex, `CX+` is modded Codex, `GK` is Grok, `SSH` is a remote shell,
and `MIX` marks mixed panes. Inspect returns pane observations and the last
projection. Unknown health remains unknown; a shell is not unhealthy simply
because it lacks agent health telemetry.

Fresh error overrides health warning, then waiting, then the type/activity base
colour. The type badge remains visible. Selection uses native current-tab
formatting with brackets and a bold/underline cue. Twenty-second native expiry
removes uncertain activity/attention cues if observations stop, even when Wake dies.
Names, stable type and the selected palette remain unchanged; no STALE label or
whole-tab dimming is added.
Actual visibility also follows the backend's redraw interval, which Wake bounds
at five seconds while decoration owns it.

## After reboot or terminal server replacement

Run `codex-wake tabs format enable --workspace WORKSPACE` again. Explicit enable
retains the previous namespace's original settings in the controller's
`tab-formatting/state.json` under `retired_workspaces`, then captures the current
namespace's originals before decorating it. Existing schema-version 1 files
remain readable; the retained map is additive. Returning to a previously seen
namespace reuses its originals. No old baseline is restored onto a new server.

Before enable, status and inspect report `status: stale_target` with
`namespace_matches: false` when saved custody belongs to another namespace.
The reported record is that saved baseline; window options describe the current
server. These reads do not change custody. Rollback, resume, reenable, reset,
pause remain fenced until explicit enable establishes current custody. Automatic
refresh retains this fence unless recover_namespace is explicitly enabled. Requests pinned to the old presentation are still rejected.
The optional startup workflow below enables automatic recovery at login; without
that opt-in, enable starts the monitor through the normal supported path.

## Automatic startup and replacement recovery

On Linux with a systemd user manager, opt in for the selected workspace:

```sh
codex-wake tabs format configure --workspace WORKSPACE --policy '{"recover_namespace":true}'
codex-wake tabs format enable --workspace WORKSPACE
codex-wake tabs startup enable
codex-wake tabs startup status
```

Startup installs one root-specific owned user unit, enabled for `default.target`,
and hands the existing monitor to its foreground service. It preserves monitor
settings and waits safely for configured or automatically discovered terminal
sockets/sessions. It does not create terminals, launch agents or keep the host
awake. Startup follows the user's normal manager/login lifecycle; it does not
change linger settings. `tabs startup disable` disables and stops this owned
service; unrelated units remain untouched. These commands are local CLI only.

`recover_namespace` defaults to false. When explicitly enabled, automatic refresh
may retain an enabled workspace's prior namespace baseline and capture originals
for its observed replacement, including after reboot. Disabled, rolled-back and
paused workspace records remain held. Returning namespace baselines preserve
their own disabled/paused state. Unavailable observations cannot authorize this
transition. Requests pinned to old identities remain rejected. Workspace IDs
must match exactly; names are not used to guess old-to-new session identities.
Turn recovery off with `--policy '{"recover_namespace":false}'`.

An edited/foreign startup unit is preserved and reported as a conflict. A missing
user-manager bus is a startup gate, not authority to change system services.

## One-command rollback and re-enable

```sh
codex-wake tabs format rollback --workspace WORKSPACE
codex-wake tabs format reenable --workspace WORKSPACE
```

Rollback stops automatic reapplication for that workspace and restores the
original affected settings captured before the first decoration, including
unset/inherited options. It restores those original values even if you manually
edited an affected setting afterward. Re-enable reapplies saved Wake preferences
without replacing that original baseline. Neither command needs a service restart
or a theme-file edit. Repeating rollback is safe.

The baseline covers the four window format/style options and the session refresh
interval/native-clock option. Unrelated settings remain yours. A missing baseline,
changed namespace identity or incomplete native readback is an error or partial
result, never a successful restoration. Inspect failures before retrying; preserve
the baseline for recovery. The commands act on one selected workspace, not every
terminal on the machine.

## Policy and manual changes

```sh
codex-wake tabs format configure --scope global --policy '{"enabled":false}'
codex-wake tabs format configure --scope global --policy '{"enabled":true}'
codex-wake tabs format configure --workspace WORKSPACE --policy '{"enabled":false}'
codex-wake tabs format configure --workspace WORKSPACE --policy '{"show_model":true,"show_provider":true}'
codex-wake tabs format pause --workspace WORKSPACE
codex-wake tabs format resume --workspace WORKSPACE
```

Global opt-out takes precedence over workspace opt-in. Configuration changes
persist; disabling a policy stops future application but does not restore old
styles—use rollback for restoration. Pause leaves the current decoration in place.
Reset restores original settings and removes workspace preference overrides while
retaining the original baseline. Re-enable retains preferences; resume is the
explicit action that clears manual-style holds.

Manual renaming works normally. Editing an affected local or parent/global theme
setting makes Wake yield for that scope; observations continue. Refresh/reconnect
and ordinary enable/re-enable respect those holds. After reviewing the new theme,
use resume to let Wake decorate again. A rolled-back workspace stays disabled
across monitor restart/reconnect until explicitly re-enabled.

Model and inference provider are optional reported dimensions, separate from the
coding harness, profile and execution host. Configured selection is not proof of
observed use. Claude Code, custom/open harnesses and Ollama are future adapter
families; merely naming one does not grant health, prompt or lifecycle support.

## Rendering and platform limits

```sh
codex-wake tabs format configure --workspace WORKSPACE --policy '{"render_mode":"basic"}'
codex-wake tabs format configure --workspace WORKSPACE --policy '{"render_mode":"plain","ascii":true}'
```

`full` uses the palette supported by the terminal; `basic` restricts colours;
`plain` retains text and selection cues without state colour. ASCII metadata is
the default. Unicode display-cell bounds are conservative; grapheme appearance
and colour fidelity depend on the client. User names remain native names. Literal
metadata is escaped; installed psmux displays a separating space in `#[` metadata
to prevent its second-stage style parser treating it as an instruction.

Qualification covers installed tmux 3.4 / Byobu 6.11 and psmux executable SHA256
`bbe825a30f7cddc91b043084049143a381aba5f7e9e36e4d0bb587e296d262ca` in disposable
namespaces, including actual attached clients. A backend name or a different
binary does not inherit that qualification. Capability inspection distinguishes
protocol support, observed identity and client-rendering acceptance. Linked
windows and changed namespace identities are held rather than changing another
workspace. A Windows-native server is future work; current Windows clients talk
to the WSL authority.

## CLI, API and MCP

`tabs format --help` and each verb's `--help` come from the shared command parser.
Flat `tabs format-rollback` aliases remain available. Bash/Zsh completion uses that
same parser; the supported installer activates it. Native PowerShell clients use
the portable `controller remote` interface with `tabs.format.*` operation names:

```powershell
# Windows PowerShell 5.x needs embedded quotes escaped for native executables.
$Arguments = '{"workspace":"WORKSPACE"}'.Replace('"', '\"')
codex-wake controller remote --endpoint $Endpoint --token-file $TokenFile --transport api tabs.format.status --arguments $Arguments
```

Use `--transport mcp` for OAuth MCP. Mutations require the exact `expected_target`
from status/inspect plus the common `_request` intent envelope; ordinary local WSL
CLI resolves those pins. Registered MCP tools are `wake_tabs_format_STATUS`, with
the lowercase verb substituted, for example `wake_tabs_format_rollback`. Remote
calls retain existing authentication/scoped-authority requirements. PowerShell
completion generation is not currently provided. See the [generated command
reference](command-reference.md) and [completion installation](shell-completion.md).

Mutation replies retain the common operation journal. Inspect the operation's
`phase`, `reason` and `result`; an admitted rejection can be conservatively
reported as `uncertain` with `reason: invalid_argument`. A successful HTTP/MCP
exchange or a false MCP transport-error flag alone does not prove the formatting
operation succeeded. Local CLI returns3 for uncertain work; use the retained
request result to reconcile rather than blindly resubmitting an effect.

## Compact neutral display

```sh
codex-wake tabs format configure --session default --policy '{"compact":true,"render_mode":"plain","show_stale":false}'
codex-wake tabs format resume --session default
```

Compact display keeps the native number/name, type badge for harnesses, and a
small `*` running, `?` waiting or `!` attention cue. Shells omit the type badge;
profile, idle and unknown badges are omitted. Plain rendering uses terminal
default colors. `show_stale:false` removes repeated STALE text, while backend
expiry still removes uncertain dynamic cues and inspection retains freshness.
Use `compact:false` or `show_stale:true` to restore those individual preferences.

## Named color presets

Built-in `slate`, `dusk` and `graphite` presets match the compact palette preview.
They select compact labels, no repeated STALE text and full-color rendering.
Only short type/attention badges carry accent colors; names remain soft gray and
the selected tab has a subtle background. Quiet expiry preserves the palette and removes uncertain dynamic cues without
adding labels or gray blocks. Detailed freshness remains available in inspection.

```sh
codex-wake tabs format configure --session default --preset slate
codex-wake tabs format resume --session default
# Switch later: use --preset dusk or --preset graphite, then resume.
```

Selection persists per session. Presets are discoverable in `tabs format status`
(`available_presets`) and generated configure help/completion. `legacy` disables
the named palette; other explicit display preferences persist until changed.
Configure saves preferences; resume applies and clears manual-style holds.
Normal automatic updates can also apply configured changes when the monitor runs.
Rollback always restores the original captured baseline, including after switching
presets. Native Windows pixel/color fidelity remains separately qualified; this
preset release is accepted on tmux, not a new Windows rendering claim.
