# Guarded retained process trees

Root-owned cache refinement after installed resource failure. Generic JSON cache
encoding experiment was reverted; it did not establish a useful whole-owner gain.

Retained monitor owners permit complete process-tree reuse for30seconds, while
ordinary inventory defaults remain2seconds. Every reused tree checks every known
process birth, executable, cwd, argv and child membership against current procfs.
New descendants, same-PID exec/cwd/argv changes, disappearance and presentation
or source-generation invalidation force fresh bounded discovery. Injected
host-owned process observers retain their own metadata provenance boundary.
No cached tree becomes stdin/input authority; no raw screen is retained.

Public regression RED: test_live_descendant_change_invalidates_cached_process_tree_before_expiry
missed a real newly spawned owned sleep child under the cached live parent.
GREEN after the fence: bothPython3.11/3.12 cache+tier selection7tests pass, plus
observer5tests and controller9tests. Real child readiness uses an explicit pipe
acknowledgement; fixture processes are reaped. Undefined-name lint/whitespace pass.

These functional checks do not prove the frozen CPU target. Actual100tab monitor
plus formatting resource qualification remains #547; no caps were changed.

The retained fast path also reuses the host inventory's captured root birth for
its observation key, and avoids rereading that root a second time inside the
same validation pass. It still obtains a fresh live root birth before cache
reuse, checks every descendant birth and verifies process metadata. Existing
replaced-birth/generation tests and the real descendant regression remain green.
