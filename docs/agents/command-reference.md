# Generated command reference

Generated from `codex_wake.command_contract`; do not edit by hand.

Scope: stores, accounts, configuration, builds, daemons, migration and history. Other Wake
commands are deferred from this contract migration; their existing interfaces remain.

Local human login and status use native stdio. Structured status is cache evidence,
not proof of current provider access. Native history MCP additionally requires
verified caller identity; local CLI and scoped remote caller admission differ.

Examples use placeholders ROOT, THREAD, TIME, FILE and exact target JSON.
Resolve fresh targets before execution; empty target objects are never valid pins.

## accounts init

Initialize a new private account registry.

Creates only an empty isolated registry; preserves existing state.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_account_init`).

```sh
codex-wake --wake-root ROOT accounts init
```

### CLI help

```text
usage: codex-wake accounts init [-h] [--json]

Initialize a new private account registry.

Creates only an empty isolated registry; preserves existing state.

options:
  -h, --help  show this help message and exit
  --json      Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT accounts init
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## accounts create

Create a private account home without credentials.

Creates account configuration and a private home; does not sign in.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_account_create`).

```sh
codex-wake --wake-root ROOT accounts create work --alias office
```

### CLI help

```text
usage: codex-wake accounts create [-h] [--alias ALIAS] [--mode {independent}]
                                  [--source SOURCE] [--json]
                                  selector

Create a private account home without credentials.

Creates account configuration and a private home; does not sign in.

positional arguments:
  selector              Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --alias ALIAS         Optional alternate name for the newly created account.
  --mode {independent}  Create an independent private configuration snapshot;
                        legacy creation remains the default.
  --source SOURCE       Registered source store selector, including stock.
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT accounts create work --alias office
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `selector` | yes | Account name or configured alias. |
| `alias` | no | Optional alternate name for the newly created account. |
| `mode` | no | Create an independent private configuration snapshot; legacy creation remains the default. |
| `source` | no | Registered source store selector, including stock. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## accounts readiness

Inspect the selected profile readiness and specific remedies.

Read-only; native limits, refresh and backend acceptance remain separately qualified. Remote callers cannot supply launcher or manifest paths.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_account_readiness`).

```sh
codex-wake --wake-root ROOT accounts readiness work --json
```

### CLI help

```text
usage: codex-wake accounts readiness [-h] [--expected-target EXPECTED_TARGET]
                                     [--manifest MANIFEST]
                                     [--launcher LAUNCHER] [--json]
                                     selector

Inspect the selected profile readiness and specific remedies.

Read-only; native limits, refresh and backend acceptance remain separately qualified. Remote callers cannot supply launcher or manifest paths.

positional arguments:
  selector              Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --manifest MANIFEST
  --launcher LAUNCHER
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT accounts readiness work --json
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `selector` | yes | Account name or configured alias. |
| `expected_target` | no | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |

## stores register

Register the stable shared stock store in Wake metadata.

Preserves stock configuration and login. Remote admin grant must pin the registry revision and selected home.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_store_register`).

```sh
codex-wake --wake-root ROOT stores register stock --home /absolute/stock/home
```

### CLI help

```text
usage: codex-wake stores register [-h] --home HOME [--json] selector

Register the stable shared stock store in Wake metadata.

Preserves stock configuration and login. Remote admin grant must pin the registry revision and selected home.

positional arguments:
  selector     Account name or configured alias.

options:
  -h, --help   show this help message and exit
  --home HOME  Absolute existing stock home; registration changes only Wake
               metadata.
  --json       Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT stores register stock --home /absolute/stock/home
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `selector` | yes | Account name or configured alias. |
| `home` | yes | Absolute existing stock home; registration changes only Wake metadata. |

## stores resolve

Resolve a registered stock or profile store.

Read-only observation; no model turn.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_store_resolve`).

```sh
codex-wake --wake-root ROOT stores resolve stock
```

### CLI help

```text
usage: codex-wake stores resolve [-h] [--json] selector

Resolve a registered stock or profile store.

Read-only observation; no model turn.

positional arguments:
  selector    Account name or configured alias.

options:
  -h, --help  show this help message and exit
  --json      Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT stores resolve stock
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `selector` | yes | Account name or configured alias. |

## stores list

List permitted registered stores with stable identities.

Read-only observation; no model turn.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_stores`).

```sh
codex-wake --wake-root ROOT stores list
```

### CLI help

```text
usage: codex-wake stores list [-h] [--json]

List permitted registered stores with stable identities.

Read-only observation; no model turn.

options:
  -h, --help  show this help message and exit
  --json      Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT stores list
```

## configuration sync preview

Preview selected directional configuration changes and conflicts.

Saves a frozen preview outside stock; sensitive values are redacted. Grant must cover every selected store.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_configuration_sync_preview`).

```sh
codex-wake --wake-root ROOT configuration sync preview --source stock --destination work --category mcp --operation-id sync-1
```

### CLI help

```text
usage: codex-wake configuration sync preview [-h] --source SOURCE
                                             --destination DESTINATIONS
                                             --category
                                             {settings,mcp,hooks,skills,rules}
                                             --operation-id OPERATION_ID
                                             [--propagate-deletions]
                                             [--reload] [--json]

Preview selected directional configuration changes and conflicts.

Saves a frozen preview outside stock; sensitive values are redacted. Grant must cover every selected store.

options:
  -h, --help            show this help message and exit
  --source SOURCE       Registered source store selector, including stock.
  --destination DESTINATIONS
                        Explicit destination store selectors.
  --category {settings,mcp,hooks,skills,rules}
                        Selected configuration categories; authentication is
                        excluded.
  --operation-id OPERATION_ID
                        Stable sync intent identifier; reconcile unknown
                        outcomes before resubmitting.
  --propagate-deletions
                        Explicitly propagate matching source deletions;
                        default preserves destination copies.
  --reload              Request selected-profile reload if supported;
                        otherwise each destination reports next-launch remedy.
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT configuration sync preview --source stock --destination work --category mcp --operation-id sync-1
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `source` | yes | Registered source store selector, including stock. |
| `destinations` | yes | Explicit destination store selectors. |
| `categories` | yes | Selected configuration categories; authentication is excluded. |
| `operation_id` | yes | Stable sync intent identifier; reconcile unknown outcomes before resubmitting. |
| `propagate_deletions` | no | Explicitly propagate matching source deletions; default preserves destination copies. |
| `reload` | no | Request selected-profile reload if supported; otherwise each destination reports next-launch remedy. |

## configuration sync apply

Apply safe selected changes and preserve divergent destination entries.

Repeat-safe per-destination results. Default takes effect at next launch; reload reports an explicit unsupported remedy when no selected-profile owner is available.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_configuration_sync_apply`).

