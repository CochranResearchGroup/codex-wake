#!/usr/bin/env python3
"""Phased, fail-closed P53-C5 webhook ingress canary.

This source runner owns only an isolated Codex Wake runtime.  It never edits or
restarts Cooper, Traefik, a bastion, GitHub, or any external route.  Every
effectful phase requires ``--execute`` and an exact private canary root.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import http.client
import importlib.util
import json
import os
import ssl
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit


_INSTALLED_NAME = "webhook_installed_smoke"
if _INSTALLED_NAME in sys.modules:
    installed = sys.modules[_INSTALLED_NAME]
else:
    _installed_spec = importlib.util.spec_from_file_location(
        _INSTALLED_NAME, Path(__file__).with_name("webhook_installed_smoke.py"),
    )
    if _installed_spec is None or _installed_spec.loader is None:
        raise RuntimeError("installed webhook qualification primitives are unavailable")
    installed = importlib.util.module_from_spec(_installed_spec)
    sys.modules[_INSTALLED_NAME] = installed
    _installed_spec.loader.exec_module(installed)


SOURCE = "p53-c5-ingress-canary"
UNIT = f"codex-wake-github-webhook-{SOURCE}.service"
HOST = "127.0.0.1"
PORT = 8820
STATE_FILE = "c5-private-state.json"
RECEIPT_VERSION = 1
CHECKPOINTS = ("raw", "local", "cooper_host", "public")
ENDPOINTS = {
    "raw": ("http://127.0.0.1:8820", None),
    "local": ("http://codex-wake.localhost", None),
    "cooper_host": (
        "http://192.168.50.108", "codex-wake.ecochran.dyndns.org",
    ),
    "public": ("https://codex-wake.ecochran.dyndns.org", None),
}
FIXTURE_LIFETIME = timedelta(minutes=15)
PUBLICATION_WINDOW = timedelta(minutes=10)


@contextmanager
def c5_contract() -> Iterator[None]:
    """Apply the distinct C5 identity to the reused qualification primitives."""
    previous = installed.SOURCE, installed.UNIT, installed.HOST, installed.PORT
    installed.SOURCE, installed.UNIT = SOURCE, UNIT
    installed.HOST, installed.PORT = HOST, PORT
    try:
        yield
    finally:
        installed.SOURCE, installed.UNIT, installed.HOST, installed.PORT = previous


def create_root(env: dict[str, str] | None = None) -> Path:
    source = os.environ if env is None else env
    configured = source.get("XDG_STATE_HOME")
    state_home = Path(configured).expanduser() if configured else Path.home() / ".local/state"
    if not state_home.is_absolute():
        raise ValueError("XDG_STATE_HOME must be absolute")
    parent = (state_home / "codex-wake" / "qualification").resolve()
    if any(parent == item or parent.is_relative_to(item) for item in (Path("/tmp"), Path("/var/tmp"))):
        raise ValueError("execution state must not resolve under a temporary directory")
    installed.owner_only_directory(parent)
    root = Path(tempfile.mkdtemp(prefix="p53-c5-ingress-", dir=parent))
    os.chmod(root, 0o700)
    return root


def context_for(root: Path) -> installed.ExecutionContext:
    root = root.resolve()
    return installed.ExecutionContext(
        root=root,
        artifact_dir=root / "evidence",
        wake_root=root / "wake",
        manager_unit_dir=installed.manager_unit_dir(),
        fixture_dir=root / "fixture",
        installed_cli=root / "venv/bin/codex-wake",
        installed_listener=root / "venv/bin/codex-wake-github-webhook",
        installed_python=root / "venv/bin/python",
        service_name=UNIT,
    )


def state_path(root: Path) -> Path:
    return root.resolve() / STATE_FILE


def write_private(root: Path, value: dict[str, Any]) -> None:
    path = state_path(root)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def load_private(root: Path) -> dict[str, Any]:
    if root.is_symlink():
        raise RuntimeError("private C5 canary root must not be a symlink")
    root = root.resolve()
    path = state_path(root)
    if root.name.startswith("p53-c5-ingress-") is False or not path.is_file() or path.is_symlink():
        raise RuntimeError("exact private C5 canary state is unavailable")
    if path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise RuntimeError("private C5 canary state ownership or mode is unsafe")
    if root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise RuntimeError("private C5 canary root ownership or mode is unsafe")
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict or value.get("source") != SOURCE or value.get("root") != str(root):
        raise RuntimeError("private C5 canary identity is invalid")
    return value


def fixture_from(state: dict[str, Any]) -> installed.Fixture:
    fixture = state["fixture"]
    return installed.Fixture(
        secret=str(fixture["secret"]),
        body=base64.b64decode(str(fixture["body_b64"]), validate=True),
        delivery_id=str(fixture["delivery_id"]),
        restart_delivery_id=str(fixture["restart_delivery_id"]),
        workflow=dict(fixture["workflow"]),
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


def fixture_freshness(
    state: dict[str, Any], *, minimum_remaining: timedelta = timedelta(0),
) -> dict[str, Any]:
    created = datetime.fromisoformat(str(state["fixture_created_at"]))
    deadline = datetime.fromisoformat(str(state["fixture_deadline"]))
    now = utc_now()
    if (
        created.tzinfo is None or deadline.tzinfo is None
        or deadline - created != FIXTURE_LIFETIME
        or now < created - timedelta(seconds=30) or now >= deadline
    ):
        raise RuntimeError("fixture freshness is invalid or expired")
    remaining = deadline - now
    if remaining < minimum_remaining:
        raise RuntimeError("fixture publication window is insufficient")
    return {
        "created_at": created.isoformat(), "deadline": deadline.isoformat(),
        "remaining_seconds": int(remaining.total_seconds()),
    }


def require_request_freshness(deadline: datetime) -> None:
    if deadline.tzinfo is None or utc_now() >= deadline:
        raise RuntimeError("fixture expired before request")


def counter_path(context: installed.ExecutionContext) -> Path:
    return context.fixture_dir / "effect-counters.json"


def initialize_counters(context: installed.ExecutionContext) -> None:
    installed.owner_only_directory(context.fixture_dir)
    path = counter_path(context)
    path.write_text(json.dumps({
        "authoritative_attempt_reads": 0,
        "production_provider_factory_calls": 0,
        "dispatch_calls": 0,
    }, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def read_counters(context: installed.ExecutionContext) -> dict[str, int]:
    path = counter_path(context)
    if not path.is_file() or path.is_symlink() or path.stat().st_mode & 0o077:
        raise RuntimeError("effect counters are unavailable or unsafe")
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "authoritative_attempt_reads", "production_provider_factory_calls",
        "dispatch_calls",
    }
    if type(value) is not dict or set(value) != expected or any(
        type(value[name]) is not int or value[name] < 0 for name in expected
    ):
        raise RuntimeError("effect counters are invalid")
    return value


def receipt_path(state: dict[str, Any]) -> Path:
    return Path(str(state["receipt"])).resolve()


def stage(state: dict[str, Any], receipt: dict[str, Any]) -> None:
    secret = str(state.get("fixture", {}).get("secret", ""))
    installed.stage_receipt(
        receipt, destination=receipt_path(state), secret_values=(secret,),
    )


def base_receipt(context: installed.ExecutionContext) -> dict[str, Any]:
    return {
        "schema_version": RECEIPT_VERSION,
        "source": SOURCE,
        "unit": UNIT,
        "loopback": f"{HOST}:{PORT}",
        "root": str(context.root),
        "phase": "preparing",
        "overall": "in_progress",
        "external_provider_access": "absent_by_fixture_bootstrap",
        "dispatch": "absent",
        "external_route_mutations": 0,
        "service_attempts": 0,
        "checkpoints": {},
    }


def canonical_candidate(
    root: Path, artifact_dir: Path,
) -> dict[str, str]:
    provenance = installed.clean_candidate(root, artifact_dir)
    canonical_ref = "refs/remotes/origin/main"
    canonical_sha = installed.run_command(
        ["git", "-C", str(root), "rev-parse", canonical_ref],
        artifact_dir=artifact_dir, name="canonical-main",
    ).stdout.strip()
    if provenance["commit"] != canonical_sha or len(canonical_sha) != 40:
        raise RuntimeError("clean candidate HEAD is not the fetched origin/main")
    return {**provenance, "canonical_ref": canonical_ref,
            "canonical_sha": canonical_sha}


def prepare(destination: Path) -> int:
    root = create_root()
    context = context_for(root)
    destination = destination.resolve()
    if destination.is_relative_to(root):
        raise ValueError("receipt must remain outside the disposable canary root")
    receipt = base_receipt(context)
    state: dict[str, Any] = {
        "source": SOURCE, "root": str(root), "receipt": str(destination),
        "phase": "preparing", "service_attempts": 0,
        "successful_checkpoints": [],
    }
    write_private(root, state)
    stage(state, receipt)
    try:
        manager, failed = installed.manager_preflight(context)
        if context.unit_path.exists() or context.unit_path.is_symlink():
            raise RuntimeError("exact service unit already exists")
        if not installed.port_is_free():
            raise RuntimeError("exact loopback port is occupied")
        if installed.matching_processes(context):
            raise RuntimeError("matching canary process already exists")
        provenance = canonical_candidate(installed.repo_root(), context.artifact_dir)
        export = root / "export"
        installed.export_clean_tree(installed.repo_root(), export, context.artifact_dir)
        wheel = installed.build_wheel(export, root / "wheel", context.artifact_dir)
        build_env = installed.isolated_build_env()
        installed.run_command(
            [sys.executable, "-m", "venv", str(root / "venv")],
            artifact_dir=context.artifact_dir, name="create-venv", env=build_env,
        )
        installed.run_command(
            [str(root / "venv/bin/pip"), "install", "--no-deps", str(wheel)],
            artifact_dir=context.artifact_dir, name="install-wheel", env=build_env,
        )
        env = installed.installed_env(context)
        provenance.update({
            "wheel_sha256": installed.sha256(wheel),
            "installed_cli_sha256": installed.sha256(context.installed_cli),
            "installed_listener_sha256": installed.sha256(context.installed_listener),
            **installed.installed_provenance(context, env),
        })
        tracked: list[tuple[int, str]] = []
        wake_id, reader = installed.configure_and_arm(
            context, env, tracked_identities=tracked,
        )
        state.update({
            "phase": "prepared", "failed_units_before": list(failed),
            "tracked_identities": tracked, "wake_id": wake_id,
            "successful_checkpoints": [],
        })
        write_private(root, state)
        receipt.update({
            "phase": "prepared", "manager_state": manager,
            "failed_units_before": list(failed), "provenance": provenance,
            "wake_id": wake_id, "managed_reader": reader,
            "next_command": f"{Path(__file__).resolve()} start --execute --root {root}",
        })
        stage(state, receipt)
        print(json.dumps({"root": str(root), "receipt": str(destination), "phase": "prepared"}, sort_keys=True))
        return 0
    except Exception as exc:
        state["phase"] = "prepare_failed"
        state["error"] = type(exc).__name__
        write_private(root, state)
        receipt.update({"phase": "prepare_failed", "overall": "failed", "error": type(exc).__name__, "recovery_root": str(root)})
        stage(state, receipt)
        print(json.dumps(installed.sanitize_receipt(receipt), sort_keys=True))
        return 1


def read_receipt(state: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(receipt_path(state).read_text(encoding="utf-8"))
    required = {
        "schema_version": RECEIPT_VERSION, "source": SOURCE,
        "root": state.get("root"), "unit": UNIT,
        "loopback": f"{HOST}:{PORT}",
    }
    if type(value) is not dict or any(
        value.get(name) != expected for name, expected in required.items()
    ) or ("wake_id" in state and value.get("wake_id") != state["wake_id"]):
        raise RuntimeError("external receipt identity is invalid")
    return value


def start(root: Path) -> int:
    state = load_private(root)
    context = context_for(root)
    receipt = read_receipt(state)
    if state.get("phase") != "prepared" or state.get("service_attempts") != 0:
        raise RuntimeError("canary is not at the one-shot prepared boundary")
    if not installed.port_is_free() or context.unit_path.exists() or context.unit_path.is_symlink():
        raise RuntimeError("service pre-effect absence check failed")
    state["phase"] = "fixture_preparing"
    write_private(context.root, state)
    receipt["phase"] = "fixture_preparing"
    stage(state, receipt)
    try:
        fixture = installed.make_fixture()
        created = datetime.fromisoformat(
            str(fixture.workflow["terminal_proof_at"]),
        )
        state.update({
            "fixture_created_at": created.isoformat(),
            "fixture_deadline": (created + FIXTURE_LIFETIME).isoformat(),
            "fixture": {
                "secret": fixture.secret,
                "body_b64": base64.b64encode(fixture.body).decode("ascii"),
                "delivery_id": fixture.delivery_id,
                "restart_delivery_id": fixture.restart_delivery_id,
                "workflow": fixture.workflow,
            },
            "security_header_fingerprint": security_header_fingerprint(fixture),
        })
        initialize_counters(context)
        installed.write_fixture_bootstrap(
            context, fixture, counter_path=counter_path(context),
        )
        installed.fixture_preflight(context, installed.installed_env(context))
        installed.write_service_environment(context, fixture)
    except Exception as exc:
        state.update({"phase": "fixture_failed", "error": type(exc).__name__})
        write_private(context.root, state)
        receipt.update({
            "phase": "fixture_failed", "overall": "failed",
            "error": type(exc).__name__, "recovery_root": str(context.root),
        })
        stage(state, receipt)
        return 1
    state.update({"phase": "service_installing", "service_attempts": 1})
    receipt.update({
        "phase": "service_installing", "service_attempts": 1,
        "request_sha256": hashlib.sha256(fixture.body).hexdigest(),
        "signed_delivery_id": fixture.delivery_id,
        "security_header_fingerprint": state["security_header_fingerprint"],
        "evidence_window": fixture_freshness(state),
    })
    write_private(context.root, state)
    stage(state, receipt)
    try:
        env = installed.installed_env(context)
        installed.service_command(
            context, "install", env=env, name="install-start",
            executable_path=context.bootstrap_path,
        )
        if not context.unit_path.is_file() or context.unit_path.is_symlink():
            raise RuntimeError("installed unit ownership is invalid")
        readiness, status, support, identity = installed.wait_ready(context, env)
        tracked = [tuple(item) for item in state.get("tracked_identities", [])]
        tracked.append((int(identity["pid"]), str(identity["process_start_ticks"])))
        state.update({"phase": "running", "tracked_identities": tracked})
        write_private(context.root, state)
        receipt.update({
            "phase": "running", "unit_sha256": installed.sha256(context.unit_path),
            "readiness": readiness, "status": status, "support": support,
            "service_identity": identity,
            "next_command": f"{Path(__file__).resolve()} probe --execute --root {context.root} --checkpoint raw --url http://127.0.0.1:8820",
        })
        stage(state, receipt)
        print(json.dumps({"root": str(context.root), "phase": "running"}, sort_keys=True))
        return 0
    except Exception as exc:
        state.update({"phase": "service_uncertain", "error": type(exc).__name__})
        write_private(context.root, state)
        receipt.update({"phase": "service_uncertain", "overall": "failed", "error": type(exc).__name__, "recovery_root": str(context.root)})
        stage(state, receipt)
        return 1


def security_header_fingerprint(fixture: installed.Fixture) -> str:
    signature = hmac.new(
        fixture.secret.encode("utf-8"), fixture.body, hashlib.sha256,
    ).hexdigest()
    values = {
        "content_type": "application/json", "event": "workflow_run",
        "delivery": fixture.delivery_id, "signature": f"sha256={signature}",
    }
    return hashlib.sha256(
        json.dumps(values, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def exchange(url: str, fixture: installed.Fixture, delivery_id: str, *,
             method: str = "POST", path: str = "/github/webhook",
             signed: bool = True, host_header: str | None = None,
             deadline: datetime | None = None) -> dict[str, Any]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.query or parsed.fragment:
        raise ValueError("probe URL must be one absolute HTTP(S) origin")
    if parsed.path not in {"", "/"}:
        raise ValueError("probe URL must not include a path")
    if deadline is None:
        raise ValueError("fixture deadline is required")
    require_request_freshness(deadline)
    body = fixture.body
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "workflow_run",
        "X-GitHub-Delivery": delivery_id,
    }
    if host_header:
        headers["Host"] = host_header
    if signed:
        digest = hmac.new(fixture.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        headers["X-Hub-Signature-256"] = f"sha256={digest}"
    connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    kwargs: dict[str, Any] = {"timeout": 15}
    if parsed.scheme == "https":
        kwargs["context"] = ssl.create_default_context()
    connection = connection_type(parsed.hostname, parsed.port, **kwargs)
    try:
        require_request_freshness(deadline)
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        content = response.read()
        response_headers = tuple(response.getheaders())
    finally:
        connection.close()
    code = None
    try:
        decoded = json.loads(content)
        if type(decoded) is dict and type(decoded.get("code")) is str:
            code = decoded["code"]
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    forbidden = (
        fixture.secret.encode(), b"8820", b"/home/", b"/github/webhook.env",
        b"configuration_identity", b"service_identity",
    )
    serialized_headers = repr(response_headers).encode("utf-8")
    return {
        "status": response.status, "code": code,
        "body_sha256": hashlib.sha256(content).hexdigest(),
        "body_bytes": len(content),
        "response_header_names": sorted(name.lower() for name, _ in response_headers),
        "leak_free": not any(value and (value in content or value in serialized_headers) for value in forbidden),
    }


def snapshot(context: installed.ExecutionContext, state: dict[str, Any]) -> dict[str, Any]:
    code = (
        "import json,sqlite3,sys;from pathlib import Path;"
        "r=Path(sys.argv[1]);w=sys.argv[2];db=r/'signals'/'journal.sqlite3';"
        "c=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True);"
        "print(json.dumps({'receipts':c.execute(\"SELECT COUNT(*) FROM receipts WHERE source='github' AND source_instance=?\",(sys.argv[3],)).fetchone()[0],"
        "'matches':c.execute('SELECT COUNT(*) FROM match_reservations WHERE wake_id=?',(w,)).fetchone()[0],"
        "'pending':int((r/'pending'/(w+'.json')).is_file()),'firing':int((r/'firing'/(w+'.json')).is_file()),"
        "'submitted':int((r/'submitted'/(w+'.json')).is_file()),'failed':int((r/'failed'/(w+'.json')).is_file())}))"
    )
    result = installed.run_command(
        [str(context.installed_python), "-I", "-c", code, str(context.wake_root), str(state["wake_id"]), SOURCE],
        artifact_dir=context.artifact_dir, name="state-snapshot",
    )
    value = json.loads(result.stdout)
    if value.get("submitted") or value.get("failed"):
        raise RuntimeError("canary reached a dispatch terminal state")
    return value


def probe(root: Path, checkpoint: str, url: str, host_header: str | None) -> int:
    state = load_private(root)
    if state.get("phase") != "running" or checkpoint not in CHECKPOINTS:
        raise RuntimeError("canary is not running or checkpoint is invalid")
    expected_endpoint = ENDPOINTS[checkpoint]
    if (url, host_header) != expected_endpoint:
        raise RuntimeError("checkpoint endpoint or Host contract is invalid")
    context = context_for(root)
    fixture = fixture_from(state)
    if security_header_fingerprint(fixture) != state.get("security_header_fingerprint"):
        raise RuntimeError("frozen security header identity is invalid")
    receipt = read_receipt(state)
    previous = receipt.get("checkpoints", {})
    successful = state.get("successful_checkpoints")
    if type(successful) is not list:
        raise RuntimeError("private checkpoint progression is invalid")
    if checkpoint in previous:
        raise RuntimeError("checkpoint already consumed")
    prefix = CHECKPOINTS[:len(successful)]
    expected = CHECKPOINTS[len(successful)] if len(successful) < len(CHECKPOINTS) else None
    expected_receipt_phase = (
        "running" if not successful else f"{successful[-1]}_checked"
    )
    if (
        tuple(successful) != prefix or checkpoint != expected
        or set(previous) != set(prefix) or len(previous) != len(prefix)
        or any(previous[name].get("accepted") is not True for name in prefix)
        or receipt.get("overall") != "in_progress"
        or receipt.get("phase") != expected_receipt_phase
    ):
        raise RuntimeError("checkpoint order is invalid")
    minimum = PUBLICATION_WINDOW if checkpoint == "cooper_host" else timedelta(0)
    freshness = fixture_freshness(state, minimum_remaining=minimum)
    receipt.setdefault("checkpoints", {})[checkpoint] = {
        "accepted": False, "stage": "probing", "url_origin": url,
        "host_header": host_header, "evidence_window": freshness,
    }
    receipt["phase"] = f"{checkpoint}_probing"
    stage(state, receipt)
    deadline = datetime.fromisoformat(str(state["fixture_deadline"]))
    try:
        observations = {
            "signed_exact": exchange(
                url, fixture, fixture.delivery_id, host_header=host_header,
                deadline=deadline,
            ),
            "unsigned_exact": exchange(
                url, fixture, str(uuid.uuid4()), signed=False,
                host_header=host_header, deadline=deadline,
            ),
            "wrong_path": exchange(
                url, fixture, str(uuid.uuid4()), path="/github/webhook-wrong",
                host_header=host_header, deadline=deadline,
            ),
            "wrong_method": exchange(
                url, fixture, str(uuid.uuid4()), method="GET",
                host_header=host_header, deadline=deadline,
            ),
        }
    except Exception as exc:
        receipt["checkpoints"][checkpoint].update({
            "stage": "failed", "error": type(exc).__name__,
        })
        receipt.update({"phase": f"{checkpoint}_failed", "overall": "failed"})
        state.update({"phase": "probe_failed", "failed_checkpoint": checkpoint})
        write_private(context.root, state)
        stage(state, receipt)
        return 1
    try:
        expected_signed_codes = {"COMMITTED", "DUPLICATE"}
        if checkpoint == "raw":
            accepted = (
                observations["signed_exact"]["status"] == 200
                and observations["signed_exact"]["code"] == "COMMITTED"
                and (observations["unsigned_exact"]["status"], observations["unsigned_exact"]["code"]) == (401, "SIGNATURE_INVALID")
                and (observations["wrong_path"]["status"], observations["wrong_path"]["code"]) == (404, "ROUTE")
                and (observations["wrong_method"]["status"], observations["wrong_method"]["code"]) == (405, "METHOD")
            )
        else:
            accepted = (
                observations["signed_exact"]["status"] == 200
                and observations["signed_exact"]["code"] in expected_signed_codes
                and observations["unsigned_exact"]["status"] == 401
                and observations["wrong_path"]["status"] in {404, 405}
                and observations["wrong_method"]["status"] in {404, 405}
            )
        accepted = accepted and all(
            item["leak_free"] for item in observations.values()
        )
        state_view = snapshot(context, state)
        counters = read_counters(context)
        expected_reads = len(successful) + 1
        accepted = accepted and state_view == {
            "receipts": 1, "matches": 0, "pending": 1, "firing": 0,
            "submitted": 0, "failed": 0,
        } and counters == {
            "authoritative_attempt_reads": expected_reads,
            "production_provider_factory_calls": 0,
            "dispatch_calls": 0,
        }
        if checkpoint == "cooper_host":
            freshness = fixture_freshness(
                state, minimum_remaining=PUBLICATION_WINDOW,
            )
    except Exception as exc:
        receipt["checkpoints"][checkpoint].update({
            "stage": "failed", "error": type(exc).__name__,
        })
        receipt.update({"phase": f"{checkpoint}_failed", "overall": "failed"})
        state.update({"phase": "probe_failed", "failed_checkpoint": checkpoint})
        write_private(context.root, state)
        stage(state, receipt)
        return 1
    checkpoint_receipt = {
        "accepted": accepted, "stage": "checked", "url_origin": url,
        "host_header": host_header,
        "request_sha256": hashlib.sha256(fixture.body).hexdigest(),
        "signed_delivery_id": fixture.delivery_id,
        "security_header_fingerprint": state["security_header_fingerprint"],
        "evidence_window": freshness, "effect_counters": counters,
        "observations": observations, "state": state_view,
        "external_provider_access": "absent_by_fixture_bootstrap", "dispatch": "absent",
    }
    receipt.setdefault("checkpoints", {})[checkpoint] = checkpoint_receipt
    receipt["phase"] = f"{checkpoint}_checked"
    if not accepted:
        receipt["overall"] = "failed"
        state.update({"phase": "probe_failed", "failed_checkpoint": checkpoint})
    else:
        state["successful_checkpoints"] = [*successful, checkpoint]
    write_private(context.root, state)
    stage(state, receipt)
    print(json.dumps(installed.sanitize_receipt(checkpoint_receipt, secret_values=(fixture.secret,)), sort_keys=True))
    return 0 if accepted else 1


def cleanup(root: Path) -> int:
    state = load_private(root)
    context = context_for(root)
    fixture = fixture_from(state) if "fixture" in state else None
    receipt = read_receipt(state)
    attempted = int(state.get("service_attempts", 0)) == 1
    tracked = tuple((int(item[0]), str(item[1])) for item in state.get("tracked_identities", []))
    checkpoints = receipt.get("checkpoints", {})
    acceptance = (
        tuple(state.get("successful_checkpoints", ())) == CHECKPOINTS
        and set(checkpoints) == set(CHECKPOINTS)
        and len(checkpoints) == len(CHECKPOINTS)
        and all(
            type(value) is dict and value.get("accepted") is True
            for value in checkpoints.values()
        )
        and receipt.get("overall") == "in_progress"
        and receipt.get("phase") == "public_checked"
    )
    with c5_contract():
        result = installed.cleanup(
            context, env=installed.installed_env(context), service_attempted=attempted,
            failed_units_before=tuple(state.get("failed_units_before", [])),
            tracked_identities=tracked,
            preserve_root_on_safe=not acceptance,
        )
    receipt["cleanup"] = result
    receipt["phase"] = "cleaned" if result.get("safe") else "cleanup_uncertain"
    receipt["overall"] = (
        "accepted" if result.get("safe") and acceptance else "failed"
    )
    installed.stage_receipt(
        receipt, destination=receipt_path(state),
        secret_values=((fixture.secret,) if fixture else ()),
    )
    print(json.dumps({"phase": receipt["phase"], "overall": receipt["overall"], "cleanup": result}, sort_keys=True))
    return 0 if result.get("safe") and acceptance else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--execute", action="store_true")
    prepare_parser.add_argument("--receipt", required=True, type=Path)
    for name in ("start", "cleanup"):
        child = subparsers.add_parser(name)
        child.add_argument("--execute", action="store_true")
        child.add_argument("--root", required=True, type=Path)
    probe_parser = subparsers.add_parser("probe")
    probe_parser.add_argument("--execute", action="store_true")
    probe_parser.add_argument("--root", required=True, type=Path)
    probe_parser.add_argument("--checkpoint", required=True, choices=CHECKPOINTS)
    probe_parser.add_argument("--url", required=True)
    probe_parser.add_argument("--host-header")
    args = parser.parse_args(argv)
    if not args.execute:
        print("ingress canary refuses by default; pass --execute only for the authorized phase", file=sys.stderr)
        return 2
    with c5_contract():
        if args.command == "prepare":
            return prepare(args.receipt)
        if args.command == "start":
            return start(args.root)
        if args.command == "probe":
            return probe(args.root, args.checkpoint, args.url, args.host_header)
        return cleanup(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
