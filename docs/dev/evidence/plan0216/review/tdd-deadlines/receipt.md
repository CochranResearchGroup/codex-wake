# TDD remediation pass 1 — deadline slices

Accepted findings S1 and P2. Public seams: ControllerTabs.execute passes a caller
budget to the presentation adapter; TabObserver.tick must mark skipped retained
rows unavailable and retry reconciliation rather than renewing evidence.
The first catches deadline extension, not arbitrary malicious adapter behavior;
the second catches freshness fabrication, not real provider broadcasts.

Red: PYTHONPATH=src:tests /tmp/wake216-py312/bin/python -m unittest
 test_tab_observer.ObserverTests.test_persistent_inventory_source_loss_and_owned_cleanup
failed monitor_unavailable=False after exhausted due reconciliation.
Minimal fix routes skipped work through the existing missing-resource invalidation
path, preserves details and leaves reconciliation due. Same command green.

Next red: PYTHONPATH=src:tests /tmp/wake216-py312/bin/python -m unittest
 test_tab_observation.ObservationTests.test_inventory_preserves_callers_remaining_deadline
failed unexpected deadline keyword. Added optional Python-only deadline to existing
inventory execute seam, capped by its existing ten-second maximum. The observer
translates remaining injected monotonic budget to the controller clock domain.
Wire arguments and generated CLI/API/MCP schemas remain unchanged.

Green: PYTHONPATH=src:tests /tmp/wake216-py312/bin/python -m unittest
 test_tab_observation test_tab_observer:10tests PASS/2.529s. Python3.11:10tests PASS/2.274s.
Budget180s per invocation; hermetic private tmux; no retries or production effects.