```sh
codex-wake --wake-root ROOT configuration sync apply --source stock --destination work --category mcp --operation-id sync-1 --expected-snapshot SNAPSHOT
```

### CLI help

```text
usage: codex-wake configuration sync apply [-h] --source SOURCE --destination
                                           DESTINATIONS --category
                                           {settings,mcp,hooks,skills,rules}
                                           --operation-id OPERATION_ID
                                           --expected-snapshot
                                           EXPECTED_SNAPSHOT
                                           [--propagate-deletions] [--reload]
                                           [--json]

Apply safe selected changes and preserve divergent destination entries.

Repeat-safe per-destination results. Default takes effect at next launch; reload reports an explicit unsupported remedy when no selected-profile owner is available.

options:
  -h, --help            show this help message and exit
  --source SOURCE       Registered source store selector, including stock.
  --destination DESTINATIONS
                        Explicit destination store selectors.
  --category {settings,mcp,hooks,skills,rules}
                        Selected configuration categories; authentication is
                        excluded.
  --operation-id OPERATION_ID
                        Stable sync intent identifier; reconcile unknown
                        outcomes before resubmitting.
  --expected-snapshot EXPECTED_SNAPSHOT
                        Exact snapshot digest returned by sync preview.
  --propagate-deletions
                        Explicitly propagate matching source deletions;
                        default preserves destination copies.
  --reload              Request selected-profile reload if supported;
                        otherwise each destination reports next-launch remedy.
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT configuration sync apply --source stock --destination work --category mcp --operation-id sync-1 --expected-snapshot SNAPSHOT
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `source` | yes | Registered source store selector, including stock. |
| `destinations` | yes | Explicit destination store selectors. |
| `categories` | yes | Selected configuration categories; authentication is excluded. |
| `operation_id` | yes | Stable sync intent identifier; reconcile unknown outcomes before resubmitting. |
| `expected_snapshot` | yes | Exact snapshot digest returned by sync preview. |
| `propagate_deletions` | no | Explicitly propagate matching source deletions; default preserves destination copies. |
| `reload` | no | Request selected-profile reload if supported; otherwise each destination reports next-launch remedy. |

## accounts list

List registered account names and targets.

Read-only observation; no model turn.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_accounts`).

```sh
codex-wake --wake-root ROOT accounts list
```

### CLI help

```text
usage: codex-wake accounts list [-h] [--json]

List registered account names and targets.

Read-only observation; no model turn.

options:
  -h, --help  show this help message and exit
  --json      Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT accounts list
```

## accounts resolve

Resolve one account name to its exact current target.

Read-only observation; no model turn.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_account_resolve`).

```sh
codex-wake --wake-root ROOT accounts resolve work
```

### CLI help

```text
usage: codex-wake accounts resolve [-h] [--json]
                                   [--expected-target EXPECTED_TARGET]
                                   selector

Resolve one account name to its exact current target.

Read-only observation; no model turn.

positional arguments:
  selector              Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --json                Emit structured results for this command.
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.

Examples:
  codex-wake --wake-root ROOT accounts resolve work
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `selector` | yes | Account name or configured alias. |
| `expected_target` | no | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |

## accounts login

Sign into a named private account through native login.

Local human CLI only. Writes native credentials; active account clients or daemons hold login.

Transport: Local human CLI only.

```sh
codex-wake --wake-root ROOT accounts login work --device-auth
```

### CLI help

```text
usage: codex-wake accounts login [-h] [--channel {stock,modded}]
                                 [--device-auth | --with-api-key]
                                 selector

Sign into a named private account through native login.

Local human CLI only. Writes native credentials; active account clients or daemons hold login.

positional arguments:
  selector              Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --device-auth         Sign in using a one-time device code approved in your
                        browser.
  --with-api-key        Read the API key from standard input; never put it in
                        command arguments.

Examples:
  codex-wake --wake-root ROOT accounts login work --device-auth
```

## accounts status

Observe sanitized local authentication evidence.

No provider verification or refresh in --json/API/MCP. Human CLI retains native login status.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_account_status`).

```sh
codex-wake --wake-root ROOT accounts status work --json
```

### CLI help

```text
usage: codex-wake accounts status [-h] [--channel {stock,modded}] [--json]
                                  [--expected-target EXPECTED_TARGET]
                                  selector

Observe sanitized local authentication evidence.

No provider verification or refresh in --json/API/MCP. Human CLI retains native login status.

positional arguments:
  selector              Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --json                Emit structured results for this command.
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.

Examples:
  codex-wake --wake-root ROOT accounts status work --json
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `selector` | yes | Account name or configured alias. |
| `expected_target` | no | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |

## configuration explain

Explain effective settings, skills and configuration provenance.

Read-only observation; no model turn.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_configuration`).

```sh
codex-wake --wake-root ROOT configuration explain work
```

### CLI help

```text
usage: codex-wake configuration explain [-h]
                                        [--expected-target EXPECTED_TARGET]
                                        [--json]
                                        selector

Explain effective settings, skills and configuration provenance.

Read-only observation; no model turn.

positional arguments:
  selector              Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT configuration explain work
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `selector` | yes | Account name or configured alias. |
| `expected_target` | no | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |

## builds list

List registered builds and their exact targets.

Read-only observation; no model turn.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_list`).

```sh
codex-wake --wake-root ROOT builds list --account work
```

### CLI help

```text
usage: codex-wake builds list [-h] [--arguments ARGUMENTS] [--account ACCOUNT]

List registered builds and their exact targets.

Read-only observation; no model turn.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --account ACCOUNT     Account name or configured alias.

Examples:
  codex-wake --wake-root ROOT builds list --account work
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `account` | yes | Account name or configured alias. |

## builds launch

Open a native client using an exact registered account build.

