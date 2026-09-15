# Installed GitHub CI wake replacement: stopped before trigger

Status: FAILED_SAFE

Issue: `CochranResearchGroup/codex-wake#37`

Candidate commit: `70cdb927e59c9b60d25b7a15083c893498788726`

Candidate tree: `1cf14944e31f1534efc05ded8fb62550d8287e08`

## Outcome

The operator-authorized replacement attempt stopped before its pull request or
selected GitHub workflow occurrence existed. The candidate CLI was invoked
without the isolated service's `XDG_STATE_HOME` and without
`--require-monitor`. Its managed-reader probe therefore used the normal user
state path and returned `READER_CAPABILITY_UNAVAILABLE` after durably preparing
the registration. The isolated daemon later recovered that preparation and
published one pending wake, contradicting the CLI's apparent failure outcome.

That ambiguity triggered the plan's hard stop. No second registration command
was issued, no pull request was opened, and no GitHub workflow run was caused.
The wake was cancelled and archived with zero receipts, matches, dispatch
attempts, acknowledgements, or visibility results. The exact candidate service
and runtime artifacts were then removed recoverably.

## Diagnosis

Prepared-registration recovery is intentional crash-safe behavior. Current
source establishes the source anchor, persists a preparing arm and outbox, and
requires a managed-reader capability before publishing the wake record. A
daemon with that exact capability may subsequently reconcile the preparation.

The procedural error was a split state identity:

- service: isolated `XDG_STATE_HOME` in the named drop-in;
- registration CLI: normal user state because `XDG_STATE_HOME` was omitted;
- registration: omitted `--require-monitor`, so no pre-write readiness gate
  rejected the mismatch.

The existing installed-canary contract requires candidate CLI readiness and
registration to use the same isolated environment as the service. This receipt
does not claim a product-code defect or authorize a code change.

## Frozen identity

- Initial branch receipt commit:
  `2a85c70e9fb73f3db823e582fc803510a1b92e7a`
- Candidate wheel SHA-256:
  `cce133b703ec919ac8042474d3d276f431f7512cfe672bf329172f0e2630ec55`
- Installed `codex-wake` SHA-256:
  `801d0e37c1d52289d2a29f2e09af940eb03df97029a8df48fe003ed9e7acf211`
- Installed `codex-waked` SHA-256:
  `b90eba0b31e80369012de4e4ce26ce18a0b0c7c9cf10849252f1512c7ee78759`
- Source configuration SHA-256:
  `d609a0507b757c872ff4f99b2c1a14cf48e7243901bb838fe09b4bbec8d90f51`
- Unit SHA-256:
  `bf00470daeafd9f0c02eef6e0b21388fc2d6ef00db512edc3eed6dcf933c5ad6`
- Isolation drop-in SHA-256:
  `8a677d7598aac87e465a913ac5aaf2a7df3123f07023f443de01ca87d6b240d9`
- Unit: `codex-wake-p50-github-canary-replacement.service`
- Initial daemon PID: `38590`
- Target: pane `%33`, socket `/tmp/tmux-1000/default`, tmux identity
  `recovered-050801-20542:34.0`
- Repository: `CochranResearchGroup/codex-wake`, numeric ID `1242753508`
- Workflow: `CI`, numeric ID `279450573`
- Ref: `refs/heads/chore/issue-37-replacement-github-canary`
- Source instance: `p50-github-ci-replacement`, evidence mode
  `positive_only`, conclusion `success`
- Credential reference: `CODEX_WAKE_GITHUB_TOKEN`; no credential value was
  printed, persisted in the repository, or copied into wake evidence.

## Wake evidence

- Wake ID: `wake_c8f2ff1960d74c6e8736f32828393eee`
- Arm ID: `arm_wake_c8f2ff1960d74c6e8736f32828393eee`
- Journal UUID: `080df15e25d14a21b789d747eb8329cf`
- Idempotency key: `p50-github-canary-replacement-20260915`
- Registered at: `2026-09-15T13:18:06Z`
- Published by recovery at: `2026-09-15T13:18:14.084891Z`
- Recovery: `source_replay`
- Anchor configuration fingerprint:
  `fa305baeba8437c02b6c0d0a79738a7d8ef10c014b10317830d7db507a4d4af2`
- Anchor order: `1789478286000000`; local sequence: `0`
- Source state: checkpoint order `0`, last local sequence `0`, no lease owner
- Source health: `GITHUB_COVERAGE_UNPROVEN` at
  `2026-09-15T13:18:41Z`
- Receipts: `0`; match reservations: `0`; dispatch attempts: `0`
- Archived lifecycle: desired/applied `archived`, revision `1`; arm
  `tombstoned`; no unapplied outbox entries
- Archived at: `2026-09-15T13:18:55Z`

## Rollback proof

- The exact service reports `inactive` and `not-found`.
- The exact unit and drop-in paths are absent.
- A fresh process scan found no candidate `codex-waked` process.
- The exact candidate and build roots were moved to user trash and are absent
  from their original paths.
- The normal global executable remains `codex-wake 0.5.2`.
- The GitHub branch existed, but no pull request or workflow run for it existed
  before the stop; no trigger-side provider mutation occurred.

## Acceptance boundary

Issue #37 remains open. This receipt proves safe cancellation and rollback; it
does not prove restart recovery after a successful supported registration, a
post-anchor GitHub occurrence, match, dispatch, acknowledgement, or visible
wake. Any later attempt must run every candidate CLI command with the exact
isolated `XDG_STATE_HOME`, require monitor readiness before writing, and obtain
fresh explicit operator authorization because the one replacement attempt was
consumed.
