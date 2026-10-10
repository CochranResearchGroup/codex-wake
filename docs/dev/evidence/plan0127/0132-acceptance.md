# Ticket0132 migration acceptance

Source candidate: feat/native-workflows, baseline5175f5f plus the frozen patch
bound by0132-source-wheel.json. Installed wheel0.9.0 matches all changed source
modules. Official Codex0.162.1 unchanged. Global Wake remains0.8.0; no other
project services or shared Codex runtime changed.

| Criterion | Verdict | Evidence |
| --- | --- | --- |
| Legacy path/caller/format/replacement inventory precedes retirement | PASS | 0132-path-inventory.md and pre-code migration contract in ticket0132 |
| Existing-state readability, recovery and rollback with disposable state | PASS | Installed explicit legacy readback; old0.8 reader holds native4 unchanged; restored reader executes; copied uncertainty and same-root original retain nonce/hash and unresolved state |
| Retire qualified redundant defaults; retain compatibility; no fallback | PASS | Classic implicit basic tmux capture refuses; explicit exact registration succeeds; legacy-to-native migration refuses; native dispatcher unchanged and uncertainty never resends |
| Publish migration/capability/product boundary documentation | NOT RUN publication | README, bundled skill, state contract, migration doc and0.9 release preparation written and reviewed; remote publication/integration still pending |

## Concrete installed outcomes

0132-installed-rollback.json: oldreader checked1/pending1/dispatched0 with
byte-identical native4 state; capable reader submitted one queue. Native turn
receipt0132-native-turn.json confirmsPLAN132_SCHEMA4_EXECUTED.

0132-final-wheel-native.json /0132-final-native-turn.json /pane: frozen0.9
wheel submitted wake_20261010_035616_a434, noncea7b09443-7234-425e-8607-efb8d92e9249,
queue01a123f4-51cc-7642-aacf-aad21de29ed3; exact thread01a123a8-5782-7d43-a214-55b293bbd65f
completed turn01a123f4-51cf-7802-8f17-47f799ffdc1c withPLAN132_FINAL_WHEEL_EXECUTED,
visible in pane%0. Acceptance still has acknowledgment not_observed; it is not
an exactly-once or business-completion claim. The mistakenly past-expiry first
fixture was retained and expired without submission, not retried.

0132-installed-uncertain-migration.json and0132-installed-same-root-recovery.json:
preview leaves bytes unchanged; apply saves exact original and only promotes
schema; oldreader holds; explicit same-root native reconciliation returns
no_exact_native_evidence and remains uncertain without new submission intent.
Copying a root is not proof that a different root can reconcile its old hash.

0132-installed-explicit-legacy.json: implicit basic registration refuses with
no pending record; explicit--legacy-tmux binds exact actor; migration of legacy
state refuses; separate cancel preserves record and oldreader inspects it.

## Validation and review

983 comprehensive tests pass91.152s against the frozen installed wheel;
0132-tests.json binds the full log. Five focused migration tests cover public
registration, original preservation, uncertainty, legacy refusal and malformed
state holds. Red samples retained. Installed product smoke passes wheel upgrade,
signal restart, public CLI/support and supervisor fixture checks; its tmux live
branch is manual_only and is not substituted for the actual native/tmux receipts.
Compilation and diff hygiene pass. Standards and Spec adjudication are separate
in0132-review.md.

## Remaining gate

Remote documentation publication is required before this child closes.
Parent0127 additionally requires hosted integration, release publication and
normal installed qualification. No production/global installation or release
has occurred yet. Existing schema1/2/3 interfaces remain, including unqualified
advanced and network-time compatibility paths. No historical-state deletion.
