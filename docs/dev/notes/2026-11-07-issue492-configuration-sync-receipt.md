# Issue 492 configuration sync domain receipt

Work item: https://github.com/CochranResearchGroup/codex-wake/issues/492
Parent: #488 / Plan0205. Worker lane: sync205.
Source commit: 9d2007d (base 9ee1d157045c8bfd6bdebca76f4043e89b3bb72d).
Branch: feat/profile-sync-492. No live effects or tracker closure.

## Delivered boundary

`configuration_sync.execute(owner, operation, arguments, reload_executor=None)`
accepts `configuration.sync.preview` and `configuration.sync.apply`.
Arguments: explicit `source`, `destinations` list, `categories` list,
`operation_id`; apply additionally requires the preview `expected_snapshot`.
Optional booleans: `propagate_deletions`, `reload`.
Categories remain the profile store owner's settings, mcp, hooks, skills, rules.

Store selection uses the existing accounts TOML owner. Metadata is private and
adjacent to that registry; it contains hashes, identities and redacted outcomes,
never configuration values. Preview hashes bind store generations, selected
entries, raw config bytes and prior baselines. Apply revalidates before writing.
An intent journal prevents automatic retries after uncertain effects; an
`outcome_unknown` requires reconciliation of the selected configuration/native
reload before a new submission. No automatic reconciliation claim is made.

Seed captures provide forward/reverse baselines and sibling common ancestry.
Safe source changes apply independently of entry conflicts; destination edits
and unresolved conflict baselines remain intact. Deletion is opt-in. TOML edits
reuse the account registry editor with whole-document semantic verification;
ambiguous/unsupported layouts fail before publication. Home-local assets are
copied/remapped privately, safe local source links are materialized, and
executable bits are preserved. Codex auth files/runtime state and the account
credential-store choice are excluded from sync. Source-preserving seed staging
revalidates input and cleans definitely unpublished homes after failure.

Default activation is next launch. The optional reload callback receives only
the selected resolved store; the integration owner must resolve supported native
identity there. Stock/absent callbacks report unsupported reload without
blocking configuration application. No restarts or native refreshes ran here.

## Local focused validation

Interpreter: repository-provided Python 3.12.13 virtual environment; PYTHONPATH=src.
Commands below were run with that interpreter, not hosted GitHub Actions.

- `python -m unittest discover -s tests -p test_configuration_sync.py`: initial
  RED missing domain module; subsequent vertical REDs caught unchanged raw-input
  approval, whole hooks.json conflict and uncertain-reload retry behavior.
  Final GREEN: 6 tests, 0.617 seconds.
- `python -m unittest discover -s tests -p 'test_controller_account*.py'`:
  19 PASS, 9.028 seconds.
- `python -m unittest discover -s tests -p test_independent_stores.py`:
  final 1 PASS, 0.090 seconds.
- `python -m compileall -q src/codex_wake/configuration_sync.py src/codex_wake/profile_stores.py tests/test_configuration_sync.py`:
  PASS.
- `git diff --check`: PASS before commit.
- Pinned undefined-name checker was unavailable: supplied venv lacks ruff/pip;
  shell lacks uv/uvx. Integration owner must run the existing pinned checker.

This is focused domain evidence, not comprehensive, installed or live proof.
Material hosted differences: one local Python version, existing environment,
no hosted matrix, package install, PowerShell client or actual native reload.
CLI/API/MCP adapters and generated contracts are owned by parity, not changed
here. Actual hook execution and runtime concurrency remain acceptance work;
these tests verify private copied content, executable modes and remapped paths.

Memory disposition: forbidden; no explicit memory-write request. No durable
memory write was attempted; the primary owns campaign closeout/reconciliation.
