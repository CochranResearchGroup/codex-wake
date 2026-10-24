# #325 — common permission convergence

Scope: source and hermetic public/controller acceptance only. Worktree
`codex-wake-hf06-f`, base `2d64cd1`; implementation owner retains shared source.
No provider input, host policy edits, install, deployment, resource renewal or
tracker closure is authorized by this receipt.

## Acceptance mapping

| Criterion | Evidence and boundary |
| --- | --- |
| Inventory legacy grants/denials/provenance/pending intent before adoption | `test_permission_migration.py`: public operator `permissions adopt` preserves explicit empty/limited caller grants, hashes original legacy bytes and preserves ceilings through subsequent configuration. Plan diagnoses unmapped profile entries and blocks adoption. Pending legacy wakes require explicit hold; original record bytes and target remain unchanged. |
| Diagnose ambiguity; retain legacy until explicit revision | Same suite checks `can_adopt=false`, actionable `unmapped_legacy_profile_entry`, and inactive common store after refusal. `permission_migration.profile_ceiling` refuses old `session_permissions` settings rather than implementing a permanent second switch. |
| Retain old intent/history/routes/deadline/charges and current revocation | Migration byte preservation; handoff uncertain-effect read-only reconciliation; shared refresh lost-response reconciliation without replay; enforcement controller retains deadline/charges and original safety stop; wake route fixtures freeze route order and forbid fallback on uncertainty. These are separate journal seams, not migration-generated authority. |
| Agreement across public requests, independent effects, restart, expiry | `test_permission_convergence.py` pins all 18 action decisions independently of the implementation catalog. Public operator CLI configures one root and binds a separate controller domain; fresh OS processes invoke public `CommandRunner` for each action before/after revocation. CLI and MCP inspect the same revision. Expired standing approvals cannot revive on restart. Bound-root independent handoff monitor observes current revocation, performs only two goal reads, and preserves counters/deadline. Existing consumer suites test actual admission and independent effects below. |
| Remove refresh-only bridge after convergence | No new self-access switch is introduced. Legacy `session_permissions` profile field requires explicit mapping; common refresh/handoff/enforcement/A2A/wake consumers share `PermissionStore`/common checks. Original caller restrictions remain compatibility ceilings. |
| Separate acceptance levels | This receipt establishes only source/subprocess fixture acceptance. Integration comprehensive and isolated-wheel/public-stdio evidence belong to primary's independent receipts. Production remains 0.20.1. Actual scoped refresh #318 and transient-stop recovery #319 remain unresolved runtime capability gates; fixtures cannot close them. |

## Independent effect evidence retained

- `test_shared_refresh.py`: public common-policy admission, independent refresh controller, post-admission revocation, legacy ceiling revocation, lost-response verification without reload replay, unchanged goals and peer-activity fences.
- `test_handoff_permissions.py`: public MCP task approval admission, post-admission revocation before native reads, uncertain observation without replay, exact successor provenance and expiry/completion boundaries.
- `test_enforcement_permissions.py`: public CLI/MCP admission; independent subprocess controller observes revocation without disabling safety; original allocation exhaustion still stops; peer remains armed; recovery reports unsupported without clearing latch or renewing resources.
- `test_a2a_permissions.py`: two-sided public send refusal, consume/claim/reply revocation and read-only reconciliation, bound-policy loss fails closed.
- `test_wake_route_permissions.py`: public CLI/MCP route registration, independent dispatcher revocation, uncertainty without fallback, original recipient/route preservation and peer isolation.

## Validation

Focused development, Python integration venv, `PYTHONPATH=src`, stable-time config
unset; disposable state only. No retries or live/soak runs.

- `python -m unittest discover -s tests -p 'test_*permissions.py' -q`: **43 pass**, 13.402s.
- `PYTHONPATH=src:tests python -m unittest test_permission_convergence.PermissionConvergenceTests.test_bound_independent_handoff_controller_observes_revocation_without_effect -v`: **1 pass**, 0.479s.
- Initial cross-action run exposed a public inspection gap: `refresh.shared`
  returned `deny/shared_scope_required` because CLI/MCP inspection supplied no
  shared relationship. The matrix recorded three assertion failures across two
  tests; all other actions matched. Sent exact hook/reproducer to shared owner.
  Shared owner confirmed the gap and fixed inspection in `085bb7c` (tested
  here as `7bc5c3a`): both public surfaces derive the actual shared target and
  relationship; no effect authority is introduced. The new tests also check
  all 18 unexpired standing approvals allow with attributable approval IDs,
  then all 18 expired approvals require approval after restart.

- `python -m unittest discover -s tests -p test_permission_convergence.py -q`: **3 pass**, 10.747s, final test revision including CLI standing-grant IDs. Earlier green was rerun because the CLI standing-grant assertions were added afterward.
- `python -m unittest discover -s tests -p test_permission_migration.py -q`: **4 pass**, 0.691s.
- `python -m unittest discover -s tests -p test_shared_refresh.py -q`: **14 pass**, 10.068s.

Memory disposition: **forbidden** — task explicitly prohibits memory writes.
