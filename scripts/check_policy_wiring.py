"""Check canonical policy pointers and the pilot's pinned source inventory."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def check(root: Path) -> list[str]:
    errors = []
    agents = root / "AGENTS.md"
    if not agents.is_file():
        return ["AGENTS.md is missing"]
    pointers = re.findall(r"`(docs/dev/policies/[^`\n]+\.md)`", agents.read_text())
    policies = sorted(p.relative_to(root).as_posix()
                      for p in (root / "docs/dev/policies").rglob("*.md"))
    for path, count in Counter(pointers).items():
        if count != 1:
            errors.append(f"duplicate policy pointer: {path}")
        if path not in policies:
            errors.append(f"missing policy target: {path}")
    for path in sorted(set(policies) - set(pointers)):
        errors.append(f"unwired policy: {path}")
    identities = Counter(re.sub(r"^\d+-", "", Path(p).name) for p in policies)
    errors.extend(f"duplicate policy identity: {name}" for name, count
                  in identities.items() if count != 1)
    try:
        manifest = json.loads((root / ".governance/policy-context.json").read_text())
        inventory = manifest["governance_inventory"]
        expected = ["AGENTS.md", *policies]
        if sorted(item["path"] for item in inventory) != sorted(expected):
            errors.append("pilot inventory differs from canonical policy files")
        for item in inventory:
            path = item["path"]
            if path not in expected:
                continue
            actual = hashlib.sha256((root / path).read_bytes()).hexdigest()
            if actual != item["sha256"]:
                errors.append(f"stale pilot hash: {path}")
        inventory_hashes = {item["path"]: item["sha256"] for item in inventory}
        for profile in manifest["profiles"]:
            for source in profile["sources"]:
                if inventory_hashes.get(source["path"]) != source["sha256"]:
                    errors.append(f"profile source differs from inventory: {source['path']}")
            for path in profile["fallback_paths"]:
                if path not in expected:
                    errors.append(f"noncanonical fallback: {path}")
        for path in manifest["fallback_paths"]:
            if path not in expected:
                errors.append(f"noncanonical fallback: {path}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append(f"invalid pilot manifest: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path,
                        default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check(args.repo_root.resolve())
    print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
