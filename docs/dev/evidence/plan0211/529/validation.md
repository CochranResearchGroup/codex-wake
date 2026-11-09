# #529 native psmux session lifecycle

Source baseline e639397, branch feat/terminal-session-529. This checkpoint adds
finite host-selected namespace create/probe, pinned native rename, durable bridge
recovery, psmux namespace inference and backend-specific absence checks. Cross-session
whole-window moves remain unsupported. Saved empty definitions launch nothing.
psmux launch defaults require a qualified profile launcher and fail explicitly;
this lane does not introduce arbitrary shell/argv forwarding.

Public seam: ControllerTabs.execute tabs.session.create/list/show/update/open/delete.
TDD red: `PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest tests.test_terminal_session_psmux -v`
failed the missing-namespace refusal assertion before implementation (1 failed,
1 passed). The same command passed after the minimal namespace fix (2 passed).

Focused final checks:

- `PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python -m unittest tests.test_terminal_session_psmux tests.test_terminal_sessions -v`: 6 passed, 0.613 seconds.
- Same command with `/tmp/codex-wake-p210-py311/bin/python`: 6 passed, 0.534 seconds.
- `git diff --check`: passed.

Native qualification command:
`WSL_INTEROP=/run/WSL/1_interop PYTHONPATH=src /tmp/codex-wake-p210-py312/bin/python /tmp/qualify529.py`
The exact retained harness is native_acceptance.py. Native receipt native.json
records eight passed checks against existing installed Windows psmux, executable
SHA256 bbe825a30f7cddc91b043084049143a381aba5f7e9e36e4d0bb587e296d262ca.
The WSL public owner runs source modules; native Python executes a source-exact
copy of tab_psmux_bridge.py. No package install, native rebuild, provider work,
production process changes or hosted CI occurred. This proves source/public-owner
plus native runtime behavior, not installed-package CLI/API/MCP parity.

Owned namespace wake529-36768fbc5b0c contained seed, bots and renamed workers.
Process births stayed unchanged across rename; the peer server stayed unchanged.
Owner restart restored the saved generation. Populated deletion refused; last-tab
close retained an empty definition; deleting empty removed it. Cleanup preserved
one bridge `closed tab remains visible` observation while closing seed. Explicit
final probes then proved all three exact names absent. The temporary Windows
bridge directory was removed. No ambiguous effect was retried.

Known limitation: common core must treat an unfinished `opening` record as
unavailable until reconciliation, including before a native ID has been saved.
Primary notified to handle this shared core invariant. Cross-server live-window
movement and profile-based native starts remain unqualified/unsupported.

Memory disposition: forbidden, per delegated no-memory-write boundary.
