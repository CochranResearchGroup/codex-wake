"""Private opaque OAuth authority for the single Wake protected resource.

Authorization is an explicit local operator act. Client registration never grants
an identity or capability. Provider credentials are outside this authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

SCOPES = frozenset({'observe', 'control', 'recovery', 'admin', 'account.observe', 'configuration.observe', 'history.observe', 'history.resume', 'migration.observe'})


class AuthError(ValueError):
    def __init__(self, code='invalid_token', message='authorization denied'):
        super().__init__(message)
        self.code = code


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Actor:
    subject: str
    principal_kind: str
    client_id: str
    grant_id: str
    issuer: str
    resource: str
    scopes: frozenset
    targets: list
    expires_at: float


class OAuthAuthority:
    def __init__(self, path, *, issuer, resource, now=time.time, on_revoke=None):
        self.on_revoke = on_revoke
        if urlsplit(issuer).path:
            raise ValueError('issuer must be a canonical origin without path or trailing slash')
        for value in (issuer, resource):
            if not isinstance(value, str) or any(ord(c) <= 32 or ord(c) == 127 for c in value):
                raise ValueError('canonical issuer/resource required')
            url = urlsplit(value)
            if (url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('127.0.0.1', '::1', 'localhost'))) or url.query or url.fragment or url.username or url.password or not url.netloc:
                raise ValueError('canonical HTTPS issuer/resource required (loopback HTTP fixtures allowed)')
        self.path, self.issuer, self.resource, self.now = Path(path), issuer, resource, now
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS authority (id INTEGER PRIMARY KEY CHECK(id=1), issuer TEXT, resource TEXT);
                CREATE TABLE IF NOT EXISTS clients (id TEXT PRIMARY KEY, metadata TEXT);
                CREATE TABLE IF NOT EXISTS grants (id TEXT PRIMARY KEY, subject TEXT, kind TEXT, client TEXT, scopes TEXT, targets TEXT, revoked INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS codes (hash TEXT PRIMARY KEY, grant_id TEXT, redirect TEXT, challenge TEXT, expires REAL, used INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS tokens (hash TEXT PRIMARY KEY, grant_id TEXT, kind TEXT, expires REAL, used INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS revocations (grant_id TEXT PRIMARY KEY, pending INTEGER, result TEXT, attempts INTEGER NOT NULL DEFAULT 0);
            ''')
            if 'attempts' not in {row[1] for row in db.execute('PRAGMA table_info(revocations)')}:
                db.execute('ALTER TABLE revocations ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0')
            previous = db.execute('SELECT issuer,resource FROM authority WHERE id=1').fetchone()
            if previous and previous != (issuer, resource):
                raise ValueError('authority issuer/resource changed; explicit new authority required')
            db.execute('INSERT OR IGNORE INTO authority VALUES(1,?,?)', (issuer, resource))
        self.recover_revocations()

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def metadata(self):
        return dict(issuer=self.issuer, authorization_endpoint=self.issuer + '/authorize',
            token_endpoint=self.issuer + '/token', registration_endpoint=self.issuer + '/register',
            revocation_endpoint=self.issuer + '/revoke', response_types_supported=['code'],
            grant_types_supported=['authorization_code', 'refresh_token'],
            code_challenge_methods_supported=['S256'], token_endpoint_auth_methods_supported=['none'],
            scopes_supported=sorted(SCOPES))

    def protected_metadata(self):
        return dict(resource=self.resource, authorization_servers=[self.issuer],
                    scopes_supported=sorted(SCOPES), bearer_methods_supported=['header'])

    def register(self, metadata):
        redirects = metadata.get('redirect_uris')
        if not isinstance(redirects, list) or not 1 <= len(redirects) <= 10:
            raise AuthError('invalid_client_metadata')
        for uri in redirects:
            if not isinstance(uri, str) or any(ord(c) <= 32 or ord(c) == 127 for c in uri): raise AuthError('invalid_client_metadata')
            url = urlsplit(uri)
            if not url.netloc or url.fragment or url.username or url.password or (url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('127.0.0.1', '::1', 'localhost'))):
                raise AuthError('invalid_client_metadata')
        if metadata.get('token_endpoint_auth_method', 'none') != 'none':
            raise AuthError('invalid_client_metadata')
        value = dict(client_id=secrets.token_urlsafe(24), redirect_uris=redirects,
            client_name=str(metadata.get('client_name', ''))[:128], token_endpoint_auth_method='none',
            grant_types=['authorization_code', 'refresh_token'], response_types=['code'])
        with self.connect() as db:
            db.execute('INSERT INTO clients VALUES(?,?)', (value['client_id'], json.dumps(value)))
        return value

    def authorize(self, *, subject, principal_kind, client_id, redirect_uri, resource,
                  scopes, targets, code_challenge):
        if resource != self.resource: raise AuthError('invalid_target')
        if not isinstance(subject, str) or not subject or principal_kind not in ('owner', 'service'):
            raise AuthError('invalid_request')
        if not scopes or not set(scopes) <= SCOPES: raise AuthError('invalid_scope')
        if not isinstance(targets, list) or not targets or any(not isinstance(t, dict) or not t or set(t) - {'host', 'environment', 'runtime', 'namespace', 'conversation_id', 'provider', 'account', 'home', 'home_generation', 'configuration_revision', 'rollout_revision', 'build_channel', 'build_sha256', 'build_revision', 'executable', 'recipe', 'recipe_sha256', 'authority', 'generation', 'workspace', 'presentation', 'fixture_id', 'migration_revision'} or any(not isinstance(v, str) or not v for v in t.values()) for t in targets):
            raise AuthError('invalid_target')
        if not isinstance(code_challenge, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', code_challenge):
            raise AuthError('invalid_request', 'S256 challenge required')
        code, grant = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        with self.connect() as db:
            row = db.execute('SELECT metadata FROM clients WHERE id=?', (client_id,)).fetchone()
            if not row or redirect_uri not in json.loads(row[0])['redirect_uris']: raise AuthError('invalid_client')
            db.execute('INSERT INTO grants(id,subject,kind,client,scopes,targets) VALUES(?,?,?,?,?,?)',
                       (grant, subject, principal_kind, client_id, json.dumps(sorted(scopes)), json.dumps(targets)))
            db.execute('INSERT INTO codes(hash,grant_id,redirect,challenge,expires) VALUES(?,?,?,?,?)',
                       (digest(code), grant, redirect_uri, code_challenge, self.now() + 120))
        return code

    def token(self, args):
        if args.get('resource') != self.resource: raise AuthError('invalid_target')
        grant_type = args.get('grant_type')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if grant_type == 'authorization_code':
                row = db.execute('SELECT grant_id,redirect,challenge,expires,used FROM codes WHERE hash=?', (digest(args.get('code', '')),)).fetchone()
                verifier = args.get('code_verifier', '')
                challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
                if not row or row[4] or row[3] <= self.now() or row[1] != args.get('redirect_uri') or not re.fullmatch(r'[A-Za-z0-9._~-]{43,128}', verifier) or not secrets.compare_digest(row[2], challenge):
                    raise AuthError('invalid_grant')
                grant = row[0]
            elif grant_type == 'refresh_token':
                row = db.execute('SELECT grant_id,expires,used FROM tokens WHERE hash=? AND kind="refresh"', (digest(args.get('refresh_token', '')),)).fetchone()
                if not row or row[1] <= self.now(): raise AuthError('invalid_grant')
                grant = row[0]
                if row[2]:
                    db.execute('UPDATE grants SET revoked=1 WHERE id=?', (grant,))
                    db.commit()
                    self.revoke_grant(grant)
                    raise AuthError('invalid_grant', 'refresh replay revoked grant')
            else: raise AuthError('unsupported_grant_type')
            current = db.execute('SELECT client,scopes,revoked FROM grants WHERE id=?', (grant,)).fetchone()
            if not current or current[2] or current[0] != args.get('client_id'): raise AuthError('invalid_grant')
            if grant_type == 'authorization_code':
                db.execute('UPDATE codes SET used=1 WHERE hash=?', (digest(args['code']),))
            # Rotation invalidates old access and refresh credentials, not operation identity.
            db.execute('UPDATE tokens SET used=1 WHERE grant_id=?', (grant,))
            access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            for secret, kind, lifetime in ((access, 'access', 600), (refresh, 'refresh', 86400)):
                db.execute('INSERT INTO tokens VALUES(?,?,?,?,0)', (digest(secret), grant, kind, self.now() + lifetime))
            return dict(access_token=access, refresh_token=refresh, token_type='Bearer', expires_in=600,
                        scope=' '.join(json.loads(current[1])))

    def authenticate(self, token):
        with self.connect() as db:
            row = db.execute('''SELECT g.subject,g.kind,g.client,g.id,g.scopes,g.targets,t.expires
                FROM tokens t JOIN grants g ON g.id=t.grant_id
                WHERE t.hash=? AND t.kind='access' AND t.used=0 AND g.revoked=0''', (digest(token),)).fetchone()
        if not row or row[6] <= self.now(): raise AuthError()
        return Actor(*row[:4], self.issuer, self.resource, frozenset(json.loads(row[4])), json.loads(row[5]), row[6])

    def recover_revocations(self, *, limit=4, grant_id=None):
        if self.on_revoke is None:
            return
        with self.connect() as db:
            rows = db.execute('SELECT grant_id,attempts FROM revocations WHERE pending=1 '
                + ('AND grant_id=? ' if grant_id is not None else '') + 'ORDER BY rowid LIMIT ?',
                (grant_id, limit) if grant_id is not None else (limit,)).fetchall()
        for identifier, attempts in rows:
            with self.connect() as db:
                db.execute('UPDATE revocations SET attempts=attempts+1 WHERE grant_id=?', (identifier,))
            try:
                if attempts >= 3:
                    raise ValueError('cancellation attempt ceiling reached')
                result = self.on_revoke(identifier, issuer=self.issuer, resource=self.resource)
                if not isinstance(result, dict):
                    raise ValueError('revocation owner returned no outcome')
                pending = bool(result.get('remaining', result.get('remaining_count', 0)))
            except Exception:
                result = dict(cancellation='uncertain', uncertain_effects=['cancellation_owner_unavailable'])
                pending = attempts + 1 < 3
                if not pending:
                    result['reason'] = 'cancellation_attempt_limit_reached'
            with self.connect() as db:
                db.execute('UPDATE revocations SET pending=?,result=?,attempts=? WHERE grant_id=?',
                    (int(pending), json.dumps(result), 0 if result.get('cancellation') != 'uncertain' else attempts + 1, identifier))

    def revoke_grant(self, grant_id):
        with self.connect() as db:
            db.execute('UPDATE grants SET revoked=1 WHERE id=?', (grant_id,))
            db.execute('INSERT OR IGNORE INTO revocations(grant_id,pending,result) VALUES(?,1,NULL)', (grant_id,))
        # Cancellation is requested after revocation commits. An interrupted request
        # stays pending for bounded server maintenance/reconstruction.
        self.recover_revocations(grant_id=grant_id)
        with self.connect() as db:
            row = db.execute('SELECT result FROM revocations WHERE grant_id=?', (grant_id,)).fetchone()
        result = json.loads(row[0]) if row and row[0] else dict(cancellation='not_configured', uncertain_effects=[])
        return dict(result, grant_id=grant_id, status='revoked')

    def revoke_token(self, token, client_id):
        with self.connect() as db:
            row = db.execute('SELECT t.grant_id FROM tokens t JOIN grants g ON g.id=t.grant_id WHERE t.hash=? AND g.client=?', (digest(token), client_id)).fetchone()
        if row: self.revoke_grant(row[0])
