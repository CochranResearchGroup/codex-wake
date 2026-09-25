"""Bounded GitHub CI observation with an injected, read-only provider client.

The fixture history contract and production positive-only contract are
distinct. Exhausted REST pages never prove completeness; terminal proof times
are explicit lower bounds, never mutable run updated_at timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import re
from types import MappingProxyType
from typing import Protocol

from .signals import (
    Degraded, Eq, In, Ingested, Invalid, NormalizedObservation, SignalEngine,
    SignalRequest, SourceAnchor, SourceCommit, SourceContract, Verification,
)


@dataclass(frozen=True, slots=True)
class GitHubPollingConfig:
    source_instance: str
    repository: str
    repository_id: int
    workflow_id: int
    refs: frozenset[str]
    conclusions: frozenset[str]
    credential_ref: str
    permissions: frozenset[str] = frozenset({"actions:read", "metadata:read"})
    page_size: int = 50
    max_pages: int = 10
    overlap_seconds: int = 60
    max_history_seconds: int = 86400
    retry_seconds: int = 30
    hostname: str = "github.com"
    enabled: bool = True
    evidence_mode: str = "complete_history"
    max_requests: int = 200
    max_response_bytes: int = 1048576
    max_poll_bytes: int = 8388608
    request_timeout_seconds: int = 10
    poll_timeout_seconds: int = 30


@dataclass(frozen=True, slots=True)
class WorkflowRun:
    repository: str
    repository_id: int
    workflow_id: int
    run_id: int
    run_attempt: int
    ref: str
    head_sha: str
    status: str
    conclusion: str | None
    completed_at: datetime | None
    terminal_proof_at: datetime | None = None
    time_provenance: str = "authoritative_completed_at"


@dataclass(frozen=True, slots=True)
class RunQuery:
    repository: str
    repository_id: int
    workflow_id: int
    refs: tuple[str, ...]
    since: datetime
    until: datetime
    page: int
    per_page: int


@dataclass(frozen=True, slots=True)
class RunPage:
    """Trusted transport coverage, never inferred from a GitHub page length.

    Every page covers one fixed query window. The last page attests that all
    terminal attempts in [covered_from, covered_through] were enumerated.
    A transport unable to establish that guarantee must return no coverage.
    """
    runs: tuple[WorkflowRun, ...]
    next_page: int | None
    covered_from: datetime | None
    covered_through: datetime | None


class GitHubReadClient(Protocol):
    def list_runs(self, query: RunQuery) -> RunPage: ...

    def get_run_attempt(self, repository: str, run_id: int, run_attempt: int) -> WorkflowRun: ...


class CheckpointReader(Protocol):
    def source_checkpoint(self, source: str, source_instance: str) -> SourceCommit | Degraded | None: ...


class GitHubReadError(Exception):
    """Sanitized transport category; never carries a response body or token."""

    def __init__(self, kind: str, *, retry_at: datetime | None = None):
        super().__init__("GitHub read failed")
        self.kind = kind if kind in {"auth", "rate_limit", "unavailable", "malformed", "budget"} else "unavailable"
        self.retry_at = retry_at if _aware(retry_at) else None


@dataclass(frozen=True, slots=True)
class PollBatch:
    observations: tuple[NormalizedObservation, ...]
    commit: SourceCommit
    coverage: str = "complete_history"
    health: Degraded | None = None


class GitHubPollingAdapter:
    def __init__(self, config: GitHubPollingConfig, client: GitHubReadClient, *, previous_failure: Degraded | None = None):
        if not _valid_config(config) or not config.enabled:
            raise ValueError("GitHub polling configuration is invalid")
        self.config = config
        self._client = client
        # A runner restores this from its durable source-health record. It is
        # separate from the committed receipt cursor, which never advances on
        # failure. This module does not invent a second checkpoint store.
        if previous_failure is not None and (
            not isinstance(previous_failure, Degraded)
            or previous_failure.code not in {"GITHUB_AUTH_UNAVAILABLE", "GITHUB_RATE_LIMITED", "GITHUB_SOURCE_UNAVAILABLE", "GITHUB_VERIFICATION_FAILED", "GITHUB_RESPONSE_INVALID", "GITHUB_POLL_BUDGET_EXHAUSTED"}
            or not _aware(previous_failure.retry_at)
            or previous_failure.evidence_ref is not None
        ):
            raise ValueError("GitHub retry state is invalid")
        self._last_failure = previous_failure

    def contract(self) -> SourceContract:
        attributes = {"workflow_id": int, "ref": str, "conclusion": str,
                      "run_id": int, "run_attempt": int, "head_sha": str, self._order_attribute(): int}
        if self.config.evidence_mode == "positive_only":
            attributes["time_provenance"] = str
        return SourceContract(
            "github", self.config.source_instance, frozenset({"workflow_run.completed"}),
            frozenset({"repo:" + self.config.repository}),
            MappingProxyType(attributes),
            max_clauses=3, max_in_values=8, max_attribute_bytes=1024,
            max_evidence_ref_bytes=256,
            occurrence_order_attribute=self._order_attribute(),
        )

    def request(self, *, ref: str, conclusions: tuple[str, ...]) -> SignalRequest | Invalid:
        if (not isinstance(ref, str) or ref not in self.config.refs or type(conclusions) is not tuple
                or not 0 < len(conclusions) <= 8 or not all(isinstance(item, str) for item in conclusions)
                or not set(conclusions) <= self.config.conclusions):
            return Invalid(None, "GITHUB_SIGNAL_NOT_ALLOWED", ("GitHub signal is outside the configured allowlist",))
        return SignalRequest(
            1, "github", self.config.source_instance, "occurrence", "workflow_run.completed",
            "repo:" + self.config.repository, "occurs",
            (Eq("workflow_id", self.config.workflow_id), Eq("ref", ref), In("conclusion", tuple(sorted(set(conclusions))))),
            "required",
        )

    def establish_anchor(self, spec: SignalRequest, now: datetime) -> SourceAnchor | Invalid:
        if not self._valid_request(spec) or not _aware(now):
            return Invalid(None, "GITHUB_SIGNAL_NOT_ALLOWED", ("GitHub signal is outside the configured allowlist",))
        return SourceAnchor(0, self._cursor(now), {self._order_attribute(): _order(now)}, "source_replay")

    def observe(self, anchor: SourceAnchor, *, checkpoint: SourceCommit | None, now: datetime) -> PollBatch | Degraded | Invalid:
        if not _aware(now):
            return Invalid(None, "GITHUB_CLOCK_INVALID", ("GitHub observation requires an aware clock",))
        if self._last_failure and self._last_failure.retry_at and now < self._last_failure.retry_at:
            return self._last_failure
        result = self._observe(anchor, checkpoint=checkpoint, now=now)
        self._last_failure = result if isinstance(result, Degraded) else None
        return result

    def _observe(self, anchor: SourceAnchor, *, checkpoint: SourceCommit | None, now: datetime) -> PollBatch | Degraded | Invalid:
        try:
            cutoff = self._parse_cursor(anchor.source_anchor)
            if (anchor.recovery != "source_replay" or type(anchor.local_after_sequence) is not int
                    or anchor.local_after_sequence < 0 or set(anchor.baseline) != {self._order_attribute()}
                    or type(anchor.baseline[self._order_attribute()]) is not int
                    or anchor.baseline[self._order_attribute()] != _order(cutoff)):
                raise ValueError("incompatible anchor")
        except (AttributeError, KeyError, TypeError, ValueError):
            return Invalid(None, "GITHUB_ANCHOR_INVALID", ("GitHub anchor is incompatible",))
        try:
            since = cutoff
            if checkpoint is not None:
                if (checkpoint.source, checkpoint.source_instance) != ("github", self.config.source_instance):
                    raise ValueError("incompatible checkpoint")
                previous = self._parse_cursor(checkpoint.checkpoint)
                if (type(checkpoint.checkpoint_order) is not int or checkpoint.checkpoint_order != _order(previous)
                        or checkpoint.observed_through != previous or now < previous):
                    raise ValueError("incompatible checkpoint")
                if self.config.evidence_mode == "positive_only" and checkpoint.checkpoint_order != 0:
                    raise ValueError("unproven coverage")
                since = max(cutoff, previous - timedelta(seconds=self.config.overlap_seconds))
        except (AttributeError, KeyError, TypeError, ValueError):
            return Invalid(None, "GITHUB_CHECKPOINT_INVALID", ("GitHub checkpoint is incompatible",))
        try:
            if now < since or now - since > timedelta(seconds=self.config.max_history_seconds):
                return Degraded(None, "GITHUB_HISTORY_GAP", None)
            observations = {}
            page = 1
            for _ in range(self.config.max_pages):
                result = self._client.list_runs(RunQuery(
                    self.config.repository, self.config.repository_id, self.config.workflow_id,
                    tuple(sorted(self.config.refs)), since, now, page, self.config.page_size,
                ))
                if not _valid_page(result, self.config.page_size):
                    return Degraded(None, "GITHUB_RESPONSE_INVALID", None)
                for candidate in result.runs:
                    if not _valid_run(candidate):
                        return Degraded(None, "GITHUB_RESPONSE_INVALID", None)
                    if not self._bound_run(candidate):
                        continue
                    if self.config.evidence_mode == "positive_only":
                        # REST lists only the latest attempt. Re-read each exact
                        # attempt under the client's shared poll request budget.
                        if candidate.run_attempt > self.config.max_requests:
                            return Degraded(None, "GITHUB_POLL_BUDGET_EXHAUSTED", None)
                        for attempt in range(1, candidate.run_attempt + 1):
                            verified = self._client.get_run_attempt(self.config.repository, candidate.run_id, attempt)
                            if (not _valid_run(verified) or verified.run_attempt != attempt
                                    or any(getattr(verified, key) != getattr(candidate, key) for key in
                                           ("repository", "repository_id", "workflow_id", "run_id", "ref", "head_sha"))):
                                return Degraded(None, "GITHUB_VERIFICATION_FAILED", None)
                            if not self._allowed_run(verified):
                                continue
                            if (verified.time_provenance != "github_attempt_started_or_job_completed_lower_bound"
                                    or not _aware(verified.terminal_proof_at)):
                                return Degraded(None, "GITHUB_VERIFICATION_FAILED", None)
                            if not cutoff < verified.terminal_proof_at <= now:
                                continue
                            observation = self.normalize_verified_attempt(verified)
                            if isinstance(observation, Invalid):
                                return Degraded(None, "GITHUB_VERIFICATION_FAILED", None)
                            key = observation.occurrence_value
                            if key in observations and observations[key] != observation:
                                return Degraded(None, "GITHUB_VERIFICATION_FAILED", None)
                            observations[key] = observation
                        continue
                    if candidate.completed_at is None:
                        continue
                    if not self._allowed_run(candidate):
                        continue
                    if not since <= candidate.completed_at <= now or candidate.completed_at <= cutoff:
                        continue
                    verified = self._client.get_run_attempt(self.config.repository, candidate.run_id, candidate.run_attempt)
                    if not _valid_run(verified) or verified != candidate:
                        return Degraded(None, "GITHUB_VERIFICATION_FAILED", now + timedelta(seconds=self.config.retry_seconds))
                    observation = self.normalize_verified_attempt(verified)
                    if isinstance(observation, Invalid):
                        return Degraded(None, "GITHUB_VERIFICATION_FAILED", None)
                    key = observation.occurrence_value
                    if key in observations and observations[key] != observation:
                        return Degraded(None, "GITHUB_VERIFICATION_FAILED", None)
                    observations[key] = observation
                if self.config.evidence_mode == "positive_only" and observations:
                    ordered = tuple(sorted(observations.values(), key=lambda item: (item.occurred_at, item.occurrence_value)))
                    return PollBatch(ordered, self.checkpoint_for_anchor(anchor), "positive_only",
                                     Degraded(None, "GITHUB_COVERAGE_UNPROVEN", None))
                if result.next_page is None:
                    if self.config.evidence_mode == "positive_only":
                        ordered = tuple(sorted(observations.values(), key=lambda item: (item.occurred_at, item.occurrence_value)))
                        return PollBatch(ordered, self.checkpoint_for_anchor(anchor), "positive_only",
                                         Degraded(None, "GITHUB_COVERAGE_UNPROVEN", None))
                    if result.covered_from is None or result.covered_through is None or result.covered_from > since or result.covered_through < now:
                        return Degraded(None, "GITHUB_HISTORY_GAP", None)
                    ordered = tuple(sorted(observations.values(), key=lambda item: (item.occurred_at, item.occurrence_value)))
                    return PollBatch(ordered, SourceCommit("github", self.config.source_instance, self._cursor(now), _order(now), now))
                if result.next_page != page + 1:
                    return Degraded(None, "GITHUB_PAGINATION_INVALID", None)
                page = result.next_page
            return Degraded(None, "GITHUB_POLL_BUDGET_EXHAUSTED", None)
        except GitHubReadError as error:
            code = {"auth": "GITHUB_AUTH_UNAVAILABLE", "rate_limit": "GITHUB_RATE_LIMITED",
                    "unavailable": "GITHUB_SOURCE_UNAVAILABLE", "malformed": "GITHUB_RESPONSE_INVALID",
                    "budget": "GITHUB_POLL_BUDGET_EXHAUSTED"}[error.kind]
            retry_at = max(now + timedelta(seconds=self.config.retry_seconds), error.retry_at or now)
            return Degraded(None, code, retry_at)
        except Exception:
            return Degraded(None, "GITHUB_SOURCE_UNAVAILABLE", now + timedelta(seconds=self.config.retry_seconds))

    def poll_into(self, module: SignalEngine, anchor: SourceAnchor, *, checkpoints: CheckpointReader, now: datetime) -> Ingested | Degraded | Invalid:
        try:
            checkpoint = checkpoints.source_checkpoint("github", self.config.source_instance)
        except Exception:
            return Degraded(None, "STORE_UNAVAILABLE", None)
        if isinstance(checkpoint, Degraded):
            return checkpoint
        batch = self.observe(anchor, checkpoint=checkpoint, now=now)
        if not isinstance(batch, PollBatch):
            return batch
        return module.ingest(batch.observations, batch.commit)

    def _valid_request(self, spec: SignalRequest) -> bool:
        try:
            if type(spec) is not SignalRequest or type(spec.where) is not tuple or len(spec.where) != 3:
                return False
            workflow, ref, conclusion = spec.where
            if type(workflow) is not Eq or type(ref) is not Eq or type(conclusion) is not In:
                return False
            fields = (
                (spec.source, "github"), (spec.source_instance, self.config.source_instance),
                (spec.semantics, "occurrence"), (spec.kind, "workflow_run.completed"),
                (spec.subject, "repo:" + self.config.repository), (spec.condition, "occurs"),
                (spec.verification, "required"), (workflow.field, "workflow_id"),
                (ref.field, "ref"), (conclusion.field, "conclusion"),
            )
            if any(type(value) is not str or type(expected) is not str or value != expected for value, expected in fields):
                return False
            if (type(spec.contract_version) is not int or spec.contract_version != 1
                    or type(workflow.value) is not int or workflow.value != self.config.workflow_id
                    or type(ref.value) is not str or ref.value not in self.config.refs
                    or type(conclusion.values) is not tuple or not 0 < len(conclusion.values) <= 8
                    or any(type(value) is not str for value in conclusion.values)):
                return False
            return (set(conclusion.values) <= self.config.conclusions
                    and conclusion.values == tuple(sorted(set(conclusion.values))))
        except (AttributeError, TypeError, ValueError):
            return False

    def _allowed_run(self, run: WorkflowRun) -> bool:
        return (self._bound_run(run) and run.status == "completed" and run.conclusion in self.config.conclusions)

    def _bound_run(self, run: WorkflowRun) -> bool:
        return (run.repository == self.config.repository and run.repository_id == self.config.repository_id
                and run.workflow_id == self.config.workflow_id and run.ref in self.config.refs)

    def checkpoint_for_anchor(self, anchor: SourceAnchor) -> SourceCommit | Invalid:
        """Validate source binding and seed an explicit no-coverage checkpoint.

        An arbitrary arm's cutoff is not source-wide polling coverage: older
        arms may still need earlier history. Epoch/order zero preserves each
        polling anchor's recovery floor without inventing coverage.
        """
        try:
            if type(anchor) is not SourceAnchor:
                raise ValueError("incompatible anchor")
            cutoff = self._parse_cursor(anchor.source_anchor)
            if (anchor.recovery != "source_replay"
                    or type(anchor.local_after_sequence) is not int or anchor.local_after_sequence < 0
                    or set(anchor.baseline) != {self._order_attribute()}
                    or type(anchor.baseline[self._order_attribute()]) is not int
                    or anchor.baseline[self._order_attribute()] != _order(cutoff)):
                raise ValueError("incompatible anchor")
            epoch = datetime(1970, 1, 1, tzinfo=UTC)
            return SourceCommit("github", self.config.source_instance, self._cursor(epoch), 0, epoch)
        except (AttributeError, KeyError, TypeError, ValueError):
            return Invalid(None, "GITHUB_ANCHOR_INVALID", ("GitHub anchor is incompatible",))

    def normalize_verified_attempt(self, run: WorkflowRun) -> NormalizedObservation | Invalid:
        """Normalize an authoritative attempt read; callers own read provenance."""
        if not _valid_run(run) or not self._allowed_run(run):
            return Invalid(None, "GITHUB_SIGNAL_NOT_ALLOWED", ("GitHub attempt is outside the configured allowlist",))
        at = run.terminal_proof_at if self.config.evidence_mode == "positive_only" else run.completed_at
        expected = ("github_attempt_started_or_job_completed_lower_bound"
                    if self.config.evidence_mode == "positive_only" else "authoritative_completed_at")
        if not _aware(at) or run.time_provenance != expected:
            return Invalid(None, "GITHUB_TIME_PROVENANCE_INVALID", ("GitHub attempt time is unsupported",))
        attributes = {"workflow_id": run.workflow_id, "ref": run.ref, "conclusion": run.conclusion,
                      "run_id": run.run_id, "run_attempt": run.run_attempt, "head_sha": run.head_sha,
                      self._order_attribute(): _order(at)}
        if self.config.evidence_mode == "positive_only":
            attributes["time_provenance"] = run.time_provenance
        return NormalizedObservation(
            "github", self.config.source_instance, "workflow_run.completed", "repo:" + self.config.repository,
            "github.workflow_run.attempt.completed", f"{run.repository_id}:{run.run_id}:{run.run_attempt}",
            at, at,
            MappingProxyType(attributes),
            Verification("verified", "github-run-attempt-read"),
            f"github:repository:{run.repository_id}:run:{run.run_id}:attempt:{run.run_attempt}",
        )

    def _cursor(self, at: datetime) -> str:
        return json.dumps({"version": 1, "config": self._identity(), "through": _time(at)}, sort_keys=True, separators=(",", ":"))

    def _parse_cursor(self, value: str) -> datetime:
        if not isinstance(value, str) or len(value) > 512:
            raise ValueError("incompatible checkpoint")
        payload = json.loads(value)
        if (type(payload) is not dict or set(payload) != {"version", "config", "through"}
                or type(payload["version"]) is not int or payload["version"] != 1
                or payload["config"] != self._identity()):
            raise ValueError("incompatible checkpoint")
        at = datetime.fromisoformat(payload["through"])
        if not _aware(at):
            raise ValueError("incompatible checkpoint")
        return at

    def _identity(self) -> str:
        value = [self.config.source_instance, self.config.repository, self.config.repository_id,
                 self.config.workflow_id, sorted(self.config.refs), sorted(self.config.conclusions)]
        if self.config.evidence_mode == "positive_only":
            value.extend([self.config.hostname, self.config.evidence_mode])
        return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()

    def _order_attribute(self) -> str:
        return "terminal_proof_at_us" if self.config.evidence_mode == "positive_only" else "completed_at_us"


def _time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _valid_config(config: GitHubPollingConfig) -> bool:
    try:
        return bool(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", config.source_instance)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}", config.repository)
            and all(type(value) is int and 0 < value < 2**63 for value in (config.repository_id, config.workflow_id))
            and type(config.refs) is frozenset and 0 < len(config.refs) <= 16
            and all(_valid_ref(ref) for ref in config.refs)
            and type(config.conclusions) is frozenset and bool(config.conclusions)
            and config.conclusions <= {"success", "failure", "cancelled", "timed_out", "neutral", "skipped", "action_required", "startup_failure"}
            and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", config.credential_ref)
            and type(config.permissions) is frozenset
            and config.permissions == {"actions:read", "metadata:read"}
            and all(type(value) is int and low <= value <= high for value, low, high in (
                (config.page_size, 1, 100), (config.max_pages, 1, 100),
                (config.overlap_seconds, 1, 3600), (config.max_history_seconds, 60, 604800),
                (config.retry_seconds, 1, 3600),
            ))
            and config.overlap_seconds <= config.max_history_seconds
            and config.hostname == "github.com"
            and type(config.enabled) is bool
            and config.evidence_mode in {"complete_history", "positive_only"}
            and (config.evidence_mode != "positive_only" or all(ref.startswith("refs/heads/") for ref in config.refs))
            and all(type(value) is int and low <= value <= high for value, low, high in (
                (config.max_requests, 1, 1000), (config.max_response_bytes, 1024, 10485760),
                (config.max_poll_bytes, 1024, 104857600),
                (config.request_timeout_seconds, 1, 60), (config.poll_timeout_seconds, 1, 300),
            ))
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _valid_ref(ref: str) -> bool:
    return bool(isinstance(ref, str) and len(ref) <= 255
                and re.fullmatch(r"refs/(heads|tags)/[A-Za-z0-9_][A-Za-z0-9_./-]*", ref)
                and not any(part in ref for part in ("..", "//", "/.", "@{"))
                and not ref.endswith(("/", ".", ".lock")))


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _valid_run(run: WorkflowRun) -> bool:
    try:
        return bool(
            type(run) is WorkflowRun
            and isinstance(run.repository, str) and len(run.repository) <= 140
            and all(type(value) is int and 0 < value < 2**63 for value in
                    (run.repository_id, run.workflow_id, run.run_id, run.run_attempt))
            and _valid_ref(run.ref)
            and isinstance(run.head_sha, str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", run.head_sha)
            and run.status in {"queued", "in_progress", "waiting", "requested", "pending", "completed"}
            and (run.conclusion is None or (isinstance(run.conclusion, str) and len(run.conclusion) <= 32))
            and (run.completed_at is None or _aware(run.completed_at))
            and (run.terminal_proof_at is None or _aware(run.terminal_proof_at))
            and run.time_provenance in {"authoritative_completed_at", "github_attempt_started_or_job_completed_lower_bound"}
            and (run.status != "completed" or (run.conclusion is not None
                 and (run.completed_at is not None or run.terminal_proof_at is not None)))
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _valid_page(page: RunPage, limit: int) -> bool:
    return bool(type(page) is RunPage and type(page.runs) is tuple and len(page.runs) <= limit
                and (page.next_page is None or (type(page.next_page) is int and page.next_page > 0))
                and (page.covered_from is None or _aware(page.covered_from))
                and (page.covered_through is None or _aware(page.covered_through)))


def _order(value: datetime) -> int:
    delta = value.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
