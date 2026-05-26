# Operator Docs And Support Boundary Verification

Date: 2026-05-26

Plan: `docs/dev/plans/0043-2026-05-26-productization-completion.md`

## Scope

Verify P43 Slice 5: operator documentation and agent guidance now provide one
canonical path from public install to monitor-ready state, and unsupported
cases are explicit.

## Documentation Updates

Updated:

- `README.md`
- `docs/daemon-service.md`
- `docs/support-boundary.md`
- `docs/product-smoke-matrix.md`
- `plugins/openclaw-codex-wake/README.md`
- `skills/codex-wake/SKILL.md`

The README now has a public-install quickstart covering:

- `uv tool install` from a public Git tag
- user-scope hook install/check
- user supervisor install/enroll/status
- monitor readiness
- product-readiness
- product smoke harness
- OpenClaw Gateway auth import for user-systemd supervisor delivery

`docs/daemon-service.md` now includes repo-service versus user-supervisor
selection guidance and marks `--no-dispatch` as polling/state evidence only.

`docs/support-boundary.md` defines supported product paths, manual-only cases,
required transport-specific evidence, no-dispatch false positives, placeholder
identifier failures, tmux visibility limits, linked-plugin install limits, and
cleanup boundaries.

The OpenClaw plugin README now points operators to product-readiness checks and
rejects linked paths, placeholder sessions, and no-dispatch smokes as durable
delivery evidence.

The `codex-wake` skill now points agents to `codex-wake --version`,
product-readiness, the product smoke harness, and `docs/support-boundary.md`.

The updated skill was synced and diff-checked across:

- `skills/codex-wake/`
- `/home/ecochran76/.agents/skills/codex-wake/`
- `/home/ecochran76/.codex/shared/skills/codex-wake/`
- `/home/ecochran76/.openclaw/skills/codex-wake/`

OpenClaw skill visibility after sync:

```text
source=agents-skills-personal
filePath=/home/ecochran76/.agents/skills/codex-wake/SKILL.md
eligible=true
modelVisible=true
commandVisible=true
```

## Validation

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

The OpenClaw plugin no-shell scan passed:

```text
no unsafe child_process imports or spawn/execFile calls found
```

Version smoke:

```text
codex-wake 0.4.15
```

Installed-wheel product smoke was rerun after the docs update:

```text
cli_version=0.4.15
schema_version=1
supervisor_once_roots=1
```

Artifact directory:

```text
.codex/wake/smoke/0067-installed-wheel
```

Live product-readiness snapshot:

```text
overall_status=warning
app_server=ready
cli=ready
hooks=warning
monitor=ready
openclaw_gateway=ready
openclaw_plugin=ready
repo_service=warning
skills=ready
supervisor=ready
tmux=ready
```

The warnings remain expected for this workstation: duplicate project/user hook
sources and inactive repo-scoped service while the user supervisor owns the
wake root.

## Known Gap

P43 remains open. Fresh live Codex app-server and OpenClaw Gateway smoke
evidence and the `v0.5.0` release are still required.
