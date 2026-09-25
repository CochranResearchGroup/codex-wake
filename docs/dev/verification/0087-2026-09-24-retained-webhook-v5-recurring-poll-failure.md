# Retained webhook v5 recurring-poll failure

Date: 2026-09-24
Issue: #141
Plan: `docs/dev/plans/0092-2026-09-24-positive-polling-retained-rollout-successor.md`
Outcome: BLOCKED_ROLLED_BACK

Canonical `f2a4c3ceda4c86ce8befe1e392e79ab68c8be116` passed 22 focused
polling tests, 689 comprehensive Python tests, 12 provider-free plugin tests,
installed-wheel smoke, and both hosted Python gates. Wheel SHA-256 was
`975489f84a5279876c332b9cbe4878f06cc72df858f5d60ef507d85aa545fa6c`.

Fresh v5 hook `685362682` was created before either service. After the
dispatch-disabled poller established reader capability, target wake
`wake_c39b669504a24348834e4bfa2c28075a` was armed and the listener started
against active generation 2. All five unsigned ingress checks returned 401.
The sole rerun of main run `36090958645` became attempt 2 and passed both
hosted gates. Completed signed delivery `3844656287021334500` returned 200.

The corrected poller then found the verified success without exhausting
historical pagination, fired the target, recorded
`GITHUB_COVERAGE_UNPROVEN`, and projected `polling_fallback=READY` with zero
dispatch. This was one successful cycle. Subsequent service and supported
one-shot evaluation checked zero records because no wake remained pending, so
no second polling timestamp was produced. The plan required two distinct
cycles and failed closed; retained v5 services never started.

Exact cleanup produced `DISABLED_PROVEN` and `DELETED_PROVEN`, removed both v5
rehearsal units, freed port 8820, and retired only the rehearsal environment.
Fresh readback showed zero hooks, zero v5 units, no listener, and zero dispatch.
The durable read token remains at its user-scoped owner-only mode-0600 path.

Counters: provider create/disable/delete `1/1/1`, workflow rerun `1`, rehearsal
install/stop `1/1`, retained install/restart `0/0`, update/redelivery/ingress
mutation/dispatch all `0`.

Plan 0093 must pre-arm a nonmatching failure sentinel under a source allowing
success and failure. The success target may then fire while the sentinel keeps
the source runner pending for a distinct second successful polling cycle.
