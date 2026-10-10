"""Opt-in fail-closed qualification of an installed governance-context CLI."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--governance-cli", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    profile = "codex-wake-policy-maintenance"
    cases = []
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="wake-policy-qualification-") as directory:
        root = Path(directory)
        shutil.copy(source / "AGENTS.md", root)
        shutil.copytree(source / "docs/dev/policies", root / "docs/dev/policies")
        shutil.copytree(source / ".governance", root / ".governance")

        def call(**changes):
            request = {"profile": profile, "task_kind": "policy-maintenance", **changes}
            run = subprocess.run([str(args.governance_cli), "--root", str(root),
                                  "policy", "-"], input=json.dumps(request),
                                 capture_output=True, text=True, timeout=15)
            if run.returncode:
                raise RuntimeError(run.stderr)
            return json.loads(run.stdout), len(run.stdout.encode())

        current, hydrated_bytes = call(include_source_text=True)
        assert current["status"] == "current" and not current["fallback_required"]
        assert all(section.get("text") for item in current["sources"]
                   for section in item["sections"])
        cases.append({"case": "current", "status": current["status"]})
        unchanged, reuse_bytes = call(
            known_decision_digest=current["decision_packet"]["decision_digest"])
        assert unchanged["unchanged"] and not unchanged["fallback_required"]
        cases.append({"case": "retained-packet-freshness", "unchanged": True})
        for case in ("changed_source", "missing_file", "added_file", "out_of_scope"):
            agents = root / "AGENTS.md"
            original = agents.read_bytes()
            added = root / "docs/dev/policies/9999-qualification.md"
            if case == "changed_source":
                agents.write_bytes(original + b"\nqualification drift\n")
            elif case == "missing_file":
                agents.unlink()
            elif case == "added_file":
                added.write_text("# Qualification policy\n")
            result, _ = call(**({"task_kind": "release"} if case == "out_of_scope" else {}))
            assert result["fallback_required"] and result["sources"] == []
            assert result["status"] != "current"
            if case == "added_file":
                assert "docs/dev/policies/9999-qualification.md" in result["fallback_paths"]
            cases.append({"case": case, "status": result["status"],
                          "reason": result.get("reason"), "fallback_required": True})
            agents.write_bytes(original)
            added.unlink(missing_ok=True)
    receipt = {"status": "PASS", "cases": cases, "profile": profile,
               "installed_cli": str(args.governance_cli.resolve()),
               "elapsed_seconds": time.monotonic() - started,
               "hydrated_response_bytes": hydrated_bytes, "reuse_response_bytes": reuse_bytes,
               "total_host_token_savings": "unmeasured; response bytes are not host tokens",
               "owned_fixture_removed": not root.exists(), "production_effects": 0}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
