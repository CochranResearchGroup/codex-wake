"""Transport-neutral signed GitHub hints, verified and committed before ACK.

No listener, HTTP client, credential loading, evaluator, or dispatcher lives
here. One ingress represents one configured source. A future transport must
preserve exact bytes and provide bounded read/lookup deadlines.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import re
import math
import threading
import time
from typing import BinaryIO

from .github_polling import CheckpointReader, GitHubPollingAdapter, GitHubReadClient, WorkflowRun
from .signals import Degraded, Ingested, Invalid, SignalEngine, SourceAnchor


@dataclass(frozen=True, slots=True)
class WebhookConfig:
    secret_refs: tuple[str, ...]
    secret_generations: tuple[int, ...] = ()
    max_body_bytes: int = 262144
    max_age_seconds: int = 900
    future_skew_seconds: int = 30
    requests_per_window: int = 120
    window_seconds: int = 60
    delivery_cache_size: int = 256


@dataclass(frozen=True, slots=True)
class WebhookResult:
    status: int
    code: str


class GitHubWebhookIngress:
    def __init__(self, adapter: GitHubPollingAdapter, client: GitHubReadClient, module: SignalEngine, *,
                 checkpoints: CheckpointReader, anchor: SourceAnchor, config: WebhookConfig,
                 resolve_secret: Callable[[str], bytes], monotonic: Callable[[], float] = time.monotonic,
                 admitted_generations: Callable[[datetime], tuple[int, ...]] | None = None,
                 committed_delivery: Callable[[int, str], None] | None = None):
        if (type(config) is not WebhookConfig or type(config.secret_refs) is not tuple
                or not 1 <= len(config.secret_refs) <= 2
                or not all(type(ref) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", ref)
                           for ref in config.secret_refs)
                or len(set(config.secret_refs)) != len(config.secret_refs)
                or type(config.secret_generations) is not tuple
                or config.secret_generations and (
                    len(config.secret_generations) != len(config.secret_refs)
                    or len(set(config.secret_generations)) != len(config.secret_generations)
                    or not all(type(item) is int and 1 <= item < 2**31 for item in config.secret_generations)
                )
                or (admitted_generations is None) != (committed_delivery is None)
                or admitted_generations is not None and (
                    not config.secret_generations or not callable(admitted_generations) or not callable(committed_delivery)
                )
                or any(type(value) is not int or not low <= value <= high for value, low, high in (
                    (config.max_body_bytes, 1024, 1048576), (config.max_age_seconds, 1, 86400),
                    (config.future_skew_seconds, 0, 300), (config.requests_per_window, 1, 10000),
                    (config.window_seconds, 1, 3600), (config.delivery_cache_size, 1, 4096)))):
            raise ValueError("GitHub webhook configuration is invalid")
        self.adapter = adapter
        self.client = client
        self.module = module
        self.checkpoints = checkpoints
        self.anchor = anchor
        self.config = config
        self.resolve_secret = resolve_secret
        self.admitted_generations = admitted_generations
        self.committed_delivery = committed_delivery
        self._monotonic = monotonic
        self._inflight = threading.Lock()
        self._window_start = None
        self._requests = 0
        # Unsigned delivery IDs are only bounded transport diagnostics. Durable
        # replay safety belongs to the journal's repository/run/attempt identity.
        self._deliveries: OrderedDict[str, str] = OrderedDict()

    def ingest(self, body: bytes | BinaryIO, headers: Mapping[str, str], *, now: datetime) -> WebhookResult:
        """Return success only after journal ingest; admit one call, queue none.

        Admission budgets are per ingress instance/process. A deployment must
        keep one owner per source and enforce shared ingress budgets if scaled.
        No wake enumeration, evaluation, or dispatch occurs in this path.
        """
        if not self._inflight.acquire(blocking=False):
            return WebhookResult(503, "BUSY")
        try:
            tick = self._monotonic()
            if type(tick) not in (int, float) or not math.isfinite(tick):
                return WebhookResult(503, "CLOCK_UNAVAILABLE")
            if self._window_start is None:
                self._window_start = tick
            if tick < self._window_start:
                return WebhookResult(503, "CLOCK_UNAVAILABLE")
            if tick - self._window_start >= self.config.window_seconds:
                self._window_start, self._requests = tick, 0
            if self._requests >= self.config.requests_per_window:
                return WebhookResult(429, "RATE_LIMITED")
            self._requests += 1
            return self._ingest(body, headers, now=now)
        except Exception:
            return WebhookResult(503, "INGRESS_UNAVAILABLE")
        finally:
            self._inflight.release()

    def _ingest(self, body: bytes | BinaryIO, headers: Mapping[str, str], *, now: datetime) -> WebhookResult:
        if not _aware(now):
            return WebhookResult(400, "CLOCK_INVALID")
        try:
            if type(body) is not bytes:
                chunks, remaining = [], self.config.max_body_bytes + 1
                # Blocking BinaryIO may return short reads. Prove EOF, or reject
                # after bounded bytes/read calls; never authenticate a prefix.
                for _ in range(1024):
                    chunk = body.read(min(remaining, 65536))
                    if type(chunk) is not bytes or len(chunk) > min(remaining, 65536):
                        return WebhookResult(400, "PAYLOAD_INVALID")
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                    if remaining == 0:
                        return WebhookResult(413, "BODY_TOO_LARGE")
                else:
                    return WebhookResult(413, "BODY_READ_LIMIT")
                body = b"".join(chunks)
            if type(body) is not bytes:
                return WebhookResult(400, "PAYLOAD_INVALID")
            if len(body) > self.config.max_body_bytes:
                return WebhookResult(413, "BODY_TOO_LARGE")
            selected = {}
            if len(headers) > 64:
                return WebhookResult(400, "HEADERS_INVALID")
            for name, value in headers.items():
                if type(name) is not str or len(name) > 128 or type(value) is not str or len(value) > 1024:
                    return WebhookResult(400, "HEADERS_INVALID")
                key = name.lower()
                if key in selected:
                    return WebhookResult(400, "HEADERS_INVALID")
                selected[key] = value
            signature = selected.get("x-hub-signature-256", "")
            admitted = None
            if self.admitted_generations is not None:
                try:
                    admitted = self.admitted_generations(now)
                    if (type(admitted) is not tuple or not admitted
                            or len(set(admitted)) != len(admitted)
                            or not all(type(item) is int and item in self.config.secret_generations for item in admitted)):
                        return WebhookResult(503, "ROTATION_UNAVAILABLE")
                except Exception:
                    return WebhookResult(503, "ROTATION_UNAVAILABLE")
            if not re.fullmatch(r"sha256=[0-9a-f]{64}", signature):
                return WebhookResult(401, "SIGNATURE_INVALID")
        except Exception:
            return WebhookResult(400, "PAYLOAD_INVALID")
        matched = False
        matched_generations = []
        unavailable = False
        pairs = zip(self.config.secret_refs, self.config.secret_generations or (0,) * len(self.config.secret_refs))
        for ref, generation in pairs:
            if admitted is not None and generation not in admitted:
                continue
            try:
                secret = self.resolve_secret(ref)
                if type(secret) is not bytes or not 16 <= len(secret) <= 4096:
                    raise ValueError("unavailable secret")
                expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
                selected_match = hmac.compare_digest(expected, signature)
                matched |= selected_match
                if selected_match and generation:
                    matched_generations.append(generation)
            except Exception:
                unavailable = True
        if not matched:
            if unavailable:
                return WebhookResult(503, "SECRET_UNAVAILABLE")
            return WebhookResult(401, "SIGNATURE_INVALID")
        if admitted is not None and len(matched_generations) != 1:
            return WebhookResult(503, "SIGNATURE_AMBIGUOUS")
        if selected.get("x-github-event") != "workflow_run":
            return WebhookResult(403, "EVENT_NOT_ALLOWED")
        if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}",
                            selected.get("x-github-delivery", "")):
            return WebhookResult(400, "DELIVERY_INVALID")
        try:
            data = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
            if type(data) is not dict or type(data.get("workflow_run")) is not dict:
                raise ValueError("invalid payload")
        except (ValueError, TypeError, UnicodeError, RecursionError):
            return WebhookResult(400, "PAYLOAD_INVALID")
        claim = data["workflow_run"]
        try:
            repository = data["repository"]
            if type(repository) is not dict or not all(type(value) is int and 0 < value < 2**63 for value in (
                    repository["id"], claim["id"], claim["workflow_id"], claim["run_attempt"])):
                raise ValueError("invalid identity")
            if (type(repository["full_name"]) is not str or type(claim["head_branch"]) is not str
                    or len(claim["head_branch"]) > 255 or type(claim["head_sha"]) is not str
                    or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", claim["head_sha"])
                    or type(claim["conclusion"]) is not str or type(claim["updated_at"]) is not str
                    or len(claim["updated_at"]) > 64):
                raise ValueError("invalid claim")
            signed_at = datetime.fromisoformat(claim["updated_at"])
            if not _aware(signed_at):
                raise ValueError("invalid timestamp")
            ref = "refs/heads/" + claim["head_branch"]
            allowed = self.adapter.config
            if (data.get("action") != "completed" or claim.get("status") != "completed"
                    or repository["id"] != allowed.repository_id or repository["full_name"] != allowed.repository
                    or claim["workflow_id"] != allowed.workflow_id or ref not in allowed.refs
                    or claim["conclusion"] not in allowed.conclusions):
                return WebhookResult(403, "EVENT_NOT_ALLOWED")
            if not self._fresh(signed_at, now):
                return WebhookResult(422, "EVENT_STALE")
        except (KeyError, TypeError, ValueError, OverflowError):
            return WebhookResult(400, "PAYLOAD_INVALID")
        delivery = selected["x-github-delivery"].lower()
        digest = hashlib.sha256(body).hexdigest()
        if delivery in self._deliveries and self._deliveries[delivery] != digest:
            return WebhookResult(409, "DELIVERY_CONFLICT")
        try:
            verified = self.client.get_run_attempt(allowed.repository, claim["id"], claim["run_attempt"])
        except Exception:
            return WebhookResult(503, "VERIFICATION_UNAVAILABLE")
        observation = self.adapter.normalize_verified_attempt(verified)
        if (isinstance(observation, Invalid) or type(verified) is not WorkflowRun
                or (verified.repository_id, verified.repository, verified.run_id, verified.run_attempt,
                    verified.workflow_id, verified.ref, verified.head_sha, verified.conclusion)
                != (repository["id"], repository["full_name"], claim["id"], claim["run_attempt"],
                    claim["workflow_id"], ref, claim["head_sha"], claim["conclusion"])):
            return WebhookResult(422, "VERIFICATION_FAILED")
        if not self._fresh(verified.completed_at, now):
            return WebhookResult(422, "EVENT_STALE")
        try:
            checkpoint = self.checkpoints.source_checkpoint("github", allowed.source_instance)
            if checkpoint is None:
                checkpoint = self.adapter.checkpoint_for_anchor(self.anchor)
            if isinstance(checkpoint, (Invalid, Degraded)):
                return WebhookResult(503, "STORE_UNAVAILABLE")
            result = self.module.ingest((observation,), checkpoint)
        except Exception:
            return WebhookResult(503, "COMMIT_FAILED")
        if not isinstance(result, Ingested) or len(result.receipts) != 1:
            return WebhookResult(503, "COMMIT_FAILED")
        if self.committed_delivery is not None:
            try:
                self.committed_delivery(matched_generations[0], str(result.receipts[0].receipt_id))
            except Exception:
                return WebhookResult(503, "ROTATION_COMMIT_FAILED")
        self._deliveries[delivery] = digest
        self._deliveries.move_to_end(delivery)
        while len(self._deliveries) > self.config.delivery_cache_size:
            self._deliveries.popitem(last=False)
        return WebhookResult(200, "DUPLICATE" if result.receipts[0].duplicate else "COMMITTED")

    def _fresh(self, at: datetime, now: datetime) -> bool:
        # GitHub signs the body, not a delivery timestamp header. updated_at is
        # a bounded hint age, while completed_at comes from the attempt read.
        return -timedelta(seconds=self.config.future_skew_seconds) <= now - at <= timedelta(seconds=self.config.max_age_seconds)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _aware(value: object) -> bool:
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def _invalid_constant(value):
    raise ValueError("non-JSON number")
