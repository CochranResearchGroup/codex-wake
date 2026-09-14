# Plan 0055: Signal Readiness And Lifecycle Productization

Status: CLOSED

Issue: `CochranResearchGroup/codex-wake#9`

Branch: `feat/issue-9-signal-productization`

## Outcome

Make the accepted filesystem and GitHub signal substrate supportable through
separate source and dispatch readiness, bounded evidence export, protected
journal lifecycle, compatibility tests, and disposable package acceptance.

## Current state

Accepted through PR #28 on `origin/main` merge
`73e775362bac0043e3852b25bbcd6d0c1c86530e`. The implementation adds installed
filesystem source reconstruction, source-specific readiness, sanitized support
export, cleanup protection diagnostics, compatibility regressions, and
package-level signal acceptance. The bounded review-repair cycle, primary
enumeration-bound reconciliation, distinct baseline-to-candidate upgrade, both
release gates, merge, and issue closure are accepted. No live or installed user
runtime was authorized or changed.

## Scope and acceptance

- Report signal capability and each configured source's health independently
  from target dispatch readiness in doctor, monitor, and product-readiness.
- Export a deterministic, size-bounded support artifact containing sanitized
  configuration/state/evidence and no raw provider payloads, secrets, or file
  contents.
- Protect active anchors, checkpoints, reservations, and evidence pins during
  retention and cleanup, with actionable repair diagnostics.
- Test schema migration and interrupted recovery, explicit downgrade behavior,
  and mixed-version supervisor/reader capability without weakening v1 support.
- Build a wheel and use disposable environments to verify clean install,
  upgrade, restart, source observation, resolution, inspection, export,
  retention, and retirement for filesystem and fixture-backed GitHub paths.
- Extend package and public-tag smoke definitions so the signal substrate is
  covered without enabling a source, creating a tag, or touching the installed
  user runtime.

## Non-goals and gates

No live GitHub access, public listener, secret provisioning, live dispatch,
installed-user-runtime mutation or cleanup, deployment, public tag, release,
or installation refresh. Provider and target readiness remain separate facts.

## Execution and ownership

Use one `gpt-5.6-sol` high implementation worker because lifecycle migration
and authority boundaries dominate this otherwise mixed mechanical slice. The
primary retains schema, authority, integration, and final acceptance. Run one
fresh `gpt-5.6-luna` medium read-only review after focused and disposable
package tests pass; allow one bounded repair cycle.

## Definition of done

Issue #9 criteria are satisfied by provider-free tests and disposable package
receipts, both release-gate jobs pass on the linked pull request, and the merge
and closure are read back from current `origin/main`. Every gated effect is
listed as unexecuted.

## Implementation receipt

- Doctor, monitor, and product-readiness now report provider-neutral signal
  capability, journal compatibility, and each configured source separately
  from dispatch-target readiness. Inspection opens an existing journal
  read-only and does not create or migrate it.
- `codex-wake support export` writes an atomic, deterministic, bounded JSON
  artifact containing allowlisted signal state and evidence references. It
  excludes prompt text, targets, idempotency keys, credentials, raw provider
  payloads, and file contents.
- Cleanup inspection now reports protected signal records and actionable repair
  guidance. Existing active-anchor and evidence pins, receipt compaction floors,
  source checkpoints, and registration retirement remain journal-governed.
- The daemon reconstructs filesystem adapters from durable pending v2 records;
  no source is enabled without an explicit durable arm. Supervisor health
  carries per-source reconciliation results while dispatch remains separately
  gated.
- Filesystem state receipts are isolated by each arm's registration baseline.
  Late `exists` arms can observe a currently present file, `created` arms cannot
  consume a pre-registration creation, delete/recreate remains valid, unchanged
  polls remain receipt-quiescent, and equally eligible same-kind arms still
  fan out from one receipt. Evaluator baseline matching is explicitly limited
  to filesystem `state`/`becomes`; unrelated state sources retain their prior
  behavior.
- The product smoke definition now exercises clean wheel install, a persisted
  filesystem arm, forced wheel reinstall and daemon restart, provider-free
  observation to `firing` with dispatch disabled, inspection, support export,
  cancel/archive/retention cleanup, and a fixture-backed GitHub match. The same
  surface is used by public-tag smoke without creating a tag or enabling a
  source outside the disposable root.

