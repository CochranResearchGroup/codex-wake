# Read-only metadata attachment preserves the session environment

A real tmux fixture sets update-environment to one synthetic variable, then gives
the session and observer different values. The original metadata attachment
overwrote the session value. Adding attach-session -E preserves it while keeping
no-output, ignore-size and read-only flags. The new formatting reader has the
same independently tested -E protection. No production environment was sampled
or changed by this regression.

Public feed seam command: PYTHONPATH=src /tmp/wake216-py{311,312}/bin/python -m
unittest discover -s tests -p test_tab_tmux_feed.py . Red exit1: observer value
replaced the original session value. Green: five tests pass on each interpreter
(2.321s on3.11,2.456s on3.12), including native baseline, reconnect, flood and
owned-client cleanup. No retries.
