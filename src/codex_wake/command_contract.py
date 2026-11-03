"""Discoverable operation contracts; execution remains with existing owners.

Only the first product slice is migrated. Native caller identity and local human
login/status presentation remain explicit adapter exceptions.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass


PARAMETERS = {
    'selector': ('Account name or configured alias.', {'type': 'string'}),
    'account': ('Account name or configured alias.', {'type': 'string'}),
    'alias': ('Optional alternate name for the newly created account.', {'type': 'string'}),
    'channel': ('Registered native build channel (default: modded).', {'type': 'string', 'enum': ['stock', 'modded']}),
    'expected_target': ('Exact target JSON from the corresponding resolve, list or status command; replacement is refused.', {'type': 'object'}),
    'expected_source': ('Exact source session target JSON from history read.', {'type': 'object'}),
    'idempotency_key': ('Stable key for this intent; retain it to reconcile an uncertain result. Different inputs conflict.', {'type': 'string'}),
    '_request': ('Durable request metadata: operation_id, idempotency_key, correlation_id, binding and exact target.', {'type': 'object'}),
    'confirm': ('Confirm interruption of the exact selected daemon; does not override a changed target.', {'type': 'boolean'}),
    'as_json': ('Emit the structured result; authentication status uses local cache evidence without provider verification.', {'type': 'boolean'}),
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
        properties = {key: dict(deepcopy(PARAMETERS[key][1]), description=PARAMETERS[key][0]) for key in self.parameters}
        return {'type': 'object', 'properties': properties, 'required': list(self.required), 'additionalProperties': False}


OPERATIONS = (
    Operation('accounts.init', 'Initialize a new private account registry.', 'wake_controller_account_init', ('_request',), ('_request',), 'Creates only an empty isolated registry; preserves existing state.', 'accounts init'),
    Operation('accounts.create', 'Create a private account home without credentials.', 'wake_controller_account_create', ('selector', 'alias', '_request'), ('selector', '_request'), 'Creates account configuration and a private home; does not sign in.', 'accounts create work --alias office'),
    Operation('accounts.list', 'List registered account names and targets.', 'wake_controller_accounts', example='accounts list'),
    Operation('accounts.resolve', 'Resolve one account name to its exact current target.', 'wake_controller_account_resolve', ('selector', 'expected_target'), ('selector',), example='accounts resolve work'),
    Operation('accounts.login', 'Sign into a named private account through native login.', None, effect='Local human CLI only. Writes native credentials; active account clients or daemons hold login.', example='accounts login work --device-auth'),
    Operation('accounts.status', 'Observe sanitized local authentication evidence.', 'wake_controller_account_status', ('selector', 'expected_target'), ('selector',), 'No provider verification or refresh in --json/API/MCP. Human CLI retains native login status.', 'accounts status work --json'),
    Operation('configuration.explain', 'Explain effective settings, skills and configuration provenance.', 'wake_controller_configuration', ('selector', 'expected_target'), ('selector',), example='configuration explain work'),
    Operation('builds.list', 'List registered builds and their exact targets.', 'wake_builds_list', ('account',), ('account',), example='builds list --arguments \'{"account":"work"}\''),
    Operation('builds.launch', 'Open a native client using an exact registered account build.', 'wake_builds_launch', ('account','channel','expected_target','_request','args'), ('account','channel','expected_target','_request'), 'Attaches a client; no provider turn unless explicitly requested through client arguments.', 'builds launch --arguments \'{"account":"work","channel":"modded","expected_target":{}}\''),
    Operation('builds.stage', 'Stage one host-registered immutable build recipe.', 'wake_builds_stage', ('recipe','_request'), ('recipe','_request'), 'Runs the configured build recipe under existing build authority.', 'builds stage --arguments \'{"recipe":"candidate"}\''),
    Operation('builds.select', 'Select a staged immutable artifact for an account.', 'wake_builds_select', ('account','channel','expected_target','_request','identifier'), ('account','channel','expected_target','_request','identifier'), 'Changes future build selection; does not imply a running daemon changed.', 'builds select --arguments \'{"account":"work","identifier":"ARTIFACT","expected_target":{}}\''),
    Operation('builds.rollback', 'Restore the prior registered account build selection.', 'wake_builds_rollback', ('account','channel','expected_target','_request'), ('account','channel','expected_target','_request'), 'Changes selected build under existing rollback policy.', 'builds rollback --arguments \'{"account":"work","channel":"modded","expected_target":{}}\''),
    Operation('history.search', 'Search explicitly permitted saved conversation metadata.', 'wake_controller_history_search', ('owners','query'), example='history search --owner work --query test'),
    Operation('history.read', 'Read a saved conversation from its exact permitted owner.', 'wake_controller_history_read', ('owner','thread_id','expected_target'), ('owner','thread_id'), example='history read THREAD --owner work'),
    Operation('history.resume', 'Resume a saved conversation under existing exact-owner authority.', 'wake_controller_history_resume', ('owner','thread_id','expected_target','intent','expires_at'), ('owner','thread_id','expected_target','intent','expires_at'), 'Requires existing enrolled caller permission; does not renew work or allowance.', 'history resume THREAD --owner work --expected-target "$TARGET" --intent INTENT --expires-at TIME --bus-root ROOT --operator-capability FILE'),
    Operation('history.import', 'Copy a completed saved conversation into another account.', 'wake_controller_history_import', ('owner','thread_id','destination','channel','expected_source','expected_target','_request'), ('owner','thread_id','destination','channel','expected_source','expected_target','_request'), 'Creates a new destination UUID; source remains unchanged. Idle, goal-free legacy JSONL only; transfers no credentials, grants or allowance.', 'history import THREAD --owner work --destination personal --expected-source "$SOURCE" --expected-target "$TARGET" --idempotency-key copy-1'),
) + tuple(
    Operation('daemons.'+verb, summary, 'wake_daemons_'+verb,
              tuple(([] if verb=='list' else ['account'])+['channel']+([] if verb in ('list','status') else ['expected_target','confirm','_request'])),
              tuple(([] if verb=='list' else ['account'])+([] if verb in ('list','status') else ['expected_target','_request'])),
              'Read-only process/socket/build observation; unavailable is not orphan-free proof.' if verb in ('list','status') else 'Exact target and durable intent required. Restart/update/stop interrupt only the selected daemon and require confirmation. Uncertain results require reconciliation.',
              'daemons '+verb+('' if verb=='list' else ' work')+('' if verb in ('list','status') else ' --expected-target "$TARGET" --idempotency-key '+verb+'-1'+('' if verb=='start' else ' --yes')))
    for verb,summary in [('list','List account-scoped native daemon observations.'),('status','Inspect the exact account daemon and selected build.'),('start','Start the selected account daemon.'),('restart','Restart one exact account daemon.'),('update','Update one exact account daemon to a registered build.'),('stop','Stop one exact account daemon.')]
)
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
        if not op:
            continue
        item.description = op.summary + '\n\n' + op.effect
        item.epilog = 'Examples:\n  codex-wake --wake-root ROOT ' + op.example
        item.formatter_class = argparse.RawDescriptionHelpFormatter
        for action in item._actions:
            if action.dest in PARAMETERS:
                action.help = PARAMETERS[action.dest][0]
    return parser


def render_reference():
    lines = ['# Generated command reference', '', 'Generated from `codex_wake.command_contract`; do not edit by hand.', '',
             'Scope: accounts, configuration, builds, daemons and history. Other Wake',
             'commands are deferred from this contract migration; their existing interfaces remain.', '',
             'Local human login and status use native stdio. Structured status is cache evidence,',
             'not proof of current provider access. Native history MCP additionally requires',
             'verified caller identity; local CLI and scoped remote caller admission differ.', '',
             'Examples use placeholders ROOT, THREAD, TIME, FILE and exact target JSON.',
             'Resolve fresh targets before execution; empty target objects are never valid pins.', '']
    from .cli import build_parser
    parsers = dict(parser_paths(build_parser()))
    for op in OPERATIONS:
        lines += ['## ' + op.name.replace('.', ' '), '', op.summary, '', op.effect, '',
                  'Transport: ' + ('CLI / API / OAuth MCP / native MCP (`'+op.tool+'`).' if op.tool else 'Local human CLI only.'), '',
                  '```sh', 'codex-wake --wake-root ROOT '+op.example, '```', '']
        item = parsers.get(tuple(op.name.split('.')))
        if item is not None:
            lines += ['### CLI help', '', '```text', item.format_help().rstrip(), '```', '']
        if op.parameters:
            lines += ['| Argument | Required remotely | Meaning |', '|---|---|---|']
            for key in op.parameters:
                lines.append('| `'+key+'` | '+('yes' if key in op.required else 'no')+' | '+PARAMETERS[key][0]+' |')
            lines.append('')
    return '\n'.join(lines)+'\n'
