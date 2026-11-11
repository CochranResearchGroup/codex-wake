# Shared wake monitor qualification and migration

Plan0218 and specification #558 own the approved design. Tickets #559–#562
separate source acceptance from working-host effects. Ordinary roots can share
bounded process workers; the HTTP controller, webhook listener and refresh
worker retain their separate lifecycles. Native/account daemons are outside this
migration. A low service count is not an acceptance criterion by itself.

## Reproduce disposable acceptance

Build and install one immutable wheel into a private prefix, then run:

```sh
python scripts/supervisor_consolidation_qualification.py \
  --prefix /absolute/path/to/candidate-prefix \
  --baseline-python /absolute/path/to/previous-prefix/bin/python \
  --output /absolute/path/to/private/qualification.json
```

The runner clears inherited `PYTHONPATH`, redirects XDG config/state to disposable
roots, never polls working roots, and calls the selected installed interpreter's
CLI/daemon modules. It records the loaded supervisor module path/hash and package
version. `--source-root /path/to/repo --python /path/to/python` instead selects
explicit source qualification; that result is not installed-wheel acceptance.
Retain the wheel hash, source commit and prefix provenance beside the receipt.
The runner hashes itself so qualification changes are distinguishable.

Checks cover a synthetic future wake through dedicated-owner contention,
dedicated-to-supervisor migration, unchanged pending record bytes and dispatch
configuration, clean restart, blocked-root timeout, continued unrelated progress,
held-state restart/no replay, root-local setup-error isolation, exact-token
reconciliation, dedicated rollback and
abrupt coordinator death with in-flight admission recovery. Record final owned
live processes; synthetic fixture children are the only eligible cleanup targets.
No native/provider request or live application is exercised. This does not
replace the separate Linux test-user/native-package qualification gate.

## Interpret resource evidence

The bounded workload uses six roots, forty synthetic future schema-one wakes per
root, and eighteen completed polls. It compares the old serial supervisor, six
old independent polling processes, and the new coordinator plus two workers and its multiprocessing helper.
The dedicated comparison measures the same public polling function in separate
processes, not six actual systemd units. CPU includes child process startup;
wall time includes short cadence waits and coordinator journaling. Sampled RSS
sums count shared pages more than once and are not PSS or service-cgroup memory.
Serial, dedicated and isolated numbers must remain separate.

A first immutable-package run measured roughly 138 MiB sampled RSS for six
independent processes versus roughly 82 MiB for the two-worker pool including its multiprocessing helper. Startup-inclusive
CPU was approximately 0.97 versus 0.30 seconds, respectively. The old serial
supervisor used approximately 22 MiB and 0.05 CPU seconds and was faster on this
small workload. These are short synthetic observations, not steady-state or
production improvement claims. The pool deliberately buys failure isolation at
an IPC/process/journaling cost. Read the exact receipt for current measurements.

Before a working rollout, compare steady-state cost and lateness for the actual
eligible workload, with the same root cadence, dispatch settings and backlog
shape. Profile any material regression; do not lower cadence to manufacture a
passing CPU result. The original twelve-second live service sample and the
read-only audit are investigation evidence, not a benchmark control. Native and
signal-journal workloads need their own bounded measurements before claims about
those paths. Do not create a performance probe by calling a production poll,
even with `--no-dispatch`: it can still mutate records or lifecycle state.

## Reconciliation and recovery

A root whose poll exceeds the configured timeout receives
`monitor-reconciliation.json`. A coordinator restart converts surviving in-flight
admissions to the same held state. The first uncertain outcome remains the
reconciliation authority. The daemon and supervisor both refuse held polling;
recent old health does not establish current readiness. Killing a process does
not prove an external delivery failed.

Inspect the recorded root, token and exact effect history. Once uncertainty has
been resolved under existing authority, release only that token:

```sh
codex-wake supervisor reconcile --root-id EXACT_ROOT_ID \
  --registry-dir /absolute/registry --state-dir /absolute/supervisor-state \
  --expected-token EXACT_OBSERVED_TOKEN --acknowledge-uncertain-effects
```

