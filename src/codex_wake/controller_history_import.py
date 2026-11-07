"""Source-preserving cross-account copies through native persisted thread fork.

The existing operation journal owns idempotency and uncertain results. Native
Codex owns destination history creation; this module never edits its database.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
from uuid import UUID

from .controller_auth import AuthError
from .controller_history import ControllerHistory
from .controller_history_authorization import _ACCOUNT_FIELDS
from .controller_runtime import ControllerRuntime
from .managed_inventory import InventoryError
from .native_protocol import native_request


def _scope(actor, target):
    return any(_ACCOUNT_FIELDS <= set(scope) and all(target.get(k) == v for k, v in scope.items())
               for scope in actor.targets)


class ControllerHistoryImport:
    def __init__(self, root, *, host=None, environment=None, daemon_owner=None, request=native_request):
        self.root = Path(root)
        self.host = host or socket.gethostname()
        self.environment = environment or os.environ.get('WSL_DISTRO_NAME') or os.name
        self.daemons = daemon_owner
        self.request = request
        self.runtime = ControllerRuntime(root)

    def _daemon(self, account, channel):
        if self.daemons is None:
            from .daemon_commands import owner_from_root
            self.daemons = owner_from_root(self.root)
        value = self.daemons.execute('daemons.status', dict(account=account, channel=channel))['daemon']
        if (value.get('state') != 'running' or value.get('selected_build_running') is not True
                or not value.get('endpoint')):
            raise InventoryError('unsupported_target', 'import requires both account daemons to be running')
        return value

    def _request(self, daemon, method, params):
        def verify(connection, metadata):
            if metadata.get('codexHome') != daemon['target']['home']:
                raise InventoryError('stale_target', 'native import endpoint changed account home')
            # The daemon owner qualifies the selected socket, executable and birth.
            # Recheck its exact peer on the connection carrying this operation.
            import struct
            pid, uid, unused = struct.unpack('3i', connection.socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            process = daemon['target'].get('process') or {}
            if pid != process.get('pid') or uid != os.geteuid():
                raise InventoryError('stale_target', 'native import endpoint changed process')
        return self.request(daemon['endpoint'], daemon['target']['executable'], method, params, 10,
                            verify_connection=verify)

    @staticmethod
    def _thread(value, identifier, *, source=False):
        thread = value.get('thread', {})
        status = thread.get('status', {}).get('type')
        if (thread.get('id') != identifier or thread.get('ephemeral') is not False
                or status not in (('idle', 'notLoaded', 'active') if source else ('idle', 'notLoaded'))):
            raise InventoryError('unsupported_target', 'import requires persisted native conversation metadata')
        turns = thread.get('turns')
        if not isinstance(turns, list) or not turns:
            raise InventoryError('unsupported_target', 'import requires saved completed native turns')
        completed, excluded = [], []
        for turn in turns:
            if turn.get('status') == 'completed' and not excluded:
                if turn.get('itemsView', 'full') != 'full' or not isinstance(turn.get('items'), list):
                    raise InventoryError('unsupported_target', 'complete native turn items required')
                completed.append(turn)
            elif source and status == 'active' and turn.get('status') == 'inProgress':
                excluded.append(dict(turn_id=turn.get('id'), reason='incomplete_turn'))
            else:
                raise InventoryError('unsupported_target', 'native saved completed prefix is unavailable')
        if not completed:
            raise InventoryError('unsupported_target', 'no completed saved prefix is available')
        return dict(thread, turns=completed, _exclusions=excluded)

    def execute(self, actor, operation, arguments, *, authorize):
        fields = {'owner', 'thread_id', 'expected_source', 'destination', 'channel', 'expected_target', '_request'}
        if operation != 'history.import' or not isinstance(arguments, dict) or set(arguments) != fields:
            raise InventoryError('invalid_argument', 'exact source, destination and durable import request required')
        source, destination = arguments['expected_source'], arguments['expected_target']
        if (not isinstance(source, dict) or not isinstance(destination, dict)
                or arguments['channel'] not in ('stock', 'modded')):
            raise InventoryError('invalid_argument', 'pinned source and destination targets required')
        try:
            valid_id = isinstance(arguments['thread_id'], str) and str(UUID(arguments['thread_id'])) == arguments['thread_id']
        except ValueError:
            valid_id = False
        if not valid_id:
            raise InventoryError('invalid_argument', 'exact native source UUID required')
        def guard():
            current = authorize()
            if current != actor or 'history.observe' not in actor.scopes or not _scope(actor, source):
                raise AuthError('insufficient_scope')
            self.runtime.check_authority(actor, destination, 'control', authorize=authorize)
        guard()
        # Serialize admission and revision reuse across callers of this owner.
        # Native history is never locked or rewritten by Wake.
        with (self.runtime.path.parent / 'history-import.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return self.runtime.execute(actor, operation, arguments, authorize=lambda: (guard() or actor),
                dispatch=lambda unused, payload: self._import(payload, guard, actor))

    def _import(self, arguments, guard, actor):
        from .history_commands import policy
        permitted = policy(self.root).get('readable_accounts', [])
        reader = ControllerHistory(self.root / 'controller-accounts.toml', root=self.root,
            host=self.host, environment=self.environment, authorized_accounts=permitted,
            authorization_guard=lambda unused_operation, unused_arguments: guard())
        selected = dict(owner=arguments['owner'], thread_id=arguments['thread_id'], expected_target=arguments['expected_source'])
        read = reader.execute('history.read', selected)
        session = read['session']
        source = self._daemon(arguments['owner'], arguments['channel'])
        destination = self._daemon(arguments['destination'], arguments['channel'])
        if destination['target'] != arguments['expected_target']:
            raise InventoryError('stale_target', 'destination daemon or account generation changed')
        if (source['target']['home'] != session['target']['home']
                or source['target']['home_generation'] != session['target']['home_generation']
                or source['target']['home'] == destination['target']['home']):
            raise InventoryError('stale_target', 'distinct exact source and destination account homes required')
        thread_id = arguments['thread_id']
        original = self._thread(self._request(source, 'thread/read', dict(threadId=thread_id, includeTurns=True)), thread_id, source=True)
        if Path(original.get('path', '')).resolve() != Path(session['rollout_path']).resolve():
            raise InventoryError('stale_target', 'native source does not match pinned saved history')
        if self._request(source, 'thread/goal/get', dict(threadId=thread_id)) != {'goal': None}:
            raise InventoryError('unsupported_goal_import', 'existing native goals cannot be transferred')
        # Import an immutable bounded snapshot, not a source path a concurrent
        # writer could extend between the final check and native fork.
        path = Path(session['rollout_path'])
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as stream:
            content = stream.read(8 * 1024 * 1024 + 1)
        if hashlib.sha256(content).hexdigest() != session['target']['rollout_revision']:
            raise InventoryError('stale_target', 'source history changed before import')
        if any('goal' in str(row.get('payload', {}).get('type', '')).lower() for row in read['records']):
            raise InventoryError('unsupported_goal_import', 'goal-bearing history cannot be transferred')
        ongoing = original.get('status', {}).get('type') == 'active'
        exclusions = original['_exclusions']
        if ongoing:
            boundary = original['turns'][-1].get('id')
            # A native task_complete record is the persisted turn boundary;
            # never guess a cut from timestamps, item counts, or display text.
            offset, saved_end = 0, None
            for line in content.splitlines(keepends=True):
                offset += len(line)
                row = json.loads(line)
                payload = row.get('payload', {})
                if (row.get('type') == 'event_msg' and payload.get('type') == 'task_complete'
                        and payload.get('turn_id') == boundary):
                    saved_end = offset
            if not boundary or saved_end is None:
                raise InventoryError('unsupported_target', 'native completed saved boundary is unavailable')
            content = content[:saved_end]
        snapshot_revision = hashlib.sha256(content).hexdigest()
        # Reuse native copies from the existing caller-owned operation journal.
        # A different request key must not duplicate an unchanged source, nor
        # overwrite work subsequently performed in its destination conversation.
        cursor = 0
        previous = None
        while cursor is not None:
            records, cursor = self.runtime.owned_operations(actor, destination['target'], 'history.import',
                authorize=lambda: (guard() or actor), cursor=cursor)
            for record in records:
                retained = record.get('result') or {}
                provenance = retained.get('provenance', {})
                prior_source = provenance.get('source_target', {})
                if (provenance.get('source_thread_id') != thread_id
                        or any(prior_source.get(key) != session['target'].get(key)
                               for key in ('home', 'home_generation'))):
                    continue
                previous = retained.get('thread_id')
                if provenance.get('source_sha256') != snapshot_revision:
                    continue
                child = self._request(destination, 'thread/read', dict(threadId=retained['thread_id'], includeTurns=False)).get('thread', {})
                if (child.get('id') != retained['thread_id'] or child.get('forkedFromId') != thread_id
                        or child.get('ephemeral') is not False):
                    raise InventoryError('uncertain_effect', 'retained destination copy cannot be reconciled')
                return retained
        directory = self.root / 'controller-imports'
        directory.mkdir(mode=0o700, exist_ok=True)
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise InventoryError('configuration_unavailable', 'private import snapshot custody required')
        key = hashlib.sha256(json.dumps([session['target']['home'], session['target']['home_generation'],
            thread_id, snapshot_revision, destination['target']['home'],
            destination['target']['home_generation']], sort_keys=True).encode()).hexdigest()
        snapshot = directory / (key + '.jsonl')
        try:
            fd = os.open(snapshot, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            # A revision snapshot without a qualified journal result may already
            # have reached native fork. Never turn an unknown outcome into a
            # second effect, even when the caller supplies a fresh request key.
            raise InventoryError('uncertain_effect', 'retained revision requires destination reconciliation') from None
        else:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        guard()
        # Re-resolve the actual socket/process immediately before the effect.
        if self._daemon(arguments['owner'], arguments['channel'])['target'] != source['target']:
            raise InventoryError('stale_target', 'source store or daemon changed before snapshot import')
        if self._daemon(arguments['destination'], arguments['channel'])['target'] != destination['target']:
            raise InventoryError('stale_target', 'destination daemon changed before import')
        if not ongoing:
            reader.execute('history.read', selected)
        forked = self._request(destination, 'thread/fork', dict(threadId=thread_id, path=str(snapshot),
            ephemeral=False, approvalPolicy='never', sandbox='read-only'))
        child_id = forked.get('thread', {}).get('id')
        if not isinstance(child_id, str) or str(UUID(child_id)) != child_id or child_id == thread_id:
            raise InventoryError('uncertain_effect', 'native import returned an invalid destination identity')
        child = self._thread(self._request(destination, 'thread/read', dict(threadId=child_id, includeTurns=True)), child_id)
        child_path = Path(child.get('path', ''))
        if (not child_path.is_file() or not child_path.resolve().is_relative_to(Path(destination['target']['home']) / 'sessions')
                or child.get('forkedFromId') != thread_id or child['turns'] != original['turns']
                or self._request(destination, 'thread/goal/get', dict(threadId=child_id)) != {'goal': None}):
            raise InventoryError('uncertain_effect', 'destination native history or retained content could not be qualified')
        if not ongoing:
            reader.execute('history.read', selected)
        guard()
        return dict(thread_id=child_id, destination=destination['target']['account'],
            target=dict(destination['target'], conversation_id=child_id), rollout_path=str(child_path),
            provenance=dict(source_target=session['target'], source_owner=session['owner'],
                source_thread_id=thread_id, source_sha256=snapshot_revision, source_capture_sha256=session['target']['rollout_revision'],
                transfer='native_thread_fork_from_snapshot', source_unchanged=True,
                previous_snapshot_thread_id=previous, saved_boundary=dict(last_completed_turn_id=original['turns'][-1].get('id')),
                exclusions=exclusions),
            work_authorized=False, allowance_renewed=False)
