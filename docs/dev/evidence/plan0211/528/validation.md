# #528 delegated selector implementation

Source base: `bfff13c`; branch `feat/session-selectors-528`.
Worker: `/root/selectors528`; owned implementation is tab_selection.py,
tab_views.py and their focused tests. Integration, portable contract and CLI
adapters remain with the coordinator. No provider, hosted CI or tracker effects.

Public seams: `tab_selection.select/validate` cover bounded Boolean selection
and qualified trait uncertainty. `ControllerTabs.execute` saved group/view
operations cover persistence and evaluation using synthetic inventory from an
injected public `tabs.list` fixture. This does not qualify installed runtime.

Expression supports all/any (1..32 children), not, trait eq/pattern/unknown:true,
group names, label names and explicit tabs [{id,identity}]. Maximum depth 8,
256 expression nodes, 512-character predicate values, 4096 explicit pins.
Unknown is a third value through Boolean composition; only true is selected.
Observed literal unknown, missing, stale and unavailable traits are unknown.
Custom labels belong to saved groups (max 32); their memberships retain the
existing platform-aware process-birth pins. Named legacy views still work.

## Red/green

Commands run from this worktree with `PYTHONPATH=src`:

- `/tmp/codex-wake-p210-py312/bin/python -m unittest discover -s tests -p test_tab_selection.py`
  Red: module import missing. Green: 1 passed, then 3 passed after additional
  bounds and missing/unavailable observation regression verification.
- `/tmp/codex-wake-p210-py312/bin/python -m unittest discover -s tests -p test_tab_views.py`
  Red: public controller group-save rejected labels. Green: 4 passed,
  including persisted custom categories, explicit pins, group union and process
  replacement exclusion after reconstructing the controller.
- Initial pytest probe failed because pytest is absent; switched to the
  repository's standard unittest runner without installing dependencies.
- `/tmp/codex-wake-p210-py312/bin/python -m ruff check --select F821,F822,F823 src/codex_wake/tab_selection.py src/codex_wake/tab_views.py tests/test_tab_selection.py tests/test_tab_views.py`: passed.
- `git diff --check`: passed.

Hosted GitHub CI intentionally skipped under repository cost policy. Local
Linux CPython 3.11/3.12 environments replace GitHub ubuntu-latest setup-python;
this lane does not claim a complete hosted release-gates equivalent, package
installation, live runtime or CLI/API/MCP adapter acceptance.

Memory disposition: `forbidden` — delegated packet explicitly prohibits memory
writes. Coordinator owns final acceptance, shared adapters and integration.

Broader affected selection (already running before coordinator requested no
further expansion):

- `PYTHONPATH=src /tmp/codex-wake-p210-py311/bin/python -m unittest discover -s tests -p 'test_tab*.py'`: 145 tests passed, 98.489 seconds.
- `PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest discover -s tests -p 'test_tab*.py'`: 145 tests passed, 100.859 seconds.

No retries or additional broad runs. Expected argparse rejection text appeared
in parser negative tests; both complete selections exited zero.
