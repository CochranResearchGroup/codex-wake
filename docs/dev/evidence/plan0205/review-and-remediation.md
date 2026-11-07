# Plan0205 single review and bounded remediation

Frozen base: 0f469f3724f88f4e607f18beb2e78dd6b8615b0b.
Frozen head: 64e9f0c36215e262312f22650716d8faf3075201.
Command: `git diff 0f469f3724f88f4e607f18beb2e78dd6b8615b0b...64e9f0c36215e262312f22650716d8faf3075201`.
Exactly one broad review: independent /root/review205_standards and /root/review205_spec; complete private reports retained user-scoped. Primary reconciled each candidate against source and public reproductions. No second broad review is planned.

## Standards

S1 **blocking, medium**: parity fixture always prepends source imports and uses module entrypoints. Verified script lines19,41-44,95-98; installed invocation alone did not test installed entrypoints. Prior installed dependency/source equivalence evidence remains valid but is reclassified; installed managed-native proof remains independent. Remedy: explicit installed binaries/mode, no source injection, actual installed parity run.

S2 **nonblocking_backlog, low**: possible Feature Envy/Message Chains between store seeding and private sync inventory helpers. Source confirms runtime mutual knowledge, but the public owner is unchanged and no correctness failure is established. Existing policy favors bounded consequential behavior changes over speculative refactoring. Owner primary; retain in Plan0205 follow-up rather than broaden this remediation.

## Spec

P1 **blocking, high**: canonical path references inside materialized linked skills point at absent profile/shared paths. Confirmed prefix-only remapping versus logical copy destination. Public seed/sync seam must map references to copied assets and preserve external/runtime boundaries.

P2 **blocking, high**: all production adapters omit reload_executor, so supported selected reload is unavailable through --reload. Confirmed both local ControllerOperations and protected profile_operations. Remedy: shared selected daemon owner; no source/sibling refresh, no implicit restarts; durable uncertain-outcome protection remains.

P3 **blocking, medium**: adoption leaves legacy independent=false and stores.list omits adopted homes. Confirmed apply receipt versus registry-only store projection. Remedy: derive stable adopted store classification from existing receipt/home identity; normal history/config activity must not revoke it, rollback must clear it. Avoid a second registry.

## One TDD pass

Seams: public accounts.create/configuration.sync for copied references; public CLI/API/MCP sync for selected runtime reload; public migration/stores resolve/list for adoption classification; executable parity script for installed entrypoints. Each catches its named externally observable failure, not universal native/provider correctness. Native installed/runtime proof supplements unit seams. Work vertically: one failing behavior then minimal implementation; preserve red/green commands. Root owns reload then adoption; /root/remediate_assets205 owns skill mapping in isolated branch; /root/remediate_parity205 owns installed fixture. Integrate serially, then focused checks only.

### Remediation evidence (single bounded pass)

S1 integrated f07038b (worker446686c): explicit installed-prefix mode validates installed interpreter/package/CLI/MCP entrypoints and excludes source imports. Script public regression red1 failure to green1PASS; actual installed CLI/REST/OAuth/native stdio/PowerShell acceptance passed. The original installed-parity checkpoint now carries an explicit scope correction rather than erasing its observations.

P1 seed/sync integrated0f62074 (workere7aaf02): canonical materialized-file mappings and baseline normalization, with omitted runtime descendants preserved as external references. Three vertical cycles, final12PASS. Focused verification also reproduced the same path issue in adoption; its copied assets were repaired in d785859 (workerdb1f692), public regression red→green; copied helper execution stays private after source changes and source SKILL contents remain intact. This is the same remediation, not a second broad review.

P2 integrated f66989e+5bf4fb0: shared selected native daemon reload owner wired to local and protected transports. Exact UID/PID/home/process/socket/build generation verification before dispatch, no launch/restart, native MCP definitions only. Non-MCP categories remain next-launch; active selected turns report pending; absent/unsupported native owners give precise remedies. Journal retains uncertain effects. Public CLI/API/MCP test red unsupported→green native reload; replay is effect-free and sibling configuration preserved. First existing no-manifest test exposed ignored callback results; callback status now preserved. A later message-compatibility assertion was corrected without changing semantics. All initial logs retained.

P3 integrated569ad36: store discovery projects applied adoption custody with original stable home identity; normal subsequent history/config activity remains independent, relinking/rollback revokes classification. No second registry. Public migration/stores seam red independentFalse→green, and both selected adopted real profiles read back independentTrue from the installed package with zero new model calls.

Root red commands: `PYTHONPATH=.:src:tests /home/ecochran76/workspace.local/codex-wake/.venv/bin/python -m unittest test_profile_sync_reload -q` and `... -m unittest test_controller_adoption.IndependentAdoptionTests.test_store_discovery_tracks_adoption_through_activity_and_rollback -q` (renamed to normal_activity after adding actual rollback coverage to the existing rollback test). Green join `... -m unittest test_controller_adoption test_independent_stores test_profile_sync_reload test_profile_transport_parity test_configuration_sync -q`:28PASS3.261s. Final transport5PASS1.356s. Private raw red/green and worker receipts retained under spec0205/review-remediation and spec0205/{reload,adoption-store}*.log.

Focused post-remediation at5bf4fb0:67PASS on each Python3.11/3.12; whole-tree Ruff, compile, policy wiring, generated reference and planning audit PASS. Installed actual transport parity passed with0provider calls and owned listener closed;260 package Python files matched exact wheel in both prefixes. Subsequent adoption-only correction has its own targeted final receipt.

Summary: Standards1 accepted blocker medium and1 low maintainability backlog; Spec3 accepted blockers, highest high. All blocking findings are addressed through this one pass; final focused qualification receipts bind the resulting source. No second broad review.


Final installed source d78585937272782cbc76e557351cc6f7d0e750a0, wheel SHA256420970c1c4c2092488ec166f3f893fbbdd7f76f55b7869475100242f5fcba23f:44 affected tests PASS on each Python3.11/3.12 using installed modules without src, changed-file Ruff PASS, actual installed CLI/REST/OAuth/native stdio/PowerShell PASS;260 files match wheel in both prefixes. Source affected44PASS12.310s. Native selected reload qualified at5bf4fb0; all eight relevant reload/transport/store modules are byte-identical in final source. Actual native selected toolv1→v2, peer remainedv1, goals/processes preserved and no restarts;0provider calls, network isolated, owned daemons stopped. Two pre-effect fixture failures retained with clean owned-process readbacks. Full final source/package/environment boundaries in final-remediation.json.