## Validation receipts

Executed on 2026-09-14 in the issue worktree:

- Focused signal and integration tier:
  `PYTHONPATH=src python -m unittest tests.test_signal_support tests.test_filesystem_signals tests.test_signal_store tests.test_signal_records tests.test_records tests.test_monitor tests.test_product_readiness tests.test_daemon tests.test_supervisor tests.test_cli`
  -> `Ran 164 tests`, `OK`.
- Comprehensive Python tier:
  `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`
  -> `Ran 299 tests`, `OK`.
- OpenClaw plugin tier:
  `npm --prefix plugins/openclaw-codex-wake test` -> `12` passed, `0`
  failed.
- Package build and clean install:
  `uv build --wheel --out-dir /tmp/codex-wake-issue9-smoke.7ayB2F/dist`
  followed by installation into a fresh venv -> built and installed
  `codex-wake-0.5.2` successfully. `python -m build` was unavailable in the
  development interpreter (`No module named build`), so the repository's
  available `uv build` frontend supplied the equivalent wheel build.
- Candidate reinstall lifecycle after forced wheel reinstall and daemon restart
  (useful lifecycle evidence, but superseded as upgrade evidence by the
  distinct-artifact receipt below):
  `python scripts/product_smoke.py --codex-wake-bin /tmp/codex-wake-issue9-smoke.7ayB2F/venv/bin/codex-wake --codex-waked-bin /tmp/codex-wake-issue9-smoke.7ayB2F/venv/bin/codex-waked --artifact-dir /tmp/codex-wake-issue9-smoke.7ayB2F/artifacts-restart --upgrade-wheel /tmp/codex-wake-issue9-smoke.7ayB2F/dist/codex_wake-0.5.2-py3-none-any.whl --json`
  -> exit `0`; filesystem status `firing`, dispatch attempted `false`, support
  artifact `1966` bytes, upgrade restart `true`, archived cleanup deleted
  `true`, fixture GitHub status `matched` with `1` receipt.
- Syntax validation: `python -m py_compile scripts/product_smoke.py
  src/codex_wake/*.py` -> exit `0`.

The required RED receipts included the late `file.exists` arm observing zero
receipts, the post-creation `file.created` arm incorrectly matching, missing
support module and CLI surfaces, absent default daemon reconstruction, and the
initial disposable smoke losing reader capability when run as one-shot. Each
failed before its bounded repair and is covered by the green tiers above.

## Review and repair receipt

The single bounded issue #9 review-repair cycle accepted and repaired four
findings without changing the journal schema or enabling a source:

- Support export resolves and rejects destinations equal to or below the wake
  root before directory creation or file access. Direct and CLI regressions
  prove attempted journal replacement leaves journal bytes and readiness
  unchanged.
- Support export enforces hard ceilings of 100 requested wakes, 1 MiB output,
  2,048 enumerated directory entries, 512 retained input paths, 64 KiB read
  per record, and 128 source instances.
  A bounded deterministic path selection replaces eager archive loading; the
  artifact reports pre-read, oversized, invalid, and unreadable omissions
  without including rejected content.
- Default source reconstruction receives explicit process-loop phase. The
  first daemon or supervisor pass is `startup`, later loop passes are
  `periodic`, and one-shot execution remains `startup`.
- Reconciliation health is emitted and persisted by exact
  `(source, source_instance)`. Instance readiness cannot copy a sibling's
  result; legacy aggregate-only health blocks on degradation and otherwise
  warns because it cannot establish instance readiness.
- Primary reconciliation found that retained-path and read limits still left
  directory enumeration unbounded. The accepted bounds finding was completed
  in the same repair cycle by capping enumeration at 2,048 entries and emitting
  explicit `scan_truncated` and incomplete-count evidence; its focused
  regression passes.

Review RED command:
`PYTHONPATH=src python -m unittest tests.test_signal_support tests.test_filesystem_signals tests.test_cli`
-> `72` tests run with the expected missing ceiling constants, missing
`signal_reconcile_reason`, and unsafe journal replacement failure.

