# #534 installed terminal-session acceptance

State: IN PROGRESS; no tracker closure or review performed. The primary owns
integration, the final affected Python3.11/3.12 selection and tracker readback.
Memory disposition: forbidden (delegation prohibits memory writes).

Named public seams: installed CLI, real SDK stdio MCP, authenticated HTTP/API,
OAuth MCP and the actual Windows portable CLI invoked by native PowerShell.
Private tmux/psmux namespaces contain inert commands only. No real profile,
provider, production session, stock harness or codex-bots launcher was touched.

## Retained first failures

- Native public formatter enable → session rename → rollback raised stale_target.
  `native-rename-red.*` retains RED. Source97cad23 transfers only an exact old
  formatter identity to the verified same Windows server/process births under
  the formatter lock. Original baselines/policy/manual holds remain intact.
  `native-rename-green.*` proves exact original rollback, pane continuity and peer
  preservation. The separate close-response failure is retained in
  `native-rename-close-firstfailure.*`; final presence probes showed no owned
  native names remaining. No blind native close replay was used.
- `installed-firstfailure.log` is a qualification input error: tabs.create omitted
  its required --name. A fresh private namespace with --name inert-worker passed;
  this did not require a source change. Each failed namespace was destroyed before
  the corrected new intent.
- `multitab-undo-firstfailure.log` exposed a product defect: undoing two tabs into
  a rematerialized empty original session restored one then skipped the other.
  The primary's0c87ae3 propagates the verified native successor to all references
  and suppresses saved launch commands during relocation bootstrap. Both tabs
  undo successfully on the second wheel.
- `uncertain-exit-firstfailure.log` exposed an uncertain native move reported as
  top-level held with exit0. The private PATH fault helper failed exactly one
  native move command without changing placement. Resolution is pending.

## Package provenance

`build-first.json` binds source3699f68 to wheelaf2f6ea55afe799c7964b43afa2d3d5cb2a44227693951f91de87f5b8f2dc630.
It is invalidated for acceptance by the subsequent product fix.
`old-wheel-transport-diagnostic.json` is explicitly DIAGNOSTIC_ONLY; it confirms
independent transports but substitutes an exact native return for the broken
second undo and cannot establish the complete workflow.

`build-second.json` binds source0c3794a to second wheel
7f5945f15f423791452295e7cc7390893d35c43353d96395b5031d383780442d.
It is blocked by the uncertain-exit failure and will be superseded after repair.
The build used setuptools84.2.1, wheel0.48.0 and SOURCE_DATE_EPOCH1794244632;
all Python members matched source and the private Linux install byte-for-byte.
Dependency constraints came from the qualified formatting0210 deployment packet.
No global package install occurred.

## Execution

```sh
SOURCE_DATE_EPOCH=1794244632 /tmp/wake534-builder/bin/pip wheel --no-build-isolation --no-deps --wheel-dir /tmp/wake534-final-package .
/tmp/wake534-final-installed/bin/pip install -c ~/.local/state/codex-wake/formatting-0210-deploy/constraints.txt '/tmp/wake534-final-package/codex_wake-0.22.0.dev2-py3-none-any.whl[mcp]'
env -u PYTHONPATH /tmp/wake534-final-installed/bin/python scripts/terminal_session_acceptance534.py --output /tmp/wake534-final-result.json --wheel /tmp/wake534-final-package/codex_wake-0.22.0.dev2-py3-none-any.whl --windows-python /mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe
```

The second command installed constrained dependencies successfully; the third
passed strict bulk undo and stopped at the uncertainty exit gate. Owned tmux
servers/monitor/listener were cleaned on each failure. Original logs remain in
/tmp/wake534-* and the named failures are retained here.

## Boundaries

Local FOCUSED checks replace paid hosted CI. This is WSL/Linux hosting plus a
native Windows portable caller and independent psmux CRUD qualification; it does
not prove Windows-native service hosting or cross-server psmux movement.
The full repository suite and provider tests are excluded. The primary runs the
combined affected PRESUBMIT selection separately. No broad Standards/Spec review,
remediation-pass counter, merge, release, deployment or memory effect occurred.
