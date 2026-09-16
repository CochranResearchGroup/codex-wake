"""Built-in reconstruction factories for local signal source families.

These factories only translate already accepted durable candidates into their
source-owned runners.  They intentionally do not sample a filesystem, inspect
``/proc``, call the user bus, or write durable state.
"""
from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import Callable

from .source_registry import (
    BuiltinSourceRegistration,
    ReconstructionCandidate,
    ReconstructionContext,
)
from .signals import SignalSourceRunner, UnavailableSourceRunner


_FILESYSTEM_KINDS = frozenset({"file.created", "file.exists", "file.changed"})
_PROCESS_OWNERSHIP = frozenset({("runtime", "process.exit")})
_SYSTEMD_OWNERSHIP = frozenset({("systemd", "unit.active_state")})


def filesystem_family(
    context: ReconstructionContext,
    candidates: tuple[ReconstructionCandidate, ...],
) -> tuple[SignalSourceRunner, ...]:
    """Construct one filesystem batch in durable pending order."""

    from .filesystem_signals import FilesystemSignalAdapter, FilesystemSignalRunner

    adapters: dict[str, FilesystemSignalAdapter] = {}
    armed_signals = []
    for candidate in candidates:
        armed = candidate.armed
        if armed.spec.source != "filesystem" or armed.spec.kind not in _FILESYSTEM_KINDS:
            continue
        predicate = candidate.pending.record.get("predicate")
        if not isinstance(predicate, dict):
            continue
        source = predicate.get("source")
        source_instance = predicate.get("source_instance")
        subject = predicate.get("subject")
        if (
            source != "filesystem"
            or not isinstance(source_instance, str)
            or not isinstance(subject, str)
            or not subject.startswith("path:")
        ):
            continue
        cwd = candidate.pending.record.get("cwd")
        if not isinstance(cwd, str):
            continue
        try:
            adapter = FilesystemSignalAdapter(
                Path(cwd), subject.removeprefix("path:"), source_instance=source_instance,
            )
        except ValueError:
            continue
        existing = adapters.get(source_instance)
        if existing is not None and (
            existing.root != adapter.root or existing.relative_path != adapter.relative_path
        ):
            continue
        adapters[source_instance] = adapter
        armed_signals.append(armed)
    if not armed_signals:
        return ()
    return (
        FilesystemSignalRunner(
            adapters.values(), armed_signals=armed_signals, initial_reason=context.initial_reason,
        ),
    )


def process_exit_family(
    context: ReconstructionContext,
    candidates: tuple[ReconstructionCandidate, ...],
) -> tuple[SignalSourceRunner, ...]:
    """Construct one runner per sorted exact process identity."""

    from .process_signals import restore_production_process_exit_adapter

    adapters = {}
    arms: dict[str, list] = {}
    failures: dict[str, str] = {}
    for candidate in candidates:
        armed = candidate.armed
        if armed.spec.source != "runtime" or armed.spec.kind != "process.exit":
            continue
        source_instance = armed.spec.source_instance
        try:
            adapter = restore_production_process_exit_adapter(armed)
        except (OSError, TypeError, ValueError):
            failures[source_instance] = "RUNTIME_ANCHOR_INVALID"
            continue
        existing = adapters.get(source_instance)
        if existing is not None and existing.descriptor != adapter.descriptor:
            continue
        adapters[source_instance] = adapter
        arms.setdefault(source_instance, []).append(armed)
    runners: list[SignalSourceRunner] = [
        adapters[source_instance].runner(arms[source_instance])
        for source_instance in sorted(arms)
    ]
    runners.extend(
        UnavailableSourceRunner("runtime", source_instance, code)
        for source_instance, code in sorted(failures.items())
    )
    return tuple(runners)


def user_systemd_family(
    context: ReconstructionContext,
    candidates: tuple[ReconstructionCandidate, ...],
    *,
    systemd_backend_factory: Callable[[object], object] | None = None,
) -> tuple[SignalSourceRunner, ...]:
    """Construct one configured user-systemd batch with injected read backend."""

    from .runtime_signals import RuntimeSourceRegistry
    from .systemd_signals import (
        SystemdReadCapability,
        SystemdSignalAdapter,
        SystemdSignalRunner,
        SystemdUserBusBackend,
    )
    from .systemd_source_config import SystemdSourceStore

    arms: dict[str, list] = {}
    for candidate in candidates:
        armed = candidate.armed
        if armed.spec.source == "systemd" and armed.spec.kind == "unit.active_state":
            arms.setdefault(armed.spec.source_instance, []).append(armed)
    if not arms:
        return ()
    failures: dict[str, str] = {}
    try:
        configuration_store = SystemdSourceStore(context.root)
        registry = configuration_store.registry()
        adapters = []
        referenced_arms = []
        for source_instance in sorted(arms):
            try:
                source_config = registry.select(source_instance)
                backend = (
                    systemd_backend_factory(source_config)
                    if systemd_backend_factory is not None
                    else SystemdUserBusBackend()
                )
                adapters.append(SystemdSignalAdapter(
                    source_config,
                    backend,
                    RuntimeSourceRegistry({
                        "systemd.unit": lambda descriptor, source_instance=source_instance: (
                            _configured_systemd_descriptor(
                                configuration_store, source_instance, descriptor,
                            )
                        ),
                    }),
                    SystemdReadCapability("user", os.geteuid()),
                ))
            except (OSError, TypeError, ValueError):
                failures[source_instance] = "SYSTEMD_SOURCE_UNSUPPORTED"
                continue
            referenced_arms.extend(arms[source_instance])
    except (OSError, TypeError, ValueError):
        failures = {
            source_instance: "SYSTEMD_SOURCE_UNSUPPORTED" for source_instance in arms
        }
        adapters = []
        referenced_arms = []
    runners: list[SignalSourceRunner] = []
    if adapters:
        runners.append(SystemdSignalRunner(
            adapters,
            armed_signals=tuple(referenced_arms),
            initial_reason=context.initial_reason,
        ))
    runners.extend(
        UnavailableSourceRunner("systemd", source_instance, code)
        for source_instance, code in sorted(failures.items())
    )
    return tuple(runners)


def local_source_registrations(
    *,
    systemd_backend_factory: Callable[[object], object] | None = None,
) -> tuple[BuiltinSourceRegistration, ...]:
    """Return the fixed built-in local source catalogue in runner order."""

    return (
        BuiltinSourceRegistration(
            "local-filesystem",
            frozenset(("filesystem", kind) for kind in _FILESYSTEM_KINDS),
            filesystem_family,
        ),
        BuiltinSourceRegistration("local-process-exit", _PROCESS_OWNERSHIP, process_exit_family),
        BuiltinSourceRegistration(
            "local-user-systemd",
            _SYSTEMD_OWNERSHIP,
            partial(user_systemd_family, systemd_backend_factory=systemd_backend_factory),
        ),
    )


def _configured_systemd_descriptor(store, source_instance: str, descriptor) -> bool:
    try:
        current = store.registry().select(source_instance)
        return any(descriptor == current.descriptor(state) for state in current.target_states)
    except (OSError, TypeError, ValueError):
        return False
