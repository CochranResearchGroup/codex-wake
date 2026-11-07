# Plan0205 / #494 transport parity

Owner: parity implementation worker, delegated by the Plan0205 primary.
Base: 77be4a5c8ef29e75442f9189ba7726e626da5777.
Scope: command contracts, presentation adapters, scoped controller admission,
completion and disposable transport acceptance. Integration and #495 installed
qualification remain with the primary. No tracker closure or deployment.

The existing account owner now exposes registered stores, independent creation,
configuration sync and selected readiness through CLI, REST, OAuth MCP and native
MCP. Existing migration preview/apply/rollback expose the host-selected
`adopt_independent` strategy; no additional migration registry is introduced.
History help describes saved snapshot boundaries and exclusions rather than an
idle-only source. Generated reference and coverage include the new commands.

Local operator account/store/sync commands do not require remote-style grants.
Remote and native MCP use existing host-approved caller scopes. Store reads
require an exact host/environment/store_id/home/home_generation grant, or an
existing exact profile account target. Sync requires permission for every source
and destination; preview uses configuration.observe and apply uses control.
Stable store grants avoid invalidating an intentional sync merely because a
configuration revision changes. Stock registration requires admin and a grant
pinning the current registry revision and explicit home. OAuth's existing target
allowlist now admits store_id without broadening grants.

Remote readiness rejects caller-provided manifest/launcher paths. Every
transport derives the build manifest from the fixed host registry when one is
registered. Local operators retain explicit path inspection. Missing launcher,
backend, watcher, limit or refresh evidence remains visible with remedies.
Sync defaults to next launch. This transport does not have a supported native
selected-profile reload dispatcher: `--reload` returns an explicit unsupported
next-launch remedy per destination, without restarting stock, peers or budgets.

## Verification

Focused public red: test_profile_transport_parity initially failed because
stores.register returned unsupported_operation. Raw receipt: /tmp/cw494-red.log.
Green now covers grant-free local seed/sync/replay, explicit unsupported reload,
CLI/completion, scoped API/native results, denied cross-store access, remote
readiness path rejection and durable independent creation/replay.

The initial actual OAuth probe found store_id rejected as invalid_target. That
product contract was fixed. Its first raw log was overwritten; this note records
the observed red, not retained raw proof. A subsequent fixture-only invalid_grant
was corrected by supplying redirect_uri to the token exchange. An initial focused
command included nonexistent test_controller_http; it was corrected to the
actual test_controller_auth module. Neither failure is reported as passing.

Focused suite: 73 PASS,33.502s before final shared readiness adapter adjustment;
its affected public/readiness checks then passed5 tests,0.855s. Additional existing
history/migration authorization checks:10 PASS,6.351s. Final immutable-source
checks and actual acceptance are rerun after this source commit; exact commit and
results are recorded in the user-scoped handoff receipts.

Commands (shared Python3.12 environment; PYTHONPATH=src:tests):

```sh
python -m unittest test_profile_transport_parity test_command_contract test_completion test_controller_accounts test_controller_product_authorization test_account_readiness test_account_observation test_controller_auth test_a2a_mcp test_configuration_sync test_independent_stores test_controller_adoption test_controller_migration -q
python -m unittest test_profile_transport_parity test_controller_history_authorization test_controller_migration_authorization -q
uv tool run --from ruff==0.14.2 ruff check --select F821,F822,F823 src scripts tests .codex/hooks
python -m compileall -q src scripts/profile_transport_parity_acceptance.py tests/test_profile_transport_parity.py
python scripts/generate_command_reference.py --check
python scripts/check_policy_wiring.py
python scripts/profile_transport_parity_acceptance.py --powershell /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe --receipt /tmp/cw494-powershell-final.json
```

Actual disposable acceptance passed Windows PowerShell5.1.26100.9711 HTTP requests
alongside WSL CLI, REST, OAuth MCP and native MCP. Assertions compare exact store
and sync result bodies and replay the same frozen sync intent. PowerShell uses
an authenticated exact-store grant; token contents are neither printed nor
passed in process arguments. The listener is owned by the fixture and closed in
finally. No model calls, copied credentials or working-profile changes occur.
This is transport proof, not installed native chat/resume or limit enforcement.

Hosted Actions were skipped under the cost policy. Local Python3.12/WSL and
Windows PowerShell5.1 differ from the hosted Ubuntu Python3.11/3.12 matrix. The
full comprehensive suite, installed stock/two-profile operation and native
selected-profile refresh remain #495 gates. The required undefined-name checker,
compile, generated-doc and policy-wiring checks passed. An exploratory broader
F check also reported three pre-existing unused imports outside the required
undefined-name selection; this slice introduces none.

Memory discovery: skip; the supplied task packet and current Plan0205/domain
source provide the required context. Memory disposition: forbidden; no explicit
memory-write request. No Graphiti write attempted.
