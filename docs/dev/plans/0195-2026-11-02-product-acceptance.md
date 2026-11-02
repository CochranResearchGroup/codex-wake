# Wake-owned account and daemon product acceptance | #380

State: CLOSED
Owner: primary / ecochran76
Ticket: https://github.com/CochranResearchGroup/codex-wake/issues/380
Branch: feat/product-acceptance-380
Base: origin/main318f9855f19438fa24ad19b1a9f713fabcaa62d8
WIP limit: one integration lane; primary plus two bounded workers

## Current State

Isolated source/product acceptance is complete at qualified source3f4052b.
Public account creation, explicit multi-daemon lifecycle and native destination
import are implemented. Installed UID1017 demo7 passed using exact stock/modded
packages and actual native TUIs; final test-user OS census is empty. Python3.12
full1959tests/1skip and Python3.11 presubmit207tests pass. Full3.11 did not complete
within its preliminary600-second attempt and is not claimed. This branch remains
local/unmerged. #380/Plan0194 live authenticated-account acceptance remains OPEN;
working-account activation is withdrawn. Import supports completed goal-free
legacy JSONL; active, incomplete, compressed/paginated and goal-bearing sources
remain unsupported.

## Scope and contract

Use the existing controller registry and operation service. Add account setup
and creation through Wake, explicit account-scoped daemon lifecycle over the
native supported manager, and destination-native session import. No new account,
build, operation, or history store competes with current owners.

Account public operations: accounts.init (new isolated registry only),
accounts.create (new private home, optional alias), existing list/resolve and
configuration.explain. Settings/skills/MCP provenance remains explicit.
Daemon public operations: daemons.list/status/start/restart/update/stop. Account
and build selection are explicit, process/home/socket/build generations visible;
mutations pin targets and persist intent through existing ControllerRuntime for
protected callers. Unsupported native capabilities are returned explicitly.
History import creates a distinct destination conversation with source
provenance; source bytes and identity remain unchanged. Repeat with the same
source revision/destination/key returns the original result; changed inputs
conflict. Owner-bound resume remains unchanged. Use the actual supported native
history owner where possible; freeze the concrete transfer contract before code.

Plan0190 user story5 is extended by this explicit operator-requested copy/fork
operation; it does not make owner-bound resume switch accounts. Plan0194 live
acceptance stays open and cannot authorize working-account activation.

## Execution graph and ownership

1. Primary reconciles source/tickets/contracts (current packet).
2. Account worker owns controller_accounts/account_commands and account tests;
   history worker owns import implementation/history_commands/history tests.
   Both return shared registration proposals to primary. No overlapping writes.
3. Primary owns daemon lifecycle, controller/auth/MCP/CLI shared integration,
   planning/roadmap/runbook and validation selection.
4. One consolidated review of the new scope and one findings remediation pass;
   primary adjudicates. Prior frozen review counts are not reused or reset.
5. Install exact wheel under UID1017; demonstrate two actual daemon instances,
   saved conversations, scoped restart/update/reconnect, peer preservation,
   source-preserving destination import, stock/modded selection and rollback.
6. Retain sanitized report plus private receipts/history/final process census.

## Acceptance and definition of done

Public commands create/manage two synthetic isolated accounts with explained
configuration, run two actual independent native daemons and saved conversations,
change only daemonA while daemonB identity/history remain intact, import a
conversation into destination native history and open it, and select stock/modded
with compatible rollback. Preserve all first failures and distinguish synthetic
account identity from real authenticated accounts. CLI/API/MCP share semantics.
Local validation records commands, source identity and differences from hosted
Linux3.11/3.12 CI. Explicitly include controller acceptance selections omitted
from the existing local profile. No paid hosted CI.

## Non-goals and hard stops

No working-account migration, active registry edit, launcher retarget, daemon
restart/recovery, credential copy/replacement or active-session interruption.
Only owned disposable state/processes may change. No native goals, governor,
allowance renewal, provider calls, #413 work, historical cleanup or memory writes.
One implementation lane with up to3active agents, bounded discovery to named
owners; shared interfaces and final acceptance remain with primary. Shared-kernel
resource limitations of UID1017 will be reported.

