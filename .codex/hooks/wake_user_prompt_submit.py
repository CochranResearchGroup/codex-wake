#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))
    from codex_wake.hook import main as hook_main

    return hook_main()


if __name__ == "__main__":
    raise SystemExit(main())
