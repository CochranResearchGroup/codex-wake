"""Generic, read-only HTTP/JSON terminal-state signals."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from types import MappingProxyType
from typing import Iterable, Mapping, Protocol
from urllib.parse import urlsplit

from .http_json_source_config import HTTPJSONSourceConfig
from .signals import (
    ArmedSignal,
    Degraded,
    EvaluationLimits,
    In,
    Ingested,
    Invalid,
    NormalizedObservation,
    SignalRequest,
    SourceAnchor,
    SourceCommit,
    SourceContract,
    SourceInstanceReconcileResult,
    SourceReconcileResult,
    Verification,
)


_SOURCE = "http-json"
_KIND = "job.terminal"


@dataclass(frozen=True, slots=True)
class HTTPJSONDocument:
    payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class HTTPJSONTerminalEvent:
    event_id: str
    state: str
    occurred_at: datetime
    attributes: dict[str, str]


class HTTPJSONReadClient(Protocol):
    def read(self) -> HTTPJSONDocument: ...


class HTTPJSONClient:
    """One fixed-origin bounded GET; response bodies never escape this class."""

    def __init__(self, config: HTTPJSONSourceConfig) -> None:
        self.config = config

    def read(self) -> HTTPJSONDocument:
        parsed = urlsplit(self.config.url)
        addresses = _resolve_addresses(parsed.hostname or "", parsed.port or (443 if parsed.scheme == "https" else 80))
        if not _addresses_allowed(addresses, self.config.allow_non_loopback):
            raise ValueError("HTTP JSON source address is not allowed")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        selected_address = str(addresses[0])
        connection = (
            _PinnedHTTPSConnection(parsed.hostname or "", selected_address, port, self.config.request_timeout_seconds)
            if parsed.scheme == "https"
            else HTTPConnection(selected_address, port, timeout=self.config.request_timeout_seconds)
        )
        host_header = parsed.hostname or ""
        if parsed.port is not None:
            host_header = f"{host_header}:{parsed.port}"
        headers = {
            "Accept": "application/json",
            "Host": host_header,
            "User-Agent": "codex-wake/http-json-v1",
        }
        if self.config.credential_ref:
            credential = os.environ.get(self.config.credential_ref, "")
            if not credential or "\n" in credential or "\r" in credential:
                raise ValueError("HTTP JSON source credential is unavailable")
            if parsed.scheme != "https" and not all(item.is_loopback for item in addresses):
                raise ValueError("HTTP JSON credential requires HTTPS or loopback")
            headers["Authorization"] = f"Bearer {credential}"
        target = parsed.path or "/"
        try:
            connection.request("GET", target, headers=headers)
            response = connection.getresponse()
            if response.status != 200 or response.getheader("Location") is not None:
                raise ValueError("HTTP JSON source response is unavailable")
            content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().lower()
            if content_type not in {"application/json", "application/problem+json"}:
                raise ValueError("HTTP JSON source response is not JSON")
            declared = response.getheader("Content-Length")
            if declared is not None and (not declared.isdigit() or int(declared) > self.config.max_response_bytes):
                raise ValueError("HTTP JSON source response is oversized")
            body = response.read(self.config.max_response_bytes + 1)
            if len(body) > self.config.max_response_bytes:
                raise ValueError("HTTP JSON source response is oversized")
            payload = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object)
            if type(payload) is not dict:
                raise ValueError("HTTP JSON source response must be an object")
            return HTTPJSONDocument(payload)
        except (OSError, HTTPException, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("HTTP JSON source response is unavailable") from exc
        finally:
            connection.close()


class HTTPJSONSignalAdapter:
    def __init__(self, config: HTTPJSONSourceConfig, client: HTTPJSONReadClient) -> None:
        if type(config) is not HTTPJSONSourceConfig or not callable(getattr(client, "read", None)):
            raise ValueError("HTTP JSON adapter is invalid")
        self.config = config
        self.client = client
        self.source_instance = config.source_instance
        self.subject = "url:" + hashlib.sha256(config.url.encode("utf-8")).hexdigest()

    def contract(self) -> SourceContract:
        return SourceContract(
            _SOURCE,
            self.source_instance,
            frozenset({_KIND}),
            frozenset({self.subject}),
            MappingProxyType({"state": str, "event_id": str}),
            max_clauses=1,
            max_in_values=16,
            max_attribute_bytes=512,
            max_evidence_ref_bytes=192,
        )

    def request(self) -> SignalRequest:
        return SignalRequest(
            1,
            _SOURCE,
            self.source_instance,
            "occurrence",
            _KIND,
            self.subject,
            "occurs",
            (In("state", tuple(sorted(self.config.terminal_values))),),
            "required",
        )

    def establish_anchor(self, spec: SignalRequest, now: datetime) -> SourceAnchor | Invalid:
        if spec != self.request() or not _aware(now):
            return Invalid(None, "HTTP_JSON_SIGNAL_NOT_ALLOWED", ("HTTP JSON signal is outside the configured source",))
        return SourceAnchor(0, f"http-json:{self.source_instance}", {}, "source_replay")

    def observe(self, now: datetime) -> HTTPJSONTerminalEvent | None:
        if not _aware(now):
            raise ValueError("observation time must be timezone-aware")
        document = self.client.read()
        payload = document.payload
        for pointer, expected in self.config.selectors:
            if _pointer(payload, pointer) != expected:
                return None
        state = _pointer(payload, self.config.state_pointer)
        if type(state) is not str or state not in self.config.terminal_values:
            return None
        event_value = (
            _pointer(payload, self.config.event_id_pointer)
            if self.config.event_id_pointer is not None
            else hashlib.sha256(self.config.url.encode("utf-8")).hexdigest()
        )
        if type(event_value) is not str or not event_value or len(event_value.encode("utf-8")) > 256:
            raise ValueError("HTTP JSON event identity is invalid")
        occurred_at = datetime(1970, 1, 1, tzinfo=UTC)
        if self.config.completed_at_pointer is not None:
            raw_time = _pointer(payload, self.config.completed_at_pointer)
            if raw_time is not None:
                if type(raw_time) is not str:
                    raise ValueError("HTTP JSON completion time is invalid")
                occurred_at = _parse_time(raw_time)
        return HTTPJSONTerminalEvent(
            event_value,
            state,
            occurred_at,
            {"state": state, "event_id": event_value},
        )


class HTTPJSONSignalRunner:
    def __init__(self, adapters: Iterable[HTTPJSONSignalAdapter], *, armed_signals: Iterable[ArmedSignal]) -> None:
        configured = tuple(adapters)
        self._adapters = {item.source_instance: item for item in configured}
        if len(self._adapters) != len(configured):
            raise ValueError("HTTP JSON source instances must be unique")
        self._armed_signals = tuple(armed_signals)

    def reconcile(self, module, now: datetime, limits: EvaluationLimits) -> SourceReconcileResult:
        if not _aware(now) or limits.max_candidates <= 0:
            return SourceReconcileResult(_SOURCE, 0, 0, 1)
        groups: dict[str, list[ArmedSignal]] = {}
        for armed in self._armed_signals[: limits.max_candidates]:
            if type(armed) is ArmedSignal and armed.spec.source == _SOURCE:
                groups.setdefault(armed.spec.source_instance, []).append(armed)
        rows: list[SourceInstanceReconcileResult] = []
        scanned = observed = degraded = 0
        for source_instance in sorted(groups):
            scanned += 1
            adapter = self._adapters.get(source_instance)
            if adapter is None or any(armed.spec != adapter.request() for armed in groups[source_instance]):
                degraded += 1
                rows.append(SourceInstanceReconcileResult(_SOURCE, source_instance, 0, 0, 1, "HTTP_JSON_SOURCE_UNAVAILABLE", now))
                continue
            try:
                event = adapter.observe(now)
                previous = module.source_checkpoint(_SOURCE, source_instance)
                if isinstance(previous, Degraded):
                    raise ValueError("checkpoint unavailable")
                order = previous.checkpoint_order + 1 if isinstance(previous, SourceCommit) else 1
                checkpoint_value = json.dumps(
                    {"event_id": event.event_id if event else "", "state": event.state if event else ""},
                    sort_keys=True,
                    separators=(",", ":"),
                )
                observations = ()
                if event is not None:
                    observations = (NormalizedObservation(
                        _SOURCE,
                        source_instance,
                        _KIND,
                        adapter.subject,
                        "http-json-terminal",
                        f"{event.event_id}:{event.state}",
                        event.occurred_at,
                        event.occurred_at,
                        MappingProxyType(event.attributes),
                        Verification("verified", "bounded_http_json_get"),
                        f"http-json:{source_instance}:{hashlib.sha256(event.event_id.encode()).hexdigest()[:24]}",
                    ),)
                result = module.ingest(observations, SourceCommit(_SOURCE, source_instance, checkpoint_value, order, now))
                if not isinstance(result, Ingested):
                    raise ValueError("ingest unavailable")
                inserted = sum(1 for receipt in result.receipts if not receipt.duplicate)
                observed += inserted
                rows.append(SourceInstanceReconcileResult(_SOURCE, source_instance, 1, inserted, 0, "", now))
            except Exception:
                degraded += 1
                rows.append(SourceInstanceReconcileResult(_SOURCE, source_instance, 1, 0, 1, "HTTP_JSON_SOURCE_UNAVAILABLE", now))
        return SourceReconcileResult(_SOURCE, scanned, observed, degraded, tuple(rows))


def _pointer(payload: object, pointer: str | None) -> object:
    if pointer is None or pointer == "":
        return payload
    current = payload
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if type(current) is dict:
            if token not in current:
                return None
            current = current[token]
        elif type(current) is list and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return None
    return current


def _resolve_addresses(host: str, port: int) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]:
    try:
        rows = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = tuple(sorted({ipaddress.ip_address(row[4][0]) for row in rows}, key=str))
    except (OSError, ValueError) as exc:
        raise ValueError("HTTP JSON source address is unavailable") from exc
    if not addresses:
        raise ValueError("HTTP JSON source address is unavailable")
    return addresses


class _PinnedHTTPSConnection(HTTPSConnection):
    """Resolve once, connect to that address, and retain hostname TLS checks."""

    def __init__(self, hostname: str, address: str, port: int, timeout: int) -> None:
        super().__init__(hostname, port, timeout=timeout, context=ssl.create_default_context())
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._address, self.port), self.timeout, self.source_address
        )
        if self._tunnel_host:
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def _addresses_allowed(addresses, allow_non_loopback: bool) -> bool:
    if all(item.is_loopback for item in addresses):
        return True
    return bool(allow_non_loopback and all(item.is_global for item in addresses))


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not _aware(parsed):
        raise ValueError("HTTP JSON completion time is invalid")
    return parsed.astimezone(UTC)


def _aware(value: datetime) -> bool:
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result
