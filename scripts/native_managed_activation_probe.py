#!/usr/bin/env python3
"""Probe only modern update/from-cli support; never an overall activation oracle."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def probe(executable):
    executable = Path(executable).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="wake-native-contract-") as temporary:
        home = Path(temporary)
        environment = dict(
            os.environ,
            HOME=str(home),
            CODEX_HOME=str(home / ".codex"),
            XDG_CONFIG_HOME=str(home / ".config"),
            XDG_STATE_HOME=str(home / ".state"),
            XDG_RUNTIME_DIR=str(home / "run"),
        )
        command = [str(executable), "app-server", "daemon", "update", "--help"]
        result = subprocess.run(
            command, env=environment, capture_output=True, text=True, timeout=10
        )
        output = result.stdout + result.stderr
        with executable.open("rb") as binary:
            digest = hashlib.file_digest(binary, "sha256").hexdigest()
        return dict(
            executable=str(executable),
            sha256=digest,
            command=command,
            returncode=result.returncode,
            output=output[:16000],
            managed_update_interface=result.returncode == 0 and "--from-cli" in output,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--reference-cli", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = probe(args.reference_cli)
    candidate = probe(args.candidate)
    verdict = (
        "PASS_INTERFACE_ONLY"
        if candidate["managed_update_interface"]
        else "MODERN_UPDATE_INTERFACE_UNAVAILABLE"
    )
    if not reference["managed_update_interface"]:
        verdict = "INVALID_REFERENCE"
    report = dict(
        verdict=verdict,
        reference=reference,
        candidate=candidate,
        route="modern_update_from_cli",
        installation_attempted=False,
        live_daemon_touched=False,
        feature_acceptance=False,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(report, stream, indent=2)
    print(
        json.dumps(
            dict(
                verdict=verdict,
                candidate_exit=candidate["returncode"],
                reference_exit=reference["returncode"],
                receipt=str(args.output),
            )
        )
    )
    return 0 if verdict == "PASS_INTERFACE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
