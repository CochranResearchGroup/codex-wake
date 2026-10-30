"""Approved supervised-command bridge, reusing BackgroundJobs without a new executor."""
import hashlib
import json
from pathlib import Path

from .background_jobs import BackgroundJobs
from .session_permissions import Principal
from .managed_inventory import InventoryError
from .controller_mailbox import ControllerMailbox


class ControllerJobs:
    def __init__(self, root):
        self.root = Path(root)
        self.jobs = BackgroundJobs(self.root)

    def context(self, actor, payload):
        config = ControllerMailbox(self.root).config()
        mapping = config.get('job_bindings', {}).get(payload.get('sender_binding'))
        if not isinstance(mapping, dict) or mapping.get('subject') != actor.subject or mapping.get('client_id') != actor.client_id:
            raise InventoryError('unauthorized_target', 'caller has no approved command binding')
        if payload.get('job_profile') != mapping['profile'] or payload.get('expected_target') != mapping['target']:
            raise InventoryError('stale_target', 'exact approved job profile target required')
        principal = Principal(mapping['native_subject'], tasks=tuple(mapping['tasks']))
        profile = self.jobs.profile(mapping['profile'])
        if profile['sha256'] != mapping['target'].get('configuration_revision'):
            raise InventoryError('stale_target', 'approved command profile generation changed')
        return mapping, principal

    def prepare(self, actor, payload):
        if set(payload) - {'backend', 'job_profile', 'sender_binding', 'expected_target'}:
            raise InventoryError('invalid_argument', 'command profiles accept no caller argv/body/credential overrides')
        mapping, principal = self.context(actor, payload)
        digest = hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()
        return dict(payload, _binding_digest=digest)

    def send(self, actor, payload, operation_id, correlation_id):
        original = {k: v for k, v in payload.items() if k != '_binding_digest'}
        prepared = self.prepare(actor, original)
        if prepared != payload: raise InventoryError('stale_target', 'approved command binding changed before launch')
        mapping, principal = self.context(actor, payload)
        value = self.jobs.launch(mapping['profile'], principal=principal, idempotency_key='controller:' + operation_id)
        return dict(_pending=True, handle=dict(kind='background_job', job_id=value['job_id'], generation=value['generation']))

    def reconcile(self, actor, record):
        # Unknown supervisor admission is never relaunched. Native job inspection
        # needs its returned handle; absence is explicitly uncertain.
        return None

    def state(self, actor, record):
        mapping, principal = self.context(actor, record['payload'])
        state = self.jobs.inspect(record['result']['job_id'])
        self.jobs.authorize_inspection(state, principal)
        if state['generation'] != record['result']['generation']:
            raise InventoryError('stale_target', 'original supervised command generation changed')
        return state, principal

    def poll(self, actor, record):
        state, principal = self.state(actor, record)
        if state['status'] not in ('completed', 'cancelled', 'failed', 'timed_out'): return []
        with Path(state['stdout_path']).open('rb') as stream: stdout = stream.read(32768).decode('utf-8', errors='replace')
        return [dict(reply_id=state['job_id'] + ':terminal', kind='result', text=stdout,
            execution='completed' if state['status'] == 'completed' else 'cancelled' if state['status'] == 'cancelled' else 'failed',
            correlation_id=record['correlation_id'], sender={'owner': state['intent']['owner']},
            peer_content_trust='untrusted', command_status=state['status'], returncode=state.get('result', {}).get('returncode'),
            output_truncated=Path(state['stdout_path']).stat().st_size > 32768)]

    def cancel(self, actor, record):
        state, principal = self.state(actor, record)
        value = self.jobs.cancel(state['job_id'], principal=principal, expected_generation=state['generation'])
        return 'confirmed' if value['status'] == 'cancelled' else 'requested'


class ControllerEffects:
    def __init__(self, root):
        self.root = Path(root)
        self.mailbox = ControllerMailbox(self.root)

    def backend(self, payload):
        return ControllerJobs(self.root) if payload.get('backend') == 'job' else self.mailbox

    def prepare(self, actor, payload): return self.backend(payload).prepare(actor, payload)
    def send(self, actor, payload, operation_id, correlation_id): return self.backend(payload).send(actor, payload, operation_id, correlation_id)
    def reconcile(self, actor, record): return self.backend(record['payload']).reconcile(actor, record)
    def poll(self, actor, record): return self.backend(record['payload']).poll(actor, record)
    def cancel(self, actor, record): return self.backend(record['payload']).cancel(actor, record)

    def reconcile_owned(self, record):
        from types import SimpleNamespace
        return self.reconcile(SimpleNamespace(**record['principal']),record)

    def cancel_owned(self, record):
        from types import SimpleNamespace
        return self.cancel(SimpleNamespace(**record['principal']),record)
