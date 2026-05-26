# Wake Monitor Readiness And User Supervisor

Date: 2026-05-25

Status: Closed by
`docs/dev/verification/0062-2026-05-26-wake-monitor-readiness-user-supervisor.md`.

## Scope

Make monitored wake delivery an explicit product contract instead of an
operator assumption.

This lane covers two related changes:

- Skill and tool hardening so agents cannot quietly schedule unattended wakes
  into an unmonitored wake root.
- A user-scoped supervisor service that can monitor registered Codex and
  OpenClaw wake roots from one durable background daemon.

The target outcome is that a wake record can answer three questions before it
is trusted:

- Which wake root owns this record?
- Which daemon or supervisor is responsible for polling it?
- What current evidence proves that monitor is active and can dispatch this
  record's target transport?

## Current State

Implemented. `codex-wake` still supports repo-scoped user-systemd services, and
now also supports a user-scoped supervisor that monitors explicitly enrolled
wake roots. The skill, CLI, and OpenClaw plugin can require monitor readiness
before writing unattended wake records, and live Codex app-server plus OpenClaw
Gateway wakes have fired from the supervisor with recorded evidence.

## Non-Goals

- Do not remove repo-scoped services in this lane.
- Do not make a daemon scan arbitrary workspace trees.
- Do not store secrets, tokens, raw Slack transcripts, or private prompt bodies
  in user-scoped supervisor registry files.
- Do not patch OpenClaw core unless plugin or Gateway surfaces lack a required
  narrow capability.
- Do not change trigger semantics for `not_before`, `file_exists`,
  `file_changed`, or `process_done` unless monitor-readiness checks require
  explicit metadata.
- Do not treat an ack, a Gateway submission, or a wake JSON file as proof that
  a future unattended wake is monitored.

## Architecture Decision

Prefer one user-scoped registry-backed supervisor as the durable monitor for
multi-repo and multi-agent wake usage.

The supervisor should be explicit and bounded:

```text
codex-wake-supervisor.service
  -> reads registered wake roots from user-scoped config
  -> polls each enabled root with codex-waked-compatible semantics
  -> dispatches through tmux, Codex app-server, or OpenClaw Gateway by target
  -> records per-root health and per-wake dispatch evidence
```

Repo-scoped services remain supported as single-root mode and as a migration
fallback. They are still useful for isolated tests, downstream repos that want
local ownership, and hosts where the supervisor is not installed.

The supervisor must not infer ownership by walking home directories. Roots are
enrolled explicitly.

Candidate registry shape:

```json
{
  "schema_version": 1,
  "root_id": "codex-wake-main",
  "wake_root": "/home/ecochran76/workspace.local/codex-wake/.codex/wake",
  "repo_root": "/home/ecochran76/workspace.local/codex-wake",
  "enabled": true,
  "created_at": "2026-05-25T00:00:00Z",
  "owner": {
    "kind": "repo",
    "name": "codex-wake"
  },
  "dispatch": {
    "codex_cmd": "/home/ecochran76/.nvm/versions/node/v24.14.0/lib/node_modules/@openai/codex/bin/codex.js",
    "openclaw_cmd": "/home/ecochran76/.local/bin/openclaw"
  }
}
```

The registry belongs in user-scoped config or state, not in tracked repo files.
The initial candidate location is:

```text
~/.config/codex-wake/roots.d/*.json
```

Supervisor health evidence can live under:

```text
~/.local/state/codex-wake/supervisor/
```

## Agent-Facing Contract

The `codex-wake` skill should require a monitor-readiness gate before any wake
that depends on unattended background firing.

Minimum agent flow:

```bash
codex-wake --wake-root .codex/wake service status
codex-wake --wake-root .codex/wake doctor --json
codex-wake --wake-root .codex/wake monitor check --json
```

If no active monitor owns the root, the skill should instruct the agent to
install or enroll a monitor before scheduling:

```bash
codex-wake --wake-root .codex/wake service install --codex-path "$(command -v codex)"
```

or, once implemented:

```bash
codex-wake supervisor install
codex-wake supervisor enroll --wake-root "$PWD/.codex/wake" --repo-root "$PWD"
codex-wake supervisor status --all
```

The CLI and OpenClaw plugin should enforce the same contract with tool-visible
status. A scheduled wake result should say one of:

- `monitor_ready=true`: a known active monitor owns the selected wake root.
- `monitor_ready=false`: the wake record was written, but no active monitor
  was found; unattended delivery is not guaranteed.
- `monitor_required_failed=true`: the caller required a monitor, so no wake
  record was written.

## Product Surface

Candidate CLI additions:

