# #408 existing native checkpoint correction

This evidence packet supersedes the provisional native protocol assumption in
`fork408-installed.json`. The original receipt remains historical evidence; it
never qualified an actual native build. Planning and closure authority remain
#408 under specification #393 and the primary agent's integration lane.

## Qualified behavior

Wake selects the last completed turn from full, persisted, non-ephemeral source
history. The opaque checkpoint binds account/process/build/profile target,
selected turn ID, and a bounded canonical digest of the complete retained turns.
It sends existing `thread/fork` with `threadId`, inclusive `lastTurnId`, `cwd`, and
`ephemeral:false`. No invented checkpoint ID, server advertisement or native
provenance response is used. Before exposing a child for prompting, Wake reads
its full history and verifies retained IDs, order, items, and terminal prefix.
Later source turns are excluded. Source-prefix changes, duplicate child IDs, and
failed verification retain uncertainty without replay or child-revert fallback.
Authorization is checked immediately before the fork after source observations.

Existing native goals, including terminal goals, are unsupported here. Each
source/child history observation must be accompanied by supported
`thread/goal/get` returning exactly `{"goal":null}`. Disabled/unavailable or
unknown goal state fails closed; it is not proof of absence. The pinned source
`ThreadForkParams.defer_goal_continuation` documents carrying a goal without its
initial automatic continuation; processor `thread_processor.rs:5679` gates the
explicit goal flush/inherit/restore branch on that setting. Neither this
accounting path nor ordinary goal-bearing fork startup is qualified by this
packet. No goal set, clear, defer, resume, allowance or renewal operation is sent.
A no-allocation result therefore follows observed goal absence at source and
child, not merely controller intent.

## Red/green receipts

Public seam: `ControllerFlowSessions.execute`, backed by deterministic native
transport fixtures; installed flow entrypoints exercise the same owner.

```
PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p test_controller_flow_fork.py -v
```

Initial correction red: 4 tests, 3 errors against the provisional capability
requirement. Green: 4 tests. Extended malformed/changed child and persisted
checkpoint cases then passed. Revocation red: 8 tests, 1 failure (fork occurred
after source-read revocation), preserved in `/tmp/fork408-guard-red.txt`; the
immediate-effect guard fixed it. Goal red: 9 tests, 4 subtest failures (existing or
unknown goal still forked), preserved in `/tmp/fork408-goal-red.txt`; explicit
absence checks fixed it.

Final validation:

```
PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p 'test_controller_flow*.py' -q
PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p test_shared_app_server.py -q
```

30 flow tests and 10 shared transport tests pass. This is routine focused
validation; the primary's final broad Standards/Spec review remains outstanding.

## Installed qualification

Source code freeze: `a31fe79` after `a12ca06` and `ec20a11`. Build/install:

```
uv build --wheel --out-dir /tmp/fork408-goal-final-wheels
uv pip install --reinstall-package codex-wake --python /tmp/codex-wake-fork408-installed/bin/python /tmp/fork408-goal-final-wheels/codex_wake-0.22.0.dev2-py3-none-any.whl
env -u PYTHONPATH /tmp/codex-wake-fork408-installed/bin/python scripts/controller_fork_acceptance.py
```

Wheel SHA256:
`e840dfd06d6f806a97870252dbcb1e927549a9ca44a5e146e66bf1e154e2d47a`.
The last command uses installed CLI executables, actual OAuth HTTP operation and
HTTP MCP, installed remote CLI executable, and installed stdio MCP. The real
Unix peer is a deterministic protocol fixture, with no invented native fields.
All five surfaces passed. Raw receipt:
`/tmp/fork408-goal-final-entrypoints.json` (stderr empty).

The separate actual native package qualification used:

```
env -u PYTHONPATH /tmp/codex-wake-fork408-installed/bin/python scripts/controller_fork_native_acceptance.py --package /tmp/health390-native-package --models /tmp/codex-native-390/codex-rs/models-manager/models.json --artifacts /tmp/fork408-native-goal-final
```

The manifest-selected CLI SHA256 is
`f1775c5dd0a1c450a6eec2c76b2f35c5197b0d3df7e9eb2cfb156bdfb403d448`,
source `95cd89dd5f3cddeb241a9de75a3cc255a9484606`. Complete package includes
its code-mode helper, rg, bwrap, resources and package manifest. This packet
reused that owner-qualified package without modifying/building it or invoking
bare PATH. Its runtime was private, with fresh HOME/CODEX_HOME/XDG roots and an
owned Unix socket verified by SO_PEERCRED.

Canonical synthetic SessionMeta, TurnStarted, user/agent message and completed
records were consumed by the actual native parser. Wake selected a two-turn
checkpoint, then fixture setup added a third completed source turn. Two actual
native forks each retained precisely the original two-turn prefix, including
IDs/order/items. Source bytes remained unchanged. Seven native goal readbacks
reported absence. No `turn/start` was called. Four startup metadata CONNECTs
were blocked by the local 503 trap; no provider/model request or turn occurred.
Owned daemon exited 0 and its PID was absent afterward. Raw native responses,
fixture history and logs remain outside Git under `/tmp/fork408-native-goal-final`.
Earlier failed harness setup/assertion runs remain outside Git; the final run
above is the qualification receipt. Curated summary is
`docs/dev/evidence/plan0190/fork408-native-correction.json`.

## Limits and handoff

This qualifies the existing primitive and no-goal fork path, not goal inheritance,
compressed/synthetic-ID history, arbitrary native builds, provider outputs, live
session mutation, production activation or aggregate #411 completion. The
checkpoint is bounded to 1 MiB; missing full items refuse. Readback checks do not
claim a global transaction against unrelated concurrent native writers. No
service restart, live account/credential use, native rebuild or resource
allocation/renewal occurred. Primary integrates, verifies, and closes #408.
