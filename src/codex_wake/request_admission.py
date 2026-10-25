"""Explicit host-selected HTTP Responses admission; no provider is assumed qualified.

The operator supplies an exact reviewed provider contract digest. Bounds are the
provider's enforced maxima for the WHOLE request, never token-count estimates.
No configuration/renewal of objective allowances occurs in this adapter.
"""

import hashlib
import hmac
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPConnection, HTTPSConnection
import json
import math
import os
from pathlib import Path
import time
import threading
import socket
from urllib.parse import urlsplit
from urllib.request import Request
from uuid import uuid4

from . import goal_supervision as supervision
from .goal_governance import native_operator, change, sync, snapshot
from .objective_ledger import ObjectiveLedger
from .session_permissions import PermissionDenied, Principal
from .records import WakeError

MAX_BODY = 2 * 1024 * 1024
MAX_RESPONSE = 8 * 1024 * 1024


def contract_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _error(code, message):
    return dict(error=dict(type=code, message=message))


def _sse(text):
    identifier = "governor-" + uuid4().hex
    values = [
        dict(type="response.created", response=dict(id=identifier)),
        dict(
            type="response.output_item.done",
            item=dict(
                type="message",
                role="assistant",
                id=identifier,
                content=[dict(type="output_text", text=text)],
            ),
        ),
        dict(
            type="response.completed",
            response=dict(
                id=identifier,
                usage=dict(
                    input_tokens=0,
                    input_tokens_details=dict(cached_tokens=0),
                    output_tokens=0,
                    total_tokens=0,
                ),
            ),
        ),
    ]
    return "".join(
        "event: " + value["type"] + "\ndata: " + json.dumps(value) + "\n\n"
        for value in values
    ).encode()


def _activation_status(root, receipt):
    """Current native delivery; screen rendering remains separate qualification."""
    from .goal_notices import NativeNoticeAdapter, read_notice
    event_id = receipt.get("notice_ids", {}).get("request_activation")
    try:
        event = read_notice(root, event_id)
        observed = NativeNoticeAdapter(root).reconcile(event)
        published = event["proof"]["notification"]["state"] == "published"
        return dict(qualified=bool(published and observed.get("transcript")
            and observed.get("model_context")), event_id=event_id,
            notification_published=published, operator_rendering="separately_qualified")
    except (OSError, ValueError, KeyError, TypeError, WakeError):
        return dict(qualified=False, event_id=event_id, reason="activation_delivery_unavailable")