```bash
codex-wake --wake-root .codex/wake monitor check --json
codex-wake --wake-root .codex/wake doctor --monitor --json

codex-wake supervisor install
codex-wake supervisor uninstall
codex-wake supervisor start
codex-wake supervisor stop
codex-wake supervisor status --all
codex-wake supervisor logs --lines 120
codex-wake supervisor enroll --wake-root "$PWD/.codex/wake" --repo-root "$PWD"
codex-wake supervisor unenroll --wake-root "$PWD/.codex/wake"
codex-wake supervisor run --once
```

Candidate scheduling flags:

```bash
codex-wake --wake-root .codex/wake after --require-monitor 30m -- "..."
codex-wake --wake-root .codex/wake openclaw after --require-monitor 30m -- "..."
```

The OpenClaw plugin should expose equivalent behavior through its tool schema,
with `requireMonitor` defaulting to true for delayed unattended wake requests.

## Implementation Slices

### Slice 1: Skill And Plugin Readiness Gate

Harden the installed `codex-wake` skill and OpenClaw plugin result text before
the supervisor exists.

Acceptance criteria:

- The skill tells agents to check monitor readiness before scheduling
  unattended wakes.
- The skill distinguishes repo-scoped service readiness from future supervisor
  readiness.
- The OpenClaw plugin reports whether the selected wake root appears monitored
  by a repo-scoped service.
- Missing monitor evidence is described as a delivery risk, not as a completed
  scheduled wake.

### Slice 2: Monitor Readiness API

Add a product-level readiness check that can evaluate the current root against
known repo-scoped services.

Acceptance criteria:

- `monitor check --json` reports root path, service name, active/enabled
  status, service wake root, and transport readiness fields.
- `doctor --json` includes a monitor-readiness block.
- Tests cover active, inactive, wrong-root, missing-unit, and
  service-environment cases without requiring live systemd.
- The check does not leak unrelated user-systemd environment values.

### Slice 3: User-Scoped Supervisor Registry

Add explicit root enrollment and a supervisor service that can poll all enabled
registered roots.

Acceptance criteria:

- `supervisor enroll` writes a user-scoped registry entry atomically.
- `supervisor status --all` reports registered roots and latest health.
- `supervisor install` creates `codex-wake-supervisor.service`.
- `supervisor run --once` polls each enabled root with the same predicate and
  dispatch behavior as the single-root daemon.
- Repo-scoped services still work unchanged.

### Slice 4: OpenClaw Plugin Enforcement

Update the OpenClaw plugin so live OpenClaw agents schedule only into monitored
roots by default.

Acceptance criteria:

- Plugin-created wakes default to `requireMonitor=true`.
- If the root is not monitored, the plugin either enrolls an allowed root or
  returns a clear failure.
- Tool results identify the root, monitor source, target session key, and
  dispatch transport without exposing secrets.
- A plugin-created OpenClaw wake can be fired by the supervisor and verified
  through Gateway and Slack/transcript evidence.

### Slice 5: Migration And Dogfood

Dogfood the supervisor across Codex app-server and OpenClaw Gateway wakes.

Acceptance criteria:

- A Codex app-server wake fires from the supervisor using a registered root and
  explicit Codex command readiness.
- An OpenClaw plugin-created wake fires from the supervisor into a real
  OpenClaw session.
- `service status`, `supervisor status --all`, `monitor check --json`, and
  `doctor --json` agree about the monitored root.
- Verification evidence records service logs, wake ids, final wake statuses,
  and human-visible or transcript-visible proof where applicable.

## Validation Plan

Minimum source validation:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q src tests .codex/hooks
node --check plugins/openclaw-codex-wake/index.js
npm --prefix plugins/openclaw-codex-wake test
git diff --check
```

Minimum installed/runtime validation:

```bash
codex-wake --wake-root .codex/wake monitor check --json
codex-wake supervisor status --all
systemctl --user status codex-wake-supervisor.service --no-pager
codex-wake --wake-root .codex/wake doctor --json
```

Live validation must include at least one real wake fired by the supervisor.
For OpenClaw, proof must include Gateway dispatch metadata plus Slack Mirror,
OpenClaw transcript, or equivalent channel readback evidence.

## Definition Of Done

- `ROADMAP.md` has an open P42 lane and this plan remains the canonical design
  authority until the lane closes.
- Skill, CLI, and plugin behavior all expose monitor readiness consistently.
- The user-scoped supervisor can monitor multiple enrolled roots without
  relying on arbitrary filesystem scans.
- Repo-scoped services remain supported and documented.
- Installed-tool and live-service validation evidence is recorded under
  `docs/dev/verification/`.
- The lane is released only after public install or user-scoped install smokes
  prove the actual executable surface.
