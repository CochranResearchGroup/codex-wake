#!/usr/bin/env python3
"""Build the pinned opt-in Codex client/server candidate; never install or restart."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-root', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parents[1] / 'runtime/codex'
    manifest = json.loads((bundle / 'manifest.json').read_text())
    patch = bundle / 'codex-wake.patch'
    if sha(patch) != manifest['patch_sha256']:
        parser.error('candidate patch does not match its manifest')
    work = args.work_root
    if not work.is_absolute() or work != work.resolve():
        parser.error('work root must be canonical and absolute')
    work.mkdir(parents=True, exist_ok=True)
    archive = args.archive or work / 'source.tar.gz'
    if not archive.exists():
        if not args.download or args.archive:
            parser.error('supply the pinned --archive or opt in to --download')
        temporary = archive.with_suffix('.download')
        try:
            with urllib.request.urlopen(manifest['archive_url'], timeout=60) as response, temporary.open('xb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if sha(temporary) != manifest['archive_sha256']:
                parser.error('download hash does not match pinned upstream source')
            temporary.rename(archive)
        finally:
            temporary.unlink(missing_ok=True)
    if sha(archive) != manifest['archive_sha256']:
        parser.error('source archive does not match pinned upstream revision')
    source = work / ('codex-' + manifest['upstream_revision'])
    inputs = dict(archive_sha256=manifest['archive_sha256'], patch_sha256=manifest['patch_sha256'],
                  upstream_revision=manifest['upstream_revision'], toolchain=manifest['toolchain'])
    marker = work / 'build-inputs.json'
    if source.exists():
        if not marker.is_file() or json.loads(marker.read_text()) != inputs:
            parser.error('existing source is not owned by this exact build; choose an unused work root')
    else:
        with tarfile.open(archive) as stream:
            # data filter rejects absolute paths, traversal and unsafe link targets.
            stream.extractall(work, filter='data')
        subprocess.run(['git', 'apply', '--check', str(patch)], cwd=source, check=True)
        subprocess.run(['git', 'apply', str(patch)], cwd=source, check=True)
        marker.write_text(json.dumps(inputs, indent=2) + '\n')
    lock = source / 'codex-rs/Cargo.lock'
    if sha(lock) == manifest['cargo_lock_archive_sha256']:
        normalized = '[[package]]'.join(
            block.replace('version = "0.0.0"', 'version = "' + manifest['upstream_version'] + '"', 1)
            if '\nsource = ' not in block else block for block in lock.read_text().split('[[package]]'))
        lock.write_text(normalized)
    if sha(lock) != manifest['cargo_lock_normalized_sha256']:
        parser.error('candidate dependency lock differs from pinned normalized upstream source')
    for filename, expected in manifest['patched_files_sha256'].items():
        if sha(source / filename) != expected:
            parser.error('candidate source differs from the pinned patch: ' + filename)
    if args.prepare_only:
        print(json.dumps(dict(prepared=True, source=str(source), **inputs), sort_keys=True))
        return
    subprocess.run(manifest['build_command'], cwd=source / 'codex-rs', check=True)
    executable = source / 'codex-rs/target/debug/codex'
    version = subprocess.run([str(executable), '--version'], capture_output=True, text=True, check=True).stdout.strip()
    receipt = dict(**inputs, executable=str(executable), executable_sha256=sha(executable),
                   version=version, installed=False, daemon_restarted=False)
    (work / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
