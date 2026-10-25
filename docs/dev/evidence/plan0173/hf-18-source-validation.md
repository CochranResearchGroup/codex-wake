# HF-18 source validation

Date: 2026-10-24
Work item: #338
Scope: isolated source branch feat/338-agent-resume from 012f173;
resume.recover catalog prerequisite cherry-picked as 80dada3.

TDD first failing command: `PYTHONPATH=src python -m unittest tests.test_agent_resume -q`
failed because agent_resume did not exist. Initial invocation without PYTHONPATH
also failed package discovery; that was environment setup, not behavior evidence.
The first exact-resume test then passed. The recovery test next failed with
resume_recovery_authority_required; adding real-principal resume.recover dispatch
made it pass. The unqualified existing attachment regression failed because it
launched and returned resumed; the attachment hold then made it pass.

Protocol setup initially lacked websockets, then exposed a fixture assumption
that process_identity contains pid. Fixed the fixture to supply its explicit
PID while retaining real process evidence. The broader selection initially
lacked jsonschema; rerun included that declared dependency. No failed result is
represented as passing.

Focused final command:

```sh
uv run --no-project --with 'websockets>=17,<18' --with packaging --with jsonschema \
  env PYTHONPATH=src python -m unittest \
  tests.test_agent_resume tests.test_agent_resume_protocol \
  tests.test_managed_inventory tests.test_session_permissions -q
```

Final result: 32 tests passed in 4.635 seconds, no retries. The selection is
focused source validation, not comprehensive or live validation.

The real Unix socket fixture uses production SharedAppServerReader and fixed
SavedRuntime launch construction. A private process/attachment fixture supplies
fresh OS generation evidence; its terminal adapter records the fixed effect and
can lose its response after creating the fixture attachment. CLI operator
capabilities are real disposable BusStore capabilities; native MCP metadata is
host-injected fixture evidence. No provider, operator tab, installed service,
GitHub operation or native model turn was exercised.

The existing shared_app_server client emits a websockets deprecation warning.
This slice does not alter that transport owner. Shared public registration and
combined review remain primary-owned; source tests are not installed acceptance.
Memory disposition: forbidden; primary explicitly prohibited memory writes.
