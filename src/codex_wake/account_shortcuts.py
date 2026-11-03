"""Local human shortcuts over the existing account/build/history owners."""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from uuid import UUID, uuid4

from .managed_inventory import InventoryError
from . import shortcut_store as store


def bounded_limit(value):
    result = int(value)
    if not 1 <= result <= 100:
        raise argparse.ArgumentTypeError('limit must be1–100')
    return result


def register(parser):
    commands = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    for verb in ('open', 'resume'):
        item = commands.add_parser(verb, help='open a named private account') if verb == 'open' else commands.choices['resume']
        item.add_argument('account', **({'nargs':'?'} if verb == 'resume' else {}), help='registered account name or alias; bare resume retains emergency-pause behavior')
        item.add_argument('--channel', choices=('stock', 'modded'), default='modded' if verb == 'open' else None, help='registered native channel (default: modded)')
        if verb == 'resume':
            item.add_argument('thread_id', nargs='?', help='exact saved UUID; omit for the native account chooser')
            item.add_argument('--last', action='store_true', help='reopen the most recently active conversation in this account')
    config = commands.choices['configuration']
    sub = next(a for a in config._actions if isinstance(a, argparse._SubParsersAction))
    item = sub.add_parser('default-root', help='explicitly save the user-local root used by account shortcuts')
    item.add_argument('root', type=Path, help='existing private Wake root containing controller-accounts.toml')
    history = commands.choices['history']
    sub = next(a for a in history._actions if isinstance(a, argparse._SubParsersAction))
    for verb in ('recent', 'import-recent'):
        item = sub.add_parser(verb, help='view recent saved conversations' if verb == 'recent' else 'preview and copy a frozen recent-session selection')
        item.add_argument('--owner', required=verb == 'recent', help='source account name or alias; required for a new transfer preview')
        item.add_argument('--limit', type=bounded_limit, default=10 if verb == 'recent' else None, help='latest N conversations,1–100 (default:10)')
        item.add_argument('--json', action='store_true', dest='as_json', help='emit structured results rather than a compact listing')
        if verb == 'import-recent':
            item.add_argument('--destination', help='destination account for source-preserving copies')
            item.add_argument('--channel', choices=('stock','modded'), default=None, help='registered native channel (default: modded)')
            item.add_argument('--batch', help='reuse this frozen batch ID; never select newer history on retry')
            item.add_argument('--yes', action='store_true', help='explicitly confirm the frozen selection for copying')
            item.add_argument('--preview', action='store_true', help='save/show the selection without native effects or confirmation')


def handles(args):
    return (args.command == 'open' or args.command == 'resume' and (args.account is not None or args.thread_id is not None or args.last or args.channel is not None) or args.command == 'configuration' and args.account_verb == 'default-root'
            or args.command == 'history' and args.history_verb in ('recent','import-recent'))


def recent(root, owner, limit):
    from .history_commands import execute, policy
    result = execute('history.search', {'owners':[owner], 'sort':'recent', 'limit':limit}, root,
                     authorized_accounts=policy(root).get('readable_accounts', []))
    if result['status'] != 'completed':
        raise InventoryError(result['error']['code'], result['error']['message'])
    return result['result']


def show_recent(value):
    print('Recent conversations (latest activity first):')
    for row in value['sessions']:
        try:
            stamp = datetime.fromtimestamp(row['updated_at'], timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError, TypeError):
            stamp = 'time unknown'
        print(row['thread_id'] + '  ' + stamp + '  ' + json.dumps(row['title']) + '  ' + json.dumps(row['cwd']))
    for hold in value.get('holds', []):
        print('Held: ' + json.dumps(hold, sort_keys=True))


