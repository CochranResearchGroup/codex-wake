# Controller account/configuration owner — issue 395

Scope: https://github.com/CochranResearchGroup/codex-wake/issues/395 under spec 393.
Base: `2a53cbc192e3df3a5b294ac2554956da8f60b318`. Worker branch:
`feat/controller-accounts395`; isolated checkout `/tmp/codex-wake-accounts395`.

Wake now packages the Profiles implementation from
`codex-profiles` commit `3a9a3d4767910e2d1535aff40c29a228958e5e4c`
under `src/codex_profiles/`, with its MIT license. Python source is absorbed
without rewriting login, auth storage, shared layout, build selection, or
concurrent admission. The preexisting Profiles version remains provenance for
that implementation, not a separately installed package dependency. Wake owns
all five executable registrations. Legacy `codex-profiles`, `codex-profile`,
`codex-stock`, and `codex-modded` delegate through `codex_wake.profile_compat`.
No installed launchers or private configuration are changed by this source slice.

## Configuration contract

The trusted host adapter reads only `WAKE_ROOT/controller-accounts.toml`.
CLI `accounts list`, `accounts resolve SELECTOR`, and `configuration explain
SELECTOR` expose `accounts.list`, `accounts.resolve`, and
`configuration.explain` through `ControllerOperations`. Equivalent MCP tools
are `wake_controller_accounts`, `wake_controller_account_resolve`, and
`wake_controller_configuration`. They are read-only: no provider launch,
account switching, process admission, credential read, or resource renewal.
Tool callers cannot select a config path or invent a caller identity.
Host configuration determines the local account scope; external caller grants
remain the authenticated transport's responsibility.

Example disposable policy (paths must be operator-selected existing homes):

```toml
[profiles]
state_root = "/disposable/homes"
source_root = "/disposable/seed"
known_profiles = ["alice", "bob"]
selection_mode = "launcher"
check_upstream_releases = false
[profiles.aliases]
work = "alice"
[configuration.base]
model = "common"
[configuration.host.example-host]
model = "host-choice"
[configuration.provider.codex]
model = "provider-choice"
[configuration.account.codex-alice]
model = "alice-choice"
```

One TOML document retains the existing Profiles table and adds explicit scoped
configuration. Effective values start with the selected native config and then
apply base, host, provider, account in that order. Explanation returns flattened
leaf values with exact source labels plus the reused native layout/MCP identity
scope view. Secret/token/password/credential/authorization fields and MCP env
values are redacted. The owner never opens `auth.json` or OAuth credential
stores. Account discovery is bounded to 256 candidate homes below the explicit
state root. Aliases, configured names, and existing homes resolve into one
namespace. Missing/replaced homes, traversal names, shared mutable symlinks or
inodes, projection/shared-session policies, and foreign-owned homes fail closed.
An optional expected target pins host, environment, account, home inode and
Wake and native configuration-content revision; mismatch never silently retargets.

The Wake-owned compatibility launch path applies the same scoped values using
native `-c` flags, preserving shared config files. Caller-provided later native
flags retain their explicit override semantics. Secret scoped overrides are
held; configure those with the native credential owner. Concurrent launch uses
the reused pinned-build private-runtime admission. Legacy unpinned launches
retain their existing exclusion behavior. No remote API/MCP launch capability
is added by these read-only operations.

`codex-wake profiles --config FILE ...` invokes the same compatibility owner.
Compatibility executables select `CODEX_WAKE_ACCOUNTS_CONFIG`, then the explicit
legacy `CODEX_PROFILES_CONFIG`, otherwise
`CODEX_WAKE_ROOT/controller-accounts.toml` (default `.codex/wake`). Explicit
legacy `--config`, `--state-root`, and `--source-root` remain migration inputs;
no file is copied or implicitly activated. Existing indirect-link/writer
migration qualification remains issue 394's boundary.

## Public seams and validation

Public operation service proves alias/config generation/precedence and rejects
unsupported arguments. CLI/MCP parity proves adapter equivalence, not external
OAuth authorization. The reused public lifetime guard proves concurrent private
homes, shared-inode denial, legacy exclusion and crash/restart generation
handling. Installed disposable executable acceptance proves package inclusion,
real legacy entrypoints, concurrent pinned account launch, scoped flags, peer
preservation on one-account restart and unchanged synthetic credentials.
It does not prove provider authentication, Windows execution or production
activation. No production configuration, credentials, service, governor or
allowance was changed.

Exact red/green commands (repository `.venv` Python, `PYTHONPATH=src`):

- `python -m unittest discover -s tests -p test_controller_accounts.py`: initial
  red `ModuleNotFoundError: codex_wake.controller_accounts`; green 1 test.
- Same command: next red CLI rejects `accounts`; green 2 tests after adapters.
- Same command: next red missing `profile_compat`; green 3 tests after launch
  wrapper (first fixture failure preserved: invalid stock provenance; corrected
  fixture to registered official provenance before the green).
- Same command: next red MCP env value `never-print-this` leaked; green 4 tests
  after redaction handles nested env paths.
- Final focused selection `*controller*py`: 11 tests pass, including held
  unknown/traversal/caller-injection/unsupported/shared-private-inode targets.
- Reused `test_absorbed_profiles_concurrency.py`: 7 tests pass.
- Existing `*mcp.py`: 19 tests pass in 16.159 seconds.
- An attempted `test_mcp_server.py` selection ran zero tests (exit 5); replaced
  with the real `*mcp.py` selection above, not treated as success.

Installed disposable environment: `/tmp/codex-wake-accounts395-installed`;
`uv venv PATH`, `uv pip install --python PATH/bin/python '.[mcp]'` installs the
actual built package and its declared dependencies, including MCP 2.2.0.
`PATH/bin/python scripts/controller_accounts_acceptance.py --bin-dir PATH/bin`
passes with CLI/MCP parity, two simultaneously running synthetic accounts,
restart preserving the peer, unchanged synthetic credential files, zero provider
calls and no production activation. This script unsets PYTHONPATH in children.
Manual resource snapshot: host available memory approximately 31 GiB; no
allowance renewal or governor enrollment. No retries or live/soak tests.

Memory discovery skipped: the parent supplied the frozen issue/spec and current
source/package authority; external recall would not add implementation authority.
A compatibility probe with a nonexistent config unexpectedly enumerated local
operator profile metadata through inherited defaults; no credentials were printed
and no provider request or configuration mutation occurred. The wrapper now
rejects absent explicit config before delegation, with an isolated HOME regression.
A separate red/green regression pins native/shared config edits as stale as well
as edits to the Wake config. Both use the same focused command above.

Worker memory disposition: `not_durable`; this is an unintegrated worker result,
and the coordinator owns the single integrated outcome and durable closeout.
