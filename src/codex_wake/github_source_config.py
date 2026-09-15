"""Explicit operator-owned, nonsecret GitHub source selection.

The registry takes configuration values, never ambient credentials or arbitrary
registration fields. Credential references name an injected resolver entry.
"""
from types import MappingProxyType

from .github_polling import GitHubPollingConfig, _valid_config


class GitHubSourceRegistry:
    def __init__(self, sources: tuple[GitHubPollingConfig, ...]):
        if type(sources) is not tuple or len(sources) > 64:
            raise ValueError("GitHub source registry is invalid")
        selected = {}
        for source in sources:
            if (not _valid_config(source) or source.evidence_mode != "positive_only"
                    or source.source_instance in selected):
                raise ValueError("GitHub source registry is invalid")
            selected[source.source_instance] = source
        self._sources = MappingProxyType(selected)

    def select(self, source_instance: str) -> GitHubPollingConfig:
        source = self._sources.get(source_instance) if type(source_instance) is str else None
        if source is None or not source.enabled:
            raise ValueError("GitHub source is not enabled")
        return source

    def enabled_sources(self) -> tuple[GitHubPollingConfig, ...]:
        return tuple(value for value in self._sources.values() if value.enabled)
