# Private history qualification adapter | #457/#453

The existing history CLI previously delegated to managed-daemon recovery and
failed at private tmux creation before proving history compatibility. That
failure remains in direct455/probes-1. It did not qualify #453.

Stable seam: existing upgrade_bot_history_probe CLI, public native app-server
stdio for synthetic seeding, then codex_profiles.history.discover/resume and
registered run_build for actual private TUI launches. This proves namespace/
history compatibility; actual UpgradeJobs rollback after promotion is a separate
#453 operation. No managed-daemon cutover or native goal recovery is required.

Red: original history native journey exits1 at deep tmux Unix-socket creation.
New adapter preflight1/2 also expose unsupported owned baseline Unix listening;
failures retained with no model/provider requests. The implementation uses the
native stdio API for seed creation and short/no shared sockets, retaining the
original input/package/namespace boundaries. No build-time test marker needed.

Green: actual CLI preflight3 against baseline0.165 and direct455 modified0.166
passes in27.135s: default/account/shared histories are native-created with three
scripted localhost Responses calls; all three visibly reopen through public
profile/TUI launch before upgrade, on candidate and after compatible rollback.
Actual process executable hashes identify each package. Reconnect, real lock
owner refusal, invalid-native-CLI-start preservation/recovery and incompatible
read-schema refusal pass; saved rollout byte prefixes remain intact. No real
model/provider requests and no owned process survivors.

Full unchanged NativeProbe aggregate with the new adapter passes11checks in
36.063s on exactFA09 reference package, model/provider0, scriptedlocalhost4,
ownedcensus0. This verifies the qualifier wiring BEFORE a release admission; it
is not a substitute for qualifying the actual newly built #457 package.

Frozen adapter SHAac5d0cfab39e1a22401020406ced632bc4945be2dae8a8a143229365284d0909.
Primary commit8c1bd27, workercherry-pickf2aaed3. Pycompile/diff and worker's
ruff0.14.2 undefined-name checks pass. Native CLI itself is the maintained
regression for the observed cross-process failure; no fake fixture result added.

The adapter explicitly labels rollback as private registered-build compatibility
and failed-start injection as an unsupported option on the real native binary.
It does not claim managed-daemon recovery, promotion or the public rollback API.
Raw orphan output/recurrence/HF-20 remain unqualified.
