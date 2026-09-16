"""Bounded, secret-free GitHub repository webhook administration.

This is deliberately only a transport adapter.  ``ManagedWebhookReconciler``
owns intent recording, mutation serialization, and ambiguity recovery; this
module performs one requested REST operation, does not retry it, and returns
only the small provider objects the reconciler is allowed to retain.
"""
from __future__ import annotations

from dataclasses import dataclass
from http.client import HTTPSConnection
import json
import math
import time
from typing import Callable
from urllib.parse import urlencode

from .managed_webhooks import ManagedWebhookBinding, ProviderHook, WebhookProviderManager


_ACCEPT = "application/vnd.github+json"
_API_VERSION = "2026-03-10"
_USER_AGENT = "codex-wake-github-webhook-admin"
_MAX_TOKEN_BYTES = 4096
_MAX_SECRET_BYTES = 4096
_MAX_HOOKS = 128
_MAX_DELIVERIES = 128
_MAX_PAGES = 4
_MAX_RESPONSE_BYTES = 262_144
_MAX_REQUESTS = 8
_REQUEST_TIMEOUT_SECONDS = 10.0
_DEADLINE_SECONDS = 30.0


class GitHubWebhookAdminError(ValueError):
    """A deliberately non-diagnostic provider-administration failure."""

    def __init__(self) -> None:
        super().__init__("GitHub webhook administration is unavailable")


@dataclass(frozen=True, slots=True)
class GitHubWebhookDelivery:
    """The bounded, nonsecret projection of a webhook delivery listing."""

    delivery_id: int
    event: str
    status: str

    def __post_init__(self) -> None:
        if (
            type(self.delivery_id) is not int or not 0 < self.delivery_id < 2**63
            or type(self.event) is not str or not 1 <= len(self.event) <= 96 or not self.event.isascii()
            or type(self.status) is not str or not 1 <= len(self.status) <= 96 or not self.status.isascii()
        ):
            raise ValueError("GitHub webhook delivery is invalid")