Attaches a client; no provider turn unless explicitly requested through client arguments.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_launch`).

```sh
codex-wake --wake-root ROOT builds launch --account work --channel modded --expected-target "$TARGET"
```

### CLI help

```text
usage: codex-wake builds launch [-h] [--arguments ARGUMENTS]
                                [--account ACCOUNT] [--channel {stock,modded}]
                                [--expected-target EXPECTED_TARGET]
                                [--arg NATIVE_ARGS | --args NATIVE_ARGS_JSON]

Open a native client using an exact registered account build.

Attaches a client; no provider turn unless explicitly requested through client arguments.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --account ACCOUNT     Account name or configured alias.
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --arg NATIVE_ARGS     Repeat for each native client argument; use
                        --arg=--flag for options.
  --args NATIVE_ARGS_JSON
                        Native client arguments as a JSON array of strings.

Examples:
  codex-wake --wake-root ROOT builds launch --account work --channel modded --expected-target "$TARGET"
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `account` | yes | Account name or configured alias. |
| `channel` | yes | Registered native build channel (default: modded). |
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |
| `args` | no | Native client arguments for the registered build. |

## builds stage

Stage one host-registered immutable build recipe.

Runs the configured build recipe under existing build authority.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_stage`).

```sh
codex-wake --wake-root ROOT builds stage --arguments '{"recipe":"candidate"}'
```

### CLI help

```text
usage: codex-wake builds stage [-h] [--arguments ARGUMENTS] [--recipe RECIPE]

Stage one host-registered immutable build recipe.

Runs the configured build recipe under existing build authority.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --recipe RECIPE       Host-registered build recipe name, never an arbitrary
                        executable or path.

Examples:
  codex-wake --wake-root ROOT builds stage --arguments '{"recipe":"candidate"}'
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `recipe` | yes | Host-registered build recipe name, never an arbitrary executable or path. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## builds select

Select a staged immutable artifact for an account.

Changes future build selection; does not imply a running daemon changed.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_select`).

```sh
codex-wake --wake-root ROOT builds select --account work --channel modded --expected-target "$TARGET" --identifier ARTIFACT
```

### CLI help

```text
usage: codex-wake builds select [-h] [--arguments ARGUMENTS]
                                [--account ACCOUNT] [--channel {stock,modded}]
                                [--expected-target EXPECTED_TARGET]
                                [--identifier IDENTIFIER]

Select a staged immutable artifact for an account.

Changes future build selection; does not imply a running daemon changed.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --account ACCOUNT     Account name or configured alias.
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --identifier IDENTIFIER
                        Existing immutable build artifact identifier to
                        select.

Examples:
  codex-wake --wake-root ROOT builds select --account work --channel modded --expected-target "$TARGET" --identifier ARTIFACT
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `account` | yes | Account name or configured alias. |
| `channel` | yes | Registered native build channel (default: modded). |
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |
| `identifier` | yes | Existing immutable build artifact identifier to select. |

## builds rollback

Restore the prior registered account build selection.

Changes selected build under existing rollback policy.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_rollback`).

```sh
codex-wake --wake-root ROOT builds rollback --account work --channel modded --expected-target "$TARGET"
```

### CLI help

```text
usage: codex-wake builds rollback [-h] [--arguments ARGUMENTS]
                                  [--account ACCOUNT]
                                  [--channel {stock,modded}]
                                  [--expected-target EXPECTED_TARGET]

Restore the prior registered account build selection.

Changes selected build under existing rollback policy.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --account ACCOUNT     Account name or configured alias.
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.

Examples:
  codex-wake --wake-root ROOT builds rollback --account work --channel modded --expected-target "$TARGET"
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `account` | yes | Account name or configured alias. |
| `channel` | yes | Registered native build channel (default: modded). |
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## history search

Search explicitly permitted saved conversation metadata.

Read-only observation; no model turn.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_history_search`).

```sh
codex-wake --wake-root ROOT history search --owner work --query test
```

### CLI help

```text
usage: codex-wake history search [-h] [--owner OWNERS] [--query QUERY]
                                 [--sort {recent}] [--limit LIMIT] [--json]

Search explicitly permitted saved conversation metadata.

Read-only observation; no model turn.

options:
  -h, --help       show this help message and exit
  --owner OWNERS   Limit search to these explicitly permitted owning accounts;
                   repeat --owner.
  --query QUERY    Filter permitted saved conversation metadata (default:
                   all).
  --sort {recent}  Order by recent activity when set to recent; default
                   preserves existing discovery order.
  --limit LIMIT    Maximum recent conversations, from1 to100 (default:10 for
                   shortcuts).
  --json           Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT history search --owner work --query test
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `owners` | no | Limit search to these explicitly permitted owning accounts; repeat --owner. |
| `query` | no | Filter permitted saved conversation metadata (default: all). |
| `limit` | no | Maximum recent conversations, from1 to100 (default:10 for shortcuts). |
| `sort` | no | Order by recent activity when set to recent; default preserves existing discovery order. |

## history read

Read a saved conversation from its exact permitted owner.

Read-only observation; no model turn.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_history_read`).

```sh
codex-wake --wake-root ROOT history read THREAD --owner work
```

### CLI help

```text
usage: codex-wake history read [-h] --owner OWNER
                               [--expected-target EXPECTED_TARGET] [--json]
                               thread_id

Read a saved conversation from its exact permitted owner.

Read-only observation; no model turn.

positional arguments:
  thread_id             Native saved conversation identifier in its owning
                        account.

options:
  -h, --help            show this help message and exit
  --owner OWNER         Exact account that owns the saved conversation.
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT history read THREAD --owner work
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `owner` | yes | Exact account that owns the saved conversation. |
| `thread_id` | yes | Native saved conversation identifier in its owning account. |
| `expected_target` | no | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |

## history resume

Resume a saved conversation under existing exact-owner authority.

Requires existing enrolled caller permission; does not renew work or allowance.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_history_resume`).

```sh
codex-wake --wake-root ROOT history resume THREAD --owner work --expected-target "$TARGET" --intent INTENT --expires-at TIME --bus-root ROOT --operator-capability FILE
```

### CLI help

```text
usage: codex-wake history resume [-h] --owner OWNER --expected-target
                                 EXPECTED_TARGET [--json] --intent INTENT
                                 --expires-at EXPIRES_AT --bus-root BUS_ROOT
                                 --operator-capability OPERATOR_CAPABILITY
                                 [--app-server APP_SERVER]
                                 thread_id

