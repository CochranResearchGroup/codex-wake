"""Resolve an operator-selected GitHub credential without persisting its value."""

import os
import subprocess
from pathlib import Path


GH_CLI_REFERENCE = "GH_CLI"
_USER_SERVICE_CANDIDATES = (
    Path("/home/linuxbrew/.linuxbrew/bin/gh"),
    Path("/opt/homebrew/bin/gh"),
)


def resolve_github_credential(reference: str, *, hostname: str = "github.com") -> str:
    if reference != GH_CLI_REFERENCE:
        return os.environ[reference]
    if hostname not in {"github.com", "api.github.com"}:
        raise ValueError("GitHub credential hostname is unsupported")
    hostname = "github.com"
    command = ["gh", "auth", "token", "--hostname", hostname]
    try:
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=5, check=False,
            )
        except FileNotFoundError:
            executable = next(
                (path for path in _USER_SERVICE_CANDIDATES if path.is_file() and os.access(path, os.X_OK)),
                None,
            )
            if executable is None:
                raise
            result = subprocess.run(
                [str(executable), *command[1:]],
                capture_output=True, text=True, timeout=5, check=False,
            )
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError("GitHub CLI authentication is unavailable") from None
    token = result.stdout.strip()
    if result.returncode != 0 or not token or len(token) > 4096 or any(
        ord(char) < 33 or ord(char) > 126 for char in token
    ):
        raise ValueError("GitHub CLI authentication is unavailable")
    return token
