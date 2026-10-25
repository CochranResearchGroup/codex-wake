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
