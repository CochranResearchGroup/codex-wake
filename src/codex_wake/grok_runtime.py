"""Qualified Grok1.0.40 minimal-UI delivery, with pinned managed-launch identity."""
from __future__ import annotations

import hashlib
import re
import time
from types import MappingProxyType

from .records import WakeError
from .runtime_delivery import (
    RuntimeCapability, RuntimeObservation, RuntimeRecipient, RuntimeSubmission,
    RuntimeReconciliation, RuntimeTargetError,
)

GENERATION_KEYS = ('pid', 'start_ticks', 'boot_id', 'session_id', 'executable_sha256')


class GrokRuntimeAdapter:
    def __init__(self, host, *, deadline=None):
        self.host = host
        self.deadline = deadline

    def resolve(self, target):
        if (target.get('transport') != 'runtime' or target.get('version') != 1
                or target.get('runtime') != 'grok' or target.get('method') != 'terminal_observation'):
            raise RuntimeTargetError('unsupported', 'unsupported_grok_target')
        binding = self.host.load_binding(target['binding_id'], target['binding_sha256'])
        if binding['session_id'] != target['session_id']:
            raise RuntimeTargetError('unavailable', 'binding_session_changed')
        return RuntimeRecipient('grok', binding['session_id'], MappingProxyType(binding))

    def _snapshot(self, recipient):
        observed = self.host.snapshot(recipient.binding)
        if any(observed.get(key) != recipient.binding.get(key) for key in GENERATION_KEYS):
            raise WakeError('grok_process_generation_changed')
        lines = [line.rstrip() for line in observed['frame'].splitlines() if line.strip()]
        versions = [line.strip() for line in lines if line.strip().startswith('Shell version:')]
        sessions = [line.strip() for line in lines if line.strip().startswith('Session ID:')]
        if (not versions or versions[-1] != 'Shell version: 1.0.40 [stable]'
                or not sessions or sessions[-1] != 'Session ID: ' + recipient.session_id):
            raise WakeError('grok_session_or_version_unavailable')
        return observed, lines

    def observe(self, recipient):
        capabilities = {
            'submit': RuntimeCapability('supported', 'grok_1_0_40_minimal_terminal_observation'),
            'reconcile': RuntimeCapability('supported', 'same_generation_submission_marker'),
            'busy_queue': RuntimeCapability('unsupported', 'dequeue_deadline_unavailable'),
            'interrupt': RuntimeCapability('unsupported', 'not_qualified'),
            'receiver_acknowledgment': RuntimeCapability('not_qualified', 'terminal_is_not_receiver_ack'),
        }
        try:
            _, lines = self._snapshot(recipient)
            last_identity=max(i for i,line in enumerate(lines) if line.strip().startswith('Session ID:'))
            if any(line.strip()=='No active session' or re.search(r'[⠀-⣿] Starting session',line)
                   for line in lines[last_identity+1:]):
                return RuntimeObservation('unavailable','session_initializing_or_missing',capabilities)
            footer = r'Grok 4\.7 \(high\) · .+ · ctrl\+o transcript'
            if (len(lines) >= 3 and lines[-3] == 'minimal · /help'
                    and lines[-2] == '❯' and re.fullmatch(footer, lines[-1])):
                return RuntimeObservation('ready', 'qualified_empty_composer', capabilities)
            return RuntimeObservation('unavailable', 'busy_draft_or_unknown_composer', capabilities)
        except Exception:
            return RuntimeObservation('unavailable', 'binding_or_ui_unavailable', capabilities)

    def submit(self, recipient, prompt):
        if self.deadline is not None and self.deadline-time.monotonic() <= 12:
            return RuntimeSubmission('not_sent', reason='original_deadline_reached')
        if self.observe(recipient).state != 'ready':
            return RuntimeSubmission('not_sent', reason='recipient_not_ready')
        try:
            self.host.refresh_identity(recipient.binding)
            if self.observe(recipient).state != 'ready':
                return RuntimeSubmission('not_sent', reason='fresh_identity_or_composer_changed')
        except Exception:
            return RuntimeSubmission('not_sent', reason='fresh_session_identity_unavailable')
        try:
            if self.deadline is not None and self.deadline-time.monotonic() <= 12:
                return RuntimeSubmission('not_sent', reason='original_deadline_reached')
            self.host.paste(recipient.binding, prompt, deadline=self.deadline)
            observed = self.reconcile(recipient, prompt)
            if observed.evidence:
                return RuntimeSubmission('accepted', evidence_kind='terminal_observation', evidence=observed.evidence)
        except Exception:
            pass
        return RuntimeSubmission('uncertain', reason='terminal_acceptance_unconfirmed')

    def reconcile(self, recipient, prompt):
        try:
            observed, lines = self._snapshot(recipient)
            marker = prompt.splitlines()[0]
            if (not re.fullmatch(r'WAKE_RUNTIME_SUBMISSION_ID=[0-9a-f-]{36}', marker)
                    or marker not in lines):
                return RuntimeReconciliation(reason='no_exact_terminal_acceptance')
            return RuntimeReconciliation(dict(
                source='terminal_observation', execution='not_observed',
                frame_sha256=hashlib.sha256(observed['frame'].encode()).hexdigest(),
                marker_sha256=hashlib.sha256(marker.encode()).hexdigest(),
            ))
        except Exception:
            return RuntimeReconciliation(reason='terminal_evidence_unavailable')
