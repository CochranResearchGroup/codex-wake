"""Explicit custody-bound worktree cleanup; unknown observations retain work.

Reference reports are operator-reviewed inputs, not automatic absence proofs.
Plan/apply does not grant cleanup authority or eliminate the process-start race.
"""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


SCHEMA = "codex-wake.cleanup.v1"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, stderr=subprocess.PIPE
    ).strip()


def registrations(repo):
    rows = []
    for block in git(repo, "worktree", "list", "--porcelain").split("\n\n"):
        fields = dict(
            line.split(" ", 1) if " " in line else (line, "")
            for line in block.splitlines()
        )
        if "worktree" in fields:
            rows.append(fields)
    return rows


def census(target):
    """Never silently discard inaccessible process observations."""
    references, unknown = [], []
    try:
        with os.scandir("/proc") as processes:
            pids = [p.name for p in processes if p.name.isdigit()]
    except OSError:
        return {"complete": False, "references": [], "unknown": ["proc_unavailable"]}
    for pid in pids:
        base = Path("/proc") / pid
        for surface in ("cwd", "exe", "fd"):
            try:
                paths = (
                    list((base / surface).iterdir())
                    if surface == "fd"
                    else [base / surface]
                )
                for path in paths:
                    value = os.readlink(path)
                    if value == str(target) or value.startswith(str(target) + "/"):
                        references.append({"pid": int(pid), "surface": surface})
            except FileNotFoundError:
                # An exited process cannot retain a reference. A still-live process
                # with a missing surface remains unknown (e.g. kernel threads).
                if base.exists():
                    unknown.append({"pid": int(pid), "surface": surface})
            except OSError:
                unknown.append({"pid": int(pid), "surface": surface})
    return {"complete": not unknown, "references": references, "unknown": unknown}


def reference_review(path, repo, target):
    if path.is_symlink():
        raise ValueError("reference report must be an owned regular file")
    stat = path.stat()
    if not path.is_file() or stat.st_uid != os.getuid() or stat.st_mode & 0o022:
        raise ValueError("reference report must be owned and not group/world writable")
    raw = path.read_bytes()
    report = json.loads(raw)
    if report.get("repository") != str(repo):
        raise ValueError("reference report repository mismatch")
    entries = [x for x in report["entries"] if x.get("path") == str(target)]
    if len(entries) != 1:
        raise ValueError("one exact reference review is required per target")
    row = entries[0]
    keys = ("service_references", "build_references", "evidence_references")
    complete = (
        row.get("reviewed") is True
        and isinstance(row.get("owner"), str)
        and bool(row["owner"])
    )
    complete = complete and all(
        isinstance(row.get(k), list) and all(isinstance(v, str) for v in row[k])
        for k in keys
    )
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "complete": complete,
        "owner": row.get("owner", "unknown"),
        "referenced": any(row.get(k) for k in keys),
    }


def observe(repo, target, custody, references):
    if not isinstance(custody, str) or not custody.startswith("refs/custody/"):
        raise ValueError("an explicit refs/custody/ recovery ref is required")
    if target.is_symlink():
        raise ValueError("symlink targets cannot be retired")
    rows = [r for r in registrations(repo) if r["worktree"] == str(target)]
    if len(rows) != 1:
        raise ValueError("target must identify exactly one registered worktree")
    row = rows[0]
    primary = Path(git(repo, "rev-parse", "--git-common-dir"))
    if not primary.is_absolute():
        primary = repo / primary
    primary = primary.resolve().parent
    if target == primary or target == repo:
        raise ValueError("primary and invoking checkouts cannot be retired")
    head = row.get("HEAD", "")
    custody_head = git(repo, "rev-parse", "--verify", custody)
    review = reference_review(references, repo, target)
    exists = os.path.lexists(target)
    state = (
        git(target, "status", "--porcelain=v1", "--untracked-files=all", "--ignored")
        if exists
        else ""
    )
    processes = (
        census(target)
        if exists
        else {"complete": True, "references": [], "unknown": []}
    )
    reasons = []
    if head != custody_head:
        reasons.append("custody_mismatch")
    if "locked" in row:
        reasons.append("locked")
    if state:
        reasons.append("dirty_or_ignored")
    if not review["complete"]:
        reasons.append("reference_review_incomplete")
    if review["referenced"]:
        reasons.append("reference_review_in_use")
    if processes["references"]:
        reasons.append("process_reference")
    if not processes["complete"]:
        reasons.append("process_visibility_incomplete")
    unknown = not processes["complete"] or not review["complete"]
    return {
        "id": digest(str(target))[:16],
        "path": str(target),
        "head": head,
        "custody": custody,
        "custody_head": custody_head,
        "exists": exists,
        "state": state,
        "locked": "locked" in row,
        "reference_review": review,
        "processes": processes,
        "owner": review["owner"],
        "reasons": reasons,
        "next_action": "Fresh complete owner/reference census before retirement"
        if reasons
        else "Apply exact approved plan",
        "action": "retain" if reasons else ("remove" if exists else "prune"),
        "disposition": ("retained_unknown" if unknown else "retained")
        if reasons
        else "eligible",
    }


