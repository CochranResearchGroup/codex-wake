"""Read selected tenant histories without changing conversation ownership."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import quote

from .config import Settings, load_settings
from .build_channels import load_build, run_build


class HistoryError(ValueError):
    pass


def selected_profiles(settings: Settings, profiles: list[str] | None = None) -> list[str]:
    names = profiles if profiles is not None else settings.known_profiles
    if not names:
        raise HistoryError('select at least one configured tenant for discovery')
    resolved = []
    for name in names:
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', name):
            raise HistoryError('tenant must be a profile name or alias')
        profile = settings.resolve_profile_name(name)
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', profile):
            raise HistoryError('resolved tenant name is invalid')
        if profile not in resolved:
            resolved.append(profile)
    return resolved


def discover(settings: Settings, profiles: list[str] | None = None) -> dict:
    sessions, holds = [], []
    for profile in selected_profiles(settings, profiles):
        home = settings.account_root(profile).absolute()
        db = home / 'state_5.sqlite'
        versions = [int(match.group(1)) for path in home.glob('state_*.sqlite')
                    if (match := re.fullmatch(r'state_(\d+)\.sqlite', path.name))]
        if any(version != 5 for version in versions):
            holds.append({'profile': profile, 'reason': 'unsupported native history schema version'})
            continue
        if not home.is_dir() or home.is_symlink() or not db.is_file():
            holds.append({'profile': profile, 'reason': 'saved native history is unavailable'})
            continue
        if not db.resolve().is_relative_to(home.resolve()):
            holds.append({'profile': profile, 'reason': 'shared mutable history cannot establish tenant ownership'})
            continue
        try:
            with sqlite3.connect('file:' + quote(str(db)) + '?mode=ro', uri=True, timeout=1) as connection:
                connection.execute('pragma query_only=ON')
                columns = {r[1] for r in connection.execute('pragma table_info(threads)')}
                if not {'id', 'cwd', 'title', 'rollout_path'} <= columns:
                    raise HistoryError('unsupported native history schema')
                rows = connection.execute('select id, cwd, title, rollout_path from threads order by id limit 10001').fetchall()
                if len(rows) > 10000:
                    raise HistoryError('tenant history exceeds bounded discovery limit')
                for thread_id, cwd, title, rollout_path in rows:
                    sessions.append({'profile': profile, 'namespace': str(home.resolve()),
                                     'thread_id': thread_id, 'cwd': cwd, 'title': title,
                                     'rollout_path': rollout_path})
        except (sqlite3.Error, HistoryError) as exc:
            holds.append({'profile': profile, 'reason': str(exc)})
    return {'status': 'partial' if holds else 'complete', 'sessions': sessions, 'holds': holds}


def select_session(settings: Settings, thread_id: str, owner: str | None = None) -> dict:
    if not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', thread_id):
        raise HistoryError('exact native conversation UUID required')
    result = discover(settings, [owner] if owner else None)
    if result['status'] != 'complete':
        raise HistoryError('incomplete discovery; select an available exact owner')
    matches = [row for row in result['sessions'] if row['thread_id'] == thread_id]
    if len(matches) != 1:
        raise HistoryError('conversation missing or ambiguous; select its exact owner')
    row = matches[0]
    rollout = Path(row['rollout_path'])
    if not rollout.is_file() or not rollout.resolve().is_relative_to(Path(row['namespace'])):
        raise HistoryError('saved conversation history is unavailable in its owning namespace')
    return row


def resume(settings: Settings, thread_id: str, manifest: Path, *, owner: str | None = None,
           channel: str = 'modded') -> int:
    row = select_session(settings, thread_id, owner)
    return run_build(load_build(manifest, channel, Path(row['namespace'])), Path(row['namespace']), row['profile'],
                     ['resume', '--no-alt-screen', '-C', row['cwd'], row['thread_id']])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(os.environ.get('CODEX_PROFILES_CONFIG', 'profiles.toml')))
    subparsers = parser.add_subparsers(dest='operation', required=True)
    listing = subparsers.add_parser('list')
    listing.add_argument('--profile', action='append')
    resuming = subparsers.add_parser('resume')
    resuming.add_argument('thread_id')
    resuming.add_argument('--owner')
    resuming.add_argument('--manifest', type=Path, required=True)
    resuming.add_argument('--channel', choices=('stock', 'modded'), default='modded')
    args = parser.parse_args(argv)
    try:
        if args.operation == 'resume':
            return resume(load_settings(args.config), args.thread_id, args.manifest,
                          owner=args.owner, channel=args.channel)
        result = discover(load_settings(args.config), args.profile)
        print(json.dumps(result, indent=2))
        return 0 if result['status'] == 'complete' else 2
    except (HistoryError, OSError, ValueError) as exc:
        print(json.dumps({'status': 'held', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