class RequestGateway:
    def __init__(
        self,
        root,
        objective_id,
        *,
        upstream_url,
        contract,
        reviewed_contract_sha256,
        thread_ids,
        thread_prior_tokens=None,
        request_timeout=2,
        now=None,
        upstream_headers=None,
        client_token=None,
    ):
        from .lifecycle_budget import trusted_upper

        self.root = Path(root).absolute()
        self.objective_id = objective_id
        self.now = now or trusted_upper
        self.thread_ids = tuple(thread_ids)
        if not self.thread_ids or len(set(self.thread_ids)) != len(self.thread_ids):
            raise ValueError("explicit native source thread binding required")
        self.source_thread = self.thread_ids[0]
        self.directory = supervision._directory(self.root)
        for thread in self.thread_ids:
            supervision._name(thread)
        self.source_path = self.directory / (
            supervision._name(self.source_thread) + ".json"
        )
        supervision._private(self.source_path)
        source = json.loads(self.source_path.read_text())
        if (
            source["allocation_id"] != objective_id
            or source["thread_id"] != self.source_thread
        ):
            raise ValueError("objective/native scope mismatch")
        self.grant = source["grant"]
        parsed = urlsplit(upstream_url)
        if (
            parsed.scheme not in ("http", "https")
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not parsed.hostname
        ):
            raise ValueError(
                "explicit provider URL without embedded credentials required"
            )
        self.upstream_url = upstream_url
        self.provider_address = parsed
        self.upstream_headers = dict(upstream_headers or {})
        self.contract = json.loads(json.dumps(contract))
        self.contract_sha256 = contract_digest(contract)
        self.eligible = (
            reviewed_contract_sha256 == self.contract_sha256
            and contract.get("version") == 1
            and contract.get("input_limit") == "provider_enforced_reject_before_billing"
            and contract.get("output_limit") == "max_output_tokens_enforced"
            and contract.get("usage") == "response.completed:fresh-v1"
            and all(
                type(contract.get(key)) is int and contract[key] > 0
                for key in ("max_input_tokens", "max_output_tokens")
            )
            and all(
                isinstance(contract.get(key), str) and contract[key].strip()
                for key in ("provider", "model", "review")
            )
        )
        if (
            type(request_timeout) not in (int, float)
            or not math.isfinite(request_timeout)
            or not 0 < request_timeout <= 30
        ):
            raise ValueError("request timeout must be positive and at most 30 seconds")
        self.timeout = request_timeout
        if not self.eligible:
            raise ValueError("selected provider contract is unsupported or unreviewed")
        self.ledger = ObjectiveLedger(self.root, objective_id)
        view = self.ledger.inspect(now=self.now())
        if source.get("token_accounting") != "fresh":
            raise ValueError("gateway requires qualified fresh input/output accounting")
        if (
            view["objective_token_limit"] != source["token_limit"]
            or view["objective_deadline"] != source["deadline"]
        ):
            raise ValueError(
                "gateway must retain the existing objective limits/deadline"
            )
        prior = thread_prior_tokens or {self.source_thread: source["used_tokens"]}
        if set(prior) != set(self.thread_ids):
            raise ValueError(
                "every initial native thread needs an explicit prior-usage binding"
            )
        if (
            not view.get("request_binding")
            and sum(prior.values()) != source["used_tokens"]
        ):
            raise ValueError("imported prior usage differs from qualified source")
        self.binding = dict(
            version=1,
            owner="http-responses",
            scope=objective_id,
            source_thread_id=self.source_thread,
            upstream_url_sha256=hashlib.sha256(upstream_url.encode()).hexdigest(),
            contract_sha256=self.contract_sha256,
            accounting="fresh",
            thread_ids=list(self.thread_ids),
        )
        self.ledger.bind_requests(self.binding, prior, now=self.now())
        token_path = self.directory / (
            "request-gateway-"
            + hashlib.sha256(objective_id.encode()).hexdigest()
            + ".token"
        )
        if token_path.exists():
            supervision._private(token_path)
            self.client_token = token_path.read_text()
            if client_token is not None and not hmac.compare_digest(
                client_token, self.client_token
            ):
                raise ValueError("existing gateway client authority differs")
        else:
            self.client_token = client_token or secrets.token_hex(32)
            if (
                not isinstance(self.client_token, str)
                or len(self.client_token) < 32
                or "\n" in self.client_token
            ):
                raise ValueError(
                    "private gateway client token must contain at least 32 characters"
                )
            descriptor = os.open(
                token_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(descriptor, "w") as target:
                target.write(self.client_token)
                target.flush()
                os.fsync(target.fileno())
        # Hand off the accounting source, not the operator's enabled choice.
        with (
            supervision._lock(self.directory, "maintenance"),
            supervision._lock(self.directory, supervision._name(self.source_thread)),
        ):
            source = json.loads(self.source_path.read_text())
            authority = dict(
                root=str(self.root),
                objective_id=objective_id,
                contract_sha256=self.contract_sha256,
                owner="http-responses",
                source_thread_id=self.source_thread,
                gateway_token_file=str(token_path),
                mode="hard_admission" if self.eligible else "unsupported",
                coverage="selected HTTP request path only",
            )
            source["request_accounting"] = authority
            supervision._save_request_accounting(self.source_path, source)

    def protect_completion(self, obligations, *, source):
        """Host-only planning; no HTTP body can install or release protection."""
        return self.ledger.protect_completion(obligations, source=source, now=self.now())

    def assign_completion(self, thread_id, obligation_id, *, source):
        """Retain the host's exact purpose assignment in request_sessions."""
        if thread_id not in self.thread_ids:
            self._inherit_thread(thread_id)
        return self.ledger.assign_completion(thread_id, obligation_id, source=source, now=self.now())

    def resolve_completion(self, obligation_id, outcome, *, source, note):
        return self.ledger.resolve_completion(obligation_id, outcome, source=source, note=note, now=self.now())

    def status(self):
        current = snapshot(self.root, self.source_thread)
        view = self.ledger.inspect(now=self.now())
        mode = (
            "inactive"
            if current.get("enabled") is False
            else ("hard_admission" if view["accounting_known"] else "degraded")
            if self.eligible
            else "unsupported"
        )
        return dict(
            mode=mode,
            completion_enforced=current.get("enabled") is not False,
            activation=_activation_status(self.root, json.loads(self.source_path.read_text())),
            scope=self.objective_id,
            source_thread_id=self.source_thread,
            contract_sha256=self.contract_sha256,
            reviewed_provider_contract=self.eligible,
            request_path="HTTP POST /v1/responses only; WebSocket/compact/bypass paths are not qualified",
            governance=current,
            accounting=self.ledger.inspect(now=self.now()),
            provider_qualification="host-reviewed contract; native path qualification is separate",
        )

    def _context(self, body):
        raw = body.get("client_metadata", {}).get("x-codex-turn-metadata")
        metadata = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(metadata, dict):
            raise ValueError("native request metadata required")
        thread = metadata.get("thread_id")
        supervision._name(thread)
        if metadata.get("session_id", thread) != thread or not metadata.get("turn_id"):
            raise ValueError("native request identity differs")
        if thread not in self.thread_ids:
            self._inherit_thread(thread)
        return thread, dict(
            threadId=thread,
            sessionId=thread,
            callId="gateway-" + uuid4().hex,
            **{"x-codex-turn-metadata": dict(metadata, session_id=thread)},
        )

    def _inherit_thread(self, thread):
        """Native session metadata proves ancestry before a child's first usage."""
        view = self.ledger.inspect(now=self.now())
        if thread in view["request_sessions"]:
            return
        sessions = Path(self.grant["codex_home"]) / "sessions"
        metadata = {}
        started = time.monotonic()
        size = 0
        for count, path in enumerate(sessions.rglob("*.jsonl"), 1):
            if count > 4096 or time.monotonic() - started > 2:
                raise ValueError("native ancestry inventory bound exceeded")
            if (
                path.is_symlink()
                or path.resolve() != path.absolute()
                or path.stat().st_uid != os.geteuid()
            ):
                raise ValueError("native ancestry source is not owned/canonical")
            with path.open("rb") as source:
                raw = source.readline(65537)
            size += len(raw)
            if len(raw) > 65536 or size > 8 * 1024 * 1024:
                raise ValueError("native ancestry metadata bound exceeded")
            row = json.loads(raw)
            if row.get("type") != "session_meta":
                continue
            item = row["payload"]
            identity = item.get("id")
            if identity in metadata:
                raise ValueError("native ancestry identity ambiguous")
            metadata[identity] = (item, path)
        pending = []
        identity = thread
        seen = set()
        while identity not in view["request_sessions"]:
            if identity in seen or len(seen) > 32 or identity not in metadata:
                raise ValueError("unregistered native request thread")
            seen.add(identity)
            item, path = metadata[identity]
            with path.open("rb") as native_source:
                history = native_source.read(8 * 1024 * 1024 + 1)
            if len(history) > 8 * 1024 * 1024 or any(
                json.loads(line).get("type") == "token_usage_record"
                for line in history.splitlines()
                if line.strip()
            ):
                raise ValueError(
                    "pre-existing descendant usage requires explicit prior-usage binding, not a new allowance"
                )
            source = item.get("source", {})
            spawn = (
                source.get("subagent", {}).get("thread_spawn", {})
                if isinstance(source, dict)
                else {}
            )
            parent = item.get("parent_thread_id") or spawn.get("parent_thread_id")
            supervision._name(parent)
            pending.append((identity, parent, contract_digest(item)))
            identity = parent
        for child, parent, proof in reversed(pending):
            self.ledger.register_request_thread(
                child,
                parent,
                dict(source="native_session_meta", sha256=proof),
                now=self.now(),
            )

    def _pause_registered_goal(self, receipt, reason):
        """Pause future native continuation, never interrupt an admitted request."""
        proof = dict(
            reason=reason, goal_created_at=receipt["goal_created_at"], verified=False
        )
        try:
            goal, _ = supervision._native(self.grant, self.source_thread)
            if not goal or goal.get("createdAt") != receipt["goal_created_at"]:
                proof["reason"] = "registered_goal_identity_unverified"
            else:
                if goal.get("status") != "paused":
                    supervision._effect(
                        self.source_path,
                        receipt,
                        "request-pause:" + uuid4().hex,
                        "thread/goal/set",
                        dict(
                            threadId=self.source_thread,
                            status="paused",
                            origin="automatic",
                        ),
                    )
                observed, _ = supervision._native(self.grant, self.source_thread)
                proof["verified"] = bool(
                    observed
                    and observed.get("createdAt") == receipt["goal_created_at"]
                    and observed.get("status") == "paused"
                )
        except (OSError, ValueError, KeyError, TypeError, WakeError) as error:
            proof.update(
                reason="registered_goal_pause_unavailable", error=type(error).__name__
            )
        receipt["request_admission_pause"] = proof
        supervision._save(self.source_path, receipt)
        return proof

    def _control(self, thread, context):
        source = json.loads(self.source_path.read_text())
        native = dict(source, thread_id=thread)
        for enabled in (False, True):
            try:
                proof = native_operator(self.root, native, context, enabled)
            except PermissionDenied:
                continue
            # Native operator input/attachment may reactivate the underlying goal.
            # Preserve a retained admission pause before committing deactivation;
            # this restores work state, never interrupts this operator response.
            if not enabled:
                with supervision._lock(
                    self.directory, supervision._name(self.source_thread)
                ):
                    retained = json.loads(self.source_path.read_text())
                    if retained.get("request_admission_pause", {}).get(
                        "verified"
                    ) and not sync(retained):
                        restored = self._pause_registered_goal(
                            retained, "operator_control_preserves_pause"
                        )
                        # A pause failure cannot veto the operator's durable disable.
                        # It remains explicit in the acknowledgement and receipt.
            result = change(
                self.root,
                self.source_thread,
                enabled=enabled,
                principal=Principal(self.source_thread, "operator"),
                allocation_id=self.objective_id,
            )
            return _sse(
                "Governor-generated acknowledgement; no model inference or provider usage. "
                + result["message"]
                + (
                    " Registered goal pause "
                    + (
                        "verified"
                        if restored["verified"]
                        else "unverified; inspect native work state"
                    )
                    + "."
                    if not enabled and "restored" in locals()
                    else ""
                )
                + " Verified native operator turn "
                + proof["turn_id"]
                + "."
            )
        return None

    def _resource_summary(self):
        view = self.ledger.inspect(now=self.now())
        completion = view.get("completion") or {}
        return dict(used=view["tokens_used"], reserved=view["tokens_reserved"],
            remaining=view["remaining_tokens"], cap=view["objective_token_limit"],
            deadline=view["objective_deadline"], accounting_known=view["accounting_known"],
            protected_tokens=completion.get("protected_tokens", 0),
            protected_seconds=completion.get("protected_seconds", 0))

    def _notice(self, receipt, reason, request_fingerprint):
        receipt["request_admission_event"] = dict(
            reason=reason, fingerprint=request_fingerprint, resources=self._resource_summary()
        )
        supervision._record_supervision_notice(self.source_path, receipt, "admission")
        supervision._save(self.source_path, receipt)
        return receipt.get("notice_ids", {}).get("admission")

    def execute(self, body):
        """One incoming attempt -> at most one reserved upstream attempt.

        Public transport seam used by HTTP and resource planning; caller bodies
        cannot select ledger, policy, provider endpoint, bounds or native grant.
        """
        thread, context = self._context(body)
        control = self._control(thread, context)
        if control is not None:
            return 200, "text/event-stream", control
        fingerprint = contract_digest(body)
        actor = "request:" + uuid4().hex
        notice = None
        with supervision._lock(self.directory, supervision._name(self.source_thread)):
            supervision._private(self.source_path)
            receipt = json.loads(self.source_path.read_text())
            inactive = sync(receipt)
            if not inactive and (
                not self.eligible
                or body.get("model") != self.contract["model"]
                or body.get("stream") is not True
                or body.get("previous_response_id")
            ):
                return (
                    501,
                    "application/json",
                    json.dumps(
                        _error(
                            "governor_path_unsupported",
                            "Selected provider bound contract or HTTP request path is unqualified. Use existing authorized manual work or a reviewed supported provider; no downgrade or renewal.",
                        )
                    ).encode(),
                )
            if not inactive:
                from .goal_notices import present_notice
                if not receipt.get("notice_ids", {}).get("request_activation"):
                    receipt["request_accounting"]["resources"] = self._resource_summary()
                    supervision._record_supervision_notice(self.source_path, receipt, "request_activation")
                    supervision._save(self.source_path, receipt)
                    event = receipt.get("notice_ids", {}).get("request_activation")
                    if event:
                        present_notice(self.root, event)
                if not _activation_status(self.root, receipt)["qualified"]:
                    return (503, "application/json", json.dumps(_error(
                        "governor_activation_unavailable",
                        "Hard-governed provider dispatch withheld: current model/operator activation delivery is unqualified. Inspect governor status or Deactivate governor; existing authorized manual repair remains available."
                    )).encode())
            goal, active = supervision._native(self.grant, thread)
            if active != [context["x-codex-turn-metadata"]["turn_id"]]:
                raise ValueError("request is not the exact current native turn")
            outgoing = dict(body)
            bound = (
                0
                if inactive
                else self.contract["max_input_tokens"]
                + self.contract["max_output_tokens"]
            )
            seconds = math.ceil(self.timeout)
            reserved = self.ledger.reserve_request(
                actor, thread, bound, seconds, enforce=not inactive, now=self.now()
            )
            if not reserved["admitted"]:
                pause = self._pause_registered_goal(receipt, "request_admission_denied")
                notice = self._notice(
                    receipt, reserved.get("admission_reason", "objective_or_session_allowance_unavailable"), fingerprint
                )
                explanation = (reserved.get("admission_reason") or "objective_or_session_allowance_unavailable") + ". "
                completion = reserved.get("completion")
                if completion:
                    explanation += ("Checkpoint or narrow authorized work; completion obligations remain pending. "
                        if completion["pending"] else "Named completion dispositions are recorded; objective acceptance remains separate. ")
                result = (
                    429,
                    "application/json",
                    json.dumps(
                        _error(
                            "governor_admission_denied",
                            "Request denied before provider submission. "
                            + explanation
                            + "Registered goal pause "
                            + ("verified" if pause["verified"] else "unverified")
                            + "; independently admitted requests were not interrupted. Say Deactivate governor in the native conversation; no inference is needed for that control.",
                        )
                    ).encode(),
                )
                upstream = None
            else:
                if not inactive:
                    outgoing["max_output_tokens"] = self.contract["max_output_tokens"]
                address = self.provider_address
                connection = (
                    HTTPSConnection if address.scheme == "https" else HTTPConnection
                )(address.hostname, address.port, timeout=None if inactive else self.timeout)
                expired = threading.Event()
                socket_ref = {}

                def expire():
                    expired.set()
                    active_socket = socket_ref.get("socket")
                    if active_socket is not None:
                        try:
                            active_socket.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass

                request_timer = None
                if not inactive:
                    request_timer = threading.Timer(self.timeout, expire)
                    request_timer.daemon = True
                    request_timer.start()
                try:
                    connection.connect()
                    socket_ref["socket"] = connection.sock
                    if expired.is_set():
                        raise TimeoutError(
                            "request wall-clock allowance expired before send"
                        )
                    # request() completes the one socket submission; response headers
                    # are awaited outside the control lock so disable stays available.
                    connection.request(
                        "POST",
                        address.path or "/",
                        body=json.dumps(outgoing).encode(),
                        headers=dict(
                            self.upstream_headers,
                            **{
                                "Content-Type": "application/json",
                                "Accept": "text/event-stream",
                            },
                        ),
                    )
                    upstream = connection
                except Exception:
                    if request_timer is not None:
                        request_timer.cancel()
                    connection.close()
                    self.ledger.settle_request(
                        actor, None, None, fingerprint, now=self.now()
                    )
                    return (
                        502,
                        "application/json",
                        json.dumps(
                            _error(
                                "governor_completion_unknown",
                                "Provider outcome unknown; reservation retained.",
                            )
                        ).encode(),
                    )
        if notice:
            from .goal_notices import present_notice

            present_notice(self.root, notice)
        if upstream is None:
            return result
        try:
            with upstream.getresponse() as response_stream:
                if response_stream.status != 200:
                    raise ValueError("provider did not return a completion")
                raw = response_stream.read(MAX_RESPONSE + 1)
                if expired.is_set():
                    raise TimeoutError("request wall-clock allowance expired")
                if len(raw) > MAX_RESPONSE:
                    raise ValueError("provider response exceeds protocol bound")
                completions = [
                    json.loads(line[5:].strip())
                    for line in raw.decode().splitlines()
                    if line.startswith("data:") and line[5:].strip() != "[DONE]"
                ]
                completed = [
                    row["response"]
                    for row in completions
                    if row.get("type") == "response.completed"
                ]
                if len(completed) != 1:
                    raise ValueError("one attributable completion required")
                response = completed[0]
                usage = response["usage"]
                values = [
                    usage["input_tokens"],
                    usage["input_tokens_details"]["cached_tokens"],
                    usage["output_tokens"],
                    usage["total_tokens"],
                ]
                if (
                    any(type(value) is not int or value < 0 for value in values)
                    or values[1] > values[0]
                    or values[3] != values[0] + values[2]
                ):
                    raise ValueError("provider usage unqualified")
                if not isinstance(response.get("id"), str) or not response["id"]:
                    raise ValueError("completion identity unavailable")
                if not inactive and (
                    values[0] > self.contract["max_input_tokens"]
                    or values[2] > self.contract["max_output_tokens"]
                ):
                    self.ledger.settle_request(
                        actor,
                        response["id"],
                        values[0] - values[1] + values[2],
                        fingerprint,
                        now=self.now(),
                    )
                    raise ValueError("reviewed provider bounds violated")
                settled = self.ledger.settle_request(
                    actor,
                    response["id"],
                    values[0] - values[1] + values[2],
                    fingerprint,
                    now=self.now(),
                )
                if not inactive and not settled["accounting_known"]:
                    raise ValueError(
                        "provider completion conflicts with prior evidence"
                    )
                return 200, "text/event-stream", raw
        except Exception:
            self.ledger.settle_request(actor, None, None, fingerprint, now=self.now())
            if inactive and "raw" in locals():
                return response_stream.status, "text/event-stream", raw
            return (
                502,
                "application/json",
                json.dumps(
                    _error(
                        "governor_completion_unknown",
                        "Provider completion/usage unavailable or conflicting; reservation retained.",
                    )
                ).encode(),
            )
        finally:
            if request_timer is not None:
                request_timer.cancel()
            upstream.close()

    def server(self, host="127.0.0.1", port=0):
        if host != "127.0.0.1":
            raise ValueError("gateway binds loopback only")
        gateway = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def _send(self, status, kind, data):
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def _authorized(self):
                if hmac.compare_digest(
                    self.headers.get("Authorization", ""),
                    "Bearer " + gateway.client_token,
                ):
                    return True
                self._send(
                    401,
                    "application/json",
                    json.dumps(
                        _error(
                            "gateway_authentication_required",
                            "Host-selected gateway credential required.",
                        )
                    ).encode(),
                )
                return False

            def do_GET(self):
                if not self._authorized():
                    return
                if self.path != "/status":
                    self.send_error(404)
                    return
                self._send(
                    200, "application/json", json.dumps(gateway.status()).encode()
                )

            def do_POST(self):
                if not self._authorized():
                    return
                if self.path != "/v1/responses":
                    self.send_error(501)
                    return
                try:
                    if self.headers.get("Transfer-Encoding"):
                        raise ValueError("chunked request unsupported")
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= MAX_BODY:
                        raise ValueError("request body out of protocol bounds")
                    body = json.loads(self.rfile.read(length))
                    result = gateway.execute(body)
                    self._send(*result)
                except (OSError, ValueError, KeyError, TypeError, WakeError) as error:
                    self._send(
                        403 if isinstance(error, PermissionDenied) else 400,
                        "application/json",
                        json.dumps(
                            _error("governor_request_unqualified", str(error)[:160])
                        ).encode(),
                    )

        server = ThreadingHTTPServer((host, port), Handler)
        self.bind_listener(f"http://{host}:{server.server_port}")
        return server

    def bind_listener(self, url):
        """Pin a host-owned listener (including an authenticated bootstrap delegate)."""
        parsed = urlsplit(url)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or not parsed.port
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
        ):
            raise ValueError("owned loopback listener origin required")
        with (
            supervision._lock(self.directory, "maintenance"),
            supervision._lock(self.directory, supervision._name(self.source_thread)),
        ):
            source = json.loads(self.source_path.read_text())
            if source["request_accounting"].get("gateway_url") != url or "resources" not in source["request_accounting"]:
                source["request_accounting"]["resources"] = self._resource_summary()
            source["request_accounting"]["gateway_url"] = url
            supervision._save_request_accounting(self.source_path, source)
            supervision._record_supervision_notice(
                self.source_path, source, "request_activation"
            )
            supervision._save(self.source_path, source)
            event = source.get("notice_ids", {}).get("request_activation")
        if event:
            from .goal_notices import present_notice

            present_notice(self.root, event)


