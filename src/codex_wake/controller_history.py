"""Permitted native history and exact-owner resume over the existing owners."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tomllib
from uuid import UUID

from codex_profiles.config import load_settings
from codex_profiles.history import discover, select_session, HistoryError
from .controller_accounts import ControllerAccounts
from .managed_inventory import InventoryError
from .records import WakeError


class ControllerHistory:
    def __init__(self, config_path, *, root, host, environment, authorized_accounts,
                 resume_owner=None, authorization_guard=None):
        self.path = Path(config_path)
        self.root, self.host, self.environment = Path(root), host, environment
        self.authorized_accounts = tuple(authorized_accounts)
        self.resume_owner = resume_owner
        self.authorization_guard = authorization_guard

    def execute(self, operation, arguments):
        schemas = {'history.search': {'owners', 'query'},
                   'history.read': {'owner', 'thread_id', 'expected_target'},
                   'history.resume': {'owner', 'thread_id', 'expected_target', 'intent', 'expires_at'}}
        if operation not in schemas:
            raise InventoryError('unsupported_operation', 'unsupported history operation')
        if not isinstance(arguments, dict) or set(arguments) - schemas[operation]:
            raise InventoryError('invalid_argument', 'unsupported history arguments')
        if self.authorization_guard is not None:
            self.authorization_guard(operation, arguments)
        try:
            if not self.path.is_file():
                raise InventoryError('configuration_unavailable', 'host history policy is unavailable')
            data = tomllib.loads(self.path.read_text())
            settings = load_settings(self.path)
            if not data.get('profiles', {}).get('state_root'):
                raise InventoryError('configuration_unavailable', 'explicit account state root required')
            history = data.get('history', {})
            permitted = {settings.resolve_profile_name(name) for name in history.get('readable_accounts', [])}
            granted = {settings.resolve_profile_name(name) for name in self.authorized_accounts}
            allowed = permitted & granted
            if operation == 'history.search':
                selected = arguments.get('owners', sorted(allowed))
                if not isinstance(selected, list) or len(selected) > 256 or any(not isinstance(n, str) for n in selected):
                    raise InventoryError('invalid_argument', 'owners must be a bounded account list')
                owners = sorted({settings.resolve_profile_name(name) for name in selected})
            else:
                name, thread = arguments.get('owner'), arguments.get('thread_id')
                if not isinstance(name, str) or not isinstance(thread, str) or str(UUID(thread)) != thread:
                    raise InventoryError('invalid_argument', 'exact owner and native UUID required')
                owners = [settings.resolve_profile_name(name)]
            # Admission happens before discover/select_session opens a native DB.
            if not set(owners) <= allowed:
                raise InventoryError('unauthorized_target', 'history owner is outside the permitted account scope')
            if not owners:
                return dict(sessions=[], holds=[], status='complete')
            account_owner = ControllerAccounts(self.path, host=self.host, environment=self.environment)
            accounts = {name: account_owner.execute('accounts.resolve', {'selector': name})['account'] for name in owners}
            if operation == 'history.search':
                query = arguments.get('query', '')
                if not isinstance(query, str) or len(query) > 1024:
                    raise InventoryError('invalid_argument', 'history query must be bounded text')
                result = discover(settings, owners)
                sessions = []
                remaining = 8 * 1024 * 1024
                for row in result['sessions']:
                    if query and not any(query.casefold() in str(row.get(key, '')).casefold()
                                         for key in ('thread_id', 'cwd', 'title')):
                        continue
                    try:
                        session = self._session(row, accounts[row['profile']], max_bytes=remaining)
                        remaining -= session['provenance']['byte_length']
                        sessions.append(session)
                    except InventoryError as error:
                        result['holds'].append(dict(profile=row['profile'], reason=error.code))
                return dict(status='partial' if result['holds'] else 'complete', sessions=sessions, holds=result['holds'])
            row = select_session(settings, arguments['thread_id'], owners[0])
            session = self._session(row, accounts[owners[0]])
            expected = arguments.get('expected_target')
            if expected is not None and expected != session['target']:
                raise InventoryError('stale_target', 'saved owner/history binding changed')
            if operation == 'history.read':
                content = self._rollout(Path(row['rollout_path']), Path(row['namespace']))
                if hashlib.sha256(content).hexdigest() != session['target']['rollout_revision']:
                    raise InventoryError('stale_target', 'history changed while being read')
                return dict(session=session, records=[json.loads(line) for line in content.decode().splitlines() if line],
                            provenance=session['provenance'], work_authorized=False)
            if expected is None:
                raise InventoryError('invalid_argument', 'resume requires the previously pinned exact target')
            if history.get('resume_enabled') is not True or self.resume_owner is None:
                raise InventoryError('unsupported_target', 'qualified owner attachment executor is unavailable')
            def revalidate():
                if self.authorization_guard is not None:
                    self.authorization_guard(operation, arguments)
                reader = ControllerHistory(self.path, root=self.root, host=self.host, environment=self.environment,
                    authorized_accounts=self.authorized_accounts)
                current = reader.execute('history.read', {key: arguments[key] for key in ('owner', 'thread_id', 'expected_target')})
                if current['session']['target'] != session['target']:
                    raise InventoryError('stale_target', 'history binding changed before resume')
            return self.resume_owner.resume(session, arguments, history, revalidate)
        except InventoryError:
            raise
        except HistoryError:
            raise InventoryError('history_unavailable', 'native history is unavailable, unsupported or ambiguous') from None
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise InventoryError('history_unavailable', 'native history or host policy cannot be qualified') from None

    def _rollout(self, path, home, max_bytes=8 * 1024 * 1024):
        if path.suffix != '.jsonl':
            raise InventoryError('unsupported_target', 'compressed/native lineage reads require their native owner')
        if not path.is_file() or not path.resolve().is_relative_to(home.resolve()) or path.stat().st_size > max_bytes:
            raise InventoryError('history_unavailable', 'bounded history is unavailable in its owning namespace')
        return path.read_bytes()

    def _session(self, row, account, *, max_bytes=8 * 1024 * 1024):
        path = Path(row['rollout_path'])
        content = self._rollout(path, Path(row['namespace']), max_bytes)
        target = dict(account['target'], conversation_id=row['thread_id'],
                      rollout_revision=hashlib.sha256(content).hexdigest())
        return dict(owner=row['profile'], thread_id=row['thread_id'], cwd=row['cwd'], title=row['title'],
                    rollout_path=str(path), target=target,
                    provenance=dict(native_schema=5, namespace=row['namespace'],
                                    source='codex_profiles.history', rollout_sha256=target['rollout_revision'], byte_length=len(content)))


class ManagedHistoryResume:
    """Adapt saved history to the existing permission/durable attachment owner.

    The principal is trusted adapter context, never a history operation argument.
    Host bindings link existing enrolled records; reading history never enrolls.
    """
    def __init__(self, root, principal, *, runtime=None, now=None):
        self.root, self.principal, self.runtime, self.now = Path(root), principal, runtime, now

    def resume(self, session, arguments, policy, revalidate):
        from .agent_resume import AgentResume
        from .agent_resume_commands import load_profiles
        from .managed_inventory import ManagedInventory
        from .session_permissions import Principal
        try:
            if not isinstance(self.principal, Principal):
                raise InventoryError('unauthorized_target', 'authenticated resume principal is required')
            binding = policy.get('bindings', {}).get(session['thread_id'], {})
            if binding.get('account') != session['owner']:
                raise InventoryError('unsupported_target', 'qualified managed history binding is unavailable')
            profiles = Path(binding['profiles'])
            config = load_profiles(profiles)
            agent = ManagedInventory(self.root, now=self.now).inspect(binding['managed_agent_id'])['agent']
            profile = config['profiles'][binding['profile']]
            if (agent['conversation_id'] != session['thread_id'] or agent['runtime'] != 'codex'
                    or agent['root'] != session['cwd'] or profile.get('codex_home') != session['target']['home']
                    or profile.get('cwd') != session['cwd']):
                raise InventoryError('stale_target', 'managed owner/account/workspace binding changed')
            def current_config():
                revalidate()
                current = load_profiles(profiles)
                selected = current['profiles'][binding['profile']]
                from .shared_app_server import SharedAppServerReader
                with SharedAppServerReader(selected['app_server'], timeout=selected['timeout']) as reader:
                    thread = reader.read_thread(session['thread_id'])
                    if (reader.server_metadata.get('codexHome') != session['target']['home']
                            or thread.get('id') != session['thread_id'] or thread.get('cwd') != session['cwd']):
                        raise InventoryError('stale_target', 'native backend no longer belongs to the saved owner')
                return current
            config = current_config()
            owner = AgentResume(self.root, config, runtime=self.runtime, now=self.now,
                                config_loader=current_config)
            result = owner.resume(dict(managed_agent_id=binding['managed_agent_id'], profile=binding['profile'],
                intent=arguments.get('intent'), expires_at=arguments.get('expires_at')), self.principal)
            attachment = dict(state='unknown', attachments=[])
            if result.get('status') == 'resumed':
                observed = ManagedInventory(self.root, now=self.now).inspect(binding['managed_agent_id'])['agent']
                if observed['binding_current']:
                    attachment = dict(state='ready', attachments=observed['attachments'],
                        process=observed['process'], observed_at=observed['observed_at'])
            return dict(session=session, resume=result, attachment=attachment, work_authorized=False,
                        accounting='existing_owner_unchanged', conversation_ownership='preserved')
        except InventoryError:
            raise
        except WakeError as error:
            raise InventoryError(error.code, 'existing owner resume was held') from None
        except (OSError, KeyError, ValueError, TypeError):
            raise InventoryError('unsupported_target', 'qualified managed resume configuration is unavailable') from None
