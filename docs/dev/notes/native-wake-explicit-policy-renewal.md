# Native wake explicit-policy renewal regression

Work item: native-explicit-policy-renewal. Owner: primary agent. Priority: P1.
State: source fixed and locally validated; not installed, production renewal open.
Request: operator invoked diagnosing-bugs after persistent monitor renewal failed.
Scope: native registration compatibility only. No permission edits, trigger writes,
existing record migration, daemon replacement, service restart or live dispatch.
Baseline origin/main5fa63408; installed MCP/CLI0.22.0.dev38-169ad1f.

## Feedback loop and cause

Actual installed decorate_policy with synthetic root/principal and mocked allowed
permission responses rejects all three advertised modes for ordered routes
existing_tab/background/new_tab: session_mode_routes_conflict. Loop0.12s, no wakes
written. Original retained key also refuses adding a target session_mode that was
absent originally. CLI fallback refused policy/identity checks; that is a separate
correct authority boundary, not permission to impersonate an operator.

Ranked predictions: mandatory-mode API cannot express independent legacy policy;
legacy record decode defect; mislabeled permissions. Constructor rejects fresh
requests before route checks even when grant response is allowed. Legacy CLI
registration with full independent fields succeeds. Public MCP regression first
failed invalid_argument for explicit_policy, then passed after adding the explicit
compatibility selector. This confirms API representability/compatibility gap.

## Fix and invariants

Add native-only session_mode selector explicit_policy. It requires wake_lifetime,
recipient_startup and routes, then uses the existing independent policy contract.
No persisted target lifecycle field is added and legacy fingerprints stay equal.
All existing permission, exact-self, owner and retry validation remains active.
A key already bound to any lifecycle mode cannot use this selector to drop it.
Missing mode remains rejected by MCP; missing explicit fields remain rejected.
Recurring schedules keep their existing three-mode schema; no new mode semantics
or reader capability is silently advertised for persisted records.

Four hermetic public-caller tests exercise exact legacy-key retry, a successor,
incomplete contract rejection, denied route and bound-lifecycle preservation.
Existing explicit-mode and route/uncertain-delivery tests continue passing.
No debug instrumentation added to tracked implementation. Private tagged repro
remains in a clearly marked diagnostic directory, outside this repository.

## Validation and limits

Use PYTHONPATH=src with the installed dev38 Python interpreter to supply runtime
dependencies; the generic python lacks websockets and uv is not on PATH. No
hosted CI under cost policy. Source syntax/diff and focused tests are local only.
The broader harness-caller fixture also failed on untouched origin/main because
it wrote synthetic monitor health without a qualified managed-reader/harness
observation. Fixture now supplies explicitly synthetic observation seams; it still
asserts once is unarmed and loop is armed. Production readiness gates are unchanged.

The source suite and injected fixture success are not installed acceptance. Before
working-account installation, qualify the exact package in the separate Linux
test user or disposable wsl-test per runtime policy, preserve active conversations,
and obtain deployment authority. Reload this client's schema only through the
approved lifecycle workflow. Then reconcile original monitor keys, use the same
prompt/cadence/TTL/startup/routes plus explicit_policy, and verify two armed receipts
and stable Codex binding. Do not invent a replacement key for an uncertain send.
Until that readback, only the already-retained next wake is known; indefinite
continuity is degraded. No extension of spam enforcement is implied.

Validation counts: native explicit-policy4, session modes5, route permissions11,
harness callers9, recurring schedules10, wake policy8, launcher continuity3:50
passing focused tests. The unchanged-baseline caller test failure was reproduced
from a clean git archive before repairing its synthetic observation fixture.
No tests dispatch to real sessions or use production wake records.
