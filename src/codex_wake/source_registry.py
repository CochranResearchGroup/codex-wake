"""Closed, in-process source-family reconstruction contracts.

Catalogue membership describes implementation availability, not observation
authority. Factories must only construct runners: configuration authorization,
observation, journal writes and retry policy remain owned by the sources and
their runners. This is not a package discovery or external plugin interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal

from .records import WakePath, classify_record
from .signals import ArmedSignal, SignalSourceRunner, WakeId


@dataclass(frozen=True, slots=True)
class ReconstructionContext:
    """Explicit reconstruction inputs; no daemon or mutable engine access."""

    root: Path
    load_armed_signal: Callable[[WakeId], ArmedSignal | None]
    initial_reason: Literal["startup", "periodic"] = "startup"


@dataclass(frozen=True, slots=True)
class ReconstructionCandidate:
    """One pending projection paired with its authoritative published arm.

    The existing record/arm objects are borrowed read-only; freezing this pair
    does not change the records' existing representation or ownership.
    """

    pending: WakePath
    armed: ArmedSignal


FamilyFactory = Callable[
    [ReconstructionContext, tuple[ReconstructionCandidate, ...]],
    tuple[SignalSourceRunner, ...],
]


@dataclass(frozen=True, slots=True)
class BuiltinSourceInventory:
    """Nonsecret, deterministic description of one closed built-in family."""

    registration_id: str
    ownership: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class BuiltinSourceRegistration:
    registration_id: str
    ownership: frozenset[tuple[str, str]]
    factory: FamilyFactory

    def __post_init__(self) -> None:
        if not isinstance(self.registration_id, str) or not self.registration_id.strip():
            raise ValueError("registration id must be nonempty")
        ownership = tuple(self.ownership)
        if not ownership or any(
            not isinstance(pair, tuple)
            or len(pair) != 2
            or any(not isinstance(value, str) or not value.strip() for value in pair)
            for pair in ownership
        ):
            raise ValueError("ownership must contain nonempty (source, kind) pairs")
        if not callable(self.factory):
            raise TypeError("registration factory must be callable")
        object.__setattr__(self, "ownership", frozenset(ownership))


@dataclass(frozen=True, slots=True)
class BuiltinSourceRegistry:
    """Immutable catalogue, with factory and runner order declared by the caller."""

    registrations: tuple[BuiltinSourceRegistration, ...]

    def __post_init__(self) -> None:
        registrations = tuple(self.registrations)
        identities: set[str] = set()
        ownership: set[tuple[str, str]] = set()
        for registration in registrations:
            if registration.registration_id in identities:
                raise ValueError(f"duplicate registration id: {registration.registration_id}")
            overlap = ownership.intersection(registration.ownership)
            if overlap:
                source, kind = min(overlap)
                raise ValueError(f"overlapping source ownership: {source}/{kind}")
            identities.add(registration.registration_id)
            ownership.update(registration.ownership)
        object.__setattr__(self, "registrations", registrations)

    @property
    def inventory(self) -> tuple[BuiltinSourceInventory, ...]:
        """Return the closed catalogue without invoking a family factory.

        This projection deliberately contains only stable registration and
        source-kind ownership labels.  It neither examines runtime state nor
        exposes factory closures or their dependency bindings.
        """

        return tuple(
            BuiltinSourceInventory(
                registration.registration_id,
                tuple(sorted(registration.ownership)),
            )
            for registration in self.registrations
        )

    def reconstruct(
        self,
        context: ReconstructionContext,
        pending: Iterable[WakePath],
    ) -> tuple[SignalSourceRunner, ...]:
        """Select durable identities and construct each nonempty family once.

        Pending order is preserved within each immutable candidate tuple.
        Unowned or malformed records are ignored. A failed load or factory
        contributes no runners and does not trigger retries or state changes.
        Source-specific dependencies can be bound in factory closures.
        """

        if not self.registrations:
            return ()
        owners = {
            pair: index
            for index, registration in enumerate(self.registrations)
            for pair in registration.ownership
        }
        batches: list[list[ReconstructionCandidate]] = [[] for _ in self.registrations]
        for item in pending:
            if classify_record(item.record) != "signal_v2" or item.record["status"] != "pending":
                continue
            try:
                armed = context.load_armed_signal(WakeId(item.record["id"]))
            except Exception:
                continue
            if (
                not isinstance(armed, ArmedSignal)
                or armed.wake_id != item.record["id"]
                or armed.arm_id != item.record["arm_id"]
                or armed.publication != "published"
            ):
                continue
            owner = owners.get((armed.spec.source, armed.spec.kind))
            if owner is not None:
                batches[owner].append(ReconstructionCandidate(item, armed))
        runners: list[SignalSourceRunner] = []
        for registration, candidates in zip(self.registrations, batches):
            if not candidates:
                continue
            try:
                # Materialize before extending, so a failed iterator cannot
                # leak a partial family into the successful result.
                family_runners = tuple(registration.factory(context, tuple(candidates)))
            except Exception:
                continue
            runners.extend(family_runners)
        return tuple(runners)


def _unavailable_github_runner(*_args: object, **_kwargs: object) -> SignalSourceRunner:
    """Keep operator catalogue inspection independent of daemon runner types."""

    raise RuntimeError("GitHub runner construction requires daemon wiring")


def builtin_source_registry(
    *,
    github_runner_factory: Callable[..., SignalSourceRunner] | None = None,
    github_client_factory: Callable[..., object] | None = None,
    systemd_backend_factory: Callable[[object], object] | None = None,
) -> BuiltinSourceRegistry:
    """Construct the one fixed production built-in source catalogue.

    The daemon supplies its GitHub runner dependency when it reconstructs
    pending arms.  Operator inventory may use the same construction path with
    the inert fallback because it only reads :attr:`BuiltinSourceRegistry.inventory`.
    No external registration or package discovery is supported.
    """

    from .github_source_family import github_source_family_registration
    from .local_source_families import local_source_registrations

    return BuiltinSourceRegistry((
        *local_source_registrations(systemd_backend_factory=systemd_backend_factory),
        github_source_family_registration(
            runner_factory=(
                github_runner_factory
                if github_runner_factory is not None
                else _unavailable_github_runner
            ),
            client_factory=github_client_factory,
        ),
    ))
