"""Dedicated executable seam for the productized GitHub webhook listener."""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .github_client import GitHubRestClient, GitHubReadDeadline
from .github_polling import GitHubPollingAdapter, GitHubReadClient, GitHubReadError
from .github_source_config import GitHubSourceStore
from .github_webhook_runtime import GitHubWebhookRuntime
from .github_webhooks import WebhookConfig
from .records import WakeError, default_wake_root
from .signal_records import signal_journal_path
from .signal_store import SQLiteSignalModule, SignalStoreError
from .signals import Invalid, SourceAnchor
from .webhook_http import WebhookHTTPConfig
from .webhook_lifecycle import WebhookListenerConfig, WebhookListenerStore, webhook_http_config_kwargs


class _UnavailablePollingClient:
    """Construction-only adapter; webhook reads use a fresh deadline client."""

    def list_runs(self, query):
        raise GitHubReadError("unavailable")

    def get_run_attempt(self, repository: str, run_id: int, run_attempt: int):
        raise GitHubReadError("unavailable")


def _secret_resolver(listener: WebhookListenerConfig,
                     environment: Mapping[str, str]) -> Callable[[str], bytes]:
    references = frozenset(
        (listener.secret_ref,)
        + ((listener.previous_secret_ref,) if listener.previous_secret_ref else ())
    )

    def resolve(reference: str) -> bytes:
        if reference not in references:
            raise WakeError("webhook listener secret reference is invalid")
        value = environment.get(reference)
        if type(value) is not str or not value:
            raise WakeError("webhook listener secret reference is unavailable")
        return value.encode("utf-8")

    return resolve


def build_webhook_runtime(
    *, wake_root: Path, listener: WebhookListenerConfig,
    environment: Mapping[str, str] | None = None,
    attempt_client_factory: Callable[[GitHubReadDeadline], GitHubReadClient] | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> GitHubWebhookRuntime:
    """Construct one source-bound runtime from durable product authority."""
    source_env = environment if environment is not None else os.environ
    def require_current_authority() -> tuple[WebhookListenerConfig, object]:
        try:
            current_listener = WebhookListenerStore(wake_root).enabled(listener.source_instance)
            current_source = GitHubSourceStore(wake_root).registry().select(listener.source_instance)
            if current_listener != listener or current_source != source:
                raise ValueError("webhook listener authority changed")
            if SQLiteSignalModule.open_existing(signal_journal_path(wake_root)) is None:
                raise SignalStoreError("webhook listener signal journal is unavailable")
            return current_listener, current_source
        except (ValueError, SignalStoreError) as exc:
            raise WakeError("webhook listener authority is unavailable") from exc

    try:
        source = GitHubSourceStore(wake_root).registry().select(listener.source_instance)
        module = SQLiteSignalModule.open_existing(signal_journal_path(wake_root))
    except (ValueError, SignalStoreError) as exc:
        raise WakeError(str(exc)) from None
    if module is None:
        raise WakeError("webhook listener signal journal is unavailable")
    adapter = GitHubPollingAdapter(source, _UnavailablePollingClient())
    request = adapter.request(
        ref=sorted(source.refs)[0],
        conclusions=tuple(sorted(source.conclusions)),
    )
    anchor = adapter.establish_anchor(request, now())
    if isinstance(anchor, Invalid) or type(anchor) is not SourceAnchor:
        raise WakeError("webhook listener source anchor is invalid")

    def resolve_credential(reference: str) -> str:
        _, current_source = require_current_authority()
        if reference != current_source.credential_ref:
            raise GitHubReadError("auth")
        value = source_env.get(reference)
        if type(value) is not str or not value:
            raise GitHubReadError("auth")
        return value

    make_client = attempt_client_factory or (
        lambda deadline: GitHubRestClient(
            source,
            credential_resolver=resolve_credential,
            deadline=deadline,
        )
    )
    secrets = tuple(
        reference for reference in (listener.secret_ref, listener.previous_secret_ref)
        if reference is not None
    )
    return GitHubWebhookRuntime(
        WebhookHTTPConfig(**webhook_http_config_kwargs(listener)),
        adapter=adapter,
        module=module,
        checkpoints=module,
        anchor=anchor,
        webhook_config=WebhookConfig(
            secret_refs=secrets,
            max_body_bytes=listener.max_body_bytes,
        ),
        resolve_secret=lambda reference: (require_current_authority(), _secret_resolver(listener, source_env)(reference))[1],
        attempt_client_factory=make_client,
        operation_timeout=listener.operation_timeout_seconds,
        now=now,
    )


def run_listener(*, wake_root: Path, source_instance: str,
                 runtime_factory: Callable[[Any, Callable[[str], bytes]], Any] | None = None,
                 env: dict[str, str] | None = None) -> int:
    listener = WebhookListenerStore(wake_root).enabled(source_instance)
    source_env = env if env is not None else os.environ
    resolve_secret = _secret_resolver(listener, source_env)
    try:
        runtime = (
            runtime_factory(listener, resolve_secret)
            if runtime_factory is not None
            else build_webhook_runtime(
                wake_root=wake_root,
                listener=listener,
                environment=source_env,
            )
        )
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
