"""Private child entrypoint; invoked only with a pinned host-approved recipe."""
import sys
from pathlib import Path
from codex_profiles.upgrades import stage, _atomic

if __name__ == '__main__':
    _atomic(Path(sys.argv[3]), stage(Path(sys.argv[1]), Path(sys.argv[2])))