## Implementation checkpoint

Account worker /root/accounts delivered7new public command regressions and8existing
account checks. History worker /root/history_import delivered native-path-fork
implementation and12history regressions. Primary accepted both disjoint results,
implemented lifecycle/shared registrations, and reproduced source checks.

One broad Standards+Spec review by /root/accounts returned two accepted blockers:
F1 grant target schemas could not represent registry/process pins; F2 daemon read
adapters omitted expiry/revocation checks. One bounded remediation pass resolved
both; closed-world verification independently passed product authorization and
existing auth checks. The reviewer implemented account files; that independence
limitation is retained. No second broad review was run.

Actual UID1017 installed demo6 passed:2native daemons, simultaneous native TUIs,
source-preserving native destination import visible/open in TUI, repeat identity,
OAuth API/MCP and actual native stdio MCP observations, scoped restart/reconnect,
stock fallback and explicit stop/update/start return, peer process/socket/build
preservation. Final fresh OS census for the test user was empty. Namespace UID0
maps to host UID1017; host kernel/resources are shared. Real authenticated accounts
were not tested; no credentials or provider turns were used.

Retained failures: namespace preflight lacked proc1 permission; isolated loopback
was initially down; hot return from stock rejected the modified upgrade protocol;
stopped native update selects a future-start package; native TUI setup persisted a
shared screen-reader flag and invalidated a configuration revision without changing
peer identity. Each failed run was retained and its owned daemons stopped. The
cold-update behavior now has an observed red/green public regression. Unknown
journal records remain retained; no replay or destructive history cleanup.

Private artifacts remain under the test user and primary's private validation
receipt locations; sanitized evidence/report will bind final source and payload
identities after local checks. Source regression suite and package qualification
remain distinct from working-host activation. Memory disposition: forbidden under
the handoff's explicit no-write boundary.

## Final validation and evidence

Qualified source:3f4052b8ba39ad68c91b1b1fb51439720a39c617. Curated receipt:
`docs/dev/evidence/issue0380/product195-installed.json`. Installed wheel SHA:
6025d33ff5858f77ec9502345c763e1e4c3a1da44220f9b8f03fe313256fbc7d;
all230Python payload members match source and installed test prefix.

- Python3.12.13 comprehensive:1959tests,0failures,0errors,1opt-in systemd skip;
  lint/policy/planning/compile/build PASS. Equivalent logged discovery asserted
  wrapper hash, included repository import path and collected1959/0import errors.
  Monotonic discovery+suite679.33s; per-check bound900s. The local bound follows
  retained600s timeouts; review performance on2026-11-09 rather than weaken tests.
- Python3.11.15 presubmit:207tests including185controller cases; all11profile
  checks PASS, including package build. Complete3.11 suite is not claimed.
- Installed final demo7, native stdio MCP, OAuth API/MCP, dependency/version and
  all230Python payload identity checks PASS. Test user had no remaining processes.
- Existing installed OAuth smoke was repaired from its stale2-tool assertion to
  the8baseline tools and explicit private fixture umask. Its actual discovery,
  consent, scope, rotation/reconnect and revocation acceptance PASS. Unconfigured
  account initialization now preserves unavailable-capability discovery;3HTTP
  authorization tests pass on both Python versions. One consolidated review and
  one closed-world findings verification remain the review bounds.

Retain additional failed validation receipts: dependency preflight lacked wheel;
initial guarded source changed; preliminary3.11/3.12 suites timed out at600s; a
logging wrapper omitted repository import path and yielded39import errors.
Corrected collection and final guarded validation passed; no failed receipt was
removed. A profiled existing watcher fault test takes32–39s for six replacement
cycles. No governor/runtime change was made to improve test timing.

Hosted differences: local WSL/Linux and Python3.11.15/3.12.13, no paid Actions,
full3.12 plus presubmit3.11, no untouched OpenClaw JavaScript/plugin checks, and
separate installed-native acceptance under UID1017. Dependency versions and exact
commands are retained in private machine receipts and the sanitized report.
No source/native/journal schema migration or working-host activation was applied.
Memory disposition: forbidden; machine non-write receipt records0Graphiti writes.
