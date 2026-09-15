from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, Mapping

from .records import (
    WakeError,
    WakeLifecycleLock,
    WakePath,
    classify_record,
    default_wake_root,
    find_record,
    iter_records,
    move_record,
    parse_utc_timestamp,
    utc_now,
)
from .builtin_signals import BuiltinPredicateSignals
from .injector import TmuxRunner, dispatch_firing_record
from .signal_store import SQLiteSignalModule
from .signal_records import WakeRecordPublisher, current_reader_capability, signal_journal_path
from .github_polling import (
    GitHubPollingAdapter,
    GitHubPollingConfig,
    GitHubReadClient,
    PollBatch,
)
from .github_source_config import GitHubSourceStore
from .signals import (
    ArmedSignal, Degraded, EvaluationLimits, Expired, Ingested,
    Matched, SignalSourceRunner, SourceInstanceReconcileResult,
    SourceReconcileResult,
)
from .monitor import write_monitor_health


@dataclass(frozen=True)
class PollResult:
    checked: int = 0
    fired: int = 0
    failed: int = 0
    pending: int = 0
    dispatched: int = 0
    requeued: int = 0
    submitted: int = 0
    signal_sources: tuple[dict[str, object], ...] = ()


def format_poll_result(result: PollResult) -> str:
    return (
        f"checked={result.checked} fired={result.fired} "
        f"failed={result.failed} pending={result.pending} "
        f"dispatched={result.dispatched} submitted={result.submitted} requeued={result.requeued}"
    )


def poll_result_has_activity(result: PollResult) -> bool:
    return any(
        (
            result.checked,
            result.fired,
            result.failed,
            result.dispatched,
            result.submitted,
            result.requeued,
        )
    )


def poll_result_dict(result: PollResult) -> dict[str, object]:
    return {
        "checked": result.checked,
        "fired": result.fired,
        "failed": result.failed,
        "pending": result.pending,
        "dispatched": result.dispatched,
        "submitted": result.submitted,
        "requeued": result.requeued,
        "signal_sources": list(getattr(result, "signal_sources", ())),
    }


