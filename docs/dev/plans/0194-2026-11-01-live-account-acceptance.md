# Real account activation and acceptance | #380

State: OPEN
Owner: primary / ecochran76
Ticket: https://github.com/CochranResearchGroup/codex-wake/issues/380
Branch: fix/live-acceptance-380
Base: origin/main289bb97ecf8a0382089819e4c4119bc5462e48d0
Ledger: 0194-live-account-ledger.json
WIP limit: one implementation lane; primary plus at most two read-only discovery workers

## Current State

Disposable modified166 qualification and Plan0193 delivery are complete. They
are not live-account acceptance. Production stock/modded launchers are staged
refusals and account homes still share mutable legacy history/database paths.
Existing #380 owns production activation and now includes explicit live journeys.
Qualified upgrade source remains in PR454/ef156ba; deploy only exact merged main.
Current live paths, process identities and configuration owner must be refreshed.

## Scope and acceptance

Implement existing #380 through real installed account/build/history commands:
correct launcher ownership, retained credentials, isolated concurrent account
writers, preserved shared skills/settings/MCP configuration, existing histories,
stock fallback, future-launch upgrade, reconnect and compatible rollback.
Keep old historical ownership unresolved where evidence is ambiguous. Preserve
raw account/runtime evidence privately; repository artifacts contain generic
results and source/receipt identifiers only. No credential copying or replacement.

Public seams: installed stock/modded/profile launchers catch PATH/shell/owner
and account selection failures; migration.preview/apply/rollback catches actual
storage dependencies and rollback; actual native account metadata/history/TUI
journeys establish installed live outcomes. Fixtures alone cannot close #380.

## Execution graph

1. Independent read-only launcher-owner and shared-store/session inventories.
2. Primary reconciles evidence, implements concrete failures through existing
owners with public-seam TDD, and qualifies exact deployment steps in isolation.
3. Integrate/review source with one broad Standards+Spec review and one bounded
findings pass; preserve qualified prior Plan0193 review counts separately.
4. Prepare exact live effects, identities, rollback and dependency checks. Apply
noninterrupting approved changes and verify actual live installed journeys.
5. Close #380 only after its current real-account acceptance criteria pass.

## Evidence-derived implementation decision

Current native clients resolve to the global legacy home; named homes have
shared mutable aliases. Existing relocation-only migration rejects that layout
and remains fixture-gated. Extend the same migration owner with an explicit
in-place isolation strategy: preserve credential inodes and all global/shared
paths, retain detached legacy links for rollback, and create private mutable
state only in qualified inactive named homes. Never copy or assign mixed legacy
history. Normal existing history access remains through its existing owner.
A fresh writer/dependency census must prove the affected homes are inactive;
unknown clients/dependencies hold the effect. Qualify rollback before native use;
changed private history must prevent destructive migration rollback. This is
separate from build rollback. Host opt-in/current scoped authorization is
required for live effects; no fake disposable marker is placed on production.

## Incremental admission after live dependency reconciliation

The refreshed live inventory maps23 native processes to tmux panes. A global
shared restart is unnecessary for enabling selected inactive accounts. Explicit
host `[accounts].enabled` admission limits the existing account and in-place
migration owners to chosen canonical accounts. Inactive legacy accounts remain
visible as inactive and cannot be resolved for private launch. Default behavior
without this host list remains unchanged. Do not use this control to bypass a
writer or protected dependency on an admitted account.

The read-only selected-account preview includes six accounts and30 aliases;
it excludes the account used by protected global cache/log/memory bindings.
That removes the protected-dependency hold without changing any binding. Actual
activation still holds on incomplete kernel process visibility. A standalone
metadata-only census was prepared privately for operator-authenticated sudo;
it cannot mutate accounts or restart processes. Its result is evidence, never
an authorization or automatic stale-census bypass.

The late selective-admission change is targeted-tested but is outside the
previous frozen broad source review. Review/TDD counters stay1/1; no repeated
broad review loop or live acceptance is claimed. Record its final source/tests
and qualify the actual installed journeys before closing #380.

## Interruption boundary

Operator explicitly requires asking BEFORE interrupting work. Never stop,
restart, signal, reload, handoff or replace an active client/shared daemon; never
rewrite/move storage or credentials used by active work without first presenting
the exact affected sessions, expected interruption, rollback and asking operator.
Elapsed time is not approval. Finish authorized read-only inspection, isolated
implementation/testing and concrete preparation before reaching that boundary.
No native goal/governor activation, resource renewal, business/provider-model
experiment, broad filesystem scan or unrelated repository cleanup is authorized.

## Noninterrupting preparation

Make exact stock/modded version inspection a pure installed launcher operation:
no account/store mutation, no private-client lock acquisition and no configuration
materialization requiring a live account. This must work while legacy mutable
state is held and while another client owns the account; actual TUI launch keeps
all existing isolation and ownership checks. This supports verifiable rollout
and fallback identity; it is not itself stock fallback acceptance.

## Definition of done and evidence

Real aliases launch the intended exact stock/modded package/account; two actual
accounts operate concurrently; active peers and existing history remain intact;
shared configuration works; actual stock fallback/rollback passes; newly owned
acceptance processes are cleaned while operator sessions intentionally survive.
Record installed identities and private before/after evidence; no staged refusal
may be presented as a completed deployment. Stop an unsafe effect, not safe work.
