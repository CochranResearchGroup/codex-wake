# Account sign-in through Wake | #380

State: CLOSED
Owner: primary / ecochran76
Ticket: https://github.com/CochranResearchGroup/codex-wake/issues/380
Branch: feat/product-acceptance-380
Base: f6553fd310d2adbd91cea74081c3f1886a3b0b82
WIP limit: one primary lane

## Current State

Implemented and locally qualified at source2a8261997f3bf700adf630bdecc020450efe2ed8.
Native login/status resolve names and builds; login creates a missing account and
persists an account-scoped file-storage policy for future launches. Installed
UID1017 synthetic login/stdin/alias checks and actual native signed-out status pass.
Forty-two affected tests pass on each Python3.11/3.12 runtime. Real authenticated
sign-in was not attempted; source remains local/unmerged and working deployment
is unchanged. Plan0195's frozen product evidence and #380 live gates are separate.

## Contract and scope

`accounts login NAME` resolves the registered build and private home, creates a
missing account through the existing owner, and runs native browser sign-in.
Optional `--device-auth` and `--with-api-key` forward supported native modes;
API keys enter native stdin only. `accounts status NAME` delegates native login
status. Both default to the managed workflow's modded channel, with explicit
`--channel stock` available. No executable or home arguments are needed.
Credentials stay in the selected home's native file store. Wake never reads,
prints, serializes or copies credential contents. Native stdio and exit status
remain visible. Login is a local human CLI operation; no remote credential API,
OAuth grant, or MCP login surface is introduced.

Login refuses an existing managed endpoint, an active private-client lock, or a
concurrent scoped daemon operation. It does not stop/restart an account daemon.
Status remains read-only and usable while clients run. Build bytes and account
identity are revalidated before native execution. No working-account sign-in,
credentials, service or launcher changes are exercised by implementation tests.

## Execution and acceptance

Primary uses public CLI red/green tests with a native executable stand-in at the
external process seam. Verify alias/home selection, stdin-only API key input,
peer isolation, build-byte refusal and active-runtime refusal. Qualify installed
commands under UID1017; actual native status on an empty home must report signed
out without starting a daemon. Real browser sign-in remains operator interaction
and is not claimed from simulated credentials. Run focused affected tests on
Python3.11/3.12 plus lint, policy and planning checks. Do not repeat the prior
full1959-test campaign for this bounded adapter change without a new failure.

## Non-goals and definition of done

No real account sign-in, provider model turns, working installation, migration,
credential copying, daemon interruption, native goals, allowance renewal or memory
writes. Done: one-command local login/status implemented, focused regressions and
installed native-status checks pass, and concise user documentation is updated.
Graphiti discovery skipped: supplied conversation and current sources suffice.
Memory disposition forbidden under the retained handoff boundary.

## Validation and closeout

Public CLI red: login was an unsupported verb. First green proves named creation
and native sign-in/status. Persistence red: explained account credential mode was
missing. Final green verifies `file` and `account:codex-alice` provenance, private
credential mode, stdin-only synthetic key, aliases/peer preservation, active-runtime
holds and changed-build refusal. Account storage policy is metadata, with only
recognized native enum values exempted from credential-value redaction.

Focused checks at qualified source2a82619:19account +14build +6controller auth
+3product authorization tests =42per version, PASS on Python3.11.15 and3.12.13.
Ruff F821/F822/F823, policy wiring, active planning audit and diff checks PASS.
Hosted CI skipped under cost policy. No full-suite rerun is claimed for this slice.

Installed prefix under UID1017 passed browser/device stand-in and synthetic stdin
login, account creation/alias/status and peer preservation. Actual modified166
native status on a fresh home returned1/"Not logged in", created no credentials or
daemon, and made no model turn. Source/wheel/installed231Python members match;
wheel SHA3efb612d49d8778921737f61b93ab98aa62285190086061c361ae9db7b3e0630.
Fresh test-user OS census is empty. Shared-kernel limitations remain.
Curated receipt:docs/dev/evidence/issue0380/product196-account-auth.json. Private
raw red/green and installed receipts remain under user-scoped product196 artifacts.
Memory disposition: forbidden; no memory update was requested or attempted.
