# Human attention queue

The shared queue retains notices and blocked-operation decisions in private
`WAKE_ROOT/attention/queue.json`. It is independent of a dashboard and sends no
notifications. There is no new permission grant or automatic operation execution.

`attention list` and `attention show --request-id ID` inspect retained records.
`--include-closed` includes closed and consumed records in a list; exact show
always retains their history. Expiry is retained as an absolute original timestamp;
an expired open record remains inspectable but cannot receive/consume a response.
`attention request --file request.json` records a question. Every command requires
`--bus-root` and either an existing `--actor-capability` or
`--operator-capability`; identity follows the common permission CLI adapter.

A request packet contains `key`, `kind` (`notice` or `decision`), `question`,
`options`, `evidence` (bounded references, never private transcript bodies),
`priority` (`low`, `normal`, `high`, `urgent`), numeric UTC `expires_at`, boolean
`permission_decision` and `context`. Notices have only `acknowledge`; decisions
have `accept` and `decline`. Priority affects presentation only, not authority.

Context fields are exact nonempty `owner` (verified principal conversation),
`operation_id`, positive integer `attempt`, `task_id`, `allocation_id`, `runtime`,
`conversation_id`, `account`, `target`, `action`, `effect_scope`, `policy_root`,
positive integer `policy_revision` and `operation_state`. Use explicit qualified
sentinels for genuinely inapplicable account/allocation dimensions; omitting one
silently is unsupported. A host feature must qualify the meaning of those values.
The fingerprint binds the entire request, including context, scope and expiry.

A local human records a choice with:

```sh
codex-wake --wake-root WAKE_ROOT attention respond --bus-root BUS_ROOT \
  --operator-capability OPERATOR_CAPABILITY --request-id ID --choice accept \
  --expected-revision 1 --fingerprint INSPECTED_FINGERPRINT
```

The operator capability is verified by the existing bus; `--operator` and supplied
role strings confer no authority. The common `attention.respond` rule must also
allow the operation when policy is adopted. Request/consume use
`attention.request`/`attention.consume`. Notices and ordinary decisions never
change those permissions. A permission decision additionally needs
`--approval-id` naming an already matching PermissionStore approval. Configure
that authority through the existing permission workflow before creating the
request at its current policy revision. Queue responses never create approvals.

Response records only a human choice, pending current-operation revalidation. It
can be recorded without an installed feature validator. Repeating a response with
a stale revision, closed request or changed fingerprint refuses; the history stays.

## Feature-owner integration

`AttentionQueue(root, context_validator=validator)` exposes `request`, `inspect`,
`respond`, `consume` and `close`. `attention_commands.execute` is the shared adapter;
CLI `register_parser`/`run` are available for the parent command registry. MCP may
call only request/list/show using verified native caller metadata and an owner
principal. MCP consume/respond/close are refused. CLI consume is present for a
trusted embedding, but safely holds without a validator; it is not a model tool.

The trusted `validator(retained_request)` reads the feature's actual current
operation journal, current runtime/account/turn, ownership generation and relevant
policy, returning a fresh context with the exact documented fields. It runs under
the queue lock, must be bounded, must not re-enter the queue and must never return
caller-supplied context merely because its hash matches. No parallel context
registry is introduced. Adapter callers supply verified task scope, not merely a
claimed task ID. The CLI resolves actor task scope through the existing verifier.

Consumption requires this callback, unchanged context and policy, unexpired
request and a positively `blocked` unsubmitted operation. Missing, stale, changed,
submitted, completed or uncertain operation evidence refuses. A response does not
resolve uncertain submission; owners retain `unknown` with an attributable reason.
`close` preserves terminal/unknown history and cannot reopen terminal decisions.

Consumption commits once and returns `executes_operation=false` and
`grants_permission=false`. The feature owner must still check current common
permission and hold its existing operation/custody fence immediately before any
I/O. A crash after consumption must be reconciled through that feature's existing
journal; recreating the queue entry or consuming again is not a retry mechanism.

The store uses private owner-controlled paths, serialization, atomic replacement
and fsync, with an initialized marker detecting missing authority. It rejects
unknown schema, duplicate keys and malformed history without rewriting the raw
store. It retains history until explicit future retention policy exists, refusing
new writes at capacity. It does not promise hostile same-UID isolation or a
transaction spanning feature journals and the queue. Provider-free fixtures do
not qualify installed provider behavior.
