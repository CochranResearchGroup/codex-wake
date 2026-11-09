# Plan 0211 review R3 — one bounded TDD findings pass

Base: `2e8896b7029bf6e6f140314e6e06f6bcac6fe80b`, branch `fix/session-review-psmux`, issue #526. Accepted R3 only; no second review, trackers, memory writes, package build, deployment, or provider calls. Final source hashes: `source.json`.

Public behavior: `ControllerTabs.execute('tabs.session.update', changes={'defaults': {'cwd': WindowsAbsoluteDirectory}})` accepts Windows absolute syntax independently of the Linux filesystem. Native existence remains a Windows bridge check. `open` passes only bounded finite cwd JSON to host-approved `session_create`; inherited cwd applies to new tabs through the existing defaults resolver/create bridge. Existing sessions/tabs are preserved on ensure/default updates. tmux/Byobu retain local absolute/existing directory validation. Opening unknown prior intent remains held with no replay.

Generic psmux argv defaults are explicitly unsupported and refused before registry mutation. Existing persisted argv/profile defaults are also refused before open. Windows account/profile launch remains unqualified, with no shell fallback. Native trial showed session creation preserves argv but running-server new-window truncates a semicolon; a quoting trial did not launch. Those first failures are retained and argv extensions were removed. No arbitrary bridge actions or executable selection were added.

Focused local commands (each under `PYTHONPATH=src`, both `python3.11` and `python3.12`):

- `-m unittest discover -s tests -p test_terminal_session_psmux.py`: initial red existing-directory error retained in red311/red312; final green 5 tests each.
- `-m unittest discover -s tests -p 'test_tab_psmux*.py'`: 7 passing each.
- `-m unittest discover -s tests -p test_terminal_sessions.py`: 8 passing each.
- `-m unittest discover -s tests -p test_tab_lifecycle.py`: 8 passing each.
- `git diff --check`: passing.

These are focused selections, not the full suite. Local Python checks substitute for hosted CI; Windows native check used source files, not a wheel. No hosted runs were enabled. Discovery initialized the worktree's ignored CodeGraph index.

Native command: `PYTHONPATH=src python3.12 docs/dev/evidence/plan0211/review-r3/native_acceptance.py`. Windows Python: `C:\Users\ecoch\AppData\Local\codex-wake-test\controller405-20261030\venv\Scripts\python.exe`. Source-exact standalone bridge hash `9ca6c21f4666d9f7e96533237a23a51a72179af2968fba9d5e88646263dbc3f7`; psmux executable pinned to `bbe825a30f7cddc91b043084049143a381aba5f7e9e36e4d0bb587e296d262ca`.

Final `native.json`/`native-green.log`: passed update(cwd) → open → ensure reuse → public new-tab inherited cwd → rename with pane/process-birth continuity → exact formatting rollback → restart restore → termination/name reuse → peer unchanged. Cwd readback comes from actual native pane-current-path snapshots, independent of stored defaults. First two native harness target lookup errors, actual argv truncation, and failed quoting launch remain in named firstfailure/argv-red/quoting-failure artifacts; each managed namespace was reconciled absent before the next run.

Fresh OS census found active native `__warm__` psmux servers and descendant pwsh/conhost processes left by native psmux even after managed names were absent and their servers exited. `cleanup-firstfailure.json` preserves that evidence. Hash-pinned `kill-session -t __warm__` failed (`warm-cleanup.json`); no blind repetition. Bounded cleanup then opened handles for only exact namespace-matched psmux servers plus their snapshot descendants, verified the server image hash, retained process creation FILETIMEs, terminated owned handles, and read exit codes (`cleanup-termination.json`, `native_cleanup.py`). All 30 owned processes exited. Fresh `native_census.py` output `cleanup-census.json` distinguishes exited retained objects from active processes via GetExitCodeProcess and confirms no active matches. No production/unrelated namespace was targeted. This native warm-server lifecycle caveat is not repaired in this bounded source change.

Memory disposition: `forbidden` — assignment explicitly prohibits memory writes. Parent owns integration and one post-review package rebuild/qualification. Cwd is qualified; generic argv and Windows selected-profile launching remain unsupported.