class GitHubWebhookAdmin(WebhookProviderManager):
    """A serial, fail-closed adapter for one exact GitHub repository binding.

    Credential and secret resolvers are called only immediately before a
    request that needs them.  Their return values are never kept on this
    object, returned, logged, or placed in an exception.
    """

    def __init__(
        self,
        binding: ManagedWebhookBinding,
        *,
        credential_resolver: Callable[[str], str],
        secret_generation_resolver: Callable[[int], str],
        connection_factory=HTTPSConnection,
        monotonic: Callable[[], float] = time.monotonic,
        max_requests: int = _MAX_REQUESTS,
        deadline_seconds: float = _DEADLINE_SECONDS,
        request_timeout_seconds: float = _REQUEST_TIMEOUT_SECONDS,
        max_response_bytes: int = _MAX_RESPONSE_BYTES,
        max_pages: int = _MAX_PAGES,
        max_hooks: int = _MAX_HOOKS,
        max_deliveries: int = _MAX_DELIVERIES,
    ) -> None:
        if (
            type(binding) is not ManagedWebhookBinding
            or binding.provider_host != "api.github.com"
            or not callable(credential_resolver)
            or not callable(secret_generation_resolver)
            or not callable(connection_factory)
            or not callable(monotonic)
            or type(max_requests) is not int or not 1 <= max_requests <= 64
            or type(max_response_bytes) is not int or not 1 <= max_response_bytes <= 1_048_576
            or type(max_pages) is not int or not 1 <= max_pages <= 16
            or type(max_hooks) is not int or not 1 <= max_hooks <= 128
            or type(max_deliveries) is not int or not 1 <= max_deliveries <= 128
            or not _positive_finite(deadline_seconds)
            or not _positive_finite(request_timeout_seconds)
        ):
            raise ValueError("GitHub webhook administration configuration is invalid")
        self._provider_host = binding.provider_host
        self._repository = binding.repository
        self._repository_id = binding.repository_id
        self._credential_ref = binding.provider_credential_ref
        self._credential_resolver = credential_resolver
        self._secret_generation_resolver = secret_generation_resolver
        self._connect = connection_factory
        self._clock = monotonic
        self._max_requests = max_requests
        self._deadline_seconds = float(deadline_seconds)
        self._request_timeout_seconds = float(request_timeout_seconds)
        self._max_response_bytes = max_response_bytes
        self._max_pages = max_pages
        self._max_hooks = max_hooks
        self._max_deliveries = max_deliveries
        self._requests = 0
        self._deadline = 0.0

    def list_hooks(self, *, repository_id: int) -> tuple[ProviderHook, ...]:
        self._require_repository(repository_id)
        self._begin()
        self._attest_repository()
        hooks: list[ProviderHook] = []
        seen: set[int] = set()
        for page in range(1, self._max_pages + 1):
            rows = self._request_json("GET", self._hooks_path(), query={"per_page": 100, "page": page})
            if type(rows) is not list or len(rows) > 100:
                self._fail()
            for row in rows:
                hook = self._hook(row)
                if hook.hook_id in seen or len(hooks) >= self._max_hooks:
                    self._fail()
                seen.add(hook.hook_id)
                hooks.append(hook)
            if len(rows) < 100:
                return tuple(hooks)
        self._fail()

    def get_hook(self, *, repository_id: int, hook_id: int) -> ProviderHook | None:
        self._require_repository(repository_id)
        self._require_hook_id(hook_id)
        self._begin()
        self._attest_repository()
        status, data = self._request_json_status("GET", self._hook_path(hook_id), accepted={200, 404})
        if status == 404:
            return None
        result = self._hook(data)
        if result.hook_id != hook_id:
            self._fail()
        return result

    def create_hook(self, binding: ManagedWebhookBinding) -> ProviderHook:
        self._require_create_binding(binding)
        self._begin()
        self._attest_repository()
        return self._hook(self._request_json("POST", self._hooks_path(), body=self._write_body(binding), expected=201))

    def update_hook(self, *, hook_id: int, binding: ManagedWebhookBinding) -> ProviderHook:
        self._require_hook_id(hook_id)
        self._require_update_binding(hook_id, binding)
        self._begin()
        self._attest_repository()
        result = self._hook(self._request_json("PATCH", self._hook_path(hook_id), body=self._write_body(binding)))
        if result.hook_id != hook_id:
            self._fail()
        return result

    # These operations are intentionally outside WebhookProviderManager until
    # the lifecycle/cleanup slice adopts them.  They retain the same exact-ID,
    # no-retry, and bounded-response contract for that later integration.
    def disable_hook(self, *, repository_id: int, hook_id: int) -> ProviderHook:
        self._require_repository(repository_id)
        self._require_hook_id(hook_id)
        self._begin()
        self._attest_repository()
        result = self._hook(self._request_json("PATCH", self._hook_path(hook_id), body={"active": False}))
        if result.hook_id != hook_id or result.active:
            self._fail()
        return result

    def delete_hook(self, *, repository_id: int, hook_id: int) -> None:
        self._require_repository(repository_id)
        self._require_hook_id(hook_id)
        self._begin()
        self._attest_repository()
        self._request_empty("DELETE", self._hook_path(hook_id), expected=204)

    def list_deliveries(self, *, repository_id: int, hook_id: int) -> tuple[GitHubWebhookDelivery, ...]:
        self._require_repository(repository_id)
        self._require_hook_id(hook_id)
        self._begin()
        self._attest_repository()
        deliveries: list[GitHubWebhookDelivery] = []
        seen: set[int] = set()
        for page in range(1, self._max_pages + 1):
            rows = self._request_json("GET", self._hook_path(hook_id) + "/deliveries", query={"per_page": 100, "page": page})
            if type(rows) is not list or len(rows) > 100:
                self._fail()
            for row in rows:
                delivery = self._delivery(row)
                if delivery.delivery_id in seen or len(deliveries) >= self._max_deliveries:
                    self._fail()
                seen.add(delivery.delivery_id)
                deliveries.append(delivery)
            if len(rows) < 100:
                return tuple(deliveries)
        self._fail()

    def _begin(self) -> None:
        try:
            now = self._clock()
        except Exception:
            self._fail()
        if type(now) not in (int, float) or not math.isfinite(now):
            self._fail()
        self._requests = 0
        self._deadline = float(now) + self._deadline_seconds

    def _attest_repository(self) -> None:
        row = self._request_json("GET", self._repository_path())
        if (
            type(row) is not dict
            or row.get("id") != self._repository_id
            or row.get("full_name") != self._repository
        ):
            self._fail()

    def _request_json(self, method: str, path: str, *, query: dict[str, int] | None = None,
                      body: dict[str, object] | None = None, expected: int = 200) -> object:
        status, data = self._request_json_status(method, path, query=query, body=body, accepted={expected})
        if status != expected:
            self._fail()
        return data

    def _request_json_status(self, method: str, path: str, *, query: dict[str, int] | None = None,
                             body: dict[str, object] | None = None, accepted: set[int]) -> tuple[int, object]:
        response = self._open(method, path, query=query, body=body)
        try:
            status = getattr(response, "status", None)
            if type(status) is not int or status not in accepted:
                self._fail()
            return status, self._decode(self._read(response))
        finally:
            try:
                response.close()
            except Exception:
                pass

    def _request_empty(self, method: str, path: str, *, expected: int) -> None:
        response = self._open(method, path)
        try:
            if type(getattr(response, "status", None)) is not int or response.status != expected:
                self._fail()
            # A DELETE response must remain bounded too, even though its
            # documented successful shape has no response document.
            if self._read(response):
                self._fail()
        finally:
            try:
                response.close()
            except Exception:
                pass

    def _open(self, method: str, path: str, *, query: dict[str, int] | None = None,
              body: dict[str, object] | None = None):
        if self._requests >= self._max_requests:
            self._fail()
        remaining = self._remaining()
        self._requests += 1
        connection = None
        try:
            token = self._credential()
            encoded = None if body is None else json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            headers = {
                "Authorization": "Bearer " + token,
                "Accept": _ACCEPT,
                "X-GitHub-Api-Version": _API_VERSION,
                "User-Agent": _USER_AGENT,
            }
            if encoded is not None:
                headers["Content-Type"] = "application/json"
            connection = self._connect(self._provider_host, timeout=min(self._request_timeout_seconds, remaining))
            if connection is None:
                self._fail()
            request_path = path + ("?" + urlencode(query) if query else "")
            connection.request(method, request_path, body=encoded, headers=headers)
            response = connection.getresponse()
            if response is None:
                self._fail()
            self._remaining()
            # ``response`` owns a live connection in http.client.  Keep that
            # connection until the response is closed, then close in _read's
            # caller through this explicit attribute-free wrapper.
            return _ResponseLease(response, connection)
        except GitHubWebhookAdminError:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            raise
        except Exception:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            self._fail()

    def _read(self, response: "_ResponseLease") -> bytes:
        chunks: list[bytes] = []
        length = 0
        while True:
            self._remaining()
            try:
                if getattr(response.connection, "sock", None) is not None:
                    response.connection.sock.settimeout(min(self._request_timeout_seconds, self._remaining()))
                chunk = response.read1(min(65_536, self._max_response_bytes - length + 1))
            except Exception:
                self._fail()
            if type(chunk) is not bytes:
                self._fail()
            length += len(chunk)
            if length > self._max_response_bytes:
                self._fail()
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)

    def _decode(self, body: bytes) -> object:
        try:
            return json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
        except (UnicodeError, ValueError, RecursionError):
            self._fail()

    def _credential(self) -> str:
        try:
            token = self._credential_resolver(self._credential_ref)
        except Exception:
            self._fail()
        if not _credential_value(token, _MAX_TOKEN_BYTES):
            self._fail()
        return token

    def _write_body(self, binding: ManagedWebhookBinding) -> dict[str, object]:
        try:
            secret = self._secret_generation_resolver(binding.secret_generation)
        except Exception:
            self._fail()
        if not _credential_value(secret, _MAX_SECRET_BYTES):
            self._fail()
        return {
            "name": "web",
            "active": True,
            "events": list(binding.events),
            "config": {
                "url": binding.callback_url,
                "content_type": "json",
                "insecure_ssl": "0",
                "secret": secret,
            },
        }

    def _hook(self, row: object) -> ProviderHook:
        try:
            if type(row) is not dict or set(row) - {"id", "name", "active", "events", "config", "type", "url", "test_url", "ping_url", "deliveries_url", "last_response", "created_at", "updated_at"}:
                self._fail()
            config = row["config"]
            if (
                row.get("name") != "web" or type(config) is not dict
                or set(config) - {"url", "content_type", "insecure_ssl", "secret", "token", "digest"}
                or type(row.get("id")) is not int or not 0 < row["id"] < 2**63
                or type(row.get("active")) is not bool
                or type(row.get("events")) is not list or not 1 <= len(row["events"]) <= 128
                or any(type(event) is not str for event in row["events"])
                or config.get("url") is None or config.get("content_type") not in {"json", "form"}
                or config.get("insecure_ssl") not in {"0", "1", 0, 1, False, True}
            ):
                self._fail()
            events = tuple(row["events"])
            if len(set(events)) != len(events):
                self._fail()
            events = tuple(sorted(events))
            return ProviderHook(
                hook_id=row["id"], callback_url=config["url"], events=events,
                active=row["active"], content_type=config["content_type"],
                insecure_ssl=config["insecure_ssl"] in {"1", 1, True},
            )
        except (GitHubWebhookAdminError, KeyError, TypeError, ValueError):
            self._fail()

    def _delivery(self, row: object) -> GitHubWebhookDelivery:
        try:
            if type(row) is not dict:
                self._fail()
            return GitHubWebhookDelivery(row["id"], row["event"], row["status"])
        except (GitHubWebhookAdminError, KeyError, TypeError, ValueError):
            self._fail()

    def _remaining(self) -> float:
        try:
            remaining = self._deadline - float(self._clock())
        except Exception:
            self._fail()
        if not math.isfinite(remaining) or remaining <= 0:
            self._fail()
        return remaining

    def _hooks_path(self) -> str:
        return f"/repos/{self._repository}/hooks"

    def _repository_path(self) -> str:
        return f"/repos/{self._repository}"

    def _hook_path(self, hook_id: int) -> str:
        return f"{self._hooks_path()}/{hook_id}"

    def _require_repository(self, repository_id: int) -> None:
        if type(repository_id) is not int or repository_id != self._repository_id:
            raise ValueError("GitHub webhook repository is invalid")

    def _require_hook_id(self, hook_id: int) -> None:
        if type(hook_id) is not int or not 0 < hook_id < 2**63:
            raise ValueError("GitHub webhook hook is invalid")

    def _require_create_binding(self, binding: object) -> None:
        self._require_binding(binding)
        if binding.provider_hook_id is not None:
            raise ValueError("GitHub webhook binding is invalid")

    def _require_update_binding(self, hook_id: int, binding: object) -> None:
        self._require_binding(binding)
        if binding.provider_hook_id != hook_id:
            raise ValueError("GitHub webhook binding is invalid")

    def _require_binding(self, binding: object) -> None:
        if (
            type(binding) is not ManagedWebhookBinding
            or binding.provider_host != self._provider_host
            or binding.repository != self._repository
            or binding.repository_id != self._repository_id
            or binding.provider_credential_ref != self._credential_ref
        ):
            raise ValueError("GitHub webhook binding is invalid")

    @staticmethod
    def _fail() -> None:
        raise GitHubWebhookAdminError()

    def __repr__(self) -> str:
        return (
            f"GitHubWebhookAdmin(provider_host={self._provider_host!r}, repository={self._repository!r}, "
            f"repository_id={self._repository_id!r}, credential_configured=True)"
        )


class _ResponseLease:
    """Closes both the response and its one-use HTTPS connection."""

    def __init__(self, response: object, connection: object) -> None:
        self._response = response
        self.connection = connection

    def read1(self, length: int) -> bytes:
        reader = getattr(self._response, "read1", None)
        return reader(length) if callable(reader) else self._response.read(length)

    def close(self) -> None:
        try:
            self._response.close()
        finally:
            self.connection.close()

    @property
    def status(self) -> object:
        return getattr(self._response, "status", None)


def _positive_finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _credential_value(value: object, maximum: int) -> bool:
    return (
        type(value) is str and 1 <= len(value.encode("utf-8")) <= maximum
        and all(33 <= ord(character) <= 126 for character in value)
    )


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError
