# Preserved qualification failures

CI38802564058 passed unit tests in both Python versions, then failed installed
MCP compatibility smoke at scripts/a2a_mcp_smoke.py:96, assert len(discovered)==19.
New catalog correctly contains25 tools. Updated expected count and required six
control tool names; same installed smoke rerun, no product/runtime behavior change.
Failed run retained at GitHub Actions38802564058; raw local failure log retained
at /tmp/p164-mcp-compatibility.err and original CI excerpt /tmp/p164-ci-failure.log.

Initial new private qualification harness used obsolete result.isError attribute;
SDK2.2 exposes is_error (wire field stays isError). Corrected harness attribute,
no product change. Raw /tmp/p164-installed-qualification-initial-harness-failure.log.
Initial daemon fixture wrote one once-health receipt under default state directory;
qualified rerun isolates XDG_STATE_HOME in its temporary fixture root. Any owned
initial health receipt is reconciled separately; no shared worker was started.
