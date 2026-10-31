"""Run the existing package build command on an external candidate snapshot."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='package-source-', dir=args.outdir.parent) as temp:
        source = Path(temp)
        paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z']).split(b'\0')
        for raw in set(paths) - {b''}:
            path = Path(raw.decode('utf-8', errors='surrogateescape'))
            if path.is_file():
                destination = source / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination, follow_symlinks=True)
        return subprocess.run([sys.executable, '-m', 'build', '--no-isolation', '--outdir', str(args.outdir), str(source)]).returncode


if __name__ == '__main__':
    raise SystemExit(main())
