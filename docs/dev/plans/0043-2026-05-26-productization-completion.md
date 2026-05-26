# Productization Completion

Date: 2026-05-26

Status: Closed

## Scope

Define the remaining productization work needed to move `codex-wake` from a
working local agent-runtime tool into a supportable `v0.5.0` product surface
for Codex and OpenClaw agents.

This lane treats productization as the point where an operator can install,
inspect, upgrade, and validate the tool without relying on chat history,
repo-linked plugin state, or one-off local knowledge.

## Current State

`v0.4.15` is released. The CLI can create and dispatch tmux, Codex
app-server, and OpenClaw Gateway wake records. `codex-wake-supervisor.service`
can monitor explicitly enrolled wake roots, and the `codex-wake` skill plus
OpenClaw plugin now require monitor readiness for unattended wakes.

The remaining product risk is not wake semantics; it is distribution,
operator diagnostics, lifecycle hygiene, and cross-runtime evidence. In
particular, the OpenClaw plugin is still validated as a linked local plugin,
not as a durable public install/update flow.

## Non-Goals

- Do not add new trigger classes before the existing product surface is
  supportable.
- Do not replace the JSON wake-record format with a database in this lane.
- Do not make the supervisor scan arbitrary workspace trees.
- Do not store OpenClaw tokens, Codex transcripts, Slack bodies, or private
  wake prompts in tracked fixtures.
- Do not patch OpenClaw core unless the plugin install/update path cannot be
  made durable through current plugin surfaces.
- Do not claim tmux operator visibility without `visibility_result` evidence
  or a direct pane inspection.

## Productization Definition

`codex-wake` is productized enough for `v0.5.0` when these operator questions
have deterministic answers from installed commands and tracked docs:

- How do I install or update the CLI, supervisor, Codex skill, hooks, and
  OpenClaw plugin from a public tag?
- Which wake roots are monitored, by which service, and with what current
  health evidence?
- Which transports are configured and dispatch-capable on this workstation?
- How do I run a safe smoke test for tmux, Codex app-server, and OpenClaw
  Gateway without confusing predicate firing with delivery?
- How do I archive, clean up, or unregister stale wake records and roots?
- What is unsupported, manual-only, or intentionally operator-gated?

## Productization Slices

### Slice 1: OpenClaw Plugin Distribution

Replace the repo-linked plugin as the only proven install path.

Implementation direction: keep the plugin as plugin-owned behavior in this
repo, but install it through OpenClaw's normal plugin installer from a
materialized public `codex-wake` tag or npm-pack artifact. Do not patch
OpenClaw core for this unless the installer cannot express a durable source.

Acceptance criteria:

- A documented install/update command installs the OpenClaw plugin from a
  public `codex-wake` tag or generated package artifact.
- `openclaw plugins inspect codex-wake --runtime --json` reports the expected
  plugin version, source, activation status, and `codex_wake_schedule` tool.
- The install path survives Gateway restart without depending on the current
  repo checkout.
- Plugin config schema exposes monitor defaults, timeout defaults, wake root,
  and OpenClaw command settings.
- A local uninstall or rollback path is documented.

Progress 2026-05-26:

- Added `codex-wake openclaw-plugin install|update|pack` helpers.
- Productized install/update materializes a public repo tag into user state and
  runs OpenClaw's normal non-linked plugin installer.
- `--prune-linked-path` removes only linked `plugins.load.paths` entries whose
  manifest id is `codex-wake`, writes an OpenClaw config backup, and refreshes
  OpenClaw's generated plugin registry.
- Verification `docs/dev/verification/0063-2026-05-26-openclaw-plugin-productized-install.md`
  confirms the active plugin source is
  `/home/ecochran76/.openclaw/extensions/codex-wake/index.js` after Gateway
  restart, with `codex_wake_schedule`, config schema present, and no plugin
  diagnostics.

### Slice 2: Unified Readiness Doctor

Make installed readiness auditable from one operator surface.

Acceptance criteria:

- `doctor --json` or a new product-readiness command reports CLI version,
  hook status, skill install status when detectable, supervisor status,
  enrolled roots, monitor health, repo-service status, app-server transport
  readiness, OpenClaw Gateway readiness, plugin readiness, and tmux command
  availability.
- The report distinguishes `ready`, `warning`, `manual_only`, and `blocked`
  outcomes.
- Secrets and raw environment values are not emitted.
- Tests cover missing supervisor, stale monitor health, missing OpenClaw
  plugin, missing Gateway auth environment, and app-server command drift.

