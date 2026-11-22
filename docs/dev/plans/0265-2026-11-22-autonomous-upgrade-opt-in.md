# Plan 0265 | First autonomous upgrade opt-in

State: OPEN
Owner: primary / ecochran76
Predecessor: #737 and Plan 0262
Spec: https://github.com/CochranResearchGroup/codex-wake/issues/756

## Recorded decisions

- Use Native Codex 0.171 as the working baseline. Record the exact selected
  package and catalog entry before staging a candidate.
- Require one fresh dedicated test run through release discovery, build,
  qualification, future-launch selection, and rollback before production opt-in.
  Keep one job identity and its original limits across phases.
- Discover releases automatically. For the first production job, admit only
  the exact release the operator selects.

- In the dedicated environment, start from the exact working 0.171 package
  and qualify a newer supported release discovered by Wake. Resolve the
  concrete candidate when release discovery runs.
- For the first production job, approval of the exact release permits its
  build and qualification. Future-launch selection requires a separate
  approval tied to the exact qualified package.
- Keep an original 0.171 client running during the dedicated test. Verify
  that it stays pinned while a new client launches on the candidate.
  Roll back future-launch selection and verify that another new client
  launches on the original 0.171 executable.

- If a required check fails or its outcome is uncertain, hold the job,
  report the exact reason, and preserve the current launch default.
  Reconcile uncertainty before retrying. Any retry uses the original
  allowance.
- Selection approval expires at the original job deadline. Retain the
  package and evidence for inspection. A later selection requires fresh
  authorization.

## Design status

The operator approved this design and its conversion to a spec. Discovery
will establish the exact candidate and package identity during qualification.

## Scope and completion

The design covers one dedicated end-to-end qualification and the first
production opt-in. Acceptance requires observable results for each step of the dedicated run
and approval tied to the exact qualified production package.
This design record grants no production activation or account changes.

## Execution ledger

Integration branch `feat/issue-756-upgrade-opt-in`, base
`eecf5554056aa1d66645cc96fefe20eb2323ec62`.

| Ticket | Blocked by | Owner | State |
| --- | --- | --- | --- |
| #757 Exact release admission | None | primary | Validated locally |
| #758 Exact-package approval | None | approval758 | Running on `feat/issue-758-approval` |
| #759 Dedicated upgrade and rollback | #757, #758 | Unassigned | Pending |

The host policy field `first_production_opt_in` selects these gates. It is
covered by the admitted job's policy digest. Existing policies retain
their admission contract. Release discovery publishes the exact version
and recipe digest through the existing discovery operation and starts no job
in this mode. The operator supplies both values to start.

For #757, the red test reproduced unexpected auto-dispatch. The green
selection `PYTHONPATH=src:tests python -m unittest test_upgrade_discovery
test_upgrade_jobs -q` passed 23 tests on Python 3.12 at deployed
dependency versions. It exercised readback, immutable release admission,
and deduplication after reopening the job owner.