def default_signal_runners(
    root: Path,
    runtime: SQLiteSignalModule,
    *,
    initial_reason: Literal["startup", "periodic"] = "startup",
    github_client_factory: Callable[[GitHubPollingConfig], GitHubReadClient] | None = None,
    systemd_backend_factory: Callable[[object], object] | None = None,
) -> tuple[SignalSourceRunner, ...]:
    """Reconstruct only configured source adapters referenced by durable arms."""

    from .filesystem_signals import FilesystemSignalAdapter, FilesystemSignalRunner
    from .github_client import GitHubRestClient

    adapters: dict[str, FilesystemSignalAdapter] = {}
    arms: list[ArmedSignal] = []
    github_arms: dict[str, list[ArmedSignal]] = {}
    process_adapters = {}
    process_arms: dict[str, list[ArmedSignal]] = {}
    systemd_arms: dict[str, list[ArmedSignal]] = {}
    for item in pending_records(root):
        if classify_record(item.record) != "signal_v2":
            continue
        wake_id = item.record.get("id")
        cwd = item.record.get("cwd")
        predicate = item.record.get("predicate")
        if not isinstance(wake_id, str) or not isinstance(cwd, str) or not isinstance(predicate, dict):
            continue
        source = predicate.get("source")
        source_instance = predicate.get("source_instance")
        if source == "systemd" and isinstance(source_instance, str):
            armed = runtime.load_armed_signal(wake_id)
            if (
                armed is not None
                and armed.spec.source == "systemd"
                and armed.spec.kind == "unit.active_state"
                and armed.spec.source_instance == source_instance
            ):
                systemd_arms.setdefault(source_instance, []).append(armed)
            continue
        if source == "runtime" and isinstance(source_instance, str):
            armed = runtime.load_armed_signal(wake_id)
            if (
                armed is not None
                and armed.spec.source == "runtime"
                and armed.spec.kind == "process.exit"
                and armed.spec.source_instance == source_instance
            ):
                try:
                    from .process_signals import restore_production_process_exit_adapter

                    adapter = restore_production_process_exit_adapter(armed)
                except (OSError, TypeError, ValueError):
                    continue
                existing = process_adapters.get(source_instance)
                if existing is not None and existing.descriptor != adapter.descriptor:
                    continue
                process_adapters[source_instance] = adapter
                process_arms.setdefault(source_instance, []).append(armed)
            continue
        if source == "github" and isinstance(source_instance, str):
            armed = runtime.load_armed_signal(wake_id)
            if armed is not None and armed.spec.source == "github":
                github_arms.setdefault(source_instance, []).append(armed)
            continue
        if source != "filesystem":
            continue
        subject = predicate.get("subject")
        if (
            not isinstance(subject, str)
            or not subject.startswith("path:")
            or not isinstance(source_instance, str)
        ):
            continue
        armed = runtime.load_armed_signal(wake_id)
        if armed is None:
            continue
        try:
            adapter = FilesystemSignalAdapter(
                Path(cwd),
                subject.removeprefix("path:"),
                source_instance=source_instance,
            )
        except ValueError:
            continue
        existing = adapters.get(source_instance)
        if existing is not None and (
            existing.root != adapter.root or existing.relative_path != adapter.relative_path
        ):
            continue
        adapters[source_instance] = adapter
        arms.append(armed)
    runners: list[SignalSourceRunner] = []
    if arms:
        runners.append(FilesystemSignalRunner(
            adapters.values(), armed_signals=arms, initial_reason=initial_reason
        ))
    for source_instance in sorted(process_arms):
        runners.append(process_adapters[source_instance].runner(process_arms[source_instance]))
    if systemd_arms:
        from .runtime_signals import RuntimeSourceRegistry
        from .systemd_signals import (
            SystemdReadCapability,
            SystemdSignalAdapter,
            SystemdSignalRunner,
            SystemdUserBusBackend,
        )
        from .systemd_source_config import SystemdSourceStore

        try:
            configuration_store = SystemdSourceStore(root)
            registry = configuration_store.registry()
            systemd_adapters = []
            referenced_arms = []
            for source_instance in sorted(systemd_arms):
                try:
                    source_config = registry.select(source_instance)
                    backend = (
                        systemd_backend_factory(source_config)
                        if systemd_backend_factory is not None
                        else SystemdUserBusBackend()
                    )
                    systemd_adapters.append(SystemdSignalAdapter(
                        source_config,
                        backend,
                        RuntimeSourceRegistry({
                            "systemd.unit": lambda descriptor, source_instance=source_instance: (
                                _configured_systemd_descriptor(
                                    configuration_store, source_instance, descriptor
                                )
                            )
                        }),
                        SystemdReadCapability("user", os.geteuid()),
                    ))
                except (OSError, TypeError, ValueError):
                    continue
                referenced_arms.extend(systemd_arms[source_instance])
            if systemd_adapters:
                runners.append(SystemdSignalRunner(
                    systemd_adapters,
                    armed_signals=tuple(referenced_arms),
                    initial_reason=initial_reason,
                ))
        except (OSError, TypeError, ValueError):
            pass
    if github_arms:
        store = GitHubSourceStore(root)
        try:
            registry = store.registry()
            github_adapters = {}
            referenced_arms = []
            for source_instance in sorted(github_arms):
                try:
                    selected = registry.select(source_instance)
                    client = (
                        github_client_factory(selected)
                        if github_client_factory is not None
                        else GitHubRestClient(
                            selected,
                            credential_resolver=lambda ref: os.environ.get(ref, ""),
                        )
                    )
                    github_adapters[source_instance] = GitHubPollingAdapter(
                        selected,
                        client,
                        previous_failure=store.retry_failure(source_instance),
                    )
                except (OSError, TypeError, ValueError):
                    continue
                referenced_arms.extend(github_arms[source_instance])
            if github_adapters:
                runners.append(
                    GitHubSignalRunner(
                        github_adapters,
                        armed_signals=tuple(referenced_arms),
                        health_store=store,
                    )
                )
        except (OSError, TypeError, ValueError):
            # A damaged or unsupported configuration cannot create network
            # authority. Other source classes remain available.
            pass
    return tuple(runners)