Progress 2026-05-26:

- Added `codex-wake product-readiness --json`.
- The report includes normalized readiness checks for CLI version/commands,
  hook sources/runtime evidence, user-scope skill installs, repo service,
  supervisor status/enrolled roots, monitor health, app-server dispatch
  readiness, OpenClaw Gateway auth/RPC readiness, OpenClaw plugin readiness,
  and tmux availability.
- The status vocabulary is `ready`, `warning`, `manual_only`, and `blocked`.
- Gateway auth values are reduced to variable names, value source, and
  presence booleans; secret values are not emitted.
- Tests cover missing supervisor, stale monitor health, missing OpenClaw
  plugin, missing Gateway auth environment, and app-server command drift.

### Slice 3: State Lifecycle And Retention

Make wake/root cleanup explicit and low-risk.

Acceptance criteria:

- Runtime state classes are documented: authoritative wake records, derived
  monitor health, logs, registry entries, acks, and archive records.
- `cleanup`, `archive`, and `supervisor unenroll` docs explain the effect on
  each state class.
- Stale enrolled roots are visible in supervisor status with an actionable
  remediation path.
- A dry-run cleanup path shows what would be removed before it removes
  anything.
- Verification records show cleanup leaves no active or terminal wake records
  behind after dogfood.

Progress 2026-05-26:

- Added `docs/runtime-state-lifecycle.md` with authoritative, derived,
  ephemeral, and retained state classes.
- Documented the exact effects of `archive`, `cleanup`, `cleanup --delete`,
  `cleanup --archive-terminal`, and `supervisor unenroll`.
- `supervisor status --json` now reports per-root `health_status` and
  `remediation` so stale or missing health can be repaired or unenrolled.
- README and the `codex-wake` skill point operators to cleanup and stale-root
  remediation behavior.

### Slice 4: Cross-Runtime Smoke Harness

Codify the release smoke matrix so product validation is repeatable.

Acceptance criteria:

- A tracked smoke script or documented command matrix verifies installed CLI
  surfaces without relying on the source tree.
- Public-tag install smoke covers CLI version, schema, monitor check, and
  supervisor `run --once`.
- Live local smoke covers one real Codex app-server wake and one real OpenClaw
  Gateway wake with unique marker evidence.
- Tmux smoke is either verified with visibility evidence or explicitly marked
  manual/operator-visible only.
- CI continues to run source tests, build artifacts, and installed-wheel
  smokes on supported Python versions.

Progress 2026-05-26:

- Added `scripts/product_smoke.py`.
- The safe installed-surface smoke verifies `codex-wake --version`, schema
  output, product-readiness output, `codex-waked --once --no-dispatch`,
  monitor-check execution, and `supervisor run --once --no-dispatch` without
  requiring source-tree CLI imports.
- Public-tag smoke can install a GitHub tag into a temporary virtualenv before
  running the same installed-surface checks.
- Live Codex app-server and OpenClaw Gateway smoke paths are opt-in and record
  unique marker evidence plus final wake JSON.
- Tmux is explicitly marked manual/operator-visible unless a human captures
  pane visibility evidence.
- Added `docs/product-smoke-matrix.md`.
- CI now runs plugin tests, plugin entrypoint syntax checks, package build, and
  the installed-wheel product smoke.
- Verification `docs/dev/verification/0068-2026-05-26-live-product-smokes.md`
  records fresh Codex app-server and OpenClaw Gateway wakes through the
  harness with unique marker evidence, real turn/session ids, Slack readback
  for OpenClaw, and a clean final wake root.

### Slice 5: Operator Docs And Support Boundary

Give future agents and operators one canonical path.

Acceptance criteria:

- README has a concise quickstart from public install to monitor-ready state.
- `docs/daemon-service.md` explains repo service versus user supervisor
  selection and env import rules.
- The `codex-wake` skill points agents to the productized install/readiness
  path and keeps the transport-selection warnings.
- OpenClaw plugin README documents public install/update, Gateway restart,
  tool catalog verification, and Slack/transcript readback.
- Unsupported cases are explicit, including absent tmux target, placeholder
  app-server thread ids, placeholder OpenClaw session keys, and no-dispatch
  false positives.

Progress 2026-05-26:

- Added a README public-install quickstart from tag install through hook
  install, supervisor install/enroll, monitor check, and product-readiness.
- Added `docs/support-boundary.md` to define supported product paths,
  manual-only cases, required dispatch evidence, and unsupported false
  positives.
