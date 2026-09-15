"""Bounded GitHub.com GET reads with explicit positive-evidence semantics.

REST list exhaustion is not a completeness watermark. Run updated_at is never
used. Exact terminal attempts use the latest known attempt start/job completion
as a lower bound on workflow completion, not an immutable completion timestamp.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http.client import HTTPSConnection
import json
import signal
import threading
import time
from typing import Callable
from urllib.parse import urlencode

from .github_polling import (
    GitHubPollingConfig, GitHubReadError, RunPage, RunQuery, WorkflowRun,
    _aware, _valid_config, _valid_run,
)


class GitHubRestClient:
    def __init__(self, config: GitHubPollingConfig, *, credential_resolver: Callable[[str], str],
                 connection_factory=HTTPSConnection, monotonic=time.monotonic):
        if (not _valid_config(config) or not config.enabled or config.evidence_mode != "positive_only"
                or any(not ref.startswith("refs/heads/") for ref in config.refs)):
            raise ValueError("GitHub production source is invalid")
        self.config = config
        self._resolve = credential_resolver
        self._connect = connection_factory
        self._clock = monotonic
        self._requests = 0
        self._bytes = 0
        self._deadline = self._clock() + config.poll_timeout_seconds

    def list_runs(self, query: RunQuery) -> RunPage:
        if (type(query) is not RunQuery
                or (query.repository, query.repository_id, query.workflow_id, query.refs) !=
                   (self.config.repository, self.config.repository_id, self.config.workflow_id, tuple(sorted(self.config.refs)))
                or type(query.page) is not int or not 1 <= query.page <= self.config.max_pages
                or query.per_page != self.config.page_size or not _aware(query.since) or not _aware(query.until)
                or not timedelta(0) <= query.until - query.since <= timedelta(seconds=self.config.max_history_seconds)):
            raise GitHubReadError("malformed")
        if query.page == 1:
            self._requests = 0
            self._bytes = 0
            self._deadline = self._clock() + self.config.poll_timeout_seconds
        # No created-time filter: old-created runs and reruns may finish later.
        data = self._get(f"/repos/{self.config.repository}/actions/workflows/{self.config.workflow_id}/runs",
                         {"per_page": query.per_page, "page": query.page})
        rows, total = self._collection(data, "workflow_runs", query.per_page)
        runs = tuple(self._run(row) for row in rows)
        # Construct page numbers; Link and provider URLs are never followed.
        more = len(rows) == query.per_page or total > query.page * query.per_page
        return RunPage(runs, query.page + 1 if more else None, None, None)

    def get_run_attempt(self, repository: str, run_id: int, run_attempt: int) -> WorkflowRun:
        if repository != self.config.repository or not all(_positive(value) for value in (run_id, run_attempt)):
            raise GitHubReadError("malformed")
        path = f"/repos/{self.config.repository}/actions/runs/{run_id}/attempts/{run_attempt}"
        run = self._run(self._get(path))
        if (run.run_id, run.run_attempt) != (run_id, run_attempt):
            raise GitHubReadError("malformed")
        if run.status != "completed":
            return run
        proof = run.terminal_proof_at
        seen = set()
        expected_total = None
        for page in range(1, self.config.max_pages + 1):
            rows, total = self._collection(self._get(path + "/jobs", {
                "per_page": self.config.page_size, "page": page}), "jobs", self.config.page_size)
            if expected_total is not None and total != expected_total:
                raise GitHubReadError("malformed")
            expected_total = total
            for row in rows:
                if (type(row) is not dict or not _positive(row.get("id")) or row["id"] in seen
                        or type(row.get("run_id")) is not int or row["run_id"] != run_id
                        or type(row.get("run_attempt")) is not int or row["run_attempt"] != run_attempt
                        or row.get("status") != "completed"):
                    raise GitHubReadError("malformed")
                seen.add(row["id"])
                completed = _timestamp(row.get("completed_at"))
                if completed is not None:
                    proof = max(proof, completed)
            if len(rows) < self.config.page_size and len(seen) == total:
                return replace(run, terminal_proof_at=proof)
            if len(rows) == 0:
                raise GitHubReadError("malformed")
        raise GitHubReadError("budget")

    def _get(self, path: str, query=None) -> dict:
        remaining = self._deadline - self._clock()
        if self._requests >= self.config.max_requests or remaining <= 0:
            raise GitHubReadError("budget")
        self._requests += 1
        with _absolute_deadline(min(self.config.request_timeout_seconds, remaining)):
            return self._read_transaction(path, query, remaining)

    def _read_transaction(self, path, query, remaining):
        connection = None
        response = None
        try:
            token = self._resolve(self.config.credential_ref)
            if type(token) is not str or not 1 <= len(token) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
                raise GitHubReadError("auth")
            connection = self._connect("api.github.com", timeout=min(self.config.request_timeout_seconds, remaining))
            connection.request("GET", path + ("?" + urlencode(query) if query else ""), headers={
                "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "codex-wake",
            })
            response = connection.getresponse()
            if response.status != 200:
                if response.status == 429 or (response.status == 403 and
                        (response.getheader("X-RateLimit-Remaining") == "0" or response.getheader("Retry-After") is not None)):
                    delay = response.getheader("Retry-After")
                    seconds = min(int(delay), 86400) if type(delay) is str and delay.isascii() and delay.isdigit() and len(delay) < 8 else self.config.retry_seconds
                    raise GitHubReadError("rate_limit", retry_at=datetime.now(UTC) + timedelta(seconds=seconds))
                raise GitHubReadError("auth" if response.status in {401, 403, 404} else "unavailable")
            chunks, length = [], 0
            # read1 returns after a bounded socket read; reapply the remaining
            # deadline each time so trickling bytes cannot extend the poll.
            while True:
                remaining = self._deadline - self._clock()
                if remaining <= 0:
                    raise GitHubReadError("budget")
                if getattr(connection, "sock", None) is not None:
                    connection.sock.settimeout(min(self.config.request_timeout_seconds, remaining))
                chunk = response.read1(min(65536, self.config.max_response_bytes - length + 1,
                                           self.config.max_poll_bytes - self._bytes + 1))
                length += len(chunk)
                self._bytes += len(chunk)
                if (length > self.config.max_response_bytes or self._bytes > self.config.max_poll_bytes
                        or self._clock() > self._deadline):
                    raise GitHubReadError("budget")
                if not chunk:
                    break
                chunks.append(chunk)
            body = b"".join(chunks)
            try:
                data = json.loads(body, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
            except (ValueError, UnicodeError, RecursionError):
                raise GitHubReadError("malformed") from None
            if type(data) is not dict:
                raise GitHubReadError("malformed")
            return data
        except GitHubReadError:
            raise
        except Exception:
            raise GitHubReadError("unavailable") from None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _run(self, data: dict) -> WorkflowRun:
        try:
            repository = data["repository"]
            head_repository = data.get("head_repository")
            if (type(repository) is not dict or type(repository.get("id")) is not int
                    or repository["id"] != self.config.repository_id
                    or repository.get("full_name") != self.config.repository
                    or type(head_repository) is not dict or type(head_repository.get("id")) is not int
                    or head_repository["id"] != self.config.repository_id
                    or head_repository.get("full_name") != self.config.repository
                    or type(data.get("workflow_id")) is not int or data["workflow_id"] != self.config.workflow_id
                    or type(data.get("head_branch")) is not str):
                raise GitHubReadError("malformed")
            # Initial production contract supports branch refs only.
            started = _timestamp(data.get("run_started_at"))
            if started is None:
                raise GitHubReadError("malformed")
            run = WorkflowRun(self.config.repository, self.config.repository_id, self.config.workflow_id,
                              data["id"], data["run_attempt"], "refs/heads/" + data["head_branch"],
                              data["head_sha"], data["status"], data["conclusion"], None, started,
                              "github_attempt_started_or_job_completed_lower_bound")
            if not _valid_run(run):
                raise GitHubReadError("malformed")
            return run
        except GitHubReadError:
            raise
        except Exception:
            raise GitHubReadError("malformed") from None

    @staticmethod
    def _collection(data, field, limit):
        rows, total = data.get(field), data.get("total_count")
        if type(rows) is not list or len(rows) > limit or type(total) is not int or total < len(rows):
            raise GitHubReadError("malformed")
        return rows, total


@contextmanager
def _absolute_deadline(seconds):
    """Bound DNS, TLS, writes, headers and body without background workers.

    Initial production support is POSIX main-thread polling with an unowned real
    timer. Never steal another alarm or start credentials/network on unsupported
    threads/platforms. A socket inactivity timeout alone is not an absolute bound.
    """
    if (threading.current_thread() is not threading.main_thread()
            or not hasattr(signal, "setitimer") or not hasattr(signal, "SIGALRM")):
        raise GitHubReadError("unavailable")
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    if previous_timer != (0.0, 0.0):
        raise GitHubReadError("unavailable")
    if (signal.SIGALRM in signal.sigpending()
            or signal.SIGALRM in signal.pthread_sigmask(signal.SIG_BLOCK, [])):
        raise GitHubReadError("unavailable")
    previous_handler = signal.getsignal(signal.SIGALRM)

    def expired(signum, frame):
        raise GitHubReadError("budget")

    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _positive(value):
    return type(value) is int and 0 < value < 2**63


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("invalid constant")


def _timestamp(value):
    if value is None:
        return None
    try:
        if type(value) is not str or len(value) > 40:
            raise ValueError()
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not _aware(result):
            raise ValueError()
        return result
    except Exception:
        raise GitHubReadError("malformed") from None