def qualify_gateway(root, profile, thread):
    """Fresh selected-provider inspection; no claim about bypass transports."""
    import tomllib
    from urllib.request import urlopen

    path = supervision._directory(root) / (supervision._name(thread) + ".json")
    supervision._private(path)
    receipt = json.loads(path.read_text())
    binding = receipt.get("request_accounting") or {}
    url = binding.get("gateway_url")
    if not url:
        raise ValueError("no selected HTTP request gateway binding")
    home = Path(receipt["grant"]["codex_home"])
    config_path = home / "config.toml"
    config_bytes = config_path.read_bytes()
    config = tomllib.loads(config_bytes.decode())
    provider = config.get("model_provider")
    selected = config.get("model_providers", {}).get(provider, {})
    if (
        selected.get("base_url", "").rstrip("/") != url + "/v1"
        or selected.get("supports_websockets") is not False
        or selected.get("wire_api") != "responses"
    ):
        raise ValueError(
            "selected native provider is not the qualified HTTP gateway path"
        )
    native = supervision._request(
        receipt["grant"], "thread/read", dict(threadId=thread, includeTurns=False)
    )["thread"]
    if native.get("modelProvider") != provider:
        raise ValueError(
            "native thread selected provider differs from host configuration"
        )
    token_path = Path(binding["gateway_token_file"])
    expected = supervision._directory(root) / (
        "request-gateway-"
        + hashlib.sha256(receipt["allocation_id"].encode()).hexdigest()
        + ".token"
    )
    if token_path != expected:
        raise ValueError("gateway credential scope differs")
    supervision._private(token_path)
    request = Request(
        url + "/status", headers={"Authorization": "Bearer " + token_path.read_text()}
    )
    with urlopen(request, timeout=1) as response:
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("gateway status exceeds inspection bound")
        status = json.loads(raw)
    if (
        status.get("scope") != receipt["allocation_id"]
        or status.get("source_thread_id") != thread
        or status.get("contract_sha256") != binding.get("contract_sha256")
        or status.get("mode") not in ("hard_admission", "degraded")
        or not status.get("reviewed_provider_contract")
        or not status.get("activation", {}).get("qualified")
    ):
        raise ValueError("gateway contract/scope/accounting is unavailable")
    if config_path.read_bytes() != config_bytes:
        raise ValueError("native provider configuration changed during qualification")
    ready = status["accounting"]["ready"]
    known = status["accounting"]["accounting_known"]
    return dict(
        mode="hard_admission" if known else "degraded",
        admitted=ready,
        reason="qualified_selected_http_request_path"
        if ready
        else "objective_resources_unavailable"
        if known
        else "request_accounting_unknown",
        scope=receipt["allocation_id"],
        gateway=url,
        contract_sha256=status["contract_sha256"],
        config_sha256=hashlib.sha256(config_bytes).hexdigest(),
        accounting=status["accounting"],
        maximum_token_overshoot=0,
        coverage="Only requests through this reviewed HTTP provider path. WS, compact, alternative providers and bypass routes remain unsupported.",
        message="The selected HTTP request path reserves enforceable reviewed provider bounds before each send. This is not qualification of arbitrary native/provider paths.",
    )
