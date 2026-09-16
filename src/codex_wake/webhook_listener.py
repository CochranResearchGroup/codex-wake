"""Dedicated executable seam for the productized GitHub webhook listener."""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .records import WakeError, default_wake_root
from .webhook_lifecycle import WebhookListenerStore


def _runtime_factory(config, secrets: tuple[bytes, ...]):
    """Deferred #105 join point; product construction remains intentionally injected."""
    from .github_webhook_runtime import GitHubWebhookRuntime  # type: ignore[import-not-found,unused-ignore]
    del GitHubWebhookRuntime, config, secrets
    raise WakeError("webhook runtime construction requires the canonical #105 join adapter")


def run_listener(*, wake_root: Path, source_instance: str,
                 runtime_factory: Callable[[Any, tuple[bytes, ...]], Any] | None = None,
                 env: dict[str, str] | None = None) -> int:
    listener = WebhookListenerStore(wake_root).enabled(source_instance)
    source_env = env if env is not None else os.environ
    refs = (listener.secret_ref,) + ((listener.previous_secret_ref,) if listener.previous_secret_ref else ())
    values = tuple(source_env.get(reference, "").encode("utf-8") for reference in refs)
    if any(not value for value in values):
        raise WakeError("webhook listener secret reference is unavailable")
    factory = runtime_factory or _runtime_factory
    try:
        runtime = factory(listener, values)
    except ModuleNotFoundError as exc:
        raise WakeError("webhook runtime is unavailable until canonical #105 is joined") from exc
    if not callable(getattr(runtime, "serve", None)) or not callable(getattr(runtime, "shutdown", None)):
        raise WakeError("webhook runtime does not satisfy the lifecycle contract")
    try:
        runtime.serve()  # Contract: blocks on the main thread after bind.
    except KeyboardInterrupt:
        pass
    finally:
        runtime.shutdown()  # Contract: the #105 runtime owns its bounded budget.
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-wake-github-webhook")
    parser.add_argument("--wake-root", type=Path, default=None)
    parser.add_argument("--source", required=True, dest="source_instance")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        root = (args.wake_root or default_wake_root(Path.cwd())).resolve()
        return run_listener(wake_root=root, source_instance=args.source_instance)
    except WakeError as exc:
        print(f"codex-wake-github-webhook: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
