# HF-04 worker implementation evidence

State: OPEN
Owner: ecochran76 / primary coordinator; worker hf04
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/331
Branch: feat/331-resource-ownership
Base: 37a5cbb

## Current state

Worker implementation complete at the owned public module and command-adapter
seams, awaiting primary integration, shared CLI/MCP wiring and final review.
No live calls, production state, installs, tracker mutations, pushes or CI.

## TDD receipts

Python: /home/ecochran76/workspace.local/codex-wake-harness-frontier/.venv/bin/python
All runs use PYTHONPATH=src in the isolated resource-ownership checkout.

For cycles 01-05,08-10 the exact command was:
`python -m unittest discover -s tests -p test_resource_claims.py`.
For cycles 06-07,11 it was:
`python -m unittest discover -s tests -p test_resource_claim_commands.py`.
Each red command failed before its implementation; the same command then passed.

| Cycle | Red observation | Green capability |
| --- | --- | --- |
| 01 | Missing module | Exclusive worktree claim and public inspection |
| 02 | Missing guard | Foreign/stale process/token cannot enter marker mutation |
| 03 | Missing transfer | Explicit operator transfer fences old token; owner release retains history |
| 04 | Missing store silently recreated authority | Initialized missing state holds; unknown version raw bytes retained |
| 05 | Unknown claim fields accepted | Unsupported record/event shapes hold without rewrite |
| 06 | Missing command adapter | Verified native caller and workspace-bound claim/check |
| 07 | Missing CLI parser | Explicit external-prefix allocation and reason-required recovery |
| 08 | Unknown lookup poisoned first store availability | Initial empty authority published before first operation |
| 09 | Shared writable root accepted | Unsafe Wake root refused before metadata creation |
| 10 | Duplicate claims field erased parsed authority | Duplicate authority keys hold original bytes |
| 11 | Aged inventory refused fresh exact runtime observation | Cache age alone no longer blocks fresh exact binding; suppression and changed process still deny |

Raw development receipts are /tmp/hf04-red01.log through red11.log and matching
green files. Primary should retain compact acceptance facts here and copy raw logs
outside Git if needed. Additional acceptance tests cover overlap both directions,
controller reconstruction, serialization while guarded effect is active, stale
owner retained, directory replacement/symlink fencing and model authority spoofing.
A test assertion was corrected from WakeError-only to (WakeError, ValueError):
verified_native_caller intentionally raises ValueError for missing metadata. This
was a test expectation correction, not a product-policy change.

## Focused validation

`PYTHONPATH=src python -m unittest discover -s tests -p 'test_resource_claim*.py'`:
13 tests PASS on Python 3.12 and Python 3.11 (latest focused receipts).
Ruff undefined-name selection F821,F822,F823 passes on owned source/tests.
`git diff --check` passes. No comprehensive suite or installed-runtime claim.

## Integration interface

resource_claim_commands.register_parser(subparsers): top-level `resources`.
resource_claim_commands.run(args, root, native_context=None, observer=None, now=...).
resource_claim_commands.execute(action, arguments, root, native_context=None,
observer=None, operator=False, now=...): list/show/claim/check/release/transfer.
MCP must expose list/show/claim/check/release only, with host-bound operator=False;
local operator recovery and transfer never become model properties.

Claim/check/release use managed_agent_id; show/check/release/transfer use claim_id;
check/release/transfer require integer generation; claim requires kind/path;
transfer requires target_managed_agent_id and operator reason. Operator release
requires reason and expected generation but no live owner. The existing qualified
RuntimeObserver is injected or built by the leaf CLI adapter. ResourceClaims.guard
is the actual cooperative mutation admission seam; check is point-in-time only.

Returned claim is directly {claim_id,generation,status,resource,owner,history};
list returns {status:claims,claims:[...]}; check returns
{status:admitted,point_in_time_only:true,claim:...}. Errors preserve code in
ResourceClaimError; leaf CLI prints {status:held,error:{code,message}} and exits 2.

## Memory disposition

not_durable: worker evidence is an intermediate integration packet; primary owns
one substantive goal closeout disposition. No Graphiti or filesystem memory write.
