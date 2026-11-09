# Single review remediation: R2, R3 and R4

Frozen remediation base:58b163177e545ce97436f61adf78d89a00debd2c.
This packet belongs to the primary's existing broad review1 and remediation1.
No new review, full suite, native colour matrix or tracker mutation was run.

## R2: current linked windows remain held during rollback/reset

Public seam: ControllerTabs over a real private tmux server. Two independent
regressions enable formatting in workspace a, then link its already-decorated
source window into session b after baseline capture. Rollback and reset each
must return partial/linked_window without changing the shared window's options,
name or pane PID. The ordinary unlinked window and session originals restore;
the source baseline remains durable and automatic decoration is disabled.
After explicit unlink, retry restores the saved originals successfully. The
second session's anchor name/window/PID remains unchanged throughout.

RED command:
`PYTHONPATH=src /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest discover -s tests -p test_tab_format_linked_rollback.py -q`
Both tests failed before the fix: rollback/reset reported complete success.
The same command passed both tests after the guard. Raw red/green results are
retained beside this receipt. Bare injected owners are passive; no monitor or
provider work starts. Each fixture kills only its private socket server.

The restore loop now retains current window metadata and rejects a currently
linked saved window before the formatting write. Other ordinary restoration and
session restoration paths remain unchanged. Native psmux linked metadata and
cross-session capability claims were not altered.

## R3: remove unused apply parameter

Removed unused automatic keyword parameter and its sole internal keyword call.
Explicit and monitor-driven application still share the same owner path. No new
mechanical test was added; focused existing formatting behavior checks cover it.

## R4: standalone immutable finite vocabulary

Defined immutable session/window managed-option tuples once in the stdlib-only
native bridge and reused them in validation and read/write paths. No imports,
allowed names, argument shapes, value limits, framing or Windows identity logic
changed. Canonical tuple equality against the portable transport vocabulary
passed. Existing finite native-protocol tests passed. No Windows job was needed
for this pure vocabulary change, as agreed with the primary.

## Focused validation

Python3.12 shared repository .venv (same pinned dependencies as qualification):
- `PYTHONPATH=src .../.venv/bin/python -m unittest discover -s tests -p 'test_tab_format*.py' -q`:33passed,22.720s.
- `PYTHONPATH=src .../.venv/bin/python -m unittest discover -s tests -p 'test_tab_psmux*.py' -q`:7passed.
- `PYTHONPATH=src .../.venv/bin/python -m unittest discover -s tests -p test_tab_contract.py -q`:5passed.

These are focused affected selections, not a full-suite claim. The monitor
readiness test repair is owned separately by the primary; its combined final
validation follows integration rather than being claimed by this worker.

Python3.11 named linked/native-protocol/projection/rendering/core/contract result
is recorded in validation.json. No failed run was silently retried or erased.
Memory disposition: forbidden; this delegated packet prohibits memory writes.
