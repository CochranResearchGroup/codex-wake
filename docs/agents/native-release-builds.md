# Native release builds

The release driver prepares, builds and qualifies a Codex mod in isolated WSL
state. WSL and PowerShell clients use the same controller operations. A successful
run ends at a qualified package; it does not install, select, restart or clean up
anything on a working account.

## Start and inspect a run

Use full upstream and retained-mod commit SHAs. `prepare` creates a detached
worktree and generates the run manifest. Integration conflicts leave that worktree
available for resolution, before compilation starts.

```sh
codex-wake --wake-root "$ROOT" builds run --recipe native \
  --upstream "$UPSTREAM_SHA" --mod-revision "$MOD_SHA"
codex-wake --wake-root "$ROOT" builds status --run-id "$RUN_ID"
codex-wake --wake-root "$ROOT" builds status --run-id "$RUN_ID" --output progress
codex-wake --wake-root "$ROOT" builds status --run-id "$RUN_ID" --output diagnostics --max-items 4
```

`run` starts a detached coordinator and returns a durable run ID. The coordinator
advances existing build and qualification stages without keeping the terminal
connected. Calling `run` again with that run ID observes the same active worker.
Supply either a run ID or the three source-selection arguments, never both.
`prepare`, `build`, `qualify`, `status` and `resume` also remain individual commands.

The defaults retain compact structured receipts; `--json` / `--output json`
includes the manifest and attempt history. `progress` returns bounded recorded
events; `diagnostics` returns bounded diagnostic entries. Full stdout and stderr
stay in private Cargo Signal job artifacts rather than being streamed into model
context. Preserve the manifest path and run ID for recovery.

For remote clients, use `controller remote` with the configured service endpoint
and private token file. For example, from PowerShell with its installed client:

```powershell
codex-wake controller remote --endpoint $Endpoint --token-file $TokenFile `
  builds.status --arguments ('{"run_id":"' + $RunId + '","output":"progress"}')
```

API `/operations` uses operation `builds.run` and the same arguments. OAuth/native
MCP exposes `wake_builds_run` and the corresponding stage/status tools. Existing
host-local versus scoped remote admission applies; no token grants installation.

## Host recipe registration

The existing fixed account registry supplies trusted recipe names:

```toml
[builds]
manifest = "/HOST/private/builds.json"
[builds.recipes]
native = "/HOST/private/native-recipe.json"
```

A recipe is host configuration, not a caller-selected executable. Ordinary build
requests choose its name and pinned source commits; the run manifest is generated
automatically. Its source repository must already contain those commits. Keep
recipes, run storage and logs private. Ensure the service's PATH resolves the
intended Python, Rust toolchain and Cargo Signal executables.

A native recipe uses the maintained package assembler rather than an independent
list of Cargo binary targets. A representative build step is:

```json
{
  "source_repository": "/HOST/source/codex",
  "target": "x86_64-unknown-linux-gnu",
  "profile": "dev-small",
  "target_directory": "codex-rs/target",
  "package_directory": "codex-rs/target/native-package",
  "max_jobs": 4,
  "workflow_timeout_seconds": 7200,
  "preflight": {"executables": ["cargo", "rustc", "python", "cargo-signal"]},
  "build_steps": [{
    "name": "package",
    "argv": ["/usr/bin/env", "CODEX_REPO_ROOT=.", "python", "scripts/build_codex_package.py", "--target", "x86_64-unknown-linux-gnu", "--cargo-profile", "dev-small", "--package-dir", "codex-rs/target/native-package"]
  }]
}
```

Read the selected upstream assembler's current help before registering its flags.
Add affected compiler/test and schema-generation steps before packaging when
needed. Each step can declare `inputs`, `outputs` and `depends_on`; dependencies
default to the preceding step, and `[]` declares independence. Explicit input
lists must cover all causal inputs. Generated outputs should not accidentally
become inputs of their own stage. Stages sharing a target directory are serialized.
Compiler job limits are selected conservatively from memory and competing builds;
`--jobs` records an explicit override.

The host recipe must also declare `qualification.environment` and helper `steps`.
Use `kind=separate_uid` with the approved test UID, or `disposable_wsl`; these share
host kernel/resources where applicable. `owned_fixture` is for source tests and
is explicitly labelled `fixture_only`. Install the selected package's declared
MCP/development extras and required helper assets before qualification.

Qualification helper argv can reference `{package}`, `{run_dir}`, `{report}` and
`{run_id}`. Helpers must produce fresh normalized reports with schema version1,
state `passed`, the actual UID, the exact package inventory digest, zero external
model calls, an empty final owned-process list, and successful checks covering
history, active/multiclient, reconnect, private ownership, upgrade, rollback and
failed-start recovery. A zero process exit without this evidence is insufficient.
Use existing acceptance helpers and normalize their observed assertions; never
synthesize a passing report for missing evidence. Protect external fixture roots,
rollback packages and evidence using the recipe's `protected_paths`,
`rollback_artifacts` and `evidence_paths` lists.

Verified retained packages may be registered with exact file hashes and a binding
to source revision, target, profile and features. Reuse is explicitly reported;
missing historical compiler provenance remains a gap, not a reproducibility
claim. Final acceptance verifies package hashes before and after qualification.

## Recovery and cleanup

`status` observes recorded workers and Cargo Signal jobs without submitting work.
Failed or unknown outcomes stop automatic orchestration. A missing worker or lost
submission response is not permission to launch a duplicate.

```sh
codex-wake --wake-root "$ROOT" builds resume --run-id "$RUN_ID"
codex-wake --wake-root "$ROOT" builds run --run-id "$RUN_ID"
```

Resolve and commit a conflicted isolated worktree first, retaining the pinned
upstream integration. Explicit resume reconciles prior jobs, checks relevant
inputs and output hashes, and reruns affected stages and their dependents.
Failed attempts remain in receipts. Unaffected verified work remains reusable.
When an outcome is still unknown, inspect its retained job/receipt rather than
repeatedly submitting. A running orchestration worker retains control until it
finishes or is reconciled.

Normal builds preserve caches. Cleanup is an explicit, separate operation:

```sh
codex-wake --wake-root "$ROOT" builds cleanup --run-id "$RUN_ID"
codex-wake --wake-root "$ROOT" builds cleanup --run-id "$RUN_ID" \
  --expected-cache "$PREVIEW_FINGERPRINT" --confirm
```

The preview must identify an owned inactive cache. A changed identity, relevant
writer/reference, unresolved job, or protected artifact prevents deletion. A
failed preflight invokes no cleanup. A package inside a cache remains protected;
archive or retain complete rollback/package evidence according to the existing
storage workflow before retiring such a cache.

Run locally required checks and retain source identity, commands, results,
artifact hashes and environment differences. Hosted GitHub Actions are not
required or funded. Source validation, disposable runtime qualification,
integration and working-host deployment remain separate evidence boundaries.
