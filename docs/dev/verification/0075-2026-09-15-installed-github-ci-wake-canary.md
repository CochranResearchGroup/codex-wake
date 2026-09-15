# Installed GitHub CI wake canary retry 2

Status: FAILED_SAFE

Issue: `CochranResearchGroup/codex-wake#37`

Candidate commit: `ee39ae1bbaf0af754e475dc79112a8787ad7f7ff`

Candidate tree: `44ccb26b9361d55000d6cbfc29f1fc224a66093c`

## Authorized boundary

This is the first of up to five newly authorized replacement attempts. It may
register one isolated wake with `max_attempts: 1`, cause one ordinary pull
request CI completion after the anchor and controlled service restart, and
make at most one live tmux dispatch. Success, ambiguity, identity drift, or a
failed restart-recovery check ends this attempt without a second registration.

The primary orchestrator owns all live effects. Every candidate CLI command
must use the candidate service's exact isolated `XDG_STATE_HOME`; registration
must also use `--require-monitor`.

## Frozen pre-registration names

- Branch: `chore/issue-37-github-canary-retry-2`
- Candidate runtime root:
  `/home/ecochran76/.local/state/codex-wake/p50-github-canary-retry-2-20260915`
- Candidate build root:
  `/tmp/codex-wake-p50-github-canary-retry-2-build.20260915`
- Wake root: candidate runtime root plus `/wake`
- Unit: `codex-wake-p50-github-canary-retry-2.service`
- Source instance: `p50-github-ci-retry-2`
- Idempotency key: `p50-github-canary-retry-2-20260915`
- Repository: `CochranResearchGroup/codex-wake`, numeric ID `1242753508`
- Workflow: `CI`, numeric ID `279450573`
- Ref: `refs/heads/chore/issue-37-github-canary-retry-2`
- Conclusion: `success`
- Credential reference: `CODEX_WAKE_GITHUB_TOKEN`; no credential value may be
  printed or persisted in repository evidence.
- Target: live Codex pane `%33` on `/tmp/tmux-1000/default`, subject to exact
  revalidation immediately before registration.

## Outcome

Retry 2 stopped safely after the selected CI run but before any provider
observation or dispatch. The credential-file provisioning command wrote a
literal escaped newline marker. Systemd loaded the configured key, but its
value was 41 characters and differed from the valid 40-character GitHub CLI
credential. A bounded request with the service-process value returned HTTP
401; the same request with the unmodified CLI credential returned HTTP 200.
No credential value or digest was printed or retained in repository evidence.

The daemon therefore recorded `GITHUB_AUTH_UNAVAILABLE` and never ingested the
successful workflow run. The original wake remained pending with zero attempts,
receipts, or reservations. The service was stopped, the wake was cancelled and
archived, and every exact candidate artifact was rolled back recoverably. No
second registration or dispatch was attempted.

## Frozen identity

- Initial branch receipt commit:
  `2356a3442d02799ad8963e2454135870c37be867`
- Initial branch tree: `f200eb7bd9bc0154c6b085e961de73063ce16a90`
- Candidate wheel SHA-256:
  `7887277066414386f27b2038d16fb97e665f31fb644ad52e657f87055fdd3e7a`
- Installed `codex-wake` SHA-256:
  `69675b8611f0bfdbf746d7a9756a8d5bb9f8778d7972a55ec7d2588c94851bb8`
- Installed `codex-waked` SHA-256:
  `bd183c7dea1a8e719cd7ac4439e9c93cc02b69023825d8f6afb3ec87b086dad9`
- Source configuration SHA-256:
  `caa2f8f1d657866939cfbeb29f5ed4f837d6289dfdc222799548cfabb3b77bd7`
- Unit SHA-256:
  `8de5ab8261dce4b28a12b1b448568e7825a032704ed708327c0cf618a279c066`
- Isolation drop-in SHA-256:
  `a29c8decdccc892e2554cf460f5a1a7ee1a9e35c76a2a7e3f5f7dc2c358c5c7e`
- Service PIDs: initial `29597`; controlled-restart `33019`
- Target: pane `%33`, socket `/tmp/tmux-1000/default`, tmux identity
  `recovered-050801-20542:34.0`
- Credential file metadata: owner UID `1000`, mode `0600`, 66 bytes; key
  present in the service process; invalid loaded value length 41

## Restart and workflow evidence

- Wake ID: `wake_9604b9cf73024b838af1ec0d5751873d`
- Arm ID: `arm_wake_9604b9cf73024b838af1ec0d5751873d`
- Journal UUID: `946604b573ed42dcaa2f208dfd7f90ae`
- Idempotency key: `p50-github-canary-retry-2-20260915`
- Registered and published at `2026-09-15T14:31:29Z`
- Anchor configuration fingerprint:
  `e011f0955999b94a92db71b93eee120ab9cd16c81d724b1a87e9249104e7fa80`
- Anchor terminal lower bound: `1789482689000000`; local sequence `0`
- Before and after the controlled restart, the record SHA-256 was
  `7ed8c708bb7ff6cda28bc212af119c29947a000dec7c042c41f0e76c4e451e60`,
  the arm was published, lifecycle was pending revision 1, and attempts were 0.
- Selected workflow run: `34982337740`, attempt `1`, event `pull_request`,
  workflow `CI`, head SHA
  `2356a3442d02799ad8963e2454135870c37be867`, terminal conclusion `success`
- Run timestamps: created/started `2026-09-15T14:32:31Z`; provider run
  `updated_at` `2026-09-15T14:33:14Z`. This receipt does not promote
  `updated_at` into completion-time provenance.
- Last source health before stop: `GITHUB_AUTH_UNAVAILABLE` at
  `2026-09-15T14:36:26Z`, retry deadline `2026-09-15T14:36:33Z`
- Receipts: `0`; match reservations: `0`; dispatch attempts: `0`;
  acknowledgements: `0`; visibility results: `0`

## Terminal and rollback proof

- Cancelled and archived at `2026-09-15T14:36:28Z`.
- The journal arm is `tombstoned`; lifecycle desired/applied state is
  `archived` revision 1; the persisted record is archived with attempts 0.
- Product uninstall removed the exact service unit. Fresh readback reports
  `inactive` and `not-found`; the isolation drop-in is absent and no candidate
  daemon process remains.
- The exact candidate and build roots were moved to user trash and are absent
  from their original paths.
- The normal global executable remains `codex-wake 0.5.2`; no global refresh,
  workflow dispatch API, rerun, release, deployment, or unrelated service
  mutation occurred.

## Diagnosis and next attempt

The red-capable check compared only token shape/equality and HTTP status: the
loaded 41-character value reproducibly returned 401 while the original
40-character value returned 200. This falsified missing systemd loading and
insufficient GitHub permission. The next attempt must write the environment
file with a direct line-prefix transform that preserves the credential bytes,
then prove process-value equality and a bounded HTTP 200 before registration.
This is a procedure correction; no product-code change is justified.
