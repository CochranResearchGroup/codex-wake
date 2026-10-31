# Source-bound validation

For #356 / parent specification #350, run existing CI or host acceptance commands
through `scripts/validate_candidate.py` when their success gates a later automated
step. This is an operator development tool; it does not deploy, renew an allocation,
or authorize the commands in its manifest.

Create a manifest outside the candidate, for example:

```json
{
  "checks": [
    {
      "name": "undefined names",
      "axis": "ci",
      "argv": ["{runtime}", "-m", "ruff", "check", "--select", "F821,F822,F823", "src", "scripts", "tests", ".codex/hooks"]
    },
    {
      "name": "policy wiring",
      "axis": "policy",
      "argv": ["{runtime}", "scripts/check_policy_wiring.py"]
    }
  ],
  "on_success": []
}
```

```sh
python scripts/validate_candidate.py --repo "$PWD" \
  --runtime /absolute/selected-prefix/bin/python \
  --manifest /tmp/candidate-checks.json --receipt /tmp/candidate-checks-receipt.json
```

Use commands from `.github/workflows/ci.yml` and the existing public host acceptance
scripts for the relevant surface. This runner wraps their outcomes rather than
implementing another version of their checks. `{runtime}` expands to the absolute
invocation path, preserving virtual-environment selection. `--timeout` bounds each
command in seconds (default 300). Commands run from the candidate's Git root and
inherit the runner environment. Commands must report their own failures correctly;
an explicitly supplied shell program remains responsible for its exit status.

Every check is required by default. A required failure stops later checks and all
`on_success` actions, exits nonzero, and records its exact argv, exit code, stdout
and stderr. Unexecuted steps remain `BLOCKED`. Optional checks (`"required": false`)
retain their individual failure without blocking required checks; a run-level
`PASS` means its required checks and success actions passed, not that every axis
passed. Success actions stop on their first failure even if marked optional.

The new receipt is exclusively created outside the candidate; rerunning requires a
new receipt path and cannot overwrite an earlier failure. It binds outcomes to Git
HEAD, index digest, working content digest, dirty status and exact dirty paths,
selected runtime invocation/resolved path and binary digest, manifest digest, virtual environment `pyvenv.cfg` digest (or its absence),
platform, runner Python version, and a digest of the complete inherited environment.
Environment values are not published. Keep the environment/configuration used for
reproduction separately under its existing controls.

Source identity covers tracked and nonignored untracked files, modes, deletions,
and regular-file symlink targets. Ignored build artifacts are excluded. Submodule
candidates and directory/dangling symlinks fail qualification; validate those sources
separately. Checks must leave the candidate unchanged, including creating new
nonignored files. Put logs and artifacts outside it or in established ignored paths.
The manifest may list additional `runtime_files` paths (absolute or relative to the
candidate) to fingerprint external configuration or pinned dependency metadata.
External dependencies/configuration must be pinned by the existing acceptance
command; the runtime binary digest does not certify every dependency or remote host.

Identity is checked before and after each check and before each success action.
Detected source, manifest or runtime changes invalidate prior passing check results
and block remaining actions. This is drift detection, not a filesystem lock or a
sandbox against a command that changes and restores files during one check. For
concurrent editors, validate a dedicated immutable checkout. A success action may
intentionally commit the qualified candidate; receipts refer to the source identity
before that action. A source-changing action cannot precede another success action
without invalidating validation. Interrupted runs retain `FAIL` with the interrupted
step `RUNNING`; they cannot become passing by rerun overwrite.

## Repository local profile (#441 / specification #439)

Use one entrypoint with an explicitly selected Python 3.11 or 3.12 environment:

```sh
/absolute/validation-prefix/bin/python scripts/local_validation.py \
  --repo "$PWD" --runtime /absolute/validation-prefix/bin/python \
  --tier presubmit --receipt /private/evidence/new-presubmit.json
```

Provision a separate disposable validation environment beforehand with `.[dev,mcp]`,
`build>=1,<2`, `setuptools>=68` and `wheel>=0.41`. Do not add tooling to the working installation.
The command installs nothing and downloads no dependencies. Setup preflight reads
`pyproject.toml`, checks declared dependency constraints (including `ruff==0.14.2`),
and reports missing or incompatible tools separately as the first named check.
Its stdout records the selected executable, prefix, Python and dependency versions.
A missing `packaging` dependency explicitly blocks constraint verification.

`scripts/local_validation_profile.json` owns these serial, bounded tiers:

