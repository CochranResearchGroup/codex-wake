"""Host-only scheduling glue for explicitly enabled recovery policies.

No credentials are stored or issued here. Existing OAuth or local authority is
revalidated against the policy's original snapshot for every scheduled step.
"""
import json
import os
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from .controller_auth import Actor, AuthError
from .controller_runtime import identity


def resolve_original(authority, root, principal, authorization):
    try:
        return authority.revalidate_original(principal,authorization)
    except AuthError:
        from .operation_commands import local_actor
        try:
            current=local_actor(root)
        except (ValueError,OSError,KeyError):
            raise AuthError() from None
        if identity(current)!=principal or current.principal_kind!=authorization['principal_kind'] or current.scopes!=frozenset(authorization['scopes']) or current.targets!=authorization['targets'] or current.expires_at<authorization['expires_at'] or authorization['expires_at']<=time.time():
            raise AuthError() from None
        return Actor(current.subject,current.principal_kind,current.client_id,current.grant_id,
            current.issuer,current.resource,current.scopes,current.targets,authorization['expires_at'])


def status(root, state, reason=None):
    directory=Path(root)/'controller-recovery'
    temporary=directory/('.scheduler-'+uuid4().hex)
    try:
        fd=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'w') as stream:
            json.dump(dict(schema_version=1,status=state,reason=reason,updated_at=time.time()),stream)
        os.replace(temporary,directory/'scheduler-status.json')
    finally:
        temporary.unlink(missing_ok=True)


def maintain(authority, root):
    from .controller_recovery import ControllerRecovery
    try:
        status(root,'running')
        result=ControllerRecovery(root).drive_due(lambda principal,snapshot:
            resolve_original(authority,root,principal,snapshot),limit=8)
        status(root,'held' if any(item['status']=='held' for item in result) else 'idle')
    except (ValueError,OSError,KeyError,AttributeError,sqlite3.Error):
        status(root,'held','scheduler_owner_unavailable')