def launch(args, root):
    from .build_commands import owner_from_root
    if args.command == 'resume' and args.last and args.thread_id:
        raise ValueError('choose an exact conversation UUID or --last, not both')
    if not args.account:
        raise ValueError('conversation resume requires an account name')
    if args.command == 'resume' and any(getattr(args, key, None) for key in ('all_roots','registry_dir','authorized_root','caller_wake_subject','as_json')):
        raise ValueError('account resume cannot be mixed with emergency-pause scope flags')
    owner = owner_from_root(root)
    account_pin = owner.accounts.execute('accounts.resolve', {'selector':args.account})['account']['target']
    def same_account(target):
        if any(target.get(key) != value for key,value in account_pin.items()):
            raise InventoryError('stale_target', 'account binding changed while selecting its conversation or build')
    native = []
    if args.command == 'resume':
        identifier = args.thread_id
        if args.last:
            found = recent(root, args.account, 1)
            if found.get('holds') or not found['sessions']:
                raise ValueError('latest conversation unavailable; inspect history recent')
            selected_session = found['sessions'][0]
            same_account(selected_session['target'])
            identifier = selected_session['thread_id']
        if identifier is not None:
            if str(UUID(identifier)) != identifier:
                raise ValueError('exact native conversation UUID required')
            from .history_commands import execute, policy
            read_arguments = {'owner':args.account,'thread_id':identifier}
            if args.last:
                read_arguments['expected_target'] = selected_session['target']
            value = execute('history.read', read_arguments, root,
                            authorized_accounts=policy(root).get('readable_accounts', []))
            if value['status'] != 'completed':
                raise InventoryError(value['error']['code'], value['error']['message'])
            same_account(value['result']['session']['target'])
        native = ['resume'] + ([identifier] if identifier else [])
    channel = args.channel or 'modded'
    builds = owner.execute('builds.list', {'account':args.account})['builds']
    selected = next(row for row in builds if row['name'] == channel)
    same_account(selected['target'])
    if selected.get('status') == 'held':
        raise ValueError(selected['reason'])
    print('Opening '+channel+' / '+selected['target']['account'], file=sys.stderr)
    result = owner.execute('builds.launch', dict(account=args.account, channel=channel, expected_target=selected['target'], args=native))
    return result['exit_code']


