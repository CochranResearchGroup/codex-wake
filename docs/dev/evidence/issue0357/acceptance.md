# Issue #357: protect completion resources inside the existing allowance

Work item: <https://github.com/CochranResearchGroup/codex-wake/issues/357>.
Parent: <https://github.com/CochranResearchGroup/codex-wake/issues/350>, stories 25–26.
Baseline: `b5f5f7720914fc990d63c22600a460dbbe1502d4`.
The coordinator owns the parent plan, actual native/UI qualification, integration,
issue closure and program review/remediation counters.

## Implemented public path

The existing `ObjectiveLedger` owns a small optional completion plan: exactly one
named acceptance, review and bounded remediation obligation, each with a frozen
criterion, token/time estimate and pinned existing source. The existing gateway's
trusted host methods install the plan before implementation request actors,
bind exact native descendant threads to purposes and record source-backed
completed/deferred dispositions. There is no new HTTP authority endpoint,
allocator, grant, deadline window or operator-consent loop.

`reserve_request` protects unfinished completion resources atomically alongside
the existing cumulative request/session accounting. HTTP body role/purpose claims
cannot choose those funds. Original actors retain their phase, spending and
original session deadline across retries and phase changes. The first actual
remediation request consumes one existing correction cycle; the plan's bounded
subsequent requests cannot create another cycle or reset that counter.

Time feasibility uses conservative serial remaining work against the original
objective and already assigned session deadlines. Each admitted request's full
timeout remains charged to its obligation's time estimate. An infeasible path
returns an explicit checkpoint/narrow-work explanation before forwarding.
Deferral retains mandatory protection, pending obligations and a partial checkpoint
outcome. It cannot free implementation funds. Completed dispositions need a
verified source and cannot release unsettled/unknown work. They release only the
unused estimate, never increase the original grant, and never infer objective
acceptance/closure from request or test counts.

Current disabled state bypasses scheduling enforcement, with usage retained and
`completion_enforced:false`. Existing manual routes are unchanged; planning adds
no watcher/start/unmask/resume requirement. The native zero-inference operator
control is processed before admission exactly as before.

Hard-path activation/denial notices now project the fresh ledger: actual used/cap,
reserved/remaining, protected funds/time, original deadline and the actual denial
trigger. No raw actors or credentials enter the notice. All tested notices stay
within 768 bytes; no UI-rendering claim follows from fixture native append.

## Deterministic public campaign

`tests.test_completion_reserve` uses authenticated real HTTP gateway/provider
servers, the existing native transport fixture, original qualified prior usage,
controlled time and the existing request owner. No external inference, production
state, actual native/frontend binary or installed service is changed.

The literal campaign starts with cap **200**, prior usage **40**, original deadline
**NOW+120**, and three completion estimates of **40 tokens / 4 seconds**. The
reviewed inert request maximum is **40**; attributable completion usage is **10**.

1. Implementation forwards once and settles, reaching **50/200**.
2. An ordinary child claiming reviewer purpose in its HTTP body is denied before
   forwarding; the **120-token/12-second** completion protection remains intact.
   The notice reads **Used 50/200**, rather than the stale native receipt's 40.
3. The host assigns the child to acceptance; that funded request still forwards.
   Source-verified acceptance releases unused protection, leaving **80** protected.
4. Another already authorized implementation request uses released funds. Review
   and remediation remain protected and then each execute under host assignments.
5. Only their verified named dispositions report all obligations completed.
   Five forwarded requests plus prior usage total **90/200**, reserved tokens are
   **0**, original deadline/authorization history remain unchanged, and the
   original fixture's authorized correction counter is **1**, not reset by phases.
   `objective_complete` remains false. A request in the now-closed completion
   purpose is denied without falsely describing its completed obligations as pending.

A separate time case advances to **NOW+112**: the **12-second** mandatory path no
longer fits the original **8 seconds**. Admission checkpoints before forwarding;
source-backed deferral keeps all mandatory funds protected and visible. Exact
native `Deactivate governor` then produces the existing governor-generated
acknowledgement with **zero provider calls**, retains the registered goal pause,
and allows an ordinary inactive-mode request. Actual usage is retained without
renewing the grant; deferred obligations remain visible as incomplete.

## Red/green and validation selection

Commands used this prefix:

```sh
PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake/.venv/bin/python \
  -W ignore::DeprecationWarning -m unittest
```

- `tests.test_completion_reserve.CompletionReserveTests.test_implementation_leaves_completion_funded_and_body_role_cannot_select_it -q`
  failed first because `RequestGateway.protect_completion` did not exist; after
  the existing ledger/gateway integration, **1 passed, 1.344 s**.
- The full tail/release case next failed because `resolve_completion` did not
  exist. With source-backed dispositions, all three public campaign cases passed,
  **3 tests, 4.278 s**.
- The remediation-counter assertion detected **0 != 1** before its first request
  was charged to the original correction bound. The three-case campaign then
  passed with that retained counter.
- The shared notice check first failed because activation omitted literal
  **Used 40/100**. Its next trigger check also detected the old generic denial
  cause. The public concurrent-request fixture now verifies actual activation
  **40/100**, reserved **0**, remaining **60**, UTC deadline, and denial
  **objective_token_allowance_unavailable**, used **40**, reserved **50**,
  remaining **10**. This is fresh request accounting, not a native display total.
- A bounded closeout rerun found one case-sensitive test assertion after the
  explanation changed from `checkpoint` to `Checkpoint`; the test now checks the
  semantic explanation without depending on capitalization. That first failure
  is retained; it is not reported as a pass or a flaky retry.

Final focused selection:

```sh
PYTHONPATH=src:tests /home/ecochran76/workspace.local/codex-wake/.venv/bin/python \
  -W ignore::DeprecationWarning -m unittest \
  tests.test_completion_reserve tests.test_request_admission \
  tests.test_objective_ledger tests.test_goal_notices -q
```

**24 tests passed, 7.452 s**, exit 0. This is the affected selection, not the
full repository suite. It includes existing concurrent admission, request timeout,
unknown/duplicate completion, native descendant/session accounting and exact
zero-inference deactivation behavior. These fixtures do not qualify external
provider contracts, actual operator rendering or a production installation.

Ruff 0.14.2 passes for the changed selection with existing E701/E702 style debt
excluded; the gateway/new test file also pass without exclusions.
`git diff --check` passes. CodeGraph was initialized and synchronized for this
verified worktree. Only source, docs and deterministic fixture tests changed.

Memory disposition: **forbidden**. This delegated lane is restricted to its
worktree; user-scoped memory writes and the parent closeout are outside its scope.

## Tested production source hashes

- `src/codex_wake/objective_ledger.py`: `33f1db376adabd43ecc08255ee53d92bcf2b44c3a5a68d0c65d000cf5b843745`
- `src/codex_wake/request_admission.py`: `4fde9a0fa4c0c30322e3914816a1306d357b753d366bb5d272ff7b6cc0357586`
- `src/codex_wake/goal_notices.py`: `6dabf464710a3b712fe631e73d9c9dc54d7572c7dff4a2f202632a5191adeaf0`
