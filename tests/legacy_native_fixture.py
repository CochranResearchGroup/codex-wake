"""Write historical native records for reader/migration compatibility tests.

The current public CLI writes policy-bearing schema8. These tests deliberately
exercise the retained legacy writer seam to obtain authentic version5/6 records;
they do not assert that new registrations still use the historical default.
"""
from codex_wake.cli import build_parser, resolve_root, run
from codex_wake.native_delivery import create_native
from unittest.mock import patch


def run_legacy_native(argv):
    args = build_parser().parse_args(argv)
    if args.command != 'native' or args.native_command not in ('after', 'at', 'file'):
        return run(argv)
    args.wake_policy_enabled = False
    with patch.dict('os.environ', {'CODEX_WAKE_STABLE_TIME_CONFIG': ''}):
        return create_native(args, resolve_root(args))
