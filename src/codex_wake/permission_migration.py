"""Explicit, operator-reviewed adoption; legacy operation intent is never rewritten."""
import hashlib
import json
from pathlib import Path

from .records import WakeError, all_records
from .session_permissions import PermissionDenied, _validate

LIFECYCLE_ACTIONS={'refresh.self','refresh.connection','refresh.shared','handoff.self','resume.self'}


def profile_ceiling(config, profile, subject):
    """Preserve an explicit old caller entry, not the absence of a UUID grant."""
    if 'session_permissions' in config:
        raise PermissionDenied('permission_legacy_self_access_requires_mapping')
    callers=config.get('callers',{})
    if not isinstance(callers,dict):raise PermissionDenied('permission_legacy_profile_invalid')
    if subject in callers:
        grants=callers[subject]
        if (not isinstance(grants,list) or any(not isinstance(x,str) for x in grants)
                or profile not in grants):
            raise PermissionDenied('permission_legacy_profile_denied')


def plan(root, policy, *, legacy_profiles=None):
    from .wake_policy import _read
    _validate(policy)
    candidate=json.loads(json.dumps(policy));issues=[];mapping={};digest=None
    if legacy_profiles is not None:
        path=Path(legacy_profiles).absolute()
        if path!=path.resolve():raise PermissionDenied('permission_profile_not_canonical')
        legacy=_read(path)
        callers=legacy.get('callers',{});profiles=legacy.get('profiles',{})
        if 'session_permissions' in legacy:issues.append('legacy_self_access_setting_requires_explicit_mapping')
        if (type(legacy.get('version')) is not int or legacy['version']!=1
                or not isinstance(callers,dict) or not isinstance(profiles,dict)):
            raise PermissionDenied('permission_legacy_profile_invalid')
        for subject,grants in callers.items():
            if (not isinstance(subject,str) or not subject or not isinstance(grants,list)
                    or any(not isinstance(x,str) or x not in profiles for x in grants)):
                issues.append('unmapped_legacy_profile_entry');continue
            mapping[subject]=list(grants)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        candidate['adoption']=dict(version=1,source_sha256=digest,legacy_profile_grants=mapping)
    pending=[]
    for item in all_records(Path(root)):
        record=item.record
        if record.get('status') in ('pending','pending_time','firing') and record.get('wake_policy',{}).get('version')!=2:
            pending.append(dict(id=record['id'],kind='wake',state=record['status'],resolution='hold_or_finish_before_adoption'))
    for directory in ('lifecycle','shared-refresh'):
        for path in (Path(root)/directory).glob('*.json'):
            value=_read(path)
            if ('state' in value and value['state'] not in ('completed','cancelled','expired','blocked','failed')
                    and not value.get('permission_context')):
                pending.append(dict(id=path.stem,kind=directory,state=value['state'],resolution='reconcile_or_hold_before_adoption'))
    _validate(candidate)
    return dict(state='needs_resolution' if issues or pending else 'ready',can_adopt=not issues and not pending,
        issues=issues,pending=pending,policy=candidate,source_sha256=digest,
        note='No operation intent, route, deadline, grant file or stop record was modified.')


def adopt(store, policy, principal, *, expected_revision, legacy_profiles=None, hold_legacy_pending=False):
    if principal.role!='operator':raise PermissionDenied('permission_operator_required')
    proposal=plan(store.execution_root,policy,legacy_profiles=legacy_profiles)
    if proposal['issues'] or (proposal['pending'] and not hold_legacy_pending):
        raise PermissionDenied('permission_adoption_needs_resolution',proposal)
    result=store.configure(proposal['policy'],principal,expected_revision=expected_revision)
    return dict(result,legacy_pending_held=len(proposal['pending']),source_sha256=proposal['source_sha256'])


def legacy_wake_held(root, record):
    from .session_permissions import PermissionStore
    if not PermissionStore(root).active():return False
    if record.get('wake_policy',{}).get('version')==2:return False
    # Definite old effects still reconcile read-only; missing actor provenance
    # cannot be converted into permission for a new submission.
    delivery=record.get('native_delivery') or record.get('runtime_delivery') or {}
    return delivery.get('state')!='uncertain'
