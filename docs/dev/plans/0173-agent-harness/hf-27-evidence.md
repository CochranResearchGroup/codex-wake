# HF-27 implementation evidence

Issue #340, branch feat/340-dashboard-overview, base 2a51dd2.

Spec frozen before implementation in hf-27-spec.md. Operator decision was terminal
first and explicit existing-only focus, form d9b59f368e984dff925597304f90e901.

Red: `PYTHONPATH=src python -m unittest discover -s tests -p 'test_operator_overview.py'`
failed importing the absent public owner. Green: same command passed first behavior.
Second red: expired binding reached session source; green after fail-closed binding
check. Public command integration initially could not import websockets in bare
Python; use declared project environment instead.

Final targeted command: `uv run python -m unittest discover -s tests -p 'test_operator_overview*.py'`
passed five tests. This includes disposable verified operator capability, policy
deny then allow, real owned private tmux pane selection/readback, live process
identity, and native protocol fixtures through RuntimeStateObserver and sessions
readers. Additional cases cover budget exhaustion, truncation, unavailable evidence,
unsupported capability display, no-policy/model focus denial, stale binding and changed native namespace holding focus without moving the selected pane.
Adjacent observation regression: `uv run --extra mcp python -m unittest discover -s tests -p 'test_agent_observation.py'` passed all ten tests. A first run without the declared MCP extra failed only on missing jsonschema; the configured-extra rerun passed.

No production/provider/installed service reads or effects, no shared caller edits,
no CI, no broad review or globally reserved final TDD pass. Primary must wire agents
parser/dispatch and read-only MCP calls, then verify those integrated public hubs.
The terminal effect selects a pane/window in its existing session; it does not
switch an unrelated attached client across sessions. Git identity remains explicitly
uninspected. The inventory owner's blocking file lock is not preempted by the
runtime scan deadline. These are explicit limits, not completed broader claims.

Memory disposition: forbidden; delegated packet explicitly prohibits memory writes.


## Original-criteria integration correction

A bounded correction replaces the initial Git-uninspected placeholder with actual
canonical common-directory device/inode and worktree identity. Git environment
poisoning is removed and tested; failed reads stay unknown. The initial pane-only
effect is corrected to qualify the invoking or explicit owned client tty and switch
that existing client to the exact existing target session before pane selection.
An actual PTY-attached private client begins in another session; client-session and
pane readbacks pass, session population remains unchanged, and namespace drift still
holds. Client process is reaped and the private server terminated by fixture cleanup.

`uv run --extra mcp python -m unittest discover -s tests -p 'test_operator_overview*.py'`
passes six tests after correction. Earlier no-cross-session/Git-uninspected limits
above describe the superseded checkpoint only. Remaining limit: inventory flock is
not preempted. No production/provider/global review or shared-file effects.
