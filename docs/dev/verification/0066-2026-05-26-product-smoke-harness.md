# Product Smoke Harness Verification

Date: 2026-05-26

Plan: `docs/dev/plans/0043-2026-05-26-productization-completion.md`

## Scope

Verify P43 Slice 4 implementation work: a repeatable product smoke harness,
documented cross-runtime smoke matrix, CI-installed-wheel smoke coverage, and
safe supervisor no-dispatch polling.

This record verifies the harness and safe installed-surface smoke. Fresh live
Codex app-server and OpenClaw Gateway smokes through the harness remain release
evidence for the `v0.5.0` closeout. Prior live supervisor-fired evidence is in
`docs/dev/verification/0062-2026-05-26-wake-monitor-readiness-user-supervisor.md`.

## Implementation

Added:

- `scripts/product_smoke.py`
- `docs/product-smoke-matrix.md`
- `codex-wake --version`
- `codex-wake supervisor run --once --no-dispatch`

The safe smoke verifies installed, non-source CLI surfaces:

- `codex-wake --version`
- `codex-wake schema --json`
- `codex-wake product-readiness --json`
- `codex-waked --once --no-dispatch`
- `codex-wake monitor check --json`
- `codex-wake supervisor run --once --no-dispatch --json`

The harness also has opt-in live paths for:

- Codex app-server wake with a real thread id
- OpenClaw Gateway wake with a real agent/session key

Tmux is explicitly recorded as `manual_only` unless pane visibility evidence is
captured by the operator.

## Safe Installed-Wheel Smoke

Built the package and installed the wheel into a temporary virtualenv, then ran:

```bash
python scripts/product_smoke.py \
  --codex-wake-bin "$tmp/venv/bin/codex-wake" \
  --codex-waked-bin "$tmp/venv/bin/codex-waked" \
  --artifact-dir .codex/wake/smoke/0066-installed-wheel \
  --json
```

Summary:

```text
artifact_dir=/home/ecochran76/workspace.local/codex-wake/.codex/wake/smoke/0066-installed-wheel
cli_version=0.4.15
schema_version=1
monitor_ready=false
supervisor_once_roots=1
tmux_status=manual_only
```

`monitor_ready=false` is expected for the isolated safe smoke because it uses
temporary XDG state and does not start a persistent monitor. This proves command
execution and structured output, not unattended delivery.

## Live Readiness Snapshot

Current workstation readiness from source:

```text
overall_status=warning
app_server=ready :: service unit sets CODEX_WAKE_CODEX_CMD
cli=ready :: required CLI commands are installed
hooks=warning :: codex-wake-hook is installed in both project and user hook sources; Codex may run both and inject duplicate wake context.
monitor=ready :: an active monitor owns this wake root
openclaw_gateway=ready :: OpenClaw Gateway RPC is ready
openclaw_plugin=ready :: OpenClaw codex-wake plugin is active
repo_service=warning :: repo-scoped service is not active
skills=ready :: codex-wake skill is installed
supervisor=ready :: codex-wake supervisor is active and this wake root is enrolled
tmux=ready :: current shell has tmux target environment
supervisor_root=codex-wake-98975473 health_status=ready remediation=
```

The warnings are expected for this workstation state: both project and user
hook sources are installed, and the user supervisor owns the root while the
repo-scoped service is inactive.

## Source Validation

Passed:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
# Ran 155 tests - OK

python -m compileall -q src tests .codex/hooks
python -m py_compile scripts/product_smoke.py

npm --prefix plugins/openclaw-codex-wake test
# tests 12, pass 12

node --check plugins/openclaw-codex-wake/index.js
node --check plugins/openclaw-codex-wake/lib/scheduler.js

git diff --check
```

The OpenClaw plugin no-shell scan also passed:

```text
no unsafe child_process imports or spawn/execFile calls found
```

## Known Gap

P43 remains open. Fresh live app-server and OpenClaw Gateway smokes must be run
through `scripts/product_smoke.py` or the documented matrix before the
productization release is closed. A public-tag smoke cannot be run for these
new harness features until the `v0.5.0` tag exists.
