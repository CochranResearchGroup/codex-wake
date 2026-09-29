# Verification 0093 | Issue #178 live AuraCall-to-tmux acceptance

Date: 2026-09-29
Issue: #178
Implementation PR: #179
Canonical implementation: `5abbc098d4c0f6832b10818755602630f2528ecc`
Result: ACCEPTED

## Frozen packet

- Run the merged source without changing the installed
  `codex-wake-auracall.service`.
- Use one isolated wake root and one disposable tmux Codex target.
- Create at most one genuine AuraCall terminal receipt and do not retry it.
- Permit at most one actual wake delivery attempt.
- Require a verified source match, submission acknowledgement, and
  `visible_prompt_observed`.

## Source receipt

The bounded AuraCall API request reached the provider and terminated with
`credit_balance_exhausted`. AuraCall persisted session
`issue-178-live-receipt` and published terminal `error` event
`evt_73ed7d78bab77c5cf12940979a79eef9e1dd25bb5f2af5e4b9184ccbe20410c7`
at `2026-09-29T13:57:57.845Z`. The request was not retried.

The authenticated loopback terminal-receipt readback returned the expected
object `auracall_terminal_session_receipt_observation`, event kind
`auracall.session.terminal`, and terminal state `error`.

## Wake receipt

- Wake: `wake_59378fecd82144b288c326d4e95b6f98`
- Target: disposable tmux pane `%27`
- Target thread: `01a0ed76-1241-7983-ad60-f53dfa6a77bc`
- Predicate verification: `bounded_http_json_get`, `verified`
- Attempts: `1` of `1`
- Dispatch evidence: `dispatch_attempt`, then `ack_observed`
- Visibility: `visible_prompt_observed`
- Privacy: `raw_pane_text_not_stored`
- Final wake state: `submitted`

The target Codex session read the fired record, acknowledged the expected
terminal error receipt, and explicitly confirmed that AuraCall was not
retried. This proves the merged classifier and accounting path in a live use
case outside the deterministic fixture suite.

## Boundaries

No installed service, existing user pane, release, deployment, or provider
retry was performed. The acceptance used an isolated source monitor and
disposable target; the provider account's exhausted credit balance remains an
external operational condition, not a failure of receipt publication or wake
delivery.
