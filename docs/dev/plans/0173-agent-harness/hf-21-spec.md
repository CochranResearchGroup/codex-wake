# HF-21 durable human attention

State: APPROVED_IMPLEMENTATION
Work item: #339; approved product form d9b59f368e984dff925597304f90e901.

One private shared queue records advisory notices and operation-blocking decisions.
The CLI can inspect and respond before a dashboard. A notice acknowledgment grants
nothing. A blocking response applies only to its exact operation context and is
never an execution, retry, resume or permission grant.

Requests bind owner, operation ID/attempt, task/allocation, runtime/conversation,
account, target/action/effect scope, policy root/revision, original expiry and
canonical context fingerprint. Responses bind request revision/fingerprint and
verified local operator identity. Consumption is single use and revalidates the
current context using an injected trusted feature-owner callback, never a model
claim. Request and response may record stated context without this callback;
response then remains pending current-operation revalidation. When supplied, the
callback also checks request/response. Current policy and expiry are always checked. Unknown/submitted-uncertain operations cannot be accepted or consumed.
Changed identity/context/policy, expiry, duplicate response and replay refuse.

Permission decisions reference an existing matching PermissionStore approval;
no second grant mechanism is introduced. All mutations check the common action
permission. CLI response uses verified_cli_principal and requires operator role;
MCP exposes request/list/show only, each owner scoped; response and consumption
are unavailable to models. Internal feature owners consume through a trusted hook.

One serialized private JSON store retains requests and attributable history across
processes. Unknown versions, corruption and missing initialized authority hold
without rewriting raw evidence. No automatic expiry cleanup or takeover exists.

Provider-free public store and command-adapter tests prove restart, operator-only
response, exact-context fences, duplicate/replayed response, single consumption,
permission reuse, notice isolation and corrupt-state retention. Parent owns shared
CLI/MCP registration and final integration. No provider or installed acceptance.
