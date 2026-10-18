# Guard deadline continuity acceptance

Base integration: ab7bf49. Focused source acceptance only, not installed-runtime
or provider acceptance. New test file is `tests/test_strict_deadline_continuity.py`.

`PYTHONPATH=src python -m unittest discover -s tests -p test_strict_deadline_continuity.py`
passed three tests in 0.273 seconds. `git diff --check` passed. No retries.

Two separate real `python -m codex_wake.strict_executor admission.json` processes
read the same immutable persisted admission, including original started_boottime,
started_upper, deadline and generation. Both wrote deadline_reached/stopped,
child_pid=null. The proposed child side-effect marker was absent. The unchanged
configuration SHA-256 and distinct guard PIDs were asserted. No restarted guard
received a fresh elapsed allowance.

A deterministic public Guard.check BOOTTIME injection moved from elapsed2 to
elapsed100 and reconstructed a second Guard from the unchanged JSON values.
Elapsed100 fenced deadline_reached both times. At elapsed2 the absent controller
produced controller_unavailable, establishing it had not prematurely reached the
deadline. An actual Linux CLOCK_BOOTTIME read and positive resolution were also
checked. The jump was injected; no actual host suspend/reboot was performed or
claimed. Kernel CLOCK_BOOTTIME semantics supply suspend-inclusive elapsed time;
this bounded check validates application use of the selected clock, not an
end-to-end host suspend event.

A third real guard executable invocation with a deliberately changed boot ID
wrote boot_identity_changed, child_pid=null, with absent child side-effect marker.
No model turns, provider calls, systemd mutations or hostwide changes occurred.
No product code defect was discovered or patched. Native blocked-tool deadline,
manager containment, and same-revision stopped-generation admission are separate
acceptance lanes and are not inferred from these tests.