Resume a saved conversation under existing exact-owner authority.

Requires existing enrolled caller permission; does not renew work or allowance.

positional arguments:
  thread_id             Native saved conversation identifier in its owning
                        account.

options:
  -h, --help            show this help message and exit
  --owner OWNER         Exact account that owns the saved conversation.
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --json                Emit structured results for this command.
  --intent INTENT       Existing exact-owner resume intent; does not grant new
                        work authority.
  --expires-at EXPIRES_AT
                        Expiration timestamp for the resume intent.
  --bus-root BUS_ROOT   Existing enrolled mailbox runtime root for caller
                        verification.
  --operator-capability OPERATOR_CAPABILITY
                        Path to the private operator capability; never its
                        secret contents.
  --app-server APP_SERVER
                        Enrolled native app-server endpoint (default:
                        unix://).

Examples:
  codex-wake --wake-root ROOT history resume THREAD --owner work --expected-target "$TARGET" --intent INTENT --expires-at TIME --bus-root ROOT --operator-capability FILE
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `owner` | yes | Exact account that owns the saved conversation. |
| `thread_id` | yes | Native saved conversation identifier in its owning account. |
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `intent` | yes | Existing exact-owner resume intent; does not grant new work authority. |
| `expires_at` | yes | Expiration timestamp for the resume intent. |

## history import

Copy a supported saved snapshot between stock and profile stores.

Creates a new destination UUID; source remains unchanged. Reports saved snapshot boundaries and excluded unsupported entries; transfers no credentials, grants or allowance.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_history_import`).

```sh
codex-wake --wake-root ROOT history import THREAD --owner work --destination personal --expected-source "$SOURCE" --expected-target "$TARGET" --idempotency-key copy-1
```

### CLI help

```text
usage: codex-wake history import [-h] --owner OWNER --destination DESTINATION
                                 [--channel {stock,modded}]
                                 [--expected-source EXPECTED_SOURCE]
                                 [--expected-target EXPECTED_TARGET]
                                 [--idempotency-key IDEMPOTENCY_KEY] [--yes]
                                 [--json]
                                 thread_id

Copy a supported saved snapshot between stock and profile stores.

Creates a new destination UUID; source remains unchanged. Reports saved snapshot boundaries and excluded unsupported entries; transfers no credentials, grants or allowance.

positional arguments:
  thread_id             Native saved conversation identifier in its owning
                        account.

options:
  -h, --help            show this help message and exit
  --owner OWNER         Exact account that owns the saved conversation.
  --destination DESTINATION
                        Destination account for a distinct source-preserving
                        conversation copy.
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --expected-source EXPECTED_SOURCE
                        Exact source session target JSON from history read.
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --idempotency-key IDEMPOTENCY_KEY
                        Stable key for this intent; retain it to reconcile an
                        uncertain result. Different inputs conflict.
  --yes                 Confirm the displayed scoped effect; does not override
                        a changed target.
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT history import THREAD --owner work --destination personal --expected-source "$SOURCE" --expected-target "$TARGET" --idempotency-key copy-1
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `owner` | yes | Exact account that owns the saved conversation. |
| `thread_id` | yes | Native saved conversation identifier in its owning account. |
| `destination` | yes | Destination account for a distinct source-preserving conversation copy. |
| `channel` | yes | Registered native build channel (default: modded). |
| `expected_source` | yes | Exact source session target JSON from history read. |
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## daemons list

List account-scoped native daemon observations.

Read-only process/socket/build observation; unavailable is not orphan-free proof.

Transport: CLI / API / OAuth MCP / native MCP (`wake_daemons_list`).

```sh
codex-wake --wake-root ROOT daemons list
```

### CLI help

```text
usage: codex-wake daemons list [-h] [--channel {stock,modded}] [--json]

List account-scoped native daemon observations.

Read-only process/socket/build observation; unavailable is not orphan-free proof.

options:
  -h, --help            show this help message and exit
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT daemons list
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `channel` | no | Registered native build channel (default: modded). |

## daemons status

Inspect the exact account daemon and selected build.

Read-only process/socket/build observation; unavailable is not orphan-free proof.

Transport: CLI / API / OAuth MCP / native MCP (`wake_daemons_status`).

```sh
codex-wake --wake-root ROOT daemons status work
```

### CLI help

```text
usage: codex-wake daemons status [-h] [--channel {stock,modded}] [--json]
                                 account

Inspect the exact account daemon and selected build.

Read-only process/socket/build observation; unavailable is not orphan-free proof.

positional arguments:
  account               Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT daemons status work
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `account` | yes | Account name or configured alias. |
| `channel` | no | Registered native build channel (default: modded). |

## daemons start

Start the selected account daemon.

Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_daemons_start`).

```sh
codex-wake --wake-root ROOT daemons start work --expected-target "$TARGET" --idempotency-key start-1
```

### CLI help

```text
usage: codex-wake daemons start [-h] [--channel {stock,modded}] [--json]
                                [--expected-target EXPECTED_TARGET]
                                [--idempotency-key IDEMPOTENCY_KEY] [--yes]
                                account

Start the selected account daemon.

Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.

positional arguments:
  account               Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --json                Emit structured results for this command.
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --idempotency-key IDEMPOTENCY_KEY
                        Stable key for this intent; retain it to reconcile an
                        uncertain result. Different inputs conflict.
  --yes                 Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT daemons start work --expected-target "$TARGET" --idempotency-key start-1
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `account` | yes | Account name or configured alias. |
| `channel` | no | Registered native build channel (default: modded). |
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## daemons restart

Restart one exact account daemon.

Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_daemons_restart`).

```sh
codex-wake --wake-root ROOT daemons restart work --expected-target "$TARGET" --idempotency-key restart-1 --yes
```

### CLI help

```text
usage: codex-wake daemons restart [-h] [--channel {stock,modded}] [--json]
                                  [--expected-target EXPECTED_TARGET]
                                  [--idempotency-key IDEMPOTENCY_KEY] [--yes]
                                  account

Restart one exact account daemon.

Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.

positional arguments:
  account               Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --json                Emit structured results for this command.
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --idempotency-key IDEMPOTENCY_KEY
                        Stable key for this intent; retain it to reconcile an
                        uncertain result. Different inputs conflict.
  --yes                 Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT daemons restart work --expected-target "$TARGET" --idempotency-key restart-1 --yes
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `account` | yes | Account name or configured alias. |
| `channel` | no | Registered native build channel (default: modded). |
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## daemons update

Update one exact account daemon to a registered build.

Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_daemons_update`).

```sh
codex-wake --wake-root ROOT daemons update work --expected-target "$TARGET" --idempotency-key update-1 --yes
```

### CLI help

```text
usage: codex-wake daemons update [-h] [--channel {stock,modded}] [--json]
                                 [--expected-target EXPECTED_TARGET]
                                 [--idempotency-key IDEMPOTENCY_KEY] [--yes]
                                 account

Update one exact account daemon to a registered build.

Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.

positional arguments:
  account               Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --json                Emit structured results for this command.
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --idempotency-key IDEMPOTENCY_KEY
                        Stable key for this intent; retain it to reconcile an
                        uncertain result. Different inputs conflict.
  --yes                 Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT daemons update work --expected-target "$TARGET" --idempotency-key update-1 --yes
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `account` | yes | Account name or configured alias. |
| `channel` | no | Registered native build channel (default: modded). |
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## daemons stop

Stop one exact account daemon.

Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_daemons_stop`).

```sh
codex-wake --wake-root ROOT daemons stop work --expected-target "$TARGET" --idempotency-key stop-1 --yes
```

### CLI help

```text
usage: codex-wake daemons stop [-h] [--channel {stock,modded}] [--json]
                               [--expected-target EXPECTED_TARGET]
                               [--idempotency-key IDEMPOTENCY_KEY] [--yes]
                               account

Stop one exact account daemon.

Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.

positional arguments:
  account               Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --json                Emit structured results for this command.
  --expected-target EXPECTED_TARGET
                        Exact target JSON from the corresponding resolve, list
                        or status command; replacement is refused.
  --idempotency-key IDEMPOTENCY_KEY
                        Stable key for this intent; retain it to reconcile an
                        uncertain result. Different inputs conflict.
  --yes                 Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT daemons stop work --expected-target "$TARGET" --idempotency-key stop-1 --yes
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `account` | yes | Account name or configured alias. |
| `channel` | no | Registered native build channel (default: modded). |
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## open

Open the registered native client for one private account.

Local human shortcut over builds.launch; internally pins the selected build and starts or attaches its daemon. No model prompt.

Transport: Local human CLI only.

```sh
codex-wake --wake-root ROOT open work
```

### CLI help

```text
usage: codex-wake open [-h] [--channel {stock,modded}] account

Open the registered native client for one private account.

Local human shortcut over builds.launch; internally pins the selected build and starts or attaches its daemon. No model prompt.

positional arguments:
  account               Account name or configured alias.

options:
  -h, --help            show this help message and exit
  --channel {stock,modded}
                        Registered native build channel (default: modded).

Examples:
  codex-wake --wake-root ROOT open work
```

## resume

Reopen a conversation in its named account; bare resume retains emergency-pause release.

ACCOUNT selects the native conversation chooser; --last or UUID selects saved account history. Never mixes account and emergency scope flags.

Transport: Local human CLI only.

```sh
codex-wake --wake-root ROOT resume work --last
```

### CLI help

```text
usage: codex-wake resume [-h] [--all-roots] [--registry-dir REGISTRY_DIR]
                         [--json] [--channel {stock,modded}] [--last]
                         [account] [thread_id]

Reopen a conversation in its named account; bare resume retains emergency-pause release.

ACCOUNT selects the native conversation chooser; --last or UUID selects saved account history. Never mixes account and emergency scope flags.

positional arguments:
  account               Account name or configured alias.
  thread_id             Native saved conversation identifier in its owning
                        account.

options:
  -h, --help            show this help message and exit
  --all-roots           snapshot all registered roots, including disabled
                        roots
  --registry-dir REGISTRY_DIR
                        operator-selected root registry
  --json                Emit structured results for this command.
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --last                Reopen the most recently active saved conversation for
                        the selected account.

Examples:
  codex-wake --wake-root ROOT resume work --last
```

## configuration default-root

Save an explicit user-local root for account shortcuts.

Changes only local shortcut preferences; explicit --wake-root wins. Does not change stock codex or unrelated legacy root defaults.

Transport: Local human CLI only.

```sh
codex-wake --wake-root ROOT configuration default-root ROOT
```

### CLI help

```text
usage: codex-wake configuration default-root [-h] root

Save an explicit user-local root for account shortcuts.

Changes only local shortcut preferences; explicit --wake-root wins. Does not change stock codex or unrelated legacy root defaults.

positional arguments:
  root        Existing private Wake account root saved only for local
              shortcuts.

options:
  -h, --help  show this help message and exit

Examples:
  codex-wake --wake-root ROOT configuration default-root ROOT
```

## history recent

View the latest saved conversations for one permitted account.

Local shortcut to history.search with sort=recent and a bounded limit; API/MCP can use those same search arguments. Partial evidence stays visible.

Transport: Local human CLI only.

```sh
codex-wake --wake-root ROOT history recent --owner work --limit 10
```

### CLI help

```text
usage: codex-wake history recent [-h] --owner OWNER [--limit LIMIT] [--json]

View the latest saved conversations for one permitted account.

Local shortcut to history.search with sort=recent and a bounded limit; API/MCP can use those same search arguments. Partial evidence stays visible.

options:
  -h, --help     show this help message and exit
  --owner OWNER  Exact account that owns the saved conversation.
  --limit LIMIT  Maximum recent conversations, from1 to100 (default:10 for
                 shortcuts).
  --json         Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT history recent --owner work --limit 10
```

## history import-recent

Preview and copy a frozen recent-conversation selection.

Local batch orchestration over protected history.import. Retains exact intents and per-entry outcomes; same source revision/destination reuses the original copy. Requires both account daemons running; preview starts none.

Transport: Local human CLI only.

```sh
codex-wake --wake-root ROOT history import-recent --owner work --destination personal --limit 10
```

### CLI help

```text
usage: codex-wake history import-recent [-h] [--owner OWNER] [--limit LIMIT]
                                        [--json] [--destination DESTINATION]
                                        [--channel {stock,modded}]
                                        [--batch BATCH] [--yes] [--preview]

Preview and copy a frozen recent-conversation selection.

Local batch orchestration over protected history.import. Retains exact intents and per-entry outcomes; same source revision/destination reuses the original copy. Requires both account daemons running; preview starts none.

options:
  -h, --help            show this help message and exit
  --owner OWNER         Exact account that owns the saved conversation.
  --limit LIMIT         Maximum recent conversations, from1 to100 (default:10
                        for shortcuts).
  --json                Emit structured results for this command.
  --destination DESTINATION
                        Destination account for a distinct source-preserving
                        conversation copy.
  --channel {stock,modded}
                        Registered native build channel (default: modded).
  --batch BATCH         Exact frozen copy-batch ID to preview or retry without
                        selecting newer sessions.
  --yes                 Explicitly confirm the frozen source-preserving batch
                        copy.
  --preview             Show/save the frozen selection without native copying
                        or daemon starts.

Examples:
  codex-wake --wake-root ROOT history import-recent --owner work --destination personal --limit 10
```

## builds prepare

Prepare pinned source in an isolated worktree.

Native release work in isolated WSL state; no working-account installation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_prepare`).

```sh
codex-wake --wake-root ROOT builds prepare --recipe RECIPE --upstream SHA --mod-revision SHA
```

### CLI help

```text
usage: codex-wake builds prepare [-h] [--arguments ARGUMENTS]
                                 [--recipe RECIPE] [--upstream UPSTREAM]
                                 [--mod-revision MOD_REVISION]
                                 [--run-id RUN_ID]
                                 [--expected-cache EXPECTED_CACHE]
                                 [--jobs JOBS]
                                 [--output {compact,json,progress,diagnostics}]
                                 [--json] [--max-items MAX_ITEMS] [--confirm]

Prepare pinned source in an isolated worktree.

Native release work in isolated WSL state; no working-account installation.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --recipe RECIPE       Host-registered build recipe name, never an arbitrary
                        executable or path.
  --upstream UPSTREAM   Pinned upstream commit SHA.
  --mod-revision MOD_REVISION
                        Pinned retained mod commit SHA.
  --run-id RUN_ID       Durable native release run identifier.
  --expected-cache EXPECTED_CACHE
                        Exact cache fingerprint returned by cleanup preview.
  --jobs JOBS           Explicit maximum compiler jobs.
  --output {compact,json,progress,diagnostics}
                        Release result presentation.
  --json                Release result presentation.
  --max-items MAX_ITEMS
                        Maximum diagnostic or progress entries.
  --confirm             Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT builds prepare --recipe RECIPE --upstream SHA --mod-revision SHA
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `recipe` | yes | Host-registered build recipe name, never an arbitrary executable or path. |
| `upstream` | yes | Pinned upstream commit SHA. |
| `mod_revision` | yes | Pinned retained mod commit SHA. |
| `run_id` | no | Durable native release run identifier. |
| `jobs` | no | Explicit maximum compiler jobs. |
| `output` | no | Release result presentation. |
| `max_items` | no | Maximum diagnostic or progress entries. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `expected_cache` | no | Exact cache fingerprint returned by cleanup preview. |

## builds status

Inspect a durable native release run.

Native release work in isolated WSL state; no working-account installation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_status`).

```sh
codex-wake --wake-root ROOT builds status --run-id RUN
```

### CLI help

```text
usage: codex-wake builds status [-h] [--arguments ARGUMENTS] [--recipe RECIPE]
                                [--upstream UPSTREAM]
                                [--mod-revision MOD_REVISION]
                                [--run-id RUN_ID]
                                [--expected-cache EXPECTED_CACHE]
                                [--jobs JOBS]
                                [--output {compact,json,progress,diagnostics}]
                                [--json] [--max-items MAX_ITEMS] [--confirm]

Inspect a durable native release run.

Native release work in isolated WSL state; no working-account installation.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --recipe RECIPE       Host-registered build recipe name, never an arbitrary
                        executable or path.
  --upstream UPSTREAM   Pinned upstream commit SHA.
  --mod-revision MOD_REVISION
                        Pinned retained mod commit SHA.
  --run-id RUN_ID       Durable native release run identifier.
  --expected-cache EXPECTED_CACHE
                        Exact cache fingerprint returned by cleanup preview.
  --jobs JOBS           Explicit maximum compiler jobs.
  --output {compact,json,progress,diagnostics}
                        Release result presentation.
  --json                Release result presentation.
  --max-items MAX_ITEMS
                        Maximum diagnostic or progress entries.
  --confirm             Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT builds status --run-id RUN
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `recipe` | no | Host-registered build recipe name, never an arbitrary executable or path. |
| `upstream` | no | Pinned upstream commit SHA. |
| `mod_revision` | no | Pinned retained mod commit SHA. |
| `run_id` | yes | Durable native release run identifier. |
| `jobs` | no | Explicit maximum compiler jobs. |
| `output` | no | Release result presentation. |
| `max_items` | no | Maximum diagnostic or progress entries. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `expected_cache` | no | Exact cache fingerprint returned by cleanup preview. |

## builds build

Build a complete immutable package through Cargo Signal.

Native release work in isolated WSL state; no working-account installation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_build`).

```sh
codex-wake --wake-root ROOT builds build --run-id RUN
```

### CLI help

```text
usage: codex-wake builds build [-h] [--arguments ARGUMENTS] [--recipe RECIPE]
                               [--upstream UPSTREAM]
                               [--mod-revision MOD_REVISION] [--run-id RUN_ID]
                               [--expected-cache EXPECTED_CACHE] [--jobs JOBS]
                               [--output {compact,json,progress,diagnostics}]
                               [--json] [--max-items MAX_ITEMS] [--confirm]

Build a complete immutable package through Cargo Signal.

Native release work in isolated WSL state; no working-account installation.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --recipe RECIPE       Host-registered build recipe name, never an arbitrary
                        executable or path.
  --upstream UPSTREAM   Pinned upstream commit SHA.
  --mod-revision MOD_REVISION
                        Pinned retained mod commit SHA.
  --run-id RUN_ID       Durable native release run identifier.
  --expected-cache EXPECTED_CACHE
                        Exact cache fingerprint returned by cleanup preview.
  --jobs JOBS           Explicit maximum compiler jobs.
  --output {compact,json,progress,diagnostics}
                        Release result presentation.
  --json                Release result presentation.
  --max-items MAX_ITEMS
                        Maximum diagnostic or progress entries.
  --confirm             Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT builds build --run-id RUN
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `recipe` | no | Host-registered build recipe name, never an arbitrary executable or path. |
| `upstream` | no | Pinned upstream commit SHA. |
| `mod_revision` | no | Pinned retained mod commit SHA. |
| `run_id` | yes | Durable native release run identifier. |
| `jobs` | no | Explicit maximum compiler jobs. |
| `output` | no | Release result presentation. |
| `max_items` | no | Maximum diagnostic or progress entries. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `expected_cache` | no | Exact cache fingerprint returned by cleanup preview. |

## builds resume

Reconcile and resume a native release run.

Native release work in isolated WSL state; no working-account installation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_resume`).

```sh
codex-wake --wake-root ROOT builds resume --run-id RUN
```

### CLI help

```text
usage: codex-wake builds resume [-h] [--arguments ARGUMENTS] [--recipe RECIPE]
                                [--upstream UPSTREAM]
                                [--mod-revision MOD_REVISION]
                                [--run-id RUN_ID]
                                [--expected-cache EXPECTED_CACHE]
                                [--jobs JOBS]
                                [--output {compact,json,progress,diagnostics}]
                                [--json] [--max-items MAX_ITEMS] [--confirm]

Reconcile and resume a native release run.

Native release work in isolated WSL state; no working-account installation.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --recipe RECIPE       Host-registered build recipe name, never an arbitrary
                        executable or path.
  --upstream UPSTREAM   Pinned upstream commit SHA.
  --mod-revision MOD_REVISION
                        Pinned retained mod commit SHA.
  --run-id RUN_ID       Durable native release run identifier.
  --expected-cache EXPECTED_CACHE
                        Exact cache fingerprint returned by cleanup preview.
  --jobs JOBS           Explicit maximum compiler jobs.
  --output {compact,json,progress,diagnostics}
                        Release result presentation.
  --json                Release result presentation.
  --max-items MAX_ITEMS
                        Maximum diagnostic or progress entries.
  --confirm             Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT builds resume --run-id RUN
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `recipe` | no | Host-registered build recipe name, never an arbitrary executable or path. |
| `upstream` | no | Pinned upstream commit SHA. |
| `mod_revision` | no | Pinned retained mod commit SHA. |
| `run_id` | yes | Durable native release run identifier. |
| `jobs` | no | Explicit maximum compiler jobs. |
| `output` | no | Release result presentation. |
| `max_items` | no | Maximum diagnostic or progress entries. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `expected_cache` | no | Exact cache fingerprint returned by cleanup preview. |

## builds qualify

Qualify the exact package in disposable state.

Native release work in isolated WSL state; no working-account installation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_qualify`).

```sh
codex-wake --wake-root ROOT builds qualify --run-id RUN
```

### CLI help

```text
usage: codex-wake builds qualify [-h] [--arguments ARGUMENTS]
                                 [--recipe RECIPE] [--upstream UPSTREAM]
                                 [--mod-revision MOD_REVISION]
                                 [--run-id RUN_ID]
                                 [--expected-cache EXPECTED_CACHE]
                                 [--jobs JOBS]
                                 [--output {compact,json,progress,diagnostics}]
                                 [--json] [--max-items MAX_ITEMS] [--confirm]

Qualify the exact package in disposable state.

Native release work in isolated WSL state; no working-account installation.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --recipe RECIPE       Host-registered build recipe name, never an arbitrary
                        executable or path.
  --upstream UPSTREAM   Pinned upstream commit SHA.
  --mod-revision MOD_REVISION
                        Pinned retained mod commit SHA.
  --run-id RUN_ID       Durable native release run identifier.
  --expected-cache EXPECTED_CACHE
                        Exact cache fingerprint returned by cleanup preview.
  --jobs JOBS           Explicit maximum compiler jobs.
  --output {compact,json,progress,diagnostics}
                        Release result presentation.
  --json                Release result presentation.
  --max-items MAX_ITEMS
                        Maximum diagnostic or progress entries.
  --confirm             Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT builds qualify --run-id RUN
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `recipe` | no | Host-registered build recipe name, never an arbitrary executable or path. |
| `upstream` | no | Pinned upstream commit SHA. |
| `mod_revision` | no | Pinned retained mod commit SHA. |
| `run_id` | yes | Durable native release run identifier. |
| `jobs` | no | Explicit maximum compiler jobs. |
| `output` | no | Release result presentation. |
| `max_items` | no | Maximum diagnostic or progress entries. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `expected_cache` | no | Exact cache fingerprint returned by cleanup preview. |

## builds cleanup

Preview or explicitly clean an inactive build cache.

Native release work in isolated WSL state; no working-account installation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_cleanup`).

```sh
codex-wake --wake-root ROOT builds cleanup --run-id RUN
```

### CLI help

```text
usage: codex-wake builds cleanup [-h] [--arguments ARGUMENTS]
                                 [--recipe RECIPE] [--upstream UPSTREAM]
                                 [--mod-revision MOD_REVISION]
                                 [--run-id RUN_ID]
                                 [--expected-cache EXPECTED_CACHE]
                                 [--jobs JOBS]
                                 [--output {compact,json,progress,diagnostics}]
                                 [--json] [--max-items MAX_ITEMS] [--confirm]

Preview or explicitly clean an inactive build cache.

Native release work in isolated WSL state; no working-account installation.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --recipe RECIPE       Host-registered build recipe name, never an arbitrary
                        executable or path.
  --upstream UPSTREAM   Pinned upstream commit SHA.
  --mod-revision MOD_REVISION
                        Pinned retained mod commit SHA.
  --run-id RUN_ID       Durable native release run identifier.
  --expected-cache EXPECTED_CACHE
                        Exact cache fingerprint returned by cleanup preview.
  --jobs JOBS           Explicit maximum compiler jobs.
  --output {compact,json,progress,diagnostics}
                        Release result presentation.
  --json                Release result presentation.
  --max-items MAX_ITEMS
                        Maximum diagnostic or progress entries.
  --confirm             Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT builds cleanup --run-id RUN
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `recipe` | no | Host-registered build recipe name, never an arbitrary executable or path. |
| `upstream` | no | Pinned upstream commit SHA. |
| `mod_revision` | no | Pinned retained mod commit SHA. |
| `run_id` | yes | Durable native release run identifier. |
| `jobs` | no | Explicit maximum compiler jobs. |
| `output` | no | Release result presentation. |
| `max_items` | no | Maximum diagnostic or progress entries. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `expected_cache` | no | Exact cache fingerprint returned by cleanup preview. |

## builds run

Prepare, build and qualify one native release.

Native release work in isolated WSL state; no working-account installation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_builds_run`).

```sh
codex-wake --wake-root ROOT builds run --recipe RECIPE --upstream SHA --mod-revision SHA
```

### CLI help

```text
usage: codex-wake builds run [-h] [--arguments ARGUMENTS] [--recipe RECIPE]
                             [--upstream UPSTREAM]
                             [--mod-revision MOD_REVISION] [--run-id RUN_ID]
                             [--expected-cache EXPECTED_CACHE] [--jobs JOBS]
                             [--output {compact,json,progress,diagnostics}]
                             [--json] [--max-items MAX_ITEMS] [--confirm]

Prepare, build and qualify one native release.

Native release work in isolated WSL state; no working-account installation.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --recipe RECIPE       Host-registered build recipe name, never an arbitrary
                        executable or path.
  --upstream UPSTREAM   Pinned upstream commit SHA.
  --mod-revision MOD_REVISION
                        Pinned retained mod commit SHA.
  --run-id RUN_ID       Durable native release run identifier.
  --expected-cache EXPECTED_CACHE
                        Exact cache fingerprint returned by cleanup preview.
  --jobs JOBS           Explicit maximum compiler jobs.
  --output {compact,json,progress,diagnostics}
                        Release result presentation.
  --json                Release result presentation.
  --max-items MAX_ITEMS
                        Maximum diagnostic or progress entries.
  --confirm             Confirm the displayed scoped effect; does not override
                        a changed target.

Examples:
  codex-wake --wake-root ROOT builds run --recipe RECIPE --upstream SHA --mod-revision SHA
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `recipe` | no | Host-registered build recipe name, never an arbitrary executable or path. |
| `upstream` | no | Pinned upstream commit SHA. |
| `mod_revision` | no | Pinned retained mod commit SHA. |
| `run_id` | no | Durable native release run identifier. |
| `jobs` | no | Explicit maximum compiler jobs. |
| `output` | no | Release result presentation. |
| `max_items` | no | Maximum diagnostic or progress entries. |
| `confirm` | no | Confirm the displayed scoped effect; does not override a changed target. |
| `expected_cache` | no | Exact cache fingerprint returned by cleanup preview. |

## migration preview

Preview the existing host-selected migration or independent-profile adoption.

Host migration strategy adopt_independent preserves history, sign-ins and local settings; no effect in preview.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_migration_preview`).

```sh
codex-wake --wake-root ROOT migration preview
```

### CLI help

```text
usage: codex-wake migration preview [-h] [--arguments ARGUMENTS] [--json]

Preview the existing host-selected migration or independent-profile adoption.

Host migration strategy adopt_independent preserves history, sign-ins and local settings; no effect in preview.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT migration preview
```

## migration apply

Apply a pinned qualified migration or independent-profile adoption.

Local CLI uses operator authority; API/MCP require scoped grants. Mutations retain exact pins, durable intent and rollback custody.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_migration_apply`).

