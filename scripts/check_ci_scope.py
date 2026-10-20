#!/usr/bin/env python3
"""Select the full CI lane unless Git proves an ordinary evidence-only change.

Only added/modified regular Markdown and JSON under docs/dev/evidence qualify.
Policy, workflow, manifest, source, rename, deletion, unknown event or missing
comparison evidence always runs the full lane. Scheduled CI always runs full.
"""
import argparse
import json
from pathlib import PurePosixPath
import subprocess


def classify(base, head, event):
    result = dict(scope='full', reason='comparison_unavailable')
    if event not in ('pull_request', 'push'):
        return dict(scope='full', reason='event_requires_full')
    if not base or not head:
        return result
    try:
        # Resolve revisions to immutable objects before inspecting paths.
        base = subprocess.check_output(['git', 'rev-parse', '--verify', base + '^{commit}'], stderr=subprocess.DEVNULL).decode().strip()
        head = subprocess.check_output(['git', 'rev-parse', '--verify', head + '^{commit}'], stderr=subprocess.DEVNULL).decode().strip()
        data = subprocess.check_output(['git', 'diff', '--name-status', '-z', '--find-renames', base, head, '--'])
        fields = data.decode('utf-8').split('\0')
        if fields[-1] != '' or len(fields) == 1:
            return dict(scope='full', reason='no_changes')
        fields.pop()
        while fields:
            status = fields.pop(0)
            if status not in ('A', 'M') or not fields:
                return dict(scope='full', reason='change_status_requires_full')
            name = fields.pop(0)
            path = PurePosixPath(name)
            if (not name.startswith('docs/dev/evidence/') or path.suffix not in ('.md', '.json')
                    or any(ord(char) < 32 for char in name)):
                return dict(scope='full', reason='path_requires_full')
            entry = subprocess.check_output(['git', 'ls-tree', '-z', head, '--', name])
            if not entry.startswith(b'100644 blob '):
                return dict(scope='full', reason='file_mode_requires_full')
            content = subprocess.check_output(['git', 'show', head + ':' + name]).decode('utf-8')
            if '\0' in content:
                return dict(scope='full', reason='binary_evidence_requires_full')
            if path.suffix == '.json':
                json.loads(content)
        return dict(scope='docs', reason='ordinary_evidence_only')
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError):
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base')
    parser.add_argument('--head')
    parser.add_argument('--event', required=True)
    args = parser.parse_args()
    print(json.dumps(classify(args.base, args.head, args.event)))


if __name__ == '__main__':
    main()
