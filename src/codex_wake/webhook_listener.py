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
from .managed_webhook_rotation import (
    ManagedWebhookRotationCoordinator, ManagedWebhookRotationStore, RuntimeProof,
)
from .managed_webhook_runtime import verify_runtime_attestation, write_runtime_attestation
from .managed_webhooks import ManagedWebhookStore
from .records import WakeError, default_wake_root
from .signal_records import signal_journal_path
from .signal_store import SQLiteSignalModule, SignalStoreError
from .signals import Invalid, SourceAnchor
from .webhook_http import WebhookHTTPConfig
from .webhook_lifecycle import (
    WebhookListenerConfig, WebhookListenerStore, build_webhook_service_config,
    webhook_http_config_kwargs, webhook_service_name,
)


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
    runtime_proof_verifier: Callable[[], RuntimeProof] | None = None,
) -> GitHubWebhookRuntime:
    """Construct one source-bound runtime from durable product authority."""
    source_env = environment if environment is not None else os.environ
    rotation_context = None
    def require_current_authority() -> tuple[WebhookListenerConfig, object]:
        try:
            current_listener = WebhookListenerStore(wake_root).enabled(listener.source_instance)
            current_source = GitHubSourceStore(wake_root).registry().select(listener.source_instance)
            if current_listener != listener or current_source != source:
                raise ValueError("webhook listener authority changed")
            current_rotations = tuple(
                record for record in ManagedWebhookRotationStore(wake_root).records()
                if record.source_instance == listener.source_instance
            )
            if rotation_context is None and current_rotations:
                raise ValueError("managed webhook rotation authority appeared after startup")
            if rotation_context is not None:
                binding, rotation = rotation_context
                if len(current_rotations) != 1 or current_rotations[0].owner_id != rotation.owner_id:
                    raise ValueError("managed webhook rotation authority changed")
                current_binding = ManagedWebhookStore(wake_root).load(rotation.owner_id)
                current_rotation = current_rotations[0]
                if (
                    current_binding != binding
                    or current_rotation.canonical_root != rotation.canonical_root
                    or current_rotation.owner_uid != rotation.owner_uid
                    or current_rotation.source_instance != rotation.source_instance
                    or current_rotation.service_id != rotation.service_id
                    or current_rotation.binding_revision != rotation.binding_revision
                    or current_rotation.previous_generation != rotation.previous_generation
                    or current_rotation.target_generation != rotation.target_generation
                ):
                    raise ValueError("managed webhook rotation authority changed")
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
    generations = tuple(
        generation for generation in (listener.current_generation, listener.previous_generation)
        if generation is not None
    )
    admitted_generations = None
    committed_delivery = None
    prove_runtime = runtime_proof_verifier
    try:
        rotations = tuple(
            record for record in ManagedWebhookRotationStore(wake_root).records()
            if record.source_instance == listener.source_instance
        )
        if rotations:
            if len(rotations) != 1:
                raise ValueError("managed webhook rotation ownership is ambiguous")
            rotation = rotations[0]
            bindings = tuple(
                binding for binding in ManagedWebhookStore(wake_root).bindings()
                if binding.owner_id == rotation.owner_id
            )
            if len(bindings) != 1:
                raise ValueError("managed webhook rotation binding is unavailable")
            binding = bindings[0]
            canonical_root = str(Path(wake_root).resolve())
            if (
                rotation.canonical_root != canonical_root
                or binding.canonical_root != canonical_root
                or rotation.owner_uid != os.getuid()
                or binding.owner_uid != os.getuid()
                or rotation.source_instance != binding.source_instance
                or rotation.service_id != webhook_service_name(listener.source_instance)
                or binding.service_id != rotation.service_id
                or binding.generation != rotation.binding_revision
                or binding.repository != source.repository
                or binding.repository_id != source.repository_id
                or binding.provider_host != "api.github.com"
                or source.hostname != "github.com"
                or not generations
            ):
                raise ValueError("managed webhook rotation authority is invalid")
            coordinator = ManagedWebhookRotationCoordinator(ManagedWebhookRotationStore(wake_root))
            rotation_context = (binding, rotation)

            def admitted_generations(observed_at: datetime) -> tuple[int, ...]:
                return coordinator.admitted_generations(
                    rotation.owner_id, now=int(observed_at.timestamp()),
                )

            def committed_delivery(generation: int, receipt_id: str) -> None:
                observed_at = int(now().timestamp())
                current = coordinator.load(rotation.owner_id, now=observed_at)
                if ManagedWebhookStore(wake_root).load(rotation.owner_id) != binding:
                    raise ValueError("managed webhook rotation binding changed")
                if generation != current.target_generation:
                    return
                if prove_runtime is None or current.runtime_proof is None:
                    raise ValueError("managed webhook rotation runtime proof is unavailable")
                live_proof = prove_runtime()
                if type(live_proof) is not RuntimeProof or live_proof != current.runtime_proof:
                    raise ValueError("managed webhook rotation runtime proof changed")
                if current.delivery_locator is not None:
                    return
                coordinator.record_delivery(
                    rotation.owner_id, expected_revision=current.revision,
                    generation=generation, journal_locator=receipt_id, now=observed_at,
                )
    except ValueError as exc:
        raise WakeError("managed webhook rotation authority is unavailable") from exc
    resolver = _secret_resolver(listener, source_env)
    try:
        loaded_secrets = {reference: resolver(reference) for reference in secrets}
        if (
            any(type(value) is not bytes or not 16 <= len(value) <= 4096 for value in loaded_secrets.values())
            or len(set(loaded_secrets.values())) != len(loaded_secrets)
        ):
            raise ValueError
    except (ValueError, WakeError):
        raise WakeError("webhook listener secret generation set is unavailable") from None
    runtime = GitHubWebhookRuntime(
        WebhookHTTPConfig(**webhook_http_config_kwargs(listener)),
        adapter=adapter,
        module=module,
        checkpoints=module,
        anchor=anchor,
        webhook_config=WebhookConfig(
            secret_refs=secrets,
            secret_generations=generations,
            max_body_bytes=listener.max_body_bytes,
        ),
        resolve_secret=lambda reference: (require_current_authority(), loaded_secrets[reference])[1],
        attempt_client_factory=make_client,
        operation_timeout=listener.operation_timeout_seconds,
        now=now,
        admitted_generations=admitted_generations,
        committed_delivery=committed_delivery,
    )
    if rotation_context is not None:
        binding, rotation = rotation_context
        try:
            write_runtime_attestation(
                wake_root=wake_root, listener=listener, binding=binding, rotation=rotation,
            )
            if prove_runtime is None:
                service = build_webhook_service_config(
                    wake_root=wake_root, source_instance=listener.source_instance,
                    validate_executable=False,
                )
                prove_runtime = lambda: verify_runtime_attestation(
                    config=service, listener=listener, binding=binding,
                    rotation=ManagedWebhookRotationStore(wake_root).load(rotation.owner_id),
                )
        except ValueError as exc:
            runtime.shutdown()
            raise WakeError("managed webhook runtime attestation is unavailable") from exc
    return runtime


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
