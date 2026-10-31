# Guarded worktree cleanup

`python scripts/cleanup_worktrees.py plan --repo REPO --target CHECKOUT --custody refs/custody/NAME --references REVIEW.json --output PLAN.json` performs read-only planning. A successful planning exit means a plan was written; inspect its PASS/HELD status. It is not permission to delete.

The explicit reference review must be an owned regular JSON file, not writable by other users. Example shape:

```json
{"repository":"/absolute/repo","entries":[{"path":"/absolute/checkout","owner":"reviewing owner","reviewed":true,"service_references":[],"build_references":[],"evidence_references":[]}]}
```

Empty lists mean the owner actually reviewed those references, not that the tool inferred absence. Missing/incomplete review retains work. Never fabricate a completed review to obtain eligibility. The tool separately observes process cwd/executable/file-descriptor references; denied or unresolved observations retain the checkout. Dirty or ignored content, locks, referenced paths and custody mismatches also retain it. The primary and invoking checkout are protected. An explicit exact custody ref must already exist; the tool never manufactures recovery evidence or discards changes.

After separately authorizing an eligible exact target, use `python scripts/cleanup_worktrees.py apply --plan PLAN.json --approve-plan PLAN_ID --output RESULT.json`. The plan ID is printed by planning and stored in the plan. Apply checks the plan digest, current identity/status/custody/review bytes and fresh process observations under a cooperative Git-store cleanup lock. It uses normal `git worktree remove` without force, including exact removal of a registration whose directory is already absent; it never broadly prunes other registrations or deletes branches.

Plans and result files must be new and outside both the invoking source and target. The result records an unknown pending effect durably before Git runs, then verifies directory/registration absence and exact custody after success. Interrupted, failed or timed-out operations retain unknown outcome and require actual Git/filesystem reconciliation before a newly authorized plan; reruns cannot overwrite the first result. A new receipt path alone is not authorization to retry an unknown operation.

A cooperative lock does not prevent unrelated programs starting after the last observation. Planning/apply is not an atomic system-wide inactivity guarantee. Incomplete cross-user visibility commonly means physical retirement remains held; obtain qualified owner evidence through an authorized future process, without granting this command additional privileges.

Tests use disposable Git repositories and inject the OS process-observation boundary; they do not prove the existing historical inventory is inactive. This packet authorizes no actual retirement there. No daemon/service/process selection or credentials are changed. Private schema `codex-wake.cleanup.v1` supports the bounded read-only receipt summary command.

For bounded plan/result inspection and the reusable local regression profile, see
[source-bound validation](source-bound-validation.md#prevention-command-navigation-443).
