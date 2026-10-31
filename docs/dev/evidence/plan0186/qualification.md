# Final candidateC qualification

State: ISOLATED_QUALIFIED. Tickets414–418 closed; review1/1 and bounded TDD remediation1/1 complete. Parent413 remains the unchanged open specification.

Native branch `fix/413-recovery-integration`, commit `fbe6dbfacff79360b00f2b38345b8aec991fb160`. CLI SHA256 `d1263d970f54a527afa244b0fc54b4f0ad3e5f33b0e8a140aeedbcc305707c54`; code-mode host SHA256 `a338ecd979e1c7cc187fd586f151a8186d1ad3b353a3ffdb2d7ddbe371ec90d7`. Complete six-file target and baseline packages ran under dummy UID1017. The baseline resource variant forces actual process replacement; actual older executable adoption/rollback were also tested.

**30 final-candidate managed journeys passed**, including actual fresh TUI `/goal` creation without an injected authority RPC, externally invalidated and legacy unknown authority staying held after TUI status actions, all prior scenarios, deletion/no replay,300 unchanged retained records,40 cold pending operations and coordinator SIGKILL after35seconds. Audit: 36 counter-continuity checks and20 negative cases with zero recovery requests beyond their checkpoint requests. [Current machine receipt](final-c.json); [historical packageA receipt](acceptance.json).

Final C local build: `cargo build --locked --offline --profile dev-small -p codex-cli -p codex-code-mode-host --bin codex --bin codex-code-mode-host` passed. Unified CLI/host/app-server/daemon `cargo test --locked --offline --profile dev-small ... --lib upgrade_`:6 recovery tests plus2 duplicate admission tests passed; `--lib turn_admission::tests`:5 passed. Zero-match targets excluded. PackageA protocol4, public deletion8 and recovery-driver2 passed before the bounded remediation; these are not represented as C reruns. No public schema changed during remediation. Python compilation and policy wiring passed at closeout.

TDD preserved the actual fresh-TUI missing-authority red and the intermediateB external-control red before C green. The first TUI attempt was a fixture setup error, separately retained. SP1 and ST1–ST3 are resolved through this one bounded pass; no second broad review ran. Full commands/results/source freezes are in user-state `plan413`. Full-tree C manifests were captured during the matrix and compared at closeout, not before its first test; every journey checked the executable digest.

This qualifies the exact isolated package with a scripted localhost provider, not independent real-model quality or production installation. Shared WSL kernel/resource differences remain. No working-account install, governor activation, upstream publication, hosted CI or credential/history copies occurred.

---

# Native upgrade recovery repairs: isolated qualification

Historical packageA state: API_INPUT_QUALIFIED_REVIEW_BLOCKED. Parent #413. Child tickets #414–#418.

The complete immutable package passed 28 managed-launcher journeys in codex-daemon-test UID1017. These include all thirteen prior scenarios, positive native authority and malformed/missing/unsupported authority holds, deletion after real completed recovery without replay, 300 unchanged terminal/legacy records, 40 operations held pending until the replacement served, and actual coordinator process SIGKILL after35seconds. Held conversations made exactly the three checkpoint provider requests and no additional recovery requests across18 negative cases. Public goal readbacks established34 cumulative-token continuity checks. Actual rollback to the older checkpoint-only executable preserved paused work and handoffs.

Native integration branch `fix/413-recovery-integration`, tip `f8e5a5c24da256dda64853c8d6c36e3a8ef78a49`. Package source `e52b43cc707e0c85f40f43558c7c13699fbfb570`; the sole later change is a one-line test-fixture environment fix. Every other frozen source byte matches. CLI SHA256 `deadc6fa49b619fba2ce07bd10464db97cf525125d88443c3ac937826cac6c19`; code-mode host `a338ecd979e1c7cc187fd586f151a8186d1ad3b353a3ffdb2d7ddbe371ec90d7`. Whole-package manifests and source snapshots are retained in user state. No native upstream publication occurred.

## Local validation

- `cargo build --locked --offline --profile dev-small -p codex-cli -p codex-code-mode-host --bin codex --bin codex-code-mode-host`: passed; frozen source unchanged.
- CLI/host/app-server admission selection:5 passed. Zero-matching CLI/host targets are excluded from counts.
- Unified CLI/host/app-server/daemon `--lib upgrade_`:6 storage/lifecycle tests and2 already-covered admission tests passed.
- Unified protocol `--lib schema_fixtures_tests`:4 passed,1 intentionally ignored generator. Stable and experimental generators separately passed one selected test each; Python SDK regenerated with its existing pinned environment.
- Unified app-server `--test all --no-run`: compiled. The staged test binary and actual app-server component ran under UID1017 with cleared environment:8 deletion tests and2 recovery-driver tests passed. The component supports test-only flags; the production CLI package was separately tested through the managed journey.
- Existing journey script exercised every required public scenario; exact cases and per-case harness hashes appear in acceptance.json. Native package and test source identities remain separate.
- Python harness compilation and repository policy wiring passed.

Full commands, selected counts, compile/test durations, subprocess identities, package manifests and raw receipts are under user-scoped `~/.local/state/codex-wake/plan413`; dummy runtime artifacts remain under its qualification home. The machine receipt contains curated results, not production credentials or histories.

## Preserved failures and corrections

All first failures remain attributable. Initial schema generation omitted a required environment variable; SDK generation first lacked uv, then used the existing pinned virtualenv. One automated edit assertion stopped before the lifetime patch completed; source was inspected and fixed before build. A redundant test-feature variant build was canceled explicitly, never counted as passing. The first bounded-pass worker test had a relative mock codexHome; its corrected red demonstrated17versus16 requests before green. The deletion journey initially treated an empty successful response as false; first adoption was initially run in ordinary-success mode despite a correct installedPaused result. A CLI adapter could not accept the component's test-only flag, so actual component binary tests replaced it. One new test lacked its fresh-session auto environment; the test-only correction then passed all8 deletion tests. None is hidden by a retry or counted as qualified behavior.

## Boundaries

This proves scripted-provider behavior for the exact isolated package. It does not qualify independent real-model quality, Windows, comprehensive native workspace coverage or working-account installation. Shared WSL kernel/resource differences remain. Hosted GitHub CI is intentionally skipped under operator cost policy; local checks satisfy that validation boundary. The governor remains masked/inactive and protected working-state readbacks are preserved separately.
