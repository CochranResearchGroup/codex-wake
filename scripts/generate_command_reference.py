#!/usr/bin/env python3
"""Generate the first command-contract reference, or fail on stale content."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codex_wake.command_contract import render_reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail without writing if checked-in reference differs')
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / 'docs/agents/command-reference.md'
    expected = render_reference()
    if args.check:
        if not path.is_file() or path.read_text() != expected:
            print('Command reference is stale; run scripts/generate_command_reference.py', file=sys.stderr)
            return 1
        return 0
    path.write_text(expected)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
