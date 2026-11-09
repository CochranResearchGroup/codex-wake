# Post-review exact package acceptance — review1 / TDD pass1

PASS. Source freeze `6afbda8cd166fc3ca08995256729a3353067f34a`; no product
source, README or pyproject changes during qualification. This is verification
within the existing single review/remediation pass, not another review. No
tracker, memory, production, provider, merge or deployment effects occurred.
Memory disposition: forbidden, per delegated scope.

## Exact package

Built once with setuptools84.2.1/wheel0.48.0 and SOURCE_DATE_EPOCH1794246888:

```sh
SOURCE_DATE_EPOCH=1794246888 /tmp/wake534-builder/bin/pip wheel --no-build-isolation --no-deps --wheel-dir /tmp/wake-p211-postreview-package .
/tmp/wake-p211-postreview-installed/bin/pip install -c ~/.local/state/codex-wake/formatting-0210-deploy/constraints.txt '/tmp/wake-p211-postreview-package/codex_wake-0.22.0.dev2-py3-none-any.whl[mcp]'
```

Wheel SHA256 `79d196c249f99ef6ff263d8619cd95e39df77619c07a78dd628162517dc368c6`.
`build.json` records every member hash:302 Python +2 data =304 package members,
all byte-equal across source, wheel, private Linux install and Windows install.
`verify_package.py` / `package-equality.json` independently compare the frozen
6afbda8 Git tree (not the working-tree docs) with every wheel/Linux member and
the same-hash Windows304-member receipt.
Linux prefix: `/tmp/wake-p211-postreview-installed` (Python3.12.13).
Windows prefix: `C:\Users\ecoch\AppData\Local\codex-wake-test\session534-cf8604b7d9b449298394401b00a0486d\venv`
(Python3.12.10). `windows-package.json` independently verifies all304 members and
the same wheel hash. Windows intentionally hosts only the portable remote caller;
Linux hosts the real controller/SDK using constrained dependencies. No global or
production installation occurred. Previous wheel2f72c019 is pre-remediation only.

## Public validation

```sh
env -u PYTHONPATH /tmp/wake-p211-postreview-installed/bin/python scripts/terminal_session_acceptance534.py --output /tmp/wake-p211-postreview-portable.json --wheel /tmp/wake-p211-postreview-package/codex_wake-0.22.0.dev2-py3-none-any.whl --windows-python /mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe
env -u PYTHONPATH /tmp/wake-p211-postreview-installed/bin/python docs/dev/evidence/plan0211/postreview/native_acceptance.py
```

Full installed public workflow PASS9 in158.070s, within180s FOCUSED budget:
help/completion, named/qualified selectors and categories, empty CRUD/defaults,
process-preserving relocation/two-tab undo, routing controls/monitor startup,
drain/terminate/rule cleanup, partial/uncertain CLI3/no replay, real SDK stdio MCP,
authenticated API/OAuth MCP and22 actual native PowerShell calls on API/MCP,
including negative-control exits3. See `installed.json/log`.

Installed focused PASS4 in2.487s (`installed-focused.json/log`): R1 actual
AuthorizedTabs mixed-backend same-name ensure denies the ungranted saved profile
and leaves the session empty; R2 fresh/stale/replacement-bound cache summaries and
empty no-monitor state; R4 existing nonmatches remain excluded after trait changes
until explicit include-existing. Installed R3 focused PASS2 in0.027s verifies
Windows cwd syntax and argv refusal before registry mutation. Tests add only the
test directory to import search; every loaded Wake/Profile module is from the
private installed prefix. Exact test hashes and names are in the receipts.

Native R3 updated fixture PASS8 (`native.json/log`): actual Windows cwd on open
and newly created tab, ensure reuse, pane/process births, exact original formatter
rollback after session rename, restart, populated-delete refusal, unsupported
cross-session move before effects, terminate/name reuse and peer preservation.
All loaded Wake modules are installed. The copied installed native bridge hash is
`9ca6c21f4666d9f7e96533237a23a51a72179af2968fba9d5e88646263dbc3f7`;
psmux image hash remains `bbe825a30f7cddc91b043084049143a381aba5f7e9e36e4d0bb587e296d262ca`.
A native close reply reported uncertainty; subsequent native names were absent,
described server processes exited/absent, and whole-namespace OS cleanup below
reconciles it. The initial error remains in `native.json`.

`causal-reuse.json` compares all package bytes against pre-remediation acceptance:
8 changed/new members,296 unchanged. The unchanged rendering matrix is reused;
no colour matrix was repeated. R1/R2/R4 and integrated R3 front-door guards were
rerun installed, rather than assuming earlier source-only acceptance. The primary
owns local Python3.11/3.12 focused post-remediation checks. No full repository suite,
second broad review or extra remediation pass was run here. Hosted CI was skipped
under the operator's cost policy.

## Complete owned-fixture cleanup

Pre-review name/PID-only cleanup had missed intentional native `__warm__` servers
and pwsh/conhost descendants. The exact6 old534 namespaces are mapped to retained
JSON/log receipts and one retained hash-matching bridge directory in
`owned-native-discovery.json` / `owned-namespaces.json`. Primary explicitly
confirmed that directory as the aborted first-census fixture; unknown namespaces
and all other agents' namespaces are excluded.

`old-initial-census.json` retained36 ACTIVE owned processes. Namespace-exact psmux
roots were image-hash checked; descendants came only from that snapshot tree.
CIM creation FILETIMEs were checked against handle births. Cleanup reopened only
those pinned PIDs, required identical birth/image hashes, held all verified
handles before termination, and read exit codes on the same handles. All36 exited;
`old-final-census.json` immediately showed0 active matches without another CLI
probe. The current installed native fixture then created one new explicitly
receipted namespace, `wake534post-a2d6353ad351`; its initial census retained6
active warm-tree processes, cleaned through the same guarded path.

```sh
python docs/dev/evidence/plan0211/postreview/native_owned_processes.py census --input docs/dev/evidence/plan0211/postreview/owned-namespaces.json --output docs/dev/evidence/plan0211/postreview/current-initial-census.json
python docs/dev/evidence/plan0211/postreview/native_owned_processes.py cleanup --input docs/dev/evidence/plan0211/postreview/current-initial-census.json --output docs/dev/evidence/plan0211/postreview/current-cleanup.json
python docs/dev/evidence/plan0211/postreview/native_owned_processes.py census --input docs/dev/evidence/plan0211/postreview/final-census-input.json --output docs/dev/evidence/plan0211/postreview/final-native-census.json
```

The final OS-only union census covers7 exact namespaces and42 pinned process
births:0 active namespace matches and0 active pinned originals. Retained exited
Windows process objects are distinguished from STILL_ACTIVE259. No psmux CLI or
bridge probe ran after cleanup; subsequent Windows checks read package/token files
only. No blanket process kill or unrelated namespace cleanup occurred.
`linux-census.json` independently shows no owned process remaining and the owned
monitor gone; listener/socket cleanup passed. `token-readback.json` verifies all4
known Windows portable fixture token paths absent. Private package prefixes remain
for review. Native warm caching is unchanged product behavior, not a claimed fix.

Generator check, acceptance-script compilation and `git diff --check` pass.
`source-hashes.json` records the reused R3 helper provenance and final qualification
scripts. All source/package build inputs remain frozen at6afbda8.