| Tier | Selection | Budget |
| --- | --- | --- |
| `focused` | Setup, pinned lint, policy wiring, active planning audit, runner, local profile, cleanup and summary public regressions | 600 seconds per check; 80 minutes total maximum |
| `presubmit` (default) | Focused checks plus compilation and package build | 600 seconds per check; 100 minutes total maximum |
| `comprehensive` | Setup, lint, policy, planning, compilation, full Python unittest discovery and package build | 600 seconds per check; 70 minutes total maximum |

All tiers use one serial process slot; checks may launch their normal subprocesses.
The local launcher defaults to 600 seconds per check: the full Python suite has
measured 350.623 seconds, exceeding the underlying runner's 300-second default.
`--timeout SECONDS` changes the per-check bound and therefore the total bound.
Receipts record the selected bound as `timeout_seconds`.
Use `comprehensive` for unknown Python impact and periodic comprehensive regression;
focused/presubmit selection proves this developer-tool surface, not the full suite.
The existing audit invocation is
`.codex/skills/repo-policy-selector/scripts/audit_planning_contract.py --repo-root . --active-only --json`.
It retains the explicit historical exceptions in
`docs/dev/planning-audit-baseline.json`; this profile does not normalize old plans.

The launcher creates fresh private HOME, XDG config/state/cache/data/runtime,
CODEX_HOME and temporary directories outside the candidate. It clears inherited
account/provider configuration and passes only PATH, locale and platform essentials,
plus explicit source import and isolated bytecode paths. Compilation writes caches
outside the candidate. Packaging snapshots Git candidate files outside the checkout
and runs the existing `python -m build --no-isolation` there. Build artifacts and
isolated state are temporary; the durable evidence is the private receipt. This is
local process isolation, not an OS security sandbox. Do not select live tests or
supply secrets to validation commands.

The launcher generates an explicit argv manifest and delegates all check execution,
failure/timeout handling and source/runtime/manifest drift detection to #356's
`scripts/validate_candidate.py`. The default profiles contain no success actions.
A custom `--profile PATH` selects the same tier keys for bounded local fixture or
changed-surface checks; it has the same authority limits. It cannot add success
actions through this launcher.

Receipts remain schema 1, exclusively created with mode `0600`. Their existing
`source`, `runtime`, `environment`, `manifest_sha256`, `checks`, `actions`, `failure`
and status fields retain their meanings. An additive `profile` field records the
profile locator, tier and material hosted-environment differences; the profile file
is also bound through `runtime.files`. Check argv arrays preserve the complete
selection, and setup stdout preserves versions. Required failures stop later checks;
corrected runs need a new receipt. No environment values are dumped, but check
stdout/stderr can contain sensitive output, so keep all receipts private.

Passing documented local checks satisfies the CI cost policy. Material differences
from hosted Actions are explicit: local OS and selected runtime, no hosted execution,
no dependency downloads during validation, no OpenClaw/plugin checks, no installed
wheel or legacy-package smoke, and no provider/native/live acceptance. Those excluded
surfaces require separate applicable authority and evidence; a tier PASS does not
certify them. The command performs no commit, push, merge, installation or publication.

## Prevention command navigation (#443)

Use [guarded worktree cleanup](worktree-cleanup.md) for read-only planning and
separately authorized exact apply. Its disposable public tests compose real plan
and result files with the summary CLI, checking held uncertainty, exact removal,
custody and peer preservation. OS observation substitution is fixture-only; it
proves denial handling, not completeness of the working host's process visibility.

Inspect private receipts without printing their raw logs:

```sh
/absolute/validation-prefix/bin/python scripts/summarize_receipt.py /private/evidence/receipt.json
/absolute/validation-prefix/bin/python scripts/summarize_receipt.py /private/evidence/receipt.json --entry ENTRY_ID_OR_EXACT_NAME
```

The supported inputs are candidate-validation schema 1 and cleanup schema
`codex-wake.cleanup.v1` plan/result records. The default output is at most 8192
UTF-8 bytes. Counts, source digest, explicit omissions and bounded exception IDs
survive large inputs; arbitrary names and paths are represented by SHA256 IDs.
Use those IDs for exact drill-down. Summary success means rendering succeeded;
a HELD/FAIL receipt remains HELD/FAIL. Unsupported or malformed input exits
nonzero. Original receipt bytes remain authoritative and unchanged. Keep raw
receipts and first-failure logs outside the candidate in private user state;
summary output is a derived view, not publication or cleanup authority.

The focused and presubmit profiles include all four relevant public regression
files: runner, local profile, cleanup and summary. The existing local-profile
regression creates a malformed real planning header, proves planning FAIL blocks
the later check, then corrects it and passes with a fresh receipt while preserving
the first failure. Independent axes remain separate in the receipt. Neither
profile constitutes comprehensive or installed/live acceptance.
