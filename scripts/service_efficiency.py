#!/usr/bin/env python3
"""Read-only Wake service audit; use the installed package or PYTHONPATH=src."""
from codex_wake.service_audit import main


if __name__ == '__main__':
    raise SystemExit(main())