def _configured_systemd_descriptor(store, source_instance: str, descriptor) -> bool:
    try:
        current = store.registry().select(source_instance)
        return any(
            descriptor == current.descriptor(state)
            for state in current.target_states
        )
    except (OSError, TypeError, ValueError):
        return False


def _evaluate_signal(
    runtime: SQLiteSignalModule,
    armed: ArmedSignal,
    now: datetime,
    limits: EvaluationLimits,
    runners: tuple[SignalSourceRunner, ...],
):
    """Use a source-owned guard for runtime sources before publication."""

    if armed.spec.source not in {"runtime", "systemd"}:
        return runtime.evaluate(armed.wake_id, armed, now, limits), False
    for runner in runners:
        handles = getattr(runner, "handles", None)
        evaluate = getattr(runner, "evaluate", None)
        if not callable(handles) or not callable(evaluate):
            continue
        try:
            if handles(armed) is True:
                return evaluate(runtime, armed, now, limits), True
        except Exception:
            return Degraded(armed.wake_id, "RUNTIME_OBSERVATION_UNAVAILABLE", None), True
    return Degraded(armed.wake_id, "RUNTIME_SOURCE_UNSUPPORTED", None), True


class GitHubSignalRunner:
    """Poll referenced GitHub sources and commit only verified positive evidence."""

    def __init__(
        self,
        adapters: Mapping[str, GitHubPollingAdapter],
        *,
        armed_signals: tuple[ArmedSignal, ...],
        health_store: GitHubSourceStore,
    ) -> None:
        self._adapters = dict(adapters)
        self._armed_signals = armed_signals
        self._health_store = health_store

    def reconcile(
        self,
        module: SQLiteSignalModule,
        now: datetime,
        limits: EvaluationLimits,
    ) -> SourceReconcileResult:
        if now.tzinfo is None or now.utcoffset() is None or limits.max_candidates <= 0:
            return SourceReconcileResult("github", 0, 0, 1)
        groups: dict[str, list[ArmedSignal]] = {}
        for armed in self._armed_signals:
            adapter = self._adapters.get(armed.spec.source_instance)
            if armed.spec.source != "github" or adapter is None:
                continue
            groups.setdefault(armed.spec.source_instance, []).append(armed)
        scanned = observed = degraded = 0
        instances: list[SourceInstanceReconcileResult] = []
        for source_instance in sorted(groups)[: limits.max_candidates]:
            source_arms = groups[source_instance]
            scanned += 1
            adapter = self._adapters[source_instance]
            earliest = min(source_arms, key=lambda item: item.registered_at)
            checkpoint = module.source_checkpoint("github", source_instance)
            if isinstance(checkpoint, Degraded):
                outcome: object = checkpoint
            else:
                outcome = adapter.observe(earliest.anchor, checkpoint=checkpoint, now=now)
            instance_observed = 0
            instance_degraded = 0
            health = None
            if isinstance(outcome, PollBatch):
                ingested = module.ingest(outcome.observations, outcome.commit)
                if isinstance(ingested, Ingested):
                    instance_observed = len(outcome.observations)
                    health = outcome.health
                else:
                    health = ingested if isinstance(ingested, Degraded) else Degraded(None, "STORE_UNAVAILABLE", None)
            else:
                health = outcome if isinstance(outcome, Degraded) else Degraded(None, "GITHUB_SOURCE_UNAVAILABLE", None)
            if health is not None:
                instance_degraded = 1
                try:
                    self._health_store.record_health(source_instance, health, observed_at=now)
                except (OSError, TypeError, ValueError):
                    instance_degraded = 1
            observed += instance_observed
            degraded += instance_degraded
            instances.append(
                SourceInstanceReconcileResult(
                    "github", source_instance, 1, instance_observed, instance_degraded
                )
            )
        return SourceReconcileResult(
            "github", scanned, observed, degraded, tuple(instances)
        )


def pending_records(root: Path) -> list[WakePath]:
    return [item for item in iter_records(root) if item.record.get("status") == "pending"]


def firing_records(root: Path) -> list[WakePath]:
    return [item for item in iter_records(root) if item.record.get("status") == "firing"]


