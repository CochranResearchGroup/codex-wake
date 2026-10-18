# Control and accounting repair validation

Scope: issue289's bounded source repair, not completed automatic provisioning.

- Focused source:30 tests PASS in3.969s using `PYTHONPATH=src:tests
  /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest
  test_goal_limits_mcp test_goal_supervision test_goal_usage -q`.
- Isolated installed: `uv build --wheel --out-dir /tmp/cw289-wheel`, install the
  resulting wheel with mcp extras into `/tmp/cw289-installed`. This candidate is
  labelled0.17.3 solely for local validation, not a release/tag replacement.
- Installed public MCP/CLI/independent-watcher qualification: candidate Python
  runs scripts/goal_supervision_qualification.py with fresh output directory,
  and separately with --unknown-accounting. Both PASS; compact hash-bound receipts
  installed-fresh.json and installed-grace.json retain results. Injected owned
  Unix native protocol, configured trusted clock, zero model calls; no production
  conversation or endpoint was used. Exact watcher PIDs absent after exit0.
- Old editable main interpreter against updated qualification failed5040tokens
  at initial enrollment, proving the installed seam distinguishes fresh defaults.
- Presubmit candidate:1369 tests,76 failures,4errors,1skipped,127.152s, exit1.
  Full log `/tmp/cw289-presubmit-20261018/unittest-owned.log`. No retry erasure.
  Baseline unchanged main comparison pending; selected baseline time tests show
  11failures/3errors out of23. No release-ready or full-suite pass claim.
- `python scripts/check_policy_wiring.py`: PASS; compileall source/tests/hooks:PASS.
- Active planning audit:0169 format repaired; pre-existing0166/0167/0168 state
  metadata findings remain. No unrelated policy/plan edits made.
- Bounded source review: review.md, no candidates, no independent live acceptance.

Unexecuted: native real-client operator exchange, production install/release,
verified automatic provisioning/continuity, host-delegated policy migration.
No host grants, counters, shared MCP connections or services were changed.


Baseline comparison completed: unchanged main89e3eb81a63ff26589860e58e6526c0462107dc7
ran1363tests in124.088s and failed76 plus4errors,1skipped, exit1. Candidate adds6tests;
all80 failure/error identifiers match baseline exactly, no candidate-only failure.
Comparison receipt: presubmit-comparison.json. This distinguishes existing local
suite failures from this repair; it does not waive CI or establish a clean suite.
