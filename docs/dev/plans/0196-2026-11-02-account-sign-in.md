# Account sign-in through Wake | #380

State: OPEN
Owner: primary / ecochran76
Ticket: https://github.com/CochranResearchGroup/codex-wake/issues/380
Branch: feat/product-acceptance-380
Base: f6553fd310d2adbd91cea74081c3f1886a3b0b82
WIP limit: one primary lane

## Current State

The operator found manual home/executable resolution and native login cumbersome.
Plan0195 is closed for its frozen isolated product scope. This additive packet
owns local human sign-in, without reopening that review or claiming live acceptance.

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