def next_attempt_is_due(record: dict, now: datetime) -> tuple[bool, str]:
    next_attempt = record.get("next_attempt_at")
    if not isinstance(next_attempt, str) or not next_attempt:
        return True, ""
    try:
        due_at = parse_utc_timestamp(next_attempt)
    except WakeError:
        return True, ""
    if due_at > now:
        return False, next_attempt
    return True, next_attempt


def predicate_is_ready(record: dict, now: datetime) -> tuple[bool, str]:
    result = BuiltinPredicateSignals().evaluate(record, now)
    return result.ready, result.message


def poll_once(
    root: Path,
    now: datetime | None = None,
    *,
    dispatch: bool = True,
    runner: TmuxRunner | None = None,
    ack_timeout_override: float | None = None,
    signal_runtime: SQLiteSignalModule | None = None,
    signal_runners: tuple[SignalSourceRunner, ...] = (),
    signal_reconcile_reason: Literal["startup", "periodic"] = "startup",
) -> PollResult:
    current = now or utc_now()
    checked = fired = failed = pending = dispatched = requeued = submitted = 0
    if signal_runtime is None:
        journal = signal_journal_path(root)
        if journal.is_file():
            try:
                signal_runtime = SQLiteSignalModule.open_existing(
                    journal,
                    record_publisher=WakeRecordPublisher(
                        root,
                        current_reader_capability(root),
                    ),
                )
            except Exception:
                signal_runtime = None
    if signal_runtime is not None:
        if not signal_runners:
            signal_runners = default_signal_runners(
                root, signal_runtime, initial_reason=signal_reconcile_reason
            )
        firing_before = {item.record.get("id") for item in firing_records(root)}
        signal_runtime.reconcile_publications(limit=100, include_matches=False)
        firing_after = {item.record.get("id") for item in firing_records(root)}
        fired += len(firing_after - firing_before)
        signal_source_health: list[dict[str, object]] = []
        for source_runner in signal_runners:
            try:
                source_result = source_runner.reconcile(signal_runtime, current, EvaluationLimits(100))
                if source_result.instances:
                    signal_source_health.extend(
                        {
                            "source": item.source,
                            "source_instance": item.source_instance,
                            "scope": "instance",
                            "scanned": item.scanned,
                            "observed": item.observed,
                            "degraded": item.degraded,
                        }
                        for item in source_result.instances
                    )
                else:
                    signal_source_health.append(
                        {
                            "source": source_result.source,
                            "source_instance": "",
                            "scope": "aggregate",
                            "scanned": source_result.scanned,
                            "observed": source_result.observed,
                            "degraded": source_result.degraded,
                        }
                    )
            except Exception:
                # Source adapters fail closed. Wake evaluation below remains
                # available for already committed observations and v1 records.
                continue
    else:
        signal_source_health = []
    terminal_signal_ids: set[str] = set()
    if signal_runtime is not None:
        for terminal in iter_records(root):
            status = terminal.record.get("status")
            wake_id = terminal.record.get("id")
            if (
                classify_record(terminal.record) == "signal_v2"
                and status in {"submitted", "failed", "cancelled", "expired", "archived"}
                and isinstance(wake_id, str)
            ):
                terminal_signal_ids.add(wake_id)
                signal_runtime.retire_terminal_record(terminal.record, now=current)
    for item in pending_records(root):
        checked += 1
        classification = classify_record(item.record)
        if classification == "hold":
            pending += 1
            continue
        if classification == "signal_v2":
            if signal_runtime is None:
                pending += 1
                continue
            wake_id = item.record.get("id")
            if wake_id in terminal_signal_ids:
                pending += 1
                continue
            with WakeLifecycleLock(root, wake_id):
                try:
                    current_item = find_record(root, wake_id)
                except WakeError:
                    continue
                if (
                    classify_record(current_item.record) != "signal_v2"
                    or current_item.record.get("status") != "pending"
                ):
                    continue
                armed = signal_runtime.load_armed_signal(wake_id)
                if armed is None:
                    terminal_status = signal_runtime.terminal_status(wake_id)
                    if terminal_status in {"cancelled", "expired", "failed", "submitted"}:
                        move_record(
                            root,
                            current_item,
                            terminal_status,
                            event_type=terminal_status,
                            message=f"Signal wake reconciled to durable {terminal_status} state",
                            now=current,
                        )
                    else:
                        pending += 1
                    continue
                outcome, source_publishes = _evaluate_signal(
                    signal_runtime,
                    armed,
                    current,
                    EvaluationLimits(100),
                    signal_runners,
                )
                if isinstance(outcome, Matched):
                    if not source_publishes:
                        signal_runtime.reconcile_match_publication(wake_id)
                    if (root / "firing" / f"{wake_id}.json").is_file():
                        fired += 1
                    else:
                        pending += 1
                elif isinstance(outcome, Expired):
                    expired = signal_runtime.expire_unreserved(wake_id, now=current)
                    if expired is True:
                        move_record(
                            root,
                            current_item,
                            "expired",
                            event_type="expired",
                            message="Signal wake expired before a match was reserved",
                            now=current,
                        )
                    else:
                        pending += 1
                else:
                    pending += 1
            continue
        due_for_attempt, _next_attempt = next_attempt_is_due(item.record, current)
        if not due_for_attempt:
            pending += 1
            continue
        try:
            ready, message = predicate_is_ready(item.record, current)
        except WakeError as exc:
            move_record(
                root,
                item,
                "failed",
                event_type="failed",
                message=str(exc),
                now=current,
                last_error=str(exc),
            )
            failed += 1
            continue
        if ready:
            move_record(
                root,
                item,
                "firing",
                event_type="predicate_matched",
                message=message,
                now=current,
            )
            fired += 1
        else:
            pending += 1
    if dispatch:
        for item in firing_records(root):
            result = dispatch_firing_record(
                root,
                item,
                runner=runner,
                now=current,
                ack_timeout_override=ack_timeout_override,
                signal_authorizer=(
                    signal_runtime.authorize_firing_record
                    if signal_runtime is not None
                    else None
                ),
            )
            if result.status == "skipped":
                continue
            dispatched += 1
            if result.status == "submitted":
                submitted += 1
            elif result.status == "requeued":
                requeued += 1
            elif result.status == "failed":
                failed += 1
    return PollResult(
        checked=checked,
        fired=fired,
        failed=failed,
        pending=pending,
        dispatched=dispatched,
        requeued=requeued,
        submitted=submitted,
        signal_sources=tuple(signal_source_health),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-waked")
    parser.add_argument(
        "--wake-root",
        type=Path,
        default=None,
        help="wake runtime root; defaults to .codex/wake under the current directory",
    )
    parser.add_argument("--once", action="store_true", help="run one polling pass and exit")
    parser.add_argument("--interval", type=float, default=5.0, help="poll interval in seconds")
    parser.add_argument("--no-dispatch", action="store_true", help="evaluate predicates but do not dispatch firing records")
    parser.add_argument(
        "--ack-timeout",
        type=float,
        default=None,
        help="override ack wait timeout in seconds",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = (args.wake_root or default_wake_root()).resolve()
    if args.once:
        result = poll_once(root, dispatch=not args.no_dispatch, ack_timeout_override=args.ack_timeout)
        write_monitor_health(
            wake_root=root,
            repo_root=Path.cwd(),
            source="codex-waked",
            mode="once",
            poll_result=poll_result_dict(result),
        )
        print(format_poll_result(result))
        return 0
    if args.interval <= 0:
        raise WakeError("--interval must be greater than zero")
    signal_reconcile_reason: Literal["startup", "periodic"] = "startup"
    while True:
        result = poll_once(
            root,
            dispatch=not args.no_dispatch,
            ack_timeout_override=args.ack_timeout,
            signal_reconcile_reason=signal_reconcile_reason,
        )
        signal_reconcile_reason = "periodic"
        write_monitor_health(
            wake_root=root,
            repo_root=Path.cwd(),
            source="codex-waked",
            mode="loop",
            poll_result=poll_result_dict(result),
        )
        if poll_result_has_activity(result):
            print(format_poll_result(result), flush=True)
        time.sleep(args.interval)


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except WakeError as exc:
        print(f"codex-waked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
