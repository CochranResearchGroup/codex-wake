# Accounts, daemons and saved conversation import

Codex Wake owns the account registry, configuration explanation, immutable build
selection, daemon lifecycle and history transfer. `profiles` and the older
`codex-stock`/`codex-modded` launchers remain compatibility entrypoints.

## Set up isolated accounts

Choose a new private Wake root. This creates empty account homes; it does not
log in, copy credentials, adopt legacy homes or migrate existing conversations.

```sh
codex-wake --wake-root "$LAB" accounts init
codex-wake --wake-root "$LAB" accounts create alice --alias work
codex-wake --wake-root "$LAB" accounts create bob
codex-wake --wake-root "$LAB" accounts list
codex-wake --wake-root "$LAB" configuration explain work
```

The fixed registry is `$LAB/controller-accounts.toml`. Homes are private under
`$LAB/accounts`; `shared/config.toml`, `shared/skills` and `shared/rules` provide
explicit common assets. Native account credentials remain local to each home.
`configuration explain` reports settings, skills and MCP provenance, including
scoped overrides and independent account/MCP identity. Shared edits apply to
subsequent launches. Native clients may persist their own shared UI preferences;
that changes the configuration revision and requires a fresh operation pin.

The host installation supplies `[builds].manifest` in that same registry, with
immutable stock/modded packages, hashes, read-schema compatibility and
`backend="managed"`. Existing `builds stage/select/rollback` operations own
catalog/promotion behavior. This registry is host configuration, not a second
account database. Creation preserves unrelated configuration; unsafe existing
homes, shared mutable runtime state and restricted account admission are refused.

## Sign in by account name

After the host's build manifest is configured, Wake selects the private home and
registered native executable for you:

```sh
codex-wake --wake-root "$LAB" accounts login alice
codex-wake --wake-root "$LAB" accounts status alice
```

Login creates a missing named account through the existing account owner and opens
native browser sign-in. For headless use, add `--device-auth`; device login must
be allowed by your OpenAI account/workspace. Both commands default to the modded
channel, with `--channel stock` available. Status returns native exit code1 when
signed out. Interactive sign-in is local CLI only, with native stdio and exit status.

For an API key, pass `--with-api-key` and supply the key on stdin. Wake strips
inherited account-auth overrides, persists the account-scoped file-store policy
for future daemon/client launches, and never captures credential input. Native
credentials are stored in that home's `auth.json`. A private client, existing
managed endpoint or active daemon operation holds login until the operator closes
or stops that selected account explicitly. Status remains readable while clients
run. These commands do not start or restart a daemon. Browser/device confirmation
is still the human account owner's action; simulated tests are not real sign-in.

## Manage exact daemon instances

```sh
codex-wake --wake-root "$LAB" daemons list
codex-wake --wake-root "$LAB" daemons status work --channel modded
```

Status returns `result.daemon.target`: account/home generation, configuration
revision, immutable build hash, native process birth/boot and socket generation.
`state=unavailable` means no verified endpoint, not proof that no orphan exists.
`selected_build_running` distinguishes the requested build from the actual peer.
Accounts are synthetic/unverified until separately authenticated.

For each mutation, pass the exact observed target and a distinct intent key:

```sh
codex-wake --wake-root "$LAB" daemons start work --channel modded \
  --expected-target "$TARGET" --idempotency-key start-alice
codex-wake --wake-root "$LAB" daemons restart work --channel modded \
  --expected-target "$CURRENT_TARGET" --idempotency-key restart-alice --yes
```

`restart`, `update` and `stop` require explicit `--yes` for the selected scope.
No other account daemon is selected. Native package bootstrap/update uses the
supported manager; Wake checks the actual socket peer, executable bytes and home.
A changed target is refused. The same key and immutable inputs return the
original operation; different inputs conflict. `phase=uncertain` is retained and
must be reconciled, never interpreted as permission to replay. Daemon failures
include a bounded private diagnostic in the operation response.

An update while stopped selects the package with `activation=future_start`;
use a new status pin and `daemons start` to run it. An update while running must
establish the requested running build. The qualified stock→modified return uses
an explicit stock stop, modified update, then modified start. Hot coordinated
return from the official stock daemon is unsupported by the modified updater;
Wake preserves that refusal rather than silently stopping it. Keep the peer's
process/socket/build identity and saved conversation visible through the change.

Use `builds list --arguments '{"account":"work"}'` to obtain a build target.
`builds launch --arguments JSON` accepts that exact account/channel/target plus
native client arguments, e.g. `args:["resume","NATIVE_UUID"]`. Managed clients
attach to their verified account daemon. Build selection, native daemon package
selection and a running process are separate observations.

## Copy a completed saved conversation

Search/read through `history search` and `history read UUID --owner SOURCE`.
Pin `result.session.target` as `SOURCE_TARGET`. Obtain the destination daemon's
current target as `DESTINATION_TARGET`, then run:

```sh
codex-wake --wake-root "$LAB" history import "$THREAD" \
  --owner alice --destination bob --channel modded \
  --expected-source "$SOURCE_TARGET" --expected-target "$DESTINATION_TARGET" \
  --idempotency-key import-alice-to-bob
```

Both daemons must be verified running builds. Initial support is completed,
idle, goal-free legacy JSONL history (native schema5); active, incomplete,
paginated/compressed or goal-bearing sources are refused. Native Codex creates a
new destination UUID from a private immutable snapshot. Wake retains source
account/UUID/revision provenance, verifies the copied native turns, and confirms
that the source is unchanged. The new conversation appears in destination native
history and opens using its ordinary resume interface. Existing `history resume`
continues to use the original owner; import transfers no goals, grants or allowance.
Repeated identical import intent returns the same child. Unknown results remain
held in the existing operation journal without another native fork.

## API, MCP and acceptance

CLI adapters, `/operations`, OAuth MCP and native stdio MCP use the same owners.
Protected mutations require durable `_request` metadata and scoped grants:
`admin` plus an exact registry target for account setup; `control` plus an exact
daemon target for lifecycle; `history.observe` on the pinned source and `control`
on the destination for import. Native stdio uses an explicit host-local grant.
An account observation grant does not grant mutation. Expiry/revocation is checked
before observation and disclosure.

Provider-free source regressions run in the local presubmit profile as
`test_controller*.py`. Full installed qualification is opt-in:

```sh
sudo -n -u codex-daemon-test unshare -Urn TEST_PREFIX/bin/python \
  scripts/controller_product_acceptance.py --root NEW_TEST_ARTIFACT_DIR \
  --modded COMPLETE_MODIFIED_PACKAGE --stock COMPLETE_OFFICIAL_PACKAGE \
  --outer-netns "$(readlink /proc/self/ns/net)"
```

The script retains synthetic history, command/RPC receipts, native TUI captures
and cleanup outcomes. It creates no model turns or production credentials and
blocks external network access. Only its own processes may be cleaned. UID1017
shares the host kernel/resources; this is not real authenticated-account or
working-host acceptance. [Plan0195](../dev/plans/0195-2026-11-02-product-acceptance.md)
owns the product demonstration; live migration remains separately gated.
