"""Registered reconstruction for the bounded GitHub CI source family.

The registration is deliberately closed and local.  Inspecting the returned
registration is inert; client construction happens only when the source
registry supplies eligible durable candidates.
"""
from __future__ import annotations

import os
from collections.abc import Callable

from .github_polling import GitHubPollingAdapter, GitHubPollingConfig, GitHubReadClient
from .github_source_config import GitHubSourceStore
from .signals import SignalSourceRunner
from .source_registry import (
    BuiltinSourceRegistration,
    ReconstructionCandidate,
    ReconstructionContext,
)


GitHubClientFactory = Callable[[GitHubPollingConfig], GitHubReadClient]
GitHubRunnerFactory = Callable[..., SignalSourceRunner]


def github_source_family_registration(
    *,
    runner_factory: GitHubRunnerFactory,
    client_factory: GitHubClientFactory | None = None,
) -> BuiltinSourceRegistration:
    """Return the sole GitHub family registration.

    Dependencies are intentionally bound in the factory closure.  In
    particular, the daemon-owned runner is supplied by the integration layer,
    while test and embedding callers can inject a provider-free client without
    expanding the registry contract.  The production client is constructed
    only for an enabled, referenced, selected source instance.
    """

    def construct(
        context: ReconstructionContext,
        candidates: tuple[ReconstructionCandidate, ...],
    ) -> tuple[SignalSourceRunner, ...]:
        return _construct_github_family(context, candidates, runner_factory, client_factory)

    return BuiltinSourceRegistration(
        "github-ci",
        frozenset({("github", "workflow_run.completed")}),
        construct,
    )


def _construct_github_family(
    context: ReconstructionContext,
    candidates: tuple[ReconstructionCandidate, ...],
    runner_factory: GitHubRunnerFactory,
    client_factory: GitHubClientFactory | None,
) -> tuple[SignalSourceRunner, ...]:
    """Build one runner for the selected GitHub instances, or silently skip.

    The registry has already established source/kind ownership.  This layer
    groups only by source instance, selects explicit configuration before
    constructing each client, restores durable retry state, and keeps a
    malformed source isolated from other configured instances.
    """

    grouped: dict[str, list[ReconstructionCandidate]] = {}
    for candidate in candidates:
        source_instance = candidate.armed.spec.source_instance
        if isinstance(source_instance, str):
            grouped.setdefault(source_instance, []).append(candidate)

    if not grouped:
        return ()
    try:
        store = GitHubSourceStore(context.root)
        registry = store.registry()
    except (OSError, TypeError, ValueError):
        # A damaged configuration creates neither a client nor GitHub read
        # authority.  The closed registry isolates this family from others.
        return ()

    adapters: dict[str, GitHubPollingAdapter] = {}
    for source_instance in sorted(grouped):
        try:
            selected = registry.select(source_instance)
            client = (
                client_factory(selected)
                if client_factory is not None
                else _production_client(selected)
            )
            adapters[source_instance] = GitHubPollingAdapter(
                selected,
                client,
                previous_failure=store.retry_failure(source_instance),
            )
        except (OSError, TypeError, ValueError):
            # Match the legacy reconstruction contract: a disabled,
            # unsupported, or locally failed instance is not a runner.
            continue
    if not adapters:
        return ()

    # Preserve the legacy daemon order: sorted configured source instances,
    # with durable pending order retained inside each instance batch.
    referenced_arms = tuple(
        candidate.armed
        for source_instance in sorted(grouped)
        if source_instance in adapters
        for candidate in grouped[source_instance]
    )

    return (runner_factory(adapters, armed_signals=referenced_arms, health_store=store),)


def _production_client(config: GitHubPollingConfig) -> GitHubReadClient:
    """Construct the bounded production client without issuing a request."""

    from .github_client import GitHubRestClient

    return GitHubRestClient(
        config,
        credential_resolver=lambda ref: os.environ.get(ref, ""),
    )
