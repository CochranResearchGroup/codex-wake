"""Closed built-in registration for generic HTTP/JSON completion sources."""

from __future__ import annotations

from typing import Callable

from .http_json_signals import HTTPJSONClient, HTTPJSONReadClient, HTTPJSONSignalAdapter, HTTPJSONSignalRunner
from .http_json_source_config import HTTPJSONSourceConfig, HTTPJSONSourceStore
from .signals import SignalSourceRunner
from .source_registry import BuiltinSourceRegistration, ReconstructionCandidate, ReconstructionContext


HTTPJSONClientFactory = Callable[[HTTPJSONSourceConfig], HTTPJSONReadClient]


def http_json_source_family_registration(
    *, client_factory: HTTPJSONClientFactory | None = None,
) -> BuiltinSourceRegistration:
    make_client = client_factory or HTTPJSONClient

    def construct(
        context: ReconstructionContext,
        candidates: tuple[ReconstructionCandidate, ...],
    ) -> tuple[SignalSourceRunner, ...]:
        try:
            store = HTTPJSONSourceStore(context.root)
            configured = {item.source_instance: item for item in store.sources() if item.enabled}
        except (OSError, TypeError, ValueError):
            return ()
        grouped: dict[str, list] = {}
        for candidate in candidates:
            grouped.setdefault(candidate.armed.spec.source_instance, []).append(candidate.armed)
        adapters = []
        arms = []
        for source_instance in sorted(grouped):
            source = configured.get(source_instance)
            if source is None:
                continue
            try:
                adapters.append(HTTPJSONSignalAdapter(source, make_client(source)))
            except Exception:
                continue
            arms.extend(grouped[source_instance])
        if not adapters:
            return ()
        return (HTTPJSONSignalRunner(adapters, armed_signals=tuple(arms)),)

    return BuiltinSourceRegistration(
        "http-json-completion",
        frozenset({("http-json", "job.terminal")}),
        construct,
    )
