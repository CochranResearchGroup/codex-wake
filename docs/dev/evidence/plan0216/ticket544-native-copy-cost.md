# Native summary and snapshot-copy cost

Source changes: 3c065301 and 9d0fd2d3; measured profile input remains
qualification547/de23-steady-profile-summary.json. The profile attributed
2,200 summary calls and 12 snapshot deep copies to a ten-second active window.
Native updates now summarize only resources containing a matched pane; source
loss does the same. Exact process checks and retained source-loss semantics stay.
Tmux snapshots retain one JSON encoding per received metadata baseline and decode
independent nested containers for each caller.

Focused check on both Python3.11.15 and3.12.13:
`PYTHONPATH=src /tmp/wake216-py311/bin/python -m unittest discover -s tests -p test_tab_observer.py`
and the same command with `/tmp/wake216-py312/bin/python`: five tests each PASS.
Includes native status/source loss and caller mutation isolation. No retries.

Python3.12 synthetic100-window snapshot-copy microbenchmark,1000 reads:
deepcopy0.62745s; retained JSON decode0.14080s (22.44% cost). Caller mutation
did not alter later snapshots. This excludes encoding on baseline arrival and
is component evidence only, not installed or60-second resource acceptance.
Full100-tab combined qualification remains required.