def private_new(path):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w")


def write_new(path, payload):
    with private_new(path) as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")


def external_output(output, repo, target):
    output = output.resolve()
    if output.is_relative_to(repo) or output.is_relative_to(target):
        raise ValueError("receipts must be outside source and cleanup target")
    return output


def apply_plan(args):
    payload = json.loads(args.plan.read_text())
    plan_id = payload.pop("plan_id")
    if payload.get("schema") != SCHEMA or payload.get("kind") != "plan":
        raise ValueError("unsupported cleanup plan")
    if digest(payload) != plan_id or args.approve_plan != plan_id:
        raise ValueError("exact unmodified plan approval is required")
    if len(payload["entries"]) != 1:
        raise ValueError("one exact target per apply is required")
    entry = payload["entries"][0]
    repo, target = Path(payload["repository"]), Path(entry["path"])
    output = external_output(args.output, repo, target)
    if entry["disposition"] != "eligible" or entry["action"] not in ("remove", "prune"):
        raise ValueError("plan retains target; obtain complete fresh evidence")
    common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    with (common / "cleanup-worktrees.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = observe(repo, target, entry["custody"], Path(payload["references"]))
        if fresh != entry:
            raise ValueError(
                "target or observation drift; create and approve a fresh plan"
            )
        result = dict(payload, kind="result", status="FAIL", plan_id=plan_id)
        result["entries"] = [
            dict(entry, disposition="unknown", reasons=["operation_pending_readback"])
        ]
        # Reserve a new durable receipt before any effect; never erase a prior run.
        with private_new(output) as stream:

            def save():
                stream.seek(0)
                json.dump(result, stream, indent=2)
                stream.write("\n")
                stream.truncate()
                stream.flush()
                os.fsync(stream.fileno())

            save()
            try:
                completed = subprocess.run(
                    ["git", "-C", str(repo), "worktree", "remove", str(target)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                remaining = any(
                    r["worktree"] == str(target) for r in registrations(repo)
                )
                custody_ok = (
                    git(repo, "rev-parse", "--verify", entry["custody"])
                    == entry["head"]
                )
                if (
                    completed.returncode == 0
                    and not remaining
                    and not os.path.lexists(target)
                    and custody_ok
                ):
                    result["entries"][0].update(
                        disposition="removed" if entry["exists"] else "pruned",
                        reasons=[],
                        next_action="Retain verified custody ref",
                    )
                    result["status"] = "PASS"
                else:
                    result["entries"][0]["reasons"] = [
                        "effect_unverified_reconcile_before_retry"
                    ]
            except (OSError, subprocess.SubprocessError):
                result["entries"][0]["reasons"] = [
                    "outcome_unknown_reconcile_before_retry"
                ]
            save()
        print(json.dumps({"status": result["status"], "plan_id": plan_id}))
        return 0 if result["status"] == "PASS" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--repo", type=Path, required=True)
    plan.add_argument("--target", type=Path, required=True)
    plan.add_argument("--custody", required=True)
    plan.add_argument("--references", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--approve-plan", required=True)
    apply.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "apply":
            return apply_plan(args)
        repo, target = args.repo.resolve(), args.target.absolute()
        if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
            raise ValueError("repo must be an exact Git checkout root")
        entry = observe(repo, target, args.custody, args.references.absolute())
        external_output(args.output, repo, target)
        payload = {
            "schema": SCHEMA,
            "kind": "plan",
            "repository": str(repo),
            "references": str(args.references.absolute()),
            "entries": [entry],
            "status": "PASS" if entry["disposition"] == "eligible" else "HELD",
        }
        payload["plan_id"] = digest(payload)
        write_new(args.output, payload)
        print(json.dumps({"status": payload["status"], "plan_id": payload["plan_id"]}))
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"cleanup held: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
