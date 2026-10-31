# Native upgrade recovery qualification

ACCEPTED_ISOLATED for Linux UID1017 and the exact native 0.165.0 package below. This does not install or activate anything in the working account.

Native source custody: `6efee650fb0633a229adbd33bb826e3f85b899a3` on `fix/native-0165-upgrade-resumption`. Built from the equivalent frozen 35-file snapshot at base `dfde754e597f0b4766f5b22fbeb990d2e78fe151`; the snapshot and patch are retained in user state. CLI SHA256: `4a38fa1793575c706630fc5765e59e3ad327b486ba637383bc81766f05ff476f`. Code-mode host SHA256: `a338ecd979e1c7cc187fd586f151a8186d1ad3b353a3ffdb2d7ddbe371ec90d7`.

Complete target package: `/home/codex-daemon-test/daemon-qualification-0165/candidate-resume2`. The main positive journey replaces a distinct complete resource package containing the same executable, and requires a different actual daemon PID. First adoption separately replaces the actual older checkpoint4 executable with this executable. All model responses come from the owned localhost fixture, with no copied credentials or external model calls.

## Observed public behavior

| Scenario | Observed result |
| --- | --- |
| Full supported update (`green3`) | Four real tabs notified; durable handoffs; two conversations resume once; original tabs and mirror display resumed output; root identity and checkpoint counters retained |
| Fresh launch and rollback | Fresh managed tab connects; supported rollback changes PID, preserves handoffs and exact paused counters; original and fresh tabs retain identity |
| Later paused-to-paused user control | Changed conversation stays paused; other conversation resumes |
| Unknown delivery journal | Explicit synthetic interrupted dispatch input is held; no extra model work for that conversation |
| Lost response | Actual recovery client killed without reading reply after native acceptance; replay does not duplicate work |
| Accepted daemon crash | Actual SIGKILL during unfinished provider streams; native startup reuses both accepted turn IDs |
| Originally paused work | Skipped; other conversation resumes |
| Exhausted allowance | Native `budgetLimited` remains stopped at 20/20 tokens; other conversation resumes; no renewal |
| Declared external deadline | Held for live authority qualification; other conversation resumes |
| Handoff changed after seal | Changed conversation held; no extra model work |
| Target path and native digest | Separate deliberately altered journal bindings rejected; both conversations remain stopped |
| Replacement cannot start | Execute bits removed from the owned staged release, preserving readable bytes; updater exits with permission denied; no work before repair; supported start after restoring permissions recovers without upgrader; full UI/dedup/rollback journey passes |
| Older daemon first adoption | Explicit `installedPaused`; actual executable changes; old and fresh tabs receive a newly appended notice from the replacement; no automatic work without seals |

The 13 named accepted receipts and exact selectors are in [acceptance.json](acceptance.json). Raw provider requests, native journals, launch logs, terminal frames, copied harness versions for final cases, and all earlier failed attempts remain under user-scoped `plan185/` state and dummy `resume-journey-*` directories.

## Focused checks and boundaries

Five current admission cases passed, including retryable holds, restart adoption, lost-owner fencing and shutdown precedence. The exact Core host-ticket integration passed after its observed red. The mixed held/accepted storage regression passed after its observed red. Fresh protocol consistency passed four cases with one generation-only case ignored. Twenty-one selected updater regressions passed using the earlier test executable with unchanged updater source; the current exact package independently qualifies the installation and recovery paths above. No broad suite is reported clean. The prior Plan0184 legacy PID-time flake remains separate.

Compilation dominated the selected admission run: 800.50 seconds including build, 0.04 seconds test body, within the 1800 second component budget. Individual runtime attempts were bounded to 360 seconds; checkpoint preparation remains bounded to 120 seconds. Preserve first failures: an invalid zero-test Core filter, stale embedded-export test executable, the fixed private-directory/empty-fence defect, fixture ceiling/status assumptions, two cold parallel bootstrap timeouts, replay connection cleanup race, and ambiguous retained-release fault selection are explicitly identified in the acceptance packet. Final fixtures disable optional plugin catalog syncing; earlier unauthenticated catalog warmups were outside model traffic.

The native source remains a private local commit and patch; nothing was pushed to OpenAI origin. The working governor remains masked/inactive, all eight supervision hashes and the lifecycle registry hash match the protected baseline, and the final fresh UID1017 process census is empty. Current working daemon identities were read without invoking launchers; observation is distinct from installation.

Independent real-model quality remains OPEN in Plan0183. Windows runtime acceptance, working-account rollout, and downstream launcher registry transactions are outside this qualification. External declared deadlines remain held rather than inferred or renewed. First adoption from a checkpoint-only daemon deliberately leaves work paused; subsequent sealed upgrades can resume it.

Memory disposition: `unavailable` because reviewed Codex Wake project routing is unresolved. One machine-readable non-write receipt is retained in user state; no graph write was attempted.