```sh
codex-wake --wake-root ROOT migration apply --arguments "$ARGUMENTS"
```

### CLI help

```text
usage: codex-wake migration apply [-h] [--arguments ARGUMENTS] [--json]

Apply a pinned qualified migration or independent-profile adoption.

Local CLI uses operator authority; API/MCP require scoped grants. Mutations retain exact pins, durable intent and rollback custody.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT migration apply --arguments "$ARGUMENTS"
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |

## migration rollback

Roll back one attributable unchanged migration or adoption.

Preserves changed targets and uncertain outcomes for reconciliation.

Transport: CLI / API / OAuth MCP / native MCP (`wake_controller_migration_rollback`).

```sh
codex-wake --wake-root ROOT migration rollback --arguments "$ARGUMENTS"
```

### CLI help

```text
usage: codex-wake migration rollback [-h] [--arguments ARGUMENTS] [--json]

Roll back one attributable unchanged migration or adoption.

Preserves changed targets and uncertain outcomes for reconciliation.

options:
  -h, --help            show this help message and exit
  --arguments ARGUMENTS
                        Advanced JSON object of operation arguments; preserved
                        for scripts. See generated command reference.
  --json                Emit structured results for this command.

Examples:
  codex-wake --wake-root ROOT migration rollback --arguments "$ARGUMENTS"
