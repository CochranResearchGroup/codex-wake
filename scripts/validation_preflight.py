"""Read-only dependency/version preflight for the repository validation profile."""
import argparse
from importlib import metadata
import json
from pathlib import Path
import sys
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--tier', choices=['focused', 'presubmit', 'comprehensive'], required=True)
    args = parser.parse_args()
    versions = {'python': sys.version, 'executable': sys.executable, 'prefix': sys.prefix}
    errors = []
    if sys.version_info[:2] not in ((3, 11), (3, 12)):
        errors.append('selected runtime must be Python 3.11 or 3.12')
    config = tomllib.loads((args.repo / 'pyproject.toml').read_text())
    requirements = [*config['project']['optional-dependencies']['dev']]
    if args.tier != 'focused':
        requirements += [*config['project']['dependencies'], *config['project']['optional-dependencies']['mcp'],
                         *config['build-system']['requires'], 'build>=1,<2', 'wheel>=0.41']
    try:
        from packaging.requirements import Requirement
    except ImportError:
        errors.append('packaging dependency missing; cannot verify declared requirements')
        Requirement = None
    for text in requirements:
        name = text.split('=')[0].split('>')[0].split('<')[0]
        try:
            version = metadata.version(name)
            versions[name] = version
            if Requirement is not None and version not in Requirement(text).specifier:
                errors.append(f'{text}: installed {version} is incompatible')
        except metadata.PackageNotFoundError:
            errors.append(f'{text}: missing dependency')
    print(json.dumps(dict(operation='setup preflight', versions=versions, errors=errors)))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
