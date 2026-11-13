# Ticket 604: family display

Source base ee592e5dfbf7e1dc3bedc1463845ad90aed43557. This receipt belongs to its containing commit.

Account/task scope, name and reference enter existing normal, compact, preset and
plain tab formats. Native #W stays present. Root-ID SHA-256 selects muted accents;
current error, health warning and waiting styles retain precedence. Existing
reversible formatting owns pause, opt-outs, manual holds and rollback baselines.
Monitor formatting requalifies exact bindings and includes family metadata in its
projection key; binding loss removes labels. Family-active observations bypass
trait-only revision shortcuts. No Bot availability, lifecycle or provider effects.

Focused checks:
- Red: PYTHONPATH=src python -m unittest discover -s tests -p test_bot_family_display.py:
  both tests failed on missing visible family labels. Green: 2 passed after fix.
- uv run --extra dev python -m unittest discover -s tests -p test_tab_format_monitor.py:
  12 passed in 2.190s, including disposable native tmux rendering/rollback.
- PYTHONPATH=src:tests uv run --extra dev python -m unittest test_bot_family_display test_tab_format_monitor test_tab_format_rendering test_tab_formatting test_tab_format_presets test_tab_format_scope test_tab_format_policy test_tab_format_compact test_tab_format_projection test_tab_format_linked_rollback:
  73 passed in 27.473s.
- After extending binding-loss coverage: PYTHONPATH=src:tests uv run --extra dev python -m unittest test_tab_format_monitor.FormattingMonitorTests.test_monitor_family_overlay_is_bound_and_rollback_remains_effective test_bot_family_display:
  3 passed in 0.304s.

No retries or hosted CI. System Python lacked msgspec; uv provisioned declared deps.
Attempted pytest could not start because pytest is not declared; unittest supplied
actual validation. Linux/Python 3.12/native tmux; Windows/psmux pixels, installed
runtime and live providers were not exercised.
Memory disposition: forbidden, coordinator prohibited worker memory writes.