```

| Argument | Required remotely | Meaning |
|---|---|---|
| `expected_target` | yes | Exact target JSON from the corresponding resolve, list or status command; replacement is refused. |
| `receipt_id` | yes | Exact prior migration receipt for a qualified rollback. |
| `_request` | yes | Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target. |


## Local session controller

See [workflow](local-session-control.md) and generated [transport contract](local-controller-contract.json).

| CLI | API operation | Local MCP |
|---|---|---|
| `control create` | `local.create` | `wake_local_create` |
| `control load` | `local.load` | `wake_local_load` |
| `control prompt` | `local.prompt` | `wake_local_prompt` |
| `control output` | `local.output` | `wake_local_output` |
| `control result` | `local.result` | `wake_local_result` |
| `control cancel` | `local.cancel` | `wake_local_cancel` |
| `control list` | `local.list` | `wake_local_list` |
| `control resolve` | `local.resolve` | `wake_local_resolve` |
| `control health` | `local.health` | `wake_local_health` |
| `control slash list` | `local.slash.list` | `wake_control_slash_list` |
| `control slash run` | `local.slash.run` | `wake_control_slash_run` |
| `control slash result` | `local.slash.result` | `wake_control_slash_result` |
| `control slash respond` | `local.slash.respond` | `wake_control_slash_respond` |
| `control slash cancel` | `local.slash.cancel` | `wake_control_slash_cancel` |
| `self-limits show` | `local.self_limits.show` | `wake_self_limits_show` |
| `self-limits set` | `local.self_limits.set` | `wake_self_limits_set` |
