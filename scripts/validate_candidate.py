"""Fail-fast validation of one Git candidate using existing check commands.

Manifest: {"checks": [{"name": "unit", "axis": "ci", "argv": ["python",
"-m", "unittest"], "required": true}], "on_success": []}.
Commands are argv arrays, executed without an implicit shell. Use the selected runtime's absolute
path in commands (or {runtime}). Receipts must be outside the candidate and new.
This runner does not grant permission to run checks or success actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def source_identity(repo):
    entries = []
    for record in git(repo, "ls-files", "--stage", "-z").split(b"\0"):
        if record and record.startswith(b"160000 "):
            raise ValueError("submodule candidates require separate validation")
    paths = git(
        repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z"
    ).split(b"\0")
    for raw in sorted(set(paths) - {b""}):
        path = repo / os.fsdecode(raw)
        try:
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                if not path.is_file():
                    raise ValueError(
                        f"candidate symlink must target a regular file: {path}"
                    )
                content = os.fsencode(os.readlink(path)) + b"\0" + path.read_bytes()
            elif stat.S_ISREG(mode):
                content = path.read_bytes()
            else:
                raise ValueError(f"unsupported candidate file: {path}")
            entries.append([os.fsdecode(raw), mode, digest(content)])
        except FileNotFoundError:
            entries.append([os.fsdecode(raw), "deleted"])
    return dict(
        root=str(repo),
        head=git(repo, "rev-parse", "HEAD").decode().strip(),
        index=digest(git(repo, "ls-files", "--stage", "-z")),
        content=digest(json.dumps(entries, ensure_ascii=True).encode()),
        dirty=bool(git(repo, "status", "--porcelain=v1", "--untracked-files=all")),
        dirty_state=git(
            repo, "status", "--porcelain=v1", "--untracked-files=all"
        ).decode(),
    )


def runtime_identity(runtime, files):
    config = runtime.parent.parent / "pyvenv.cfg"
    paths = {config, *files}
    return dict(
        path=str(runtime),
        resolved_path=str(runtime.resolve()),
        sha256=digest(runtime.read_bytes()),
        files={
            str(path): digest(path.read_bytes()) if path.is_file() else None
            for path in sorted(paths)
        },
    )


def run(args):
    repo = args.repo.resolve()
    if (
        Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
        != repo
    ):
        raise ValueError("--repo must identify the Git candidate root")
    runtime_path = shutil.which(args.runtime)
    if runtime_path is None:
        raise ValueError("selected runtime is unavailable")
    runtime = Path(runtime_path).absolute()
    receipt_path = args.receipt.resolve()
    if receipt_path.is_relative_to(repo):
        raise ValueError("receipt must be outside candidate")
    # Exclusive creation prevents a rerun from erasing the original failure.
    with receipt_path.open("x") as output:
        receipt = dict(
            schema=1, status="FAIL", checks=[], actions=[], started_at=time.time()
        )

        def save():
            output.seek(0)
            json.dump(receipt, output, indent=2)
            output.truncate()
            output.flush()
            os.fsync(output.fileno())

        save()
        try:
            manifest_bytes = args.manifest.read_bytes()
            manifest = json.loads(manifest_bytes)
            receipt["manifest_sha256"] = digest(manifest_bytes)
            checks = manifest["checks"]
            actions = manifest.get("on_success", [])
            runtime_files = manifest.get("runtime_files", [])
            if not isinstance(runtime_files, list) or not all(
                isinstance(path, str) for path in runtime_files
            ):
                raise ValueError("runtime_files must be an array of file paths")
            runtime_files = [
                Path(path).resolve()
                if Path(path).is_absolute()
                else (repo / path).resolve()
                for path in runtime_files
            ]
            if not all(path.is_file() for path in runtime_files):
                raise ValueError("runtime_files must exist as regular files")
            if (
                not isinstance(checks, list)
                or not checks
                or not isinstance(actions, list)
            ):
                raise ValueError("nonempty checks and an actions list are required")
            for row in checks + actions:
                if (
                    not isinstance(row, dict)
                    or not isinstance(row.get("name"), str)
                    or not isinstance(row.get("argv"), list)
                    or not row["argv"]
                    or not all(isinstance(part, str) and part for part in row["argv"])
                    or type(row.get("required", True)) is not bool
                ):
                    raise ValueError(
                        "each step needs a name, argv array and boolean required"
                    )
            receipt["source"] = source_identity(repo)
            receipt["runtime"] = runtime_identity(runtime, runtime_files)
            # Bind the entire inherited environment without publishing secrets.
            receipt["environment"] = dict(
                platform=sys.platform,
                runner_python=sys.version,
                sha256=digest(json.dumps(dict(os.environ), sort_keys=True).encode()),
            )
            receipt["checks"] = [
                dict(
                    name=row["name"],
                    axis=row.get("axis", row["name"]),
                    required=row.get("required", True),
                    argv=[
                        part.replace("{runtime}", str(runtime)) for part in row["argv"]
                    ],
                    status="BLOCKED",
                )
                for row in checks
            ]
            receipt["actions"] = [
                dict(
                    name=row["name"],
                    argv=[
                        part.replace("{runtime}", str(runtime)) for part in row["argv"]
                    ],
                    status="BLOCKED",
                )
                for row in actions
            ]
            save()

            def unchanged():
                if (
                    source_identity(repo) != receipt["source"]
                    or runtime_identity(runtime, runtime_files) != receipt["runtime"]
                    or args.manifest.read_bytes() != manifest_bytes
                ):
                    for row in receipt["checks"]:
                        if row["status"] == "PASS":
                            row["status"] = "INVALIDATED"
                    receipt["qualified"] = False
                    raise ValueError(
                        "candidate, runtime or check manifest changed during validation"
                    )

            def execute(row):
                row["status"] = "RUNNING"
                save()
                try:
                    result = subprocess.run(
                        row["argv"],
                        cwd=repo,
                        capture_output=True,
                        text=True,
                        errors="replace",
                        timeout=args.timeout,
                    )
                    row.update(
                        returncode=result.returncode,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        status="PASS" if result.returncode == 0 else "FAIL",
                    )
                except (OSError, subprocess.TimeoutExpired) as error:
                    row.update(status="FAIL", error=str(error))
                save()

            for row in receipt["checks"]:
                unchanged()
                execute(row)
                unchanged()
                if row["status"] != "PASS" and row["required"]:
                    receipt["failure"] = dict(
                        reason="required check failed", command=row["argv"]
                    )
                    break
            else:
                unchanged()
                receipt["qualified"] = True
                # These steps may intentionally commit the qualified candidate. Their
                # outcomes remain separate from the source-bound check outcomes.
                for row in receipt["actions"]:
                    unchanged()
                    execute(row)
                    if row["status"] != "PASS":
                        receipt["failure"] = dict(
                            reason="success action failed", command=row["argv"]
                        )
                        break
                else:
                    receipt["status"] = "PASS"
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            subprocess.SubprocessError,
        ) as error:
            receipt["failure"] = dict(reason=str(error))
        receipt["finished_at"] = time.time()
        save()
    print(json.dumps(receipt))
    return int(receipt["status"] != "PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        return run(args)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