- Updated `docs/daemon-service.md` with repo-service versus user-supervisor
  selection guidance and the `--no-dispatch` smoke boundary.
- Updated the OpenClaw plugin README with product-readiness checks and explicit
  non-evidence cases for linked paths, placeholders, and no-dispatch smokes.
- Updated the `codex-wake` skill to point agents at version/readiness checks,
  product smoke, and the support boundary.

### Slice 6: v0.5.0 Release

Cut the productization release only after the install and smoke story is
operator-repeatable.

Acceptance criteria:

- Package version, release notes, README install examples, and plugin metadata
  name `v0.5.0` or the selected productization release version.
- Source tests, package build, installed-wheel smoke, plugin tests, and plugin
  no-shell scan pass.
- Public tag install smoke validates the CLI and supervisor from GitHub.
- OpenClaw plugin install/update smoke validates the non-linked plugin path.
- User-scoped `uv tool` install is refreshed from the public tag.
- The user supervisor remains active and monitor-ready after the refresh.
- GitHub release, CI run ids, live wake ids, and runtime status are recorded
  under `docs/dev/verification/`.

Progress 2026-05-26:

- Bumped package and OpenClaw plugin metadata to `0.5.0`.
- Added `docs/releases/v0.5.0.md`.
- Committed productization release candidate as
  `64627ab7217c4eab232127ed3d388d46964b9e39`.
- Tagged and pushed `v0.5.0`.
- GitHub Actions run `26450020574` passed release gates on Python 3.11 and
  3.12.
- Published GitHub release
  `https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.5.0`.
- Public-tag product smoke from GitHub reported `cli_version=0.5.0`,
  `schema_version=1`, and `supervisor_once_roots=1`.
- Refreshed user-scoped `uv tool` install from the public tag.
- Restarted `codex-wake-supervisor.service`; the repo wake root remained
  monitor-ready through supervisor health.
- Updated the OpenClaw plugin from the public tag; Gateway runtime reports
  plugin version `0.5.0`, `codex_wake_schedule`, and zero diagnostics.
- Verification is recorded in
  `docs/dev/verification/0069-2026-05-26-v050-release.md`.

## Bounded Definition Of Done

P43 is done when:

- the OpenClaw plugin has a durable public install/update path that does not
  require `openclaw plugins install --link ./plugins/openclaw-codex-wake`;
- installed readiness can be inspected from a single documented command or
  command sequence;
- state cleanup and supervisor root lifecycle are documented and validated;
- a repeatable smoke matrix proves installed CLI, supervisor, Codex
  app-server, and OpenClaw Gateway behavior;
- the `codex-wake` skill and operator docs reflect the productized path;
- `v0.5.0` or the selected productization release is tagged, published, and
  public-install-smoked;
- `ROADMAP.md`, `RUNBOOK.md`, and `docs/dev/verification/` record the closeout
  evidence.

Closeout 2026-05-26: all DOD items are satisfied by verification records
`0063` through `0069`.

Explicitly out of bounds for this DOD:

- PyPI or npm publication unless chosen as the plugin distribution mechanism;
- additional trigger classes;
- a database-backed wake store;
- remote multi-user service deployment;
- fully automated CI for live Slack/OpenClaw/Codex app-server smokes that
  require local credentials.

## Validation Plan

Minimum source validation:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q src tests .codex/hooks
python -m py_compile scripts/product_smoke.py
npm --prefix plugins/openclaw-codex-wake test
node --check plugins/openclaw-codex-wake/index.js
node --check plugins/openclaw-codex-wake/lib/scheduler.js
git diff --check
```

Minimum installed/runtime validation:

```bash
uv tool install --force --reinstall git+https://github.com/CochranResearchGroup/codex-wake.git@<tag>
uv tool list | rg 'codex-wake'
codex-wake --wake-root .codex/wake doctor --json
codex-wake --wake-root .codex/wake monitor check --json
codex-wake supervisor status --all --json
python scripts/product_smoke.py --json
openclaw plugins inspect codex-wake --runtime --json
openclaw gateway status --require-rpc --json --timeout 180000
```

Live release evidence must include:

- one Codex app-server wake fired through the installed monitor path;
- one OpenClaw Gateway wake fired through the installed monitor path;
- Slack, transcript, app-server turn, or equivalent readback for any
  human-visible delivery claim;
- a final clean wake-root status with no active or terminal records left from
  dogfood.
