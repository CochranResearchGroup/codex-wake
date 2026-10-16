# Stopped executor final usage and explicit renewal

Base5619904. Owned changes are strict_final_usage.py, strict_runtime.py,
sessions_cli.py, and test_strict_final_usage.py. No provider/model/host-service
operations were performed. The host subprocess seam is patched in these focused
operator CLI tests; actual stopped native acceptance is a separate lane.

First meaningful red: public `sessions execution --reconcile` rejected its
unknown option before implementation. Green settles an owned native cumulative
counter27, including cached input, only after task_started -> counter -> matching
task_complete. Another actual red exposed malformed total_token_usage raising
AttributeError; the final parser returns explicit accounting_unknown instead.

Interpreter:
`/home/ecochran76/.local/share/codex-wake/releases/0.16.0-d3ea192/bin/python`
Environment: CODEX_WAKE_STABLE_TIME_CONFIG='',
XDG_CONFIG_HOME=/tmp/cw166-finalusage-worker-config,
XDG_STATE_HOME=/tmp/cw166-finalusage-worker-state, PYTHONPATH=src:tests.

Focused commands: `python -m unittest discover -s tests -p NAME`:
- test_strict_final_usage.py:8PASS1.283s.
- test_strict_execution.py:6PASS0.611s.
- test_lifecycle_configuration.py:1PASS0.686s.
`git diff --check` passed. Default system Python attempts of the latter two
selections failed before exercising affected behavior because websockets and
jsonschema were absent; canonical installed interpreter resolved the dependency
gap. These were environment diagnostics, not retries masking a product failure.

Public operator tests prove missing terminals, later in-progress work, counters
after terminal, decreases and malformed usage cannot turn a sampled floor into
final usage. The floor20/reservation100 remain intact and unknown. Proven changed
usage invalidates previously settled-known usage without replacing its floor27.
An exact live or changed invocation cannot trigger offline ledger effects.
Nonblocking guard-ledger lock contention returns explicit unknown in under0.2s.

Renewal tests use the real public --apply-budget-authorization path. An explicit
newrevision preserves oldspent27, then admits the zero-used fresh reservation
before ensure_execution. The new guard configuration historical_actors map is
{'spawn:owned':27}. Both known-unsettled and unknown prior actors reject renewal
without launch. Existing binding/guard final_usage.accounting_unknown also gates
renewal until explicit operator reconciliation. A fresh current reservation is
excluded only under the prepared/no-thread/no-uncertain-effect/non-inherited,
zero-used known-new fingerprint contract; old bindings prevent exclusion.

Reads are regular-file/nonblocking, no-follow, bounded to512 combined lifecycle
and rollout artifacts plus32MiB aggregate including guard configuration. The
private guard generation, root, home, endpoint, objective and saved revision must
match the exact empty executor binding. Historical receipt revisions must appear
in ledger authorization_history. Previously proven historical settled-known
actors may retain their proof when their old artifact is unavailable; new actors
receive no inferred zero/final counters.

Known integration boundary: denial after reserve-before-ensure can leave a
never-launched reservation. A later reconciliation must not fabricate its final
zero. The primary lane must preflight renewal eligibility before reservation or
use an already-authorized exact no-effects cancellation contract. Multiple native
threads bound to one actor remain ambiguous rather than guessing cumulative
transfers. These focused checks do not claim native final-stop acceptance.
