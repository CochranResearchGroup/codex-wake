"""Discoverable operation contracts; execution remains with existing owners.

Only the first product slice is migrated. Native caller identity and local human
login/status presentation remain explicit adapter exceptions.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass


PARAMETERS = {
    'mode': ('Create an independent private configuration snapshot; legacy creation remains the default.', {'type':'string','enum':['independent']}),
    'source': ('Registered source store selector, including stock.', {'type':'string'}),
    'home': ('Absolute existing stock home; registration changes only Wake metadata.', {'type':'string'}),
    'destinations': ('Explicit destination store selectors.', {'type':'array','items':{'type':'string'},'minItems':1,'maxItems':64}),
    'categories': ('Selected configuration categories; authentication is excluded.', {'type':'array','items':{'type':'string','enum':['settings','mcp','hooks','skills','rules']},'minItems':1}),
    'operation_id': ('Stable sync intent identifier; reconcile unknown outcomes before resubmitting.', {'type':'string'}),
    'expected_snapshot': ('Exact snapshot digest returned by sync preview.', {'type':'string'}),
    'propagate_deletions': ('Explicitly propagate matching source deletions; default preserves destination copies.', {'type':'boolean'}),
    'reload': ('Request selected-profile reload if supported; otherwise each destination reports next-launch remedy.', {'type':'boolean'}),
    'receipt_id': ('Exact prior migration receipt for a qualified rollback.', {'type':'string'}),
    'limit': ('Maximum recent conversations, from1 to100 (default:10 for shortcuts).', {'type': 'integer', 'minimum': 1, 'maximum': 100}),
    'sort': ('Order by recent activity when set to recent; default preserves existing discovery order.', {'type': 'string', 'enum': ['recent']}),
    'root': ('Existing private Wake account root saved only for local shortcuts.', {'type':'string'}),
    'last': ('Reopen the most recently active saved conversation for the selected account.', {'type':'boolean'}),
    'batch': ('Exact frozen copy-batch ID to preview or retry without selecting newer sessions.', {'type':'string'}),
    'yes': ('Explicitly confirm the frozen source-preserving batch copy.', {'type':'boolean'}),
    'preview': ('Show/save the frozen selection without native copying or daemon starts.', {'type':'boolean'}),
    'selector': ('Account name or configured alias.', {'type': 'string'}),
    'account': ('Account name or configured alias.', {'type': 'string'}),
    'alias': ('Optional alternate name for the newly created account.', {'type': 'string'}),
    'channel': ('Registered native build channel (default: modded).', {'type': 'string', 'enum': ['stock', 'modded']}),
    'expected_target': ('Exact target JSON from the corresponding resolve, list or status command; replacement is refused.', {'type': 'object'}),
    'expected_source': ('Exact source session target JSON from history read.', {'type': 'object'}),
    'idempotency_key': ('Stable key for this intent; retain it to reconcile an uncertain result. Different inputs conflict.', {'type': 'string'}),
    '_request': ('Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target.', {'type': 'object'}),
    'confirm': ('Confirm the displayed scoped effect; does not override a changed target.', {'type': 'boolean'}),
    'as_json': ('Emit structured results for this command.', {'type': 'boolean'}),
    'device_auth': ('Sign in using a one-time device code approved in your browser.', {'type': 'boolean'}),
    'with_api_key': ('Read the API key from standard input; never put it in command arguments.', {'type': 'boolean'}),
    'arguments': ('Advanced JSON object of operation arguments; preserved for scripts. See generated command reference.', {'type': 'object'}),
    'thread_id': ('Native saved conversation identifier in its owning account.', {'type': 'string'}),
    'owner': ('Exact account that owns the saved conversation.', {'type': 'string'}),
    'owners': ('Limit search to these explicitly permitted owning accounts; repeat --owner.', {'type': 'array', 'items': {'type': 'string'}}),
    'destination': ('Destination account for a distinct source-preserving conversation copy.', {'type': 'string'}),
    'query': ('Filter permitted saved conversation metadata (default: all).', {'type': 'string'}),
    'intent': ('Existing exact-owner resume intent; does not grant new work authority.', {'type': 'string'}),
    'expires_at': ('Expiration timestamp for the resume intent.', {'type': 'string'}),
    'bus_root': ('Existing enrolled mailbox runtime root for caller verification.', {'type': 'string'}),
    'operator_capability': ('Path to the private operator capability; never its secret contents.', {'type': 'string'}),
    'app_server': ('Enrolled native app-server endpoint (default: unix://).', {'type': 'string'}),
    'upstream': ('Pinned upstream commit SHA.', {'type':'string', 'pattern':'^[a-fA-F0-9]{40}$'}),
    'mod_revision': ('Pinned retained mod commit SHA.', {'type':'string', 'pattern':'^[a-fA-F0-9]{40}$'}),
    'run_id': ('Durable native release run identifier.', {'type':'string'}),
    'jobs': ('Explicit maximum compiler jobs.', {'type':'integer', 'minimum':1}),
    'output': ('Release result presentation.', {'type':'string','enum':['compact','json','progress','diagnostics']}),
    'max_items': ('Maximum diagnostic or progress entries.', {'type':'integer','minimum':1,'maximum':40}),
    'expected_cache': ('Exact cache fingerprint returned by cleanup preview.', {'type':'string'}),
    'recipe': ('Host-registered build recipe name, never an arbitrary executable or path.', {'type': 'string'}),
    'identifier': ('Existing immutable build artifact identifier to select.', {'type': 'string'}),
    'args': ('Native client arguments for the registered build.', {'type': 'array', 'items': {'type': 'string'}}),
}


@dataclass(frozen=True)
class Operation:
    name: str
    summary: str
    tool: str | None
    parameters: tuple[str, ...] = ()
    required: tuple[str, ...] = ()
    effect: str = 'Read-only observation; no model turn.'
    example: str = ''

    def schema(self):
        if self.name.startswith('tabs.') and self.tool:
            from .tab_contract import BY_OPERATION
            spec=BY_OPERATION[self.name][1]
            return {'type':'object','properties':deepcopy(spec[3]),'required':list(spec[4]),'additionalProperties':False}
        properties = {key: dict(deepcopy(PARAMETERS[key][1]), description=PARAMETERS[key][0]) for key in self.parameters}
        schema = {'type': 'object', 'properties': properties, 'required': list(self.required), 'additionalProperties': False}
        if self.name == 'builds.run':
            schema['oneOf'] = [
                {'required':['run_id'], 'not':{'anyOf':[{'required':[key]} for key in ('recipe','upstream','mod_revision')]}},
                {'required':['recipe','upstream','mod_revision'], 'not':{'required':['run_id']}},
            ]
        return schema


OPERATIONS = (
    Operation('accounts.init', 'Initialize a new private account registry.', 'wake_controller_account_init', ('_request',), ('_request',), 'Creates only an empty isolated registry; preserves existing state.', 'accounts init'),
    Operation('accounts.create', 'Create a private account home without credentials.', 'wake_controller_account_create', ('selector', 'alias', 'mode', 'source', '_request'), ('selector', '_request'), 'Creates account configuration and a private home; does not sign in.', 'accounts create work --alias office'),
    Operation('accounts.readiness', 'Inspect the selected profile readiness and specific remedies.', 'wake_controller_account_readiness', ('selector','expected_target'), ('selector',), 'Read-only; native limits, refresh and backend acceptance remain separately qualified. Remote callers cannot supply launcher or manifest paths.', 'accounts readiness work --json'),
    Operation('stores.register', 'Register the stable shared stock store in Wake metadata.', 'wake_controller_store_register', ('selector','home'), ('selector','home'), 'Preserves stock configuration and login. Remote admin grant must pin the registry revision and selected home.', 'stores register stock --home /absolute/stock/home'),
    Operation('stores.resolve', 'Resolve a registered stock or profile store.', 'wake_controller_store_resolve', ('selector',), ('selector',), example='stores resolve stock'),
    Operation('stores.list', 'List permitted registered stores with stable identities.', 'wake_controller_stores', example='stores list'),
    Operation('configuration.sync.preview', 'Preview selected directional configuration changes and conflicts.', 'wake_controller_configuration_sync_preview', ('source','destinations','categories','operation_id','propagate_deletions','reload'), ('source','destinations','categories','operation_id'), 'Saves a frozen preview outside stock; sensitive values are redacted. Grant must cover every selected store.', 'configuration sync preview --source stock --destination work --category mcp --operation-id sync-1'),
    Operation('configuration.sync.apply', 'Apply safe selected changes and preserve divergent destination entries.', 'wake_controller_configuration_sync_apply', ('source','destinations','categories','operation_id','expected_snapshot','propagate_deletions','reload'), ('source','destinations','categories','operation_id','expected_snapshot'), 'Repeat-safe per-destination results. Default takes effect at next launch; reload reports an explicit unsupported remedy when no selected-profile owner is available.', 'configuration sync apply --source stock --destination work --category mcp --operation-id sync-1 --expected-snapshot SNAPSHOT'),
    Operation('accounts.list', 'List registered account names and targets.', 'wake_controller_accounts', example='accounts list'),
    Operation('accounts.resolve', 'Resolve one account name to its exact current target.', 'wake_controller_account_resolve', ('selector', 'expected_target'), ('selector',), example='accounts resolve work'),
    Operation('accounts.login', 'Sign into a named private account through native login.', None, effect='Local human CLI only. Writes native credentials; active account clients or daemons hold login.', example='accounts login work --device-auth'),
    Operation('accounts.status', 'Observe sanitized local authentication evidence.', 'wake_controller_account_status', ('selector', 'expected_target'), ('selector',), 'No provider verification or refresh in --json/API/MCP. Human CLI retains native login status.', 'accounts status work --json'),
    Operation('configuration.explain', 'Explain effective settings, skills and configuration provenance.', 'wake_controller_configuration', ('selector', 'expected_target'), ('selector',), example='configuration explain work'),
    Operation('builds.list', 'List registered builds and their exact targets.', 'wake_builds_list', ('account',), ('account',), example='builds list --account work'),
    Operation('builds.launch', 'Open a native client using an exact registered account build.', 'wake_builds_launch', ('account','channel','expected_target','_request','args'), ('account','channel','expected_target','_request'), 'Attaches a client; no provider turn unless explicitly requested through client arguments.', 'builds launch --account work --channel modded --expected-target "$TARGET"'),
    Operation('builds.stage', 'Stage one host-registered immutable build recipe.', 'wake_builds_stage', ('recipe','_request'), ('recipe','_request'), 'Runs the configured build recipe under existing build authority.', 'builds stage --arguments \'{"recipe":"candidate"}\''),
    Operation('builds.select', 'Select a staged immutable artifact for an account.', 'wake_builds_select', ('account','channel','expected_target','_request','identifier'), ('account','channel','expected_target','_request','identifier'), 'Changes future build selection; does not imply a running daemon changed.', 'builds select --account work --channel modded --expected-target "$TARGET" --identifier ARTIFACT'),
    Operation('builds.rollback', 'Restore the prior registered account build selection.', 'wake_builds_rollback', ('account','channel','expected_target','_request'), ('account','channel','expected_target','_request'), 'Changes selected build under existing rollback policy.', 'builds rollback --account work --channel modded --expected-target "$TARGET"'),
    Operation('history.search', 'Search explicitly permitted saved conversation metadata.', 'wake_controller_history_search', ('owners','query','limit','sort'), example='history search --owner work --query test'),
    Operation('history.read', 'Read a saved conversation from its exact permitted owner.', 'wake_controller_history_read', ('owner','thread_id','expected_target'), ('owner','thread_id'), example='history read THREAD --owner work'),
    Operation('history.resume', 'Resume a saved conversation under existing exact-owner authority.', 'wake_controller_history_resume', ('owner','thread_id','expected_target','intent','expires_at'), ('owner','thread_id','expected_target','intent','expires_at'), 'Requires existing enrolled caller permission; does not renew work or allowance.', 'history resume THREAD --owner work --expected-target "$TARGET" --intent INTENT --expires-at TIME --bus-root ROOT --operator-capability FILE'),
    Operation('history.import', 'Copy a supported saved snapshot between stock and profile stores.', 'wake_controller_history_import', ('owner','thread_id','destination','channel','expected_source','expected_target','_request'), ('owner','thread_id','destination','channel','expected_source','expected_target','_request'), 'Creates a new destination UUID; source remains unchanged. Reports saved snapshot boundaries and excluded unsupported entries; transfers no credentials, grants or allowance.', 'history import THREAD --owner work --destination personal --expected-source "$SOURCE" --expected-target "$TARGET" --idempotency-key copy-1'),
) + tuple(
    Operation('daemons.'+verb, summary, 'wake_daemons_'+verb,
              tuple(([] if verb=='list' else ['account'])+['channel']+([] if verb in ('list','status') else ['expected_target','confirm','_request'])),
              tuple(([] if verb=='list' else ['account'])+([] if verb in ('list','status') else ['expected_target','_request'])),
              'Read-only process/socket/build observation; unavailable is not orphan-free proof.' if verb in ('list','status') else 'Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.',
              'daemons '+verb+('' if verb=='list' else ' work')+('' if verb in ('list','status') else ' --expected-target "$TARGET" --idempotency-key '+verb+'-1'+('' if verb=='start' else ' --yes')))
    for verb,summary in [('list','List account-scoped native daemon observations.'),('status','Inspect the exact account daemon and selected build.'),('start','Start the selected account daemon.'),('restart','Restart one exact account daemon.'),('update','Update one exact account daemon to a registered build.'),('stop','Stop one exact account daemon.')]
)
OPERATIONS += (
    Operation('open', 'Open the registered native client for one private account.', None, effect='Local human shortcut over builds.launch; internally pins the selected build and starts or attaches its daemon. No model prompt.', example='open work'),
    Operation('resume', 'Reopen a conversation in its named account; bare resume retains emergency-pause release.', None, effect='ACCOUNT selects the native conversation chooser; --last or UUID selects saved account history. Never mixes account and emergency scope flags.', example='resume work --last'),
    Operation('configuration.default-root', 'Save an explicit user-local root for account shortcuts.', None, effect='Changes only local shortcut preferences; explicit --wake-root wins. Does not change stock codex or unrelated legacy root defaults.', example='configuration default-root ROOT'),
    Operation('history.recent', 'View the latest saved conversations for one permitted account.', None, effect='Local shortcut to history.search with sort=recent and a bounded limit; API/MCP can use those same search arguments. Partial evidence stays visible.', example='history recent --owner work --limit 10'),
    Operation('history.import-recent', 'Preview and copy a frozen recent-conversation selection.', None, effect='Local batch orchestration over protected history.import. Retains exact intents and per-entry outcomes; same source revision/destination reuses the original copy. Requires both account daemons running; preview starts none.', example='history import-recent --owner work --destination personal --limit 10'),
)
OPERATIONS += tuple(Operation('builds.' + verb, summary, 'wake_builds_' + verb,
    ('recipe','upstream','mod_revision','run_id','jobs','output','max_items','confirm','expected_cache'),
    ('recipe','upstream','mod_revision') if verb == 'prepare' else (() if verb == 'run' else ('run_id',)),
    'Native release work in isolated WSL state; no working-account installation.',
    'builds ' + verb + (' --recipe RECIPE --upstream SHA --mod-revision SHA' if verb in ('prepare','run') else ' --run-id RUN'))
    for verb, summary in [('prepare','Prepare pinned source in an isolated worktree.'),('status','Inspect a durable native release run.'),('build','Build a complete immutable package through Cargo Signal.'),('resume','Reconcile and resume a native release run.'),('qualify','Qualify the exact package in disposable state.'),('cleanup','Preview or explicitly clean an inactive build cache.'),('run','Prepare, build and qualify one native release.')])
OPERATIONS += (
    Operation('migration.preview', 'Preview the existing host-selected migration or independent-profile adoption.', 'wake_controller_migration_preview', effect='Host migration strategy adopt_independent preserves history, sign-ins and local settings; no effect in preview.', example='migration preview'),
    Operation('migration.apply', 'Apply a pinned qualified migration or independent-profile adoption.', 'wake_controller_migration_apply', ('expected_target','_request'), ('expected_target','_request'), 'Local CLI uses operator authority; API/MCP require scoped grants. Mutations retain exact pins, durable intent and rollback custody.', 'migration apply --arguments "$ARGUMENTS"'),
    Operation('migration.rollback', 'Roll back one attributable unchanged migration or adoption.', 'wake_controller_migration_rollback', ('expected_target','receipt_id','_request'), ('expected_target','receipt_id','_request'), 'Preserves changed targets and uncertain outcomes for reconciliation.', 'migration rollback --arguments "$ARGUMENTS"'),
)
from .tab_contract import tool_specs as tab_tool_specs, cli_verb as tab_cli_verb
_TAB_EFFECT = ('Same-user local CLI resolves exact generations and retains durable request identity; '
               'API/MCP use explicit pins and authenticated scopes. Uncertain effects are never replayed. '
               'Grok/SSH exact health and unsupported backend continuity remain explicit unknown/held. '
               'Raw capture and input retain separate privacy/custody checks; observation grants no input access.')
OPERATIONS += tuple(Operation(spec[1],spec[2],tool,tuple(spec[3]),tuple(spec[4]),_TAB_EFFECT,
    'tabs '+tab_cli_verb(spec[1])+(' --workspace WORKSPACE' if 'workspace' in spec[3] else ''))
    for tool,spec in tab_tool_specs().items())
OPERATIONS += (Operation('tabs.result','Read a retained local UID-owned tab request after disconnect or workspace closure.',
    None,effect='Local CLI shortcut for authenticated common operations.result; no live workspace or new effect.',
    example='tabs result --request-id REQUEST'),)
BY_NAME = {op.name: op for op in OPERATIONS}


def public_tools():
    """Canonical OAuth schemas; native verified caller fields are adapter extras."""
    return {op.tool: (op.name, op.schema()) for op in OPERATIONS if op.tool}


def parser_paths(parser, path=()):
    yield path, parser
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                yield from parser_paths(child, (*path, name))


def apply_help(parser):
    """Enrich the existing compatibility parser from migrated operation metadata."""
    for path, item in parser_paths(parser):
        op = BY_NAME.get('.'.join(path))
        if not op and len(path)==3 and path[:2]==('tabs','routing'):
            op=BY_NAME.get('tabs.route.'+path[2])
        if not op and len(path)==3 and path[:2]==('tabs','sessions'):
            op=BY_NAME.get('tabs.session.'+path[2])
        if not op and len(path)==2 and path[0]=='tabs':
            op=next((candidate for candidate in OPERATIONS if candidate.name.startswith('tabs.') and tab_cli_verb(candidate.name)==path[1]),None)
        if not op:
            continue
        item.description = op.summary + '\n\n' + op.effect
        item.epilog = 'Examples:\n  codex-wake --wake-root ROOT ' + op.example
        item.formatter_class = argparse.RawDescriptionHelpFormatter
        for action in item._actions:
            if action.dest in PARAMETERS and not op.name.startswith('tabs.'):
                action.help = PARAMETERS[action.dest][0]
    return parser


def render_reference():
    lines = ['# Generated command reference', '', 'Generated from `codex_wake.command_contract`; do not edit by hand.', '',
             'Scope: stores, accounts, configuration, builds, daemons, migration and history. Other Wake',
             'commands are deferred from this contract migration; their existing interfaces remain.', '',
             'Local human login and status use native stdio. Structured status is cache evidence,',
             'not proof of current provider access. Native history MCP additionally requires',
             'verified caller identity; local CLI and scoped remote caller admission differ.', '',
             'Examples use placeholders ROOT, THREAD, TIME, FILE and exact target JSON.',
             'Resolve fresh targets before execution; empty target objects are never valid pins.', '']
    from .cli import build_parser
    parsers = dict(parser_paths(build_parser()))
    from .tab_contract import CAPABILITIES
    lines += ['## Tab capability boundaries', '']
    for capability, details in CAPABILITIES.items():
        lines += ['- `'+capability+'`: **'+details['status']+'**. '+details['reason']]
    lines += ['']
    for op in OPERATIONS:
        lines += ['## ' + op.name.replace('.', ' '), '', op.summary, '', op.effect, '',
                  'Transport: ' + ('CLI / API / OAuth MCP / native MCP (`'+op.tool+'`).' if op.tool else 'Local human CLI only.'), '',
                  '```sh', 'codex-wake --wake-root ROOT '+op.example, '```', '']
        item = parsers.get(('tabs',tab_cli_verb(op.name)) if op.name.startswith('tabs.') else tuple(op.name.split('.')))
        if item is not None:
            lines += ['### CLI help', '', '```text', item.format_help().rstrip(), '```', '']
        if op.parameters:
            lines += ['| Argument | Required remotely | Meaning |', '|---|---|---|']
            for key in op.parameters:
                lines.append('| `'+key+'` | '+('yes' if key in op.required else 'no')+' | '+PARAMETERS.get(key,(key.replace('_',' ')+'.',{}))[0]+' |')
            lines.append('')
    return '\n'.join(lines)+'\n'


def describe(operation):
    op = BY_NAME.get(operation)
    return op.summary + ' ' + op.effect if op else 'Controller operation ' + operation


def apply_native_contract(specs):
    """Keep native dispatch and verified-caller admission; share domain arguments."""
    for op in OPERATIONS:
        if op.tool not in specs:
            continue
        old = specs[op.tool]
        schema = op.schema()
        extras = {key: value for key, value in old[3].items() if key == 'caller_thread_id'}
        required = list(op.required) + [key for key in old[4] if key in extras]
        specs[op.tool] = (*old[:2], describe(op.name), {**schema['properties'], **extras}, required, old[5])


def coverage_report(parser):
    paths = ['.'.join(path) for path, item in parser_paths(parser) if path and not any(isinstance(a, argparse._SubParsersAction) for a in item._actions)]
    result = {'schema_version': 1, 'migrated_operations': sorted(BY_NAME),
            'local_only': [op.name for op in OPERATIONS if op.tool is None],
            'deferred_commands': sorted(path for path in paths if path not in BY_NAME and not path.startswith('completion.')),
            'adapter_exceptions': {'accounts.login': 'Local native credential stdin/stdio only.',
                'accounts.status': 'Human CLI uses native login status; structured transports observe unverified local cache only.',
                'history.search/read/resume': 'Native MCP additionally verifies caller_thread_id; API/OAuth use scoped grants.',
                'resume': 'ACCOUNT selects local conversation reopening; bare resume retains existing emergency-pause controls outside the shortcut contract.',
                'local_cli': 'Host operator admission differs from scoped remote authorization; no implicit remote privilege.'},
            'mcp_tools': {op.name: op.tool for op in OPERATIONS if op.tool}}

    tab_paths={'tabs.'+tab_cli_verb(op.name) for op in OPERATIONS if op.name.startswith('tabs.')}
    tab_paths.update('tabs.sessions.'+op.name.rsplit('.',1)[1] for op in OPERATIONS if op.name.startswith('tabs.session.'))
    tab_paths.update('tabs.routing.'+op.name.rsplit('.',1)[1] for op in OPERATIONS if op.name.startswith('tabs.route.'))
    result['deferred_commands']=[name for name in result['deferred_commands'] if name not in tab_paths]
    from .tab_contract import CAPABILITIES
    result['tab_capabilities']=deepcopy(CAPABILITIES)
    result['adapter_exceptions']['tabs']='Same-user local CLI resolves pins; API/MCP retain explicit pins and scoped authority. Raw input/capture and unsupported runtime/backends remain held. tabs result aliases common operations.result locally.'
    from .local_control_service import contract
    local=contract()
    result['local_controller']=local
    covered={'.'.join(value['cli']) for value in local['operations'].values()}|set(local['local_only'])
    result['deferred_commands']=[name for name in result['deferred_commands'] if name not in covered]
    result['adapter_exceptions']['local_controller']=local['admission']
    return result
