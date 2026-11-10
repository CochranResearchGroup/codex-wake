# Quiet owner heartbeat regression

The installed49435e8e60second qualification exposed579ticks/minute whilequiet.
Publisherheartbeat had changed10seconds but serve sleep deadline stillused5.
After5seconds delay clamped to.05s until10second publication, causing a spin.
One shared interval calculation now governs publication and sleep.

Public realowner regression uses interval.5,stale_after12: wait fornextfullsnapshot
at6seconds and require atmost18ticks (normalabout12). Redobserved30ticks; green
passes. Owner status remainsfresh. This is actualprivateprocess/resource evidence,
not a mocked sleep or private-method assertion.

Exact focused command: PYTHONPATH=src /tmp/wake216-py{311,312}/bin/python -m unittest
discover -s tests -p test_tab_monitor_publication.py . Redexit1; bothgreenexit0,
5tests,8.472s/Python3.11 and8.351s/Python3.12. No retries. CPUacceptance pending
new exactinstalledpackage; wheel3failure is preserved.
