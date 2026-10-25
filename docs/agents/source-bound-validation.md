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