def batch_path(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch('[0-9a-f]{32}', identifier):
        raise ValueError('batch must be an exact saved32-character hexadecimal ID')
    return Path(root) / 'controller-history-batches' / (identifier + '.json')


def import_recent(args, root):
    from .daemon_commands import execute as daemon_execute, local_operator
    from .history_commands import protected_import
    directory = Path(root) / 'controller-history-batches'
    with store.locked(directory):
        if args.batch:
            path = batch_path(root,args.batch)
            batch = store.read(path)
            if (not isinstance(batch,dict) or batch.get('version') != 1 or batch.get('id') != args.batch
                    or not isinstance(batch.get('entries'),list) or len(batch['entries']) > 100):
                raise ValueError('invalid frozen copy batch')
            if (args.owner is not None and args.owner != batch['owner']) or (args.destination is not None and args.destination != batch['destination']):
                raise ValueError('batch owner/destination is fixed; omit conflicting flags')
            if (args.channel is not None and args.channel != batch['channel']) or (args.limit is not None and args.limit != batch['limit']):
                raise ValueError('batch channel/selection limit is fixed; create a new preview to change it')
        else:
            if not args.owner or not args.destination:
                raise ValueError('new transfer requires --owner and --destination')
            channel=args.channel or 'modded'
            limit=args.limit or 10
            found = recent(root,args.owner,limit)
            destination = daemon_execute(root,'daemons.status',dict(account=args.destination,channel=channel))['result']['daemon']
            identifier=uuid4().hex
            batch=dict(version=1,id=identifier,owner=args.owner,destination=args.destination,channel=channel,limit=limit,
                       entries=[],holds=found['holds'],status='preview')
            for session in found['sessions']:
                if session['target']['home'] == destination['target']['home']:
                    raise ValueError('source and destination must be distinct account homes')
                transfer=hashlib.sha256(json.dumps([session['target']['home'],session['target']['home_generation'],session['thread_id'],session['target']['rollout_revision'],destination['target']['home'],destination['target']['home_generation'],channel],sort_keys=True).encode()).hexdigest()
                key='recent-'+transfer
                target=destination['target']
                payload=dict(owner=args.owner,thread_id=session['thread_id'],destination=args.destination,channel=channel,
                             expected_source=session['target'],expected_target=target,
                             _request=dict(operation_id='history-import-'+hashlib.sha256(key.encode()).hexdigest()[:32],
                                           idempotency_key=key,correlation_id=key,binding='local-cli',target=target))
                batch['entries'].append(dict(thread_id=session['thread_id'],title=session['title'],transfer_key=transfer,arguments=payload,status='pending'))
            path=batch_path(root,identifier)
            store.write(path,batch)
        if not args.as_json:
            print('Frozen batch: '+batch['id']+'; copy '+str(len(batch['entries']))+' selected conversations from '+batch['owner']+' to '+batch['destination'])
            for entry in batch['entries']:
                print(entry['thread_id']+'  '+json.dumps(entry['title'])+'  '+entry['status'])
            for hold in batch['holds']:
                print('Held discovery: '+json.dumps(hold,sort_keys=True))
            print('Retry only this selection with: history import-recent --batch '+batch['id'])
        from .cli_targets import interactive, confirm_intent
        confirmed=args.yes
        if not args.preview and not confirmed and interactive():
            confirmed=confirm_intent('Create destination copies; preserve originals. Unsupported histories stay held.')
        if confirmed and not args.preview:
            for entry in batch['entries']:
                if entry['status'] in ('copied','unsupported','failed'):
                    continue
                transfer=entry.get('transfer_key')
                if not isinstance(transfer,str) or not re.fullmatch('[0-9a-f]{64}',transfer):
                    raise ValueError('invalid retained transfer identity')
                retained=directory/('intent-'+transfer+'.json')
                if retained.exists() or retained.is_symlink():
                    payload=store.read(retained)
                    if not isinstance(payload,dict) or payload.get('thread_id') != entry['thread_id']:
                        raise ValueError('invalid retained transfer intent')
                    entry['arguments']=payload
                else:
                    payload=entry['arguments']
                    store.write(retained,payload)
                # Save admission before dispatch; a killed caller must reconcile
                # this same intent via the existing operation journal on retry.
                entry['status']='submitted';store.write(path,batch)
                actor=local_operator(payload['expected_target'],{'control','observe','history.observe'})
                actor=replace(actor,targets=[payload['expected_source'],payload['expected_target']])
                try:
                    value=protected_import(payload,root,actor=actor,authorize=lambda:actor)
                    operation=value['result']['operation']
                    entry['operation_id']=operation['operation_id']
                    entry['operation_phase']=operation['phase']
                    entry['status']=('copied' if operation['execution']=='completed' else 'unsupported' if operation.get('reason') == 'unsupported_goal_import' else 'failed' if operation.get('execution')=='not_started' else 'uncertain')
                    if entry['status']=='copied':entry['destination_thread_id']=operation['result']['thread_id']
                    else:entry['reason']=operation.get('reason') or operation.get('execution')
                except (ValueError,OSError) as error:
                    # The durable owner may already have submitted an effect.
                    # Keep this intent rather than manufacturing another fork.
                    entry.update(status='uncertain',reason=getattr(error,'code','observation_unavailable'))
                store.write(path,batch)
            states=[entry['status'] for entry in batch['entries']]
            batch['status']='completed' if all(s=='copied' for s in states) and not batch['holds'] else 'partial'
            store.write(path,batch)
        print(json.dumps(batch,sort_keys=True) if args.as_json else 'Batch '+batch['id']+': '+batch['status']+'; '+json.dumps({s:sum(e['status']==s for e in batch['entries']) for s in sorted({e['status'] for e in batch['entries']})}))
        if not args.as_json and batch['status'] != 'preview':
            for entry in batch['entries']:
                print(entry['thread_id']+'  '+entry['status']+'  '+str(entry.get('destination_thread_id') or entry.get('reason','')))
        return 0 if batch['status'] in ('preview','completed') else 2


def command(args):
    try:
        if args.command == 'configuration':
            from .account_commands import execute
            root=args.root.expanduser().absolute()
            if root != root.resolve() or not root.is_dir():
                raise ValueError('existing real Wake root required')
            store.private_directory(root)
            value=execute('accounts.list',{},root)
            if value['status']!='completed':raise ValueError('configured account registry required')
            path=store.preference_path()
            with store.locked(path.parent):store.write(path,{'version':1,'wake_root':str(root)})
            print('Shortcut default root: '+str(root))
            return 0
        root=store.default_root(args.wake_root)
        if args.command in ('open','resume'):return launch(args,root)
        if args.history_verb=='recent':
            value=recent(root,args.owner,args.limit)
            if args.as_json:print(json.dumps(value,sort_keys=True))
            else:show_recent(value)
            return 0 if value['status']=='complete' else 2
        return import_recent(args,root)
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'status':'failed','error':{'code':getattr(error,'code','shortcut_held'),'message':str(error)}}))
        return 2
    except KeyboardInterrupt:
        return 130