Focused repair command:
`PYTHONPATH=src python -m unittest tests.test_signal_support tests.test_filesystem_signals tests.test_signal_store tests.test_signal_records tests.test_monitor tests.test_daemon tests.test_supervisor tests.test_cli`
-> `Ran 147 tests`, `OK`.

Distinct-artifact disposable upgrade receipt:

- Local `origin/main` baseline commit:
  `bf05bb8c027e1b4451d1bbc8065a5ab39112fec5`; baseline wheel SHA-256:
  `bcc6830cd2733fcfd1752481c9da44340ca7d2fd1abb0ee46ce738bace23a162`.
- Issue-worktree candidate is the uncommitted Plan0055 diff on the same base;
  candidate wheel SHA-256:
  `f65743dce4b15a595dc03d0670bb99ca80a12ca30468b0ff858ba40a6065a10d`.
  The differing artifact hashes prove the same-version wheels are distinct.
- Baseline was built from `git archive origin/main`, installed into a fresh
  venv, and used to start the disposable monitor and arm the filesystem wake.
  `scripts/product_smoke.py` then force-installed the candidate wheel, restarted
  the daemon, and completed provider-free observation and retirement.
- Exact final commands after creating the temporary directories were:
  `git archive origin/main | tar -x -C /tmp/codex-wake-issue9-upgrade.bcgTRp/baseline-src`;
  `uv build --wheel --out-dir /tmp/codex-wake-issue9-upgrade.bcgTRp/baseline-dist /tmp/codex-wake-issue9-upgrade.bcgTRp/baseline-src`;
  `uv build --wheel --out-dir /tmp/codex-wake-issue9-upgrade.bcgTRp/candidate-dist2 .`;
  `python -m venv /tmp/codex-wake-issue9-upgrade.bcgTRp/venv2`;
  `/tmp/codex-wake-issue9-upgrade.bcgTRp/venv2/bin/python -m pip install /tmp/codex-wake-issue9-upgrade.bcgTRp/baseline-dist/codex_wake-0.5.2-py3-none-any.whl`;
  and `python scripts/product_smoke.py --codex-wake-bin /tmp/codex-wake-issue9-upgrade.bcgTRp/venv2/bin/codex-wake --codex-waked-bin /tmp/codex-wake-issue9-upgrade.bcgTRp/venv2/bin/codex-waked --artifact-dir /tmp/codex-wake-issue9-upgrade.bcgTRp/artifacts2 --upgrade-wheel /tmp/codex-wake-issue9-upgrade.bcgTRp/candidate-dist2/codex_wake-0.5.2-py3-none-any.whl --json`.
- Result: exit `0`; filesystem status `firing`, dispatch attempted `false`,
  upgrade restart `true`, support artifact `2284` bytes, cleanup deleted
  `true`, and fixture-backed GitHub status `matched` with `1` receipt.
  Artifacts and both wheels are under
  `/tmp/codex-wake-issue9-upgrade.bcgTRp/`; the final lifecycle artifacts are
  under its `artifacts2/` directory and the candidate wheel is under
  `candidate-dist2/`.

## Integration receipt

Primary reconciliation on the final candidate passed on both supported Python
versions: `PYTHONPATH=src python3.11 -m unittest discover -s tests -p
'test_*.py'` and the equivalent `python3.12` command each ran 307 tests with
`OK`. The plugin tier passed 12/12; syntax compilation and `git diff --check`
passed; and the selector's `--active-only` planning audit returned `ok: true`.

- PR #28 passed the Python 3.11 and 3.12 release gates, merged as `73e7753`,
  and closed issue #9. Current `origin/main` contains that merge.
- Public-tag smoke is defined but was not executed because no tag/release is
  authorized. Live GitHub, public listeners, live dispatch, installed-user
  mutation/cleanup, deployment, release, tag creation, and install refresh were
  not performed.
- The plan requested one `gpt-5.6-sol` high implementation worker and a later
  `gpt-5.6-luna` review. This delegated implementation used no subagents; the
  runtime-reported effective model and effort were unavailable and are recorded
  as unknown.