A live polling owner or changed token refuses reconciliation. Never remove a
hold or in-flight journal manually to force progress. In-flight work must remain
held when effects cannot be established. Reconciliation does not renew deadlines,
resume unrelated work or grant dispatch authority. Keep private receipts outside
Git; no prompts, credentials or private histories belong in qualification data.

## Working-host SoyLei ownership transition

The audit observed `codex-wake-soylei-website.service` active while the shared
supervisor also had SoyLei root `soylei-website-bb3c1b12` enabled at
`/home/ecochran76/workspace.local/soylei-website/.codex/wake`. This establishes
configured overlap, not proven duplicate delivery. Refresh that readback before
acting; do not use this historical inventory as current owner proof.

1. Record an audit using the qualified installed interpreter, for example
   `python -m codex_wake.service_audit --sample-seconds 12 --json`. Save exact
   unit identities, effective command, cadence, root registration, current
   monitor process birth/boot, pending/firing identities and protected-state
   fingerprints outside Git. Preserve the original unit, enablement and registry
   bytes for rollback. Preserve the root's existing dispatch executable and all
   additional dispatch/authority fields; enrollment defaults cannot reconstruct
   unknown settings.
2. Qualify the exact candidate package and supported rollback in disposable
   state. Ensure both prospective polling entrypoints load the new ownership
   implementation. Old running monitors do not gain locking merely because a
   package was installed. Check the exact unit KillMode and child ownership before
   stopping any service; a default cgroup stop can terminate unrelated native
   children. Preserve lifecycle-supervision and receipt-authority flags: a root
   requiring flags the supervisor cannot represent remains an isolated exception.
   Bound any root pause/quiescence and ownership transition
   using the supported control interface and actual current process readback;
   inspect existing in-flight work before stopping an owner. Do not restart the
   shared supervisor casually: it serves unrelated enrolled roots.
3. Select the shared supervisor as the sole future SoyLei owner. In a controlled
   cutover, stop only `codex-wake-soylei-website.service`, verify its exact old
   owner exited and reconcile uncertain work. Retain its unit for rollback and
   disable its automatic start only after ownership is verified. Keep the shared
   registration enabled, its canonical wake root unchanged, and explicitly set
   `poll_interval` to the dedicated monitor's observed cadence (previous audit:
   one second). Preserve every other registration/dispatch field. Use an atomic
   supported configuration update; a new registration must not silently discard
   existing nondefault settings.
4. Verify root-specific supervisor health from a new polling generation, one
   owner for the canonical root and aliases, unchanged deadlines/pending intent,
   no unexplained firing work, and continued health of unrelated roots. Inspect
   fresh process/resource evidence. Unpause only the exact scope deliberately
   paused for this cutover. A recent old health file is insufficient.
5. On failed acceptance, prevent new shared admission for only this root,
   reconcile any current/uncertain poll and prove no shared owner remains, then
   restore the original registry bytes, dedicated unit/enablement and cadence.
   Start the dedicated owner only after the shared owner is absent. Retain wake
   records and outcome evidence; do not restore stale wake-state backups over
   new effects. Refresh the read-only owner inventory after rollback.

No working-host cutover was performed by ticket #562. This procedure describes
its required evidence and ordering, not proof of that effect. Existing merge,
release and live-effect authority still applies to a future operator execution.

## Other consolidation and retirement candidates

Migrate one eligible root at a time after the pilot. Graphiti's previously
observed sixty-second interval must remain sixty seconds. Keep a dedicated
exception when workload, failure isolation or authority requires it. Preserve
independent controller, refresh and webhook roles and protected service masks.

Four enabled-but-skipped historical services had missing working directories;
two still had existing wake roots. Five inactive static notification workers
were historical fixture candidates. Check unit references, timers/targets,
registries, retained external-source responsibilities, pending intent and owner
custody before retiring any definition. A missing worktree or inactive unit does
not authorize deleting its wake root or unmasking a protected service. Removing
inactive definitions is operational cleanup, not measured CPU savings. Keep the
retained webhook listener until its external delivery responsibility is explicitly
reconciled.
