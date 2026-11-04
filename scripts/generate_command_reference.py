#!/usr/bin/env python3
"""Generate the first command-contract reference, or fail on stale content."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codex_wake.command_contract import render_reference, coverage_report
from codex_wake.cli import build_parser
from codex_wake.local_control_service import contract as local_contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail without writing if checked-in reference differs')
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / 'docs/agents/command-reference.md'
    outputs = {path: render_reference(), path.with_name('command-coverage.json'): json.dumps(coverage_report(build_parser()), indent=2) + '\n'}
    local=local_contract()
    outputs[path.with_name('local-controller-contract.json')]=json.dumps(local,indent=2)+'\n'
    outputs[path]+='\n## Local session controller\n\nSee [workflow](local-session-control.md) and generated [transport contract](local-controller-contract.json).\n\n| CLI | API operation | Local MCP |\n|---|---|---|\n'
    for operation,value in local['operations'].items():
        outputs[path]+='| `'+ ' '.join(value['cli'])+'` | `'+operation+'` | `'+value['mcp_tool']+'` |\n'
    if args.check:
        stale = [str(target) for target, content in outputs.items() if not target.is_file() or target.read_text() != content]
        if stale:
            print('Command reference/coverage is stale; run scripts/generate_command_reference.py: ' + ', '.join(stale), file=sys.stderr)
            return 1
        return 0
    for target, content in outputs.items():
        target.write_text(content)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
