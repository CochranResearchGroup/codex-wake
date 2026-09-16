"""Main-thread durable join between one HTTP listener and signed GitHub ingress."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import math
import threading
import time

from .github_client import GitHubReadDeadline, _absolute_deadline
from .github_polling import CheckpointReader, GitHubPollingAdapter, GitHubReadClient, GitHubReadError, WorkflowRun
from .github_webhooks import GitHubWebhookIngress, WebhookConfig, WebhookResult
from .signals import SignalEngine, SourceAnchor
from .webhook_http import WebhookHTTPConfig, WebhookHTTPServer


class _DeliveryClient:
    """The ingress's narrow read seam; each admitted delivery gets one client."""

    def __init__(self, runtime: "GitHubWebhookRuntime"):
        self._runtime = runtime

    def list_runs(self, query):
        raise GitHubReadError("unavailable")

    def get_run_attempt(self, repository: str, run_id: int, run_attempt: int) -> WorkflowRun:
        deadline = self._runtime._deadline
        if deadline is None:
            raise GitHubReadError("unavailable")
        client = self._runtime._attempt_client_factory(deadline)
        if not callable(getattr(client, "get_run_attempt", None)):
            raise GitHubReadError("unavailable")
        return client.get_run_attempt(repository, run_id, run_attempt)


class _Delivery:
    def __init__(self, body: bytes, headers: Mapping[str, str]):
        self.body = body
        self.headers = headers
        self.done = threading.Event()
        self.result: WebhookResult | None = None


class GitHubWebhookRuntime:
    """One-source lifecycle: bound address, blocking main-thread serve, shutdown.

    The HTTP server owns sockets on its serving thread. Its callback transfers
    one request, with no application queue, to this controller's main-thread
    loop. The complete ingress operation therefore shares one real POSIX
    absolute deadline with its freshly constructed production read client.
    """

    def __init__(self, http_config: WebhookHTTPConfig, *, adapter: GitHubPollingAdapter,
                 module: SignalEngine, checkpoints: CheckpointReader, anchor: SourceAnchor,
                 webhook_config: WebhookConfig, resolve_secret: Callable[[str], bytes],
                 attempt_client_factory: Callable[[GitHubReadDeadline], GitHubReadClient],
                 operation_timeout: float = 10.0,
                 now: Callable[[], datetime] = lambda: datetime.now(UTC)):
        if (type(http_config) is not WebhookHTTPConfig or not isinstance(adapter, GitHubPollingAdapter)
                or type(webhook_config) is not WebhookConfig or not callable(resolve_secret)
                or not callable(attempt_client_factory) or not callable(now)
                or type(operation_timeout) not in (int, float) or not math.isfinite(operation_timeout)
                or not .01 <= operation_timeout <= min(300.0, http_config.request_timeout,
                                                        http_config.shutdown_timeout)):
            raise ValueError("GitHub webhook runtime configuration is invalid")
        self._condition = threading.Condition()
        self._stopping = False
        self._owner: threading.Thread | None = None
        self._delivery: _Delivery | None = None
        self._processing = False
        self._deadline: GitHubReadDeadline | None = None
        self._operation_timeout = float(operation_timeout)
        self._now = now
        self._attempt_client_factory = attempt_client_factory
        self._ingress = GitHubWebhookIngress(
            adapter, _DeliveryClient(self), module, checkpoints=checkpoints, anchor=anchor,
            config=webhook_config, resolve_secret=resolve_secret,
        )
        self._http = WebhookHTTPServer(http_config, self._transfer)
        self.address = self._http.address
        self._serving_thread: threading.Thread | None = None
        self._serve_failure: BaseException | None = None

    def serve(self) -> None:
        """Block on the POSIX main thread until another owner shuts down."""
        with self._condition:
            if self._owner is not None:
                raise RuntimeError("GitHub webhook runtime already serving")
            if threading.current_thread() is not threading.main_thread():
                raise RuntimeError("GitHub webhook runtime requires the main thread")
            if self._stopping:
                return
            self._owner = threading.current_thread()
            self._serving_thread = threading.Thread(target=self._serve_http,
                                                     name="github-webhook-http", daemon=False)
            self._serving_thread.start()
        while True:
            with self._condition:
                while self._delivery is None and not self._stopping and self._serve_failure is None:
                    self._condition.wait(.05)
                if self._stopping:
                    return
                if self._serve_failure is not None:
                    raise RuntimeError("GitHub webhook listener failed") from self._serve_failure
                delivery = self._delivery
                self._processing = True
            result = self._ingest(delivery)
            with self._condition:
                self._deadline = None
                self._processing = False
                self._delivery = None
                delivery.result = result
                delivery.done.set()
                self._condition.notify_all()

    def shutdown(self) -> None:
        """Stop admission and wait only for the listener's bounded shutdown."""
        with self._condition:
            self._stopping = True
            if self._delivery is not None and not self._processing:
                self._delivery.result = WebhookResult(503, "INGRESS_UNAVAILABLE")
                self._delivery.done.set()
                self._delivery = None
            self._condition.notify_all()
        self._http.shutdown()

    def _serve_http(self) -> None:
        try:
            self._http.serve()
        except BaseException as exc:
            with self._condition:
                self._serve_failure = exc
                self._condition.notify_all()

    def _transfer(self, body: bytes, headers: Mapping[str, str]) -> WebhookResult:
        delivery = _Delivery(body, headers)
        with self._condition:
            if self._stopping or self._delivery is not None:
                return WebhookResult(503, "BUSY")
            self._delivery = delivery
            self._condition.notify_all()
        delivery.done.wait()
        return delivery.result or WebhookResult(503, "INGRESS_UNAVAILABLE")

    def _ingest(self, delivery: _Delivery) -> WebhookResult:
        try:
            with _absolute_deadline(self._operation_timeout) as deadline:
                with self._condition:
                    self._deadline = deadline
                return self._ingress.ingest(delivery.body, delivery.headers, now=self._now())
        except Exception:
            return WebhookResult(503, "INGRESS_UNAVAILABLE")
