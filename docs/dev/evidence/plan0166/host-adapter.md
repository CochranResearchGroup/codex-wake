# Host execution adapter boundary evidence

Owned slice: `SystemdExecution`, #275/#276. No installed code, existing Codex
sessions, shared services, or provider calls were changed.

Public seam: launch, inspect, stop. Hermetic tests inject only the external
subprocess protocol. The opt-in host test uses a uniquely named disposable user
service, a temporary owned CWD, explicit resource limits, and `/bin/sleep`.

First red: `PYTHONPATH=src python -m unittest discover -s tests -p test_host_execution.py`
failed with ModuleNotFoundError before the adapter existed. First green passed
launch identity and runtime/kill-policy assertions. Subsequent focused checks
passed invalid-limit rejection without host effects, existing-unit rejection,
reused-invocation stop refusal, and collected-unit terminal handling.

Final focused: six tests, five pass and one opt-in skip, 0.005 seconds.
`python -m compileall -q src/codex_wake/host_execution.py` and
`git diff --check` passed.

Live tier: `CODEX_WAKE_HOST_EXECUTION_LIVE=1 PYTHONPATH=src python -m unittest discover -s tests -p test_host_execution.py`
passed five then-current tests in 1.529 seconds. The independent manager deadline
terminated `/bin/sleep 9` with RuntimeMaxSec=1; recursive membership became empty.
A separate direct launch/stop smoke read back memory.max=67108864,
memory.swap.max=0, cpu.max='50000 100000', pids.max=16, and verified stop empty.
No retry of uncertain effects was performed. The deadline test reset only its own
exact failed unit after the empty-cgroup assertion.

The adapter rejects existing unit names rather than adopting or restarting them.
Ambiguous transport errors name the deterministic unit for reconciliation and
never launch again automatically. InvocationID and ControlGroup are checked
before stop; changed identity produces no stop call. A collected unit is terminal
only if its recorded cgroup no longer exists. Active units with inaccessible or
missing cgroups are errors, never empty-success receipts.

Limitations: process containment is not a security sandbox against a malicious
same-user process deliberately escaping through the user's service manager.
Kernel limits are directly read by inspect while the cgroup exists; after
collection they cannot be reconstructed as live observations. No Codex executor,
controller-death, suspend/resume, or full objective accounting acceptance is claimed
by this adapter slice; those belong to coordinator integration.
