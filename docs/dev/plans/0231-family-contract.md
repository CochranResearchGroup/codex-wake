# P231 frozen integration interface

Owner: primary. Bot descriptor: bot_id,parent_bot_id(nullable),name,scope_kind
(specialist/account/task),scope_ref(nonsecret),temporary(defaultfalse).
Root ID is derived by registering ancestors first. No credential or entitlement
payloads. Existing per-client native/authorization checks remain authoritative.

Wake API: ControllerTabs.execute('tabs.family.VERB', args), CLI
`codex-wake --wake-root ROOT tabs family VERB --arguments JSON --json`.
Portable schema: bot_family_contract.specs(), shared CLI/HTTP/MCP. Mutations retain
existing expected_target/_request journal semantics under logical@bot-families.

Core owner BotFamilies(root,tabs=ControllerTabs) in bot_families.py:
state()/save(state),get(bot_id,state=None),ancestors(bot,state=None),
register(descriptor,state),bind(args,state),resolve_binding(bot,client_id,environment=None),
observations(),annotate(resources),target(),execute(operation,args).
State: version1,bots mapping; each descriptor includes root_bot_id and bindings{}.
Binding key: binding_key(client_id,environment) JSON tuple. Binding contains
client_id,environment,attachment{workspace,window_id,pane_id,namespace,process,backend,server},
optional thread_id. namespace hashes backend socket identity independently of session;
process is exact /proc birth evidence. resolve_binding scans enrolled namespaces,
returns saved binding with live attachment and manually_moved flag; None if absent,
replaced or ambiguous. Manual moves retain identity; no title-based binding.

T3 owns bot_family_placement.py and focused existing-harness tests. Its
execute(registry,verb,args,state) is invoked under registry lock for open/accept/
adopt/focus. Do not recurse into registry.execute while locked. Use core methods;
mutate state then registry.save. Primary owns core/schema/CLI, so communicate needed
contract changes rather than racing edits. Shared fields are in schema already.
Existing exact bound tabs need initial placement then reuse; later manual placement
wins. Persist intent before physical effect, reconcile missing results; don't silently
repeat unknown launch/close/move. Existing protected lifecycle/session/relocation
owners handle actual effects; focus detached until explicitly asked.

T4 owns new bot_family_display.py, formatter/monitor integration and focused tests.
Use BotFamilies.annotate(resources) to expose row.bot_family descriptor only after
exact live binding proof. ControllerTabs public inventory already annotates; monitor
rows bypass that path, so overlay through existing formatting/monitor seam. Preserve
formatting opt-out/manual hold/rollback and attention precedence. Navigation is T3.

T5 configures an explicit Wake adapter in Bots and registers ancestors/binds exact
bot conversation attachments before organization. Native Bots currently checks its
owned codex-bots tmux session; migration to a shared workers session must retain
window bot/thread/process ownership proof and supported native discovery. Never
create a duplicate native session merely to arrange tabs; uncertain effect holds.
No configured adapter means no change to existing installations.
