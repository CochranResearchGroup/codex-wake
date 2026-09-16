#!/usr/bin/env python3
"""Provider-free, injected P53-C6 GitHub webhook qualification runner.

The default command is a read-only frozen preflight. The runner intentionally
contains no GitHub transport, PR merge, network, subprocess, systemd, or
dispatch implementation. Its local runtime contract accepts explicit injected
effectors so an authorized primary can execute a bounded packet while unit
tests exercise every effect with fakes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


SOURCE = "p53-c6-live-github"
UNIT = f"codex-wake-github-webhook-{SOURCE}.service"
LISTENER = "127.0.0.1:8820"
GITHUB_HOST = "github.com"
GITHUB_ACTOR = "ecochran76"
REPOSITORY = "CochranResearchGroup/codex-wake"
REPOSITORY_ID = 1242753508
WORKFLOW_ID = 279450573
WORKFLOW_PATH = ".github/workflows/ci.yml"
REF = "refs/heads/main"
CONCLUSION = "success"
CALLBACK_URL = "https://codex-wake.ecochran.dyndns.org/github/webhook"
TOKEN_REF = "CODEX_WAKE_P53_C6_GITHUB_TOKEN"
SECRET_REF = "CODEX_WAKE_P53_C6_WEBHOOK_SECRET"
STATE_FILE = "c6-private-state.json"
RECEIPT_VERSION = 2
PRIVATE_ROOT_PREFIX = "p53-c6-live-github-"
_COUNTERS = ("create", "trigger", "delete", "redelivery", "dispatch")
_RUNTIME_COUNTERS = ("establish", "cleanup", "secret_provision", "secret_retirement", "observation")
_ENV_VALUE = re.compile(r"[A-Za-z0-9_.=-]+")


@dataclass(frozen=True)
class FrozenIdentity:
    github_host: str = GITHUB_HOST
    actor: str = GITHUB_ACTOR
    repository: str = REPOSITORY
    repository_id: int = REPOSITORY_ID
    workflow_id: int = WORKFLOW_ID
    workflow_path: str = WORKFLOW_PATH
    ref: str = REF
    conclusion: str = CONCLUSION
    callback_url: str = CALLBACK_URL
    source_instance: str = SOURCE
    unit: str = UNIT
    listener: str = LISTENER
    token_ref: str = TOKEN_REF
    secret_ref: str = SECRET_REF


@dataclass(frozen=True)
class ProviderRequest:
    action: str
    method: str
    path: str
    body: dict[str, Any]


@dataclass(frozen=True)
class RuntimeEffectors:
    """The only runtime-effect boundary. Every callable is caller-injected."""

    canonical_candidate: Callable[[Path], Mapping[str, Any]]
    build_wheel: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]
    create_venv: Callable[[Path], Mapping[str, Any]]
    install_wheel: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]
    configure_source: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]
    initialize_daemon: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]
    configure_listener: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]
    install_service: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]
    readiness: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]
    uninstall_service: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]
    runtime_census: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]
    unrelated_state: Callable[[Path, Mapping[str, Any]], Mapping[str, Any]]


def frozen_identity() -> FrozenIdentity:
    return FrozenIdentity()


def build_provider_request(action: str, *, secret: str | None = None,
                           hook_id: int | None = None) -> ProviderRequest:
    """Build a request only. This module provides no transport for it."""
    if action == "create":
        if type(secret) is not str or not secret:
            raise ValueError("create request requires a non-empty in-memory secret")
        return ProviderRequest("create", "POST", f"/repos/{REPOSITORY}/hooks", {
            "name": "web", "active": True, "events": ["workflow_run"],
            "config": {"url": CALLBACK_URL, "content_type": "json",
                       "insecure_ssl": "0", "secret": secret},
        })
    if action == "trigger":
        return ProviderRequest("trigger", "EXTERNAL", "primary-owned-pr-merge", {
            "required_ref": REF, "workflow_id": WORKFLOW_ID,
            "workflow_path": WORKFLOW_PATH, "merge_attempts": 1,
        })
    if action == "delete":
        if type(hook_id) is not int or hook_id <= 0:
            raise ValueError("delete request requires the returned positive hook ID")
        return ProviderRequest("delete", "DELETE", f"/repos/{REPOSITORY}/hooks/{hook_id}", {})
    raise ValueError("unknown provider lifecycle action")


def _hook_projection(response: Mapping[str, Any]) -> dict[str, Any]:
    config = response.get("config")
    if not isinstance(config, Mapping):
        raise RuntimeError("hook response mismatch: missing config")
    return {"hook_id": response.get("id"), "active": response.get("active"),
            "events": response.get("events"), "url": config.get("url"),
            "content_type": config.get("content_type"),
            "insecure_ssl": str(config.get("insecure_ssl"))}


def validate_hook_response(response: Mapping[str, Any]) -> dict[str, Any]:
    observed = _hook_projection(response)
    expected = {"active": True, "events": ["workflow_run"], "url": CALLBACK_URL,
                "content_type": "json", "insecure_ssl": "0"}
    if (type(observed["hook_id"]) is not int or observed["hook_id"] <= 0
            or any(observed[key] != value for key, value in expected.items())):
        raise RuntimeError("hook response mismatch")
    return observed


def sanitize_for_receipt(value: Any, *, secrets: tuple[str, ...] = ()) -> Any:
    hidden = ("secret", "token", "authorization", "payload", "body", "environment")
    if isinstance(value, Mapping):
        return {str(key): "[redacted]" if (
            not str(key).lower().endswith("_ref")
            and any(part in str(key).lower() for part in hidden)
        ) else sanitize_for_receipt(item, secrets=secrets) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_for_receipt(item, secrets=secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[redacted]")
    return value


def _contains_secret(value: Any, secret_values: tuple[str, ...]) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_secret(item, secret_values) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_secret(item, secret_values) for item in value)
    return isinstance(value, str) and any(secret and secret in value for secret in secret_values)


def sanitized_request_summary(request: ProviderRequest, *, secrets: tuple[str, ...] = ()) -> dict[str, Any]:
    serialized = json.dumps(request.body, sort_keys=True, separators=(",", ":"))
    return {"action": request.action, "method": request.method, "path": request.path,
            "request_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
            "body": sanitize_for_receipt(request.body, secrets=secrets)}


def _is_temporary(path: Path) -> bool:
    resolved = path.resolve()
    return any(resolved == item or resolved.is_relative_to(item)
               for item in (Path("/tmp").resolve(), Path("/var/tmp").resolve()))


def qualification_directory(env: Mapping[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    state_home = Path(values.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))).expanduser()
    if not state_home.is_absolute() or _is_temporary(state_home):
        raise RuntimeError("XDG_STATE_HOME must be absolute and outside temporary roots")
    return state_home / "codex-wake" / "qualification"


def create_private_root(*, env: Mapping[str, str] | None = None, armed: bool = False) -> Path:
    if not armed:
        raise RuntimeError("private-root creation requires explicit execution arm")
    parent = qualification_directory(env)
    parent.mkdir(parents=True, exist_ok=True)
    if any(item.is_symlink() for item in (parent, parent.parent, parent.parent.parent)) or parent.stat().st_uid != os.getuid():
        raise RuntimeError("governed qualification directory is unsafe")
    os.chmod(parent, 0o700)
    root = Path(tempfile.mkdtemp(prefix=PRIVATE_ROOT_PREFIX, dir=parent))
    os.chmod(root, 0o700)
    return exact_private_root(root, env=env)


def exact_private_root(root: Path, *, env: Mapping[str, str] | None = None) -> Path:
    if not root.is_absolute() or root.is_symlink() or not root.name.startswith(PRIVATE_ROOT_PREFIX):
        raise RuntimeError("exact private root is required")
    parent = qualification_directory(env)
    if (any(item.is_symlink() for item in (parent, parent.parent, parent.parent.parent))
            or root.parent != parent or _is_temporary(root)):
        raise RuntimeError("exact private root is outside the governed qualification directory")
    if not root.exists() or not root.is_dir() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise RuntimeError("exact private root ownership or mode is unsafe")
    return root.resolve()


def _state_path(root: Path) -> Path:
    return root / STATE_FILE


def new_state(root: Path, receipt: Path) -> dict[str, Any]:
    return {"schema_version": RECEIPT_VERSION, "source": SOURCE, "root": str(root.resolve()),
            "receipt": str(receipt.resolve()), "phase": "prepared",
            "requires_exact_readback": False, "counters": {name: 0 for name in _COUNTERS},
            "runtime_counters": {name: 0 for name in _RUNTIME_COUNTERS},
            "deleted_hook_id": None, "delete_readback_absent": False,
            "secret_retired": False, "runtime_cleanup_evidence": None}


def _validate_counter_set(value: Mapping[str, Any], names: tuple[str, ...], label: str) -> None:
    if set(value) != set(names) or any(type(value[name]) is not int or value[name] < 0 for name in names):
        raise RuntimeError(f"{label} counters are invalid")


def _validate_counters(value: Mapping[str, Any]) -> None:
    _validate_counter_set(value, _COUNTERS, "lifecycle")


def _validate_runtime_counters(value: Mapping[str, Any]) -> None:
    _validate_counter_set(value, _RUNTIME_COUNTERS, "runtime")


def write_private_state(root: Path, state: Mapping[str, Any], *, env: Mapping[str, str] | None = None) -> None:
    root = exact_private_root(root, env=env)
    if state.get("source") != SOURCE or state.get("root") != str(root):
        raise RuntimeError("private state identity is invalid")
    _validate_counters(state.get("counters", {}))
    _validate_runtime_counters(state.get("runtime_counters", {}))
    path = _state_path(root)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def load_private_state(root: Path, *, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    root = exact_private_root(root, env=env)
    path = _state_path(root)
    if not path.is_file() or path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise RuntimeError("private state ownership or mode is unsafe")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("source") != SOURCE or value.get("root") != str(root):
        raise RuntimeError("private state identity is invalid")
    _validate_counters(value.get("counters", {}))
    _validate_runtime_counters(value.get("runtime_counters", {}))
    return value


def stage_receipt(receipt: Mapping[str, Any], destination: Path, *, root: Path | None = None,
                  secrets: tuple[str, ...] = ()) -> None:
    destination = destination.resolve()
    if root is not None and destination.is_relative_to(root.resolve()):
        raise RuntimeError("receipt must remain outside the private root")
    safe = sanitize_for_receipt(receipt, secrets=secrets)
    if _contains_secret(safe, secrets):
        raise RuntimeError("receipt secret scan failed")
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(json.dumps(safe, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)


def receipt_for(state: Mapping[str, Any], *, cleanup: Mapping[str, Any] | None = None) -> dict[str, Any]:
    receipt: dict[str, Any] = {"schema_version": RECEIPT_VERSION, "source": SOURCE,
        "unit": UNIT, "listener": LISTENER, "phase": state["phase"],
        "identity": asdict(frozen_identity()), "counters": dict(state["counters"]),
        "runtime_counters": dict(state["runtime_counters"]),
        "requires_exact_readback": state["requires_exact_readback"], "dispatch": "disabled",
        "provider_transport": "primary_owned_injected_only"}
    for key in ("candidate", "wheel", "anchor", "trigger", "delivery", "runtime_evidence"):
        if key in state:
            receipt[key] = (
                {name: value for name, value in state[key].items() if name != "wheel_path"}
                if key == "wheel" and isinstance(state[key], Mapping)
                else state[key]
            )
    if cleanup is not None:
        receipt["cleanup"] = dict(cleanup)
    return receipt


def _stage_state(root: Path, state: Mapping[str, Any], *, secrets: tuple[str, ...] = (),
                 env: Mapping[str, str] | None = None) -> None:
    stage_receipt(receipt_for(state), Path(str(state["receipt"])), root=root, secrets=secrets)
    write_private_state(root, state, env=env)


def prepare_local(root: Path, receipt: Path, *, env: Mapping[str, str] | None = None,
                  armed: bool = False) -> dict[str, Any]:
    if not armed:
        raise RuntimeError("local preparation requires explicit execution arm")
    root = exact_private_root(root, env=env)
    if receipt.resolve().is_relative_to(root):
        raise RuntimeError("receipt must remain outside the private root")
    if any(root.iterdir()):
        raise RuntimeError("fresh preparation refuses existing lifecycle state or packet material")
    state = new_state(root, receipt)
    _stage_state(root, state, env=env)
    return receipt_for(state)


def read_token(env: Mapping[str, str]) -> str:
    token = env.get(TOKEN_REF)
    if type(token) is not str or not token:
        raise RuntimeError(f"{TOKEN_REF} is required only from the environment")
    return token


def environment_path(root: Path) -> Path:
    return root / "wake" / "github" / "webhook.env"


def provider_payload_path(root: Path) -> Path:
    return root / "provider" / "create-hook.json"


def write_webhook_environment(root: Path, *, token: str, secret: str) -> dict[str, Any]:
    if (type(token) is not str or type(secret) is not str
            or _ENV_VALUE.fullmatch(token) is None
            or _ENV_VALUE.fullmatch(secret) is None):
        raise RuntimeError("webhook environment requires fresh token and secret bytes")
    path = environment_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(f"{TOKEN_REF}={token}\n{SECRET_REF}={secret}\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    mode = stat.S_IMODE(path.stat().st_mode)
    if path.stat().st_uid != os.getuid() or mode != 0o600:
        raise RuntimeError("webhook environment ownership or mode is unsafe")
    return {"path": str(path), "owner_uid": path.stat().st_uid, "mode": oct(mode),
            "token_ref": TOKEN_REF, "secret_ref": SECRET_REF}


def write_provider_payload(root: Path, *, secret: str) -> dict[str, Any]:
    request = build_provider_request("create", secret=secret)
    path = provider_payload_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(request.body, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise RuntimeError("provider payload ownership or mode is unsafe")
    return {"path": str(path), "owner_uid": path.stat().st_uid, "mode": "0o600",
            "request_sha256": sanitized_request_summary(request, secrets=(secret,))["request_sha256"]}


def retire_webhook_environment(root: Path) -> bool:
    paths = (environment_path(root), provider_payload_path(root))
    for path in paths:
        if not path.exists():
            continue
        if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
            raise RuntimeError("secret material ownership or mode is unsafe")
        size = path.stat().st_size
        with path.open("r+b") as handle:
            handle.write(b"\0" * size)
            handle.flush()
            os.fsync(handle.fileno())
        path.unlink()
    return not any(path.exists() for path in paths)


def _count_runtime(state: Mapping[str, Any], action: str) -> dict[str, Any]:
    counters = state["runtime_counters"]
    _validate_runtime_counters(counters)
    if counters[action] != 0:
        raise RuntimeError(f"runtime {action} retry is forbidden by P53-C6")
    updated = dict(state)
    updated["runtime_counters"] = {**counters, action: 1}
    return updated


def _exact_sha(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise RuntimeError(f"{label} is not an exact SHA")
    return value


def _validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("clean") is not True or value.get("canonical_ref") != "refs/remotes/origin/main":
        raise RuntimeError("candidate is not a clean exact origin/main")
    return {"canonical_ref": "refs/remotes/origin/main", "commit": _exact_sha(value.get("commit"), "candidate commit"),
            "tree": _exact_sha(value.get("tree"), "candidate tree")}


def _expect(value: Mapping[str, Any], **expected: Any) -> dict[str, Any]:
    if any(value.get(key) != item for key, item in expected.items()):
        raise RuntimeError("injected runtime evidence mismatched the frozen contract")
    return dict(value)


def _validate_wheel_evidence(value: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "archive_ref": candidate["canonical_ref"],
        "archive_commit": candidate["commit"],
        "archive_tree": candidate["tree"],
        "build_commit": candidate["commit"],
    }
    if any(value.get(key) != item for key, item in expected.items()):
        raise RuntimeError("wheel archive is not bound to the validated canonical candidate")
    digest = value.get("wheel_sha256")
    if type(digest) is not str or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise RuntimeError("isolated wheel evidence is invalid")
    wheel_path = value.get("wheel_path")
    if type(wheel_path) is not str or not wheel_path:
        raise RuntimeError("isolated wheel path is invalid")
    return {**expected, "wheel_path": wheel_path, "wheel_sha256": digest}


def prepare_runtime(root: Path, *, env: Mapping[str, str], effectors: RuntimeEffectors,
                    secret_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32),
                    armed: bool = False) -> dict[str, Any]:
    """Execute the local-only runtime sequence exclusively through effectors."""
    if not armed:
        raise RuntimeError("runtime preparation requires explicit execution arm")
    root = exact_private_root(root, env=env)
    state = load_private_state(root, env=env)
    if state["phase"] != "prepared":
        raise RuntimeError("runtime preparation requires the exact prepared boundary")
    token = read_token(env)
    secret = secret_factory()
    if type(secret) is not str or len(secret) < 32:
        raise RuntimeError("secret factory did not produce a fresh HMAC secret")
    state = _count_runtime(state, "secret_provision")
    state.update({
        "phase": "secret_provisioning",
        "secret_material": {
            "expected_paths": [str(environment_path(root)), str(provider_payload_path(root))],
            "created": [],
        },
    })
    _stage_state(root, state, secrets=(token, secret), env=env)
    try:
        environment = write_webhook_environment(root, token=token, secret=secret)
        state["environment"] = environment
        state["secret_material"] = {**state["secret_material"], "created": ["webhook_env"]}
        _stage_state(root, state, secrets=(token, secret), env=env)
        provider_payload = write_provider_payload(root, secret=secret)
        state["provider_payload"] = provider_payload
        state["secret_material"] = {**state["secret_material"], "created": ["webhook_env", "provider_payload"]}
        _stage_state(root, state, secrets=(token, secret), env=env)
        state = _count_runtime(state, "establish")
        state["runtime_stage"] = "candidate"
        _stage_state(root, state, secrets=(token, secret), env=env)
        candidate = _validate_candidate(effectors.canonical_candidate(root))
        state.update({"candidate": candidate, "runtime_stage": "wheel"})
        _stage_state(root, state, secrets=(token, secret), env=env)
        wheel = _validate_wheel_evidence(effectors.build_wheel(root, candidate), candidate)
        state.update({"wheel": wheel,
                      "runtime_stage": "venv"})
        _stage_state(root, state, secrets=(token, secret), env=env)
        venv = dict(effectors.create_venv(root))
        if venv.get("isolated") is not True:
            raise RuntimeError("virtual environment is not isolated")
        state["runtime_stage"] = "install"
        _stage_state(root, state, secrets=(token, secret), env=env)
        install = dict(effectors.install_wheel(root, wheel))
        if install.get("global_install_mutations", 0) != 0:
            raise RuntimeError("ordinary global install mutation is forbidden")
        state["runtime_stage"] = "source_disabled"
        _stage_state(root, state, secrets=(token, secret), env=env)
        source = _expect(effectors.configure_source(root, environment), source=SOURCE, enabled=False)
        state["runtime_stage"] = "anchor"
        _stage_state(root, state, secrets=(token, secret), env=env)
        daemon = _expect(effectors.initialize_daemon(root, environment), dispatch_enabled=False)
        if (not isinstance(daemon.get("anchor"), str) or not daemon["anchor"]
                or daemon.get("source_enabled") is not True
                or not isinstance(daemon.get("wake_id"), str)
                or not daemon["wake_id"].startswith("wake_")):
            raise RuntimeError("durable no-dispatch anchor is absent")
        state.update({"anchor": daemon["anchor"], "wake_id": daemon["wake_id"],
                      "runtime_stage": "listener"})
        _stage_state(root, state, secrets=(token, secret), env=env)
        listener = _expect(effectors.configure_listener(root, environment), source=SOURCE,
                           address="127.0.0.1", port=8820)
        state["runtime_stage"] = "service_install"
        _stage_state(root, state, secrets=(token, secret), env=env)
        service = _expect(effectors.install_service(root, environment), unit=UNIT)
        state.update({"service_attempted": True, "runtime_stage": "readiness"})
        _stage_state(root, state, secrets=(token, secret), env=env)
        readiness = _expect(effectors.readiness(root, environment), ready=True, source=SOURCE,
                            dispatch_enabled=False)
        state.update({"phase": "runtime_ready", "candidate": candidate,
            "wheel": wheel, "anchor": daemon["anchor"],
            "wake_id": daemon["wake_id"], "runtime_established": True,
            "runtime_stage": "ready",
            "runtime_evidence": {"venv": {"isolated": True}, "install": install,
                "source": source, "listener": listener, "service": service,
                "readiness": readiness, "environment": environment,
                "provider_payload": provider_payload}})
        _stage_state(root, state, secrets=(token, secret), env=env)
        return receipt_for(state)
    except Exception:
        state = {**state, "phase": "runtime_prepare_uncertain"}
        _stage_state(root, state, secrets=(token, secret), env=env)
        raise


def record_attempt(state: Mapping[str, Any], action: str) -> dict[str, Any]:
    if state.get("requires_exact_readback"):
        raise RuntimeError("ambiguous provider write requires exact readback; retry refused")
    counters = state.get("counters")
    if not isinstance(counters, Mapping):
        raise RuntimeError("lifecycle counters are invalid")
    _validate_counters(counters)
    if action in {"redelivery", "dispatch"}:
        raise RuntimeError(f"{action} is forbidden by P53-C6")
    if action not in {"create", "trigger", "delete"}:
        raise ValueError("unknown lifecycle action")
    if counters[action] != 0:
        raise RuntimeError(f"{action} retry is forbidden by P53-C6")
    if action in {"trigger", "delete"} and type(state.get("hook_id")) is not int:
        raise RuntimeError(f"{action} requires exact created-hook readback")
    updated = dict(state)
    updated["counters"] = {**counters, action: 1}
    updated["phase"] = f"{action}_attempted"
    return updated


def record_provider_result(state: Mapping[str, Any], action: str, *, response: Mapping[str, Any] | None,
                           ambiguous: bool = False) -> dict[str, Any]:
    if action not in {"create", "delete"}:
        raise ValueError("only provider hook writes have provider results")
    if state["counters"].get(action) != 1:
        raise RuntimeError("provider result requires exactly one recorded attempt")
    updated = dict(state)
    if ambiguous:
        return {**updated, "phase": "provider_write_ambiguous", "requires_exact_readback": True,
                "ambiguous_action": action}
    if response is None:
        raise RuntimeError("provider result is absent without an ambiguity classification")
    if action == "create":
        observed = validate_hook_response(response)
        return {**updated, "phase": "hook_created_readback", "hook_id": observed["hook_id"], "hook_readback": observed}
    if response.get("absent") is not True or response.get("hook_id") != state.get("hook_id"):
        raise RuntimeError("delete readback hook identity mismatch")
    return {**updated, "phase": "hook_deleted_readback", "deleted_hook_id": state["hook_id"],
            "delete_readback_absent": True}


def reconcile_ambiguous_write(state: Mapping[str, Any], action: str,
                              readbacks: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    """Reconcile the already-counted write from exact reads; never send a retry."""
    if state.get("requires_exact_readback") is not True or state.get("ambiguous_action") != action:
        raise RuntimeError("no matching ambiguous provider write is pending")
    if action == "create":
        matches: list[dict[str, Any]] = []
        for item in readbacks:
            try:
                matches.append(validate_hook_response(item))
            except RuntimeError:
                continue
        if len(matches) != 1:
            raise RuntimeError("ambiguous create requires one exact hook readback")
        observed = matches[0]
        return {**dict(state), "phase": "hook_created_reconciled", "requires_exact_readback": False,
                "hook_id": observed["hook_id"], "hook_readback": observed}
    if action == "delete":
        hook_id = state.get("hook_id")
        matches = [item for item in readbacks if item.get("hook_id") == hook_id and item.get("absent") is True]
        if len(matches) != 1:
            raise RuntimeError("ambiguous delete requires exact absence readback")
        return {**dict(state), "phase": "hook_deleted_reconciled", "requires_exact_readback": False,
                "deleted_hook_id": hook_id, "delete_readback_absent": True}
    raise ValueError("unknown ambiguous write action")


def freeze_trigger(state: Mapping[str, Any], trigger: Mapping[str, Any]) -> dict[str, Any]:
    if state["counters"].get("create") != 1 or type(state.get("hook_id")) is not int:
        raise RuntimeError("trigger freeze requires exact created-hook readback")
    expected = {"base_ref": REF, "docs_only": True, "green": True, "merge_method": "squash"}
    if any(trigger.get(key) != value for key, value in expected.items()):
        raise RuntimeError("trigger PR is not frozen and green")
    frozen = {"pr_number": trigger.get("pr_number"), "head_sha": _exact_sha(trigger.get("head_sha"), "trigger head"),
              "hook_id": state["hook_id"], **expected}
    if type(frozen["pr_number"]) is not int or frozen["pr_number"] <= 0:
        raise RuntimeError("trigger PR number is invalid")
    return {**dict(state), "trigger": frozen, "phase": "trigger_frozen"}


def record_trigger_result(state: Mapping[str, Any], *, merge_sha: str) -> dict[str, Any]:
    """Bind the already-counted merge to its resulting canonical main commit."""
    trigger = state.get("trigger")
    if state["counters"].get("trigger") != 1 or not isinstance(trigger, Mapping):
        raise RuntimeError("trigger result requires one frozen merge attempt")
    updated_trigger = {**dict(trigger), "merge_sha": _exact_sha(merge_sha, "trigger merge")}
    return {**dict(state), "phase": "trigger_merged", "trigger": updated_trigger}


def validate_delivery_window(deliveries: tuple[Mapping[str, Any], ...], *, trigger: Mapping[str, Any]) -> dict[str, Any]:
    merge_sha = _exact_sha(trigger.get("merge_sha"), "trigger merge")
    qualifying: list[Mapping[str, Any]] = []
    seen: list[str] = []
    for delivery in deliveries:
        delivery_id = delivery.get("delivery_id")
        if type(delivery_id) is not str or not delivery_id or delivery_id in seen:
            raise RuntimeError("delivery identity is invalid")
        seen.append(delivery_id)
        run = delivery.get("run")
        if not isinstance(run, Mapping):
            continue
        required = {"event": "workflow_run", "action": "completed", "authenticated": True,
                    "status_code": 200, "repository": REPOSITORY, "repository_id": REPOSITORY_ID,
                    "workflow_id": WORKFLOW_ID, "ref": REF, "conclusion": CONCLUSION,
                    "head_sha": merge_sha, "hook_id": trigger.get("hook_id"),
                    "terminal_after_anchor": True}
        if (all(delivery.get(key) == value for key, value in required.items())
                and run.get("status") == "completed" and run.get("event") == "push"):
            if type(run.get("run_id")) is int and run["run_id"] > 0 and type(run.get("run_attempt")) is int and run["run_attempt"] > 0:
                qualifying.append(delivery)
    if len(qualifying) != 1:
        raise RuntimeError("delivery window requires exactly one qualifying completed workflow_run")
    value = qualifying[0]
    run = value["run"]
    occurrence = (
        f"github:repository:{REPOSITORY_ID}:run:{run['run_id']}:"
        f"attempt:{run['run_attempt']}"
    )
    return {"delivery_ids": tuple(seen), "qualifying_delivery_id": value["delivery_id"],
            "occurrence": occurrence, "run_id": run["run_id"], "run_attempt": run["run_attempt"],
            "head_sha": merge_sha}


def record_convergence(state: Mapping[str, Any], delivery: Mapping[str, Any], *, journal_before: int,
                       journal_after_webhook: int, journal_after_poll: int,
                       wake_before: str, wake_after: str, dispatch_calls: int) -> dict[str, Any]:
    if (journal_before, journal_after_webhook, journal_after_poll) != (0, 1, 1):
        raise RuntimeError("journal did not converge at exactly one occurrence")
    if (wake_before, wake_after) != ("pending", "firing_local") or dispatch_calls != 0:
        raise RuntimeError("wake transition or dispatch boundary is invalid")
    if state["counters"]["dispatch"] != 0 or state["counters"]["redelivery"] != 0:
        raise RuntimeError("forbidden lifecycle counter is nonzero")
    state = _count_runtime(state, "observation")
    return {**state, "phase": "converged", "delivery": {**dict(delivery), "journal_before": 0,
            "journal_after_webhook": 1, "journal_after_poll": 1, "wake_before": wake_before,
            "wake_after": wake_after, "dispatch_calls": 0}}


def _validate_cleanup_census(census: Mapping[str, Any], unrelated: Mapping[str, Any]) -> dict[str, Any]:
    expected = {"unit_absent": True, "active": "inactive", "enabled": "disabled", "pid": 0,
                "matching_processes": 0, "port_8820_released": True}
    query_names = ("unit_query", "failed_units_query")
    queries = {name: census.get(name) for name in query_names}
    if any(
        not isinstance(query, Mapping)
        or query.get("ok") is not True
        or query.get("returncode") != 0
        or query.get("bus_error") not in (None, "")
        for query in queries.values()
    ):
        raise RuntimeError("runtime cleanup systemctl query is unavailable or failed")
    if any(census.get(key) != value for key, value in expected.items()) or not unrelated:
        raise RuntimeError("runtime cleanup census is incomplete")
    return {**expected, "systemctl_queries": queries, "unrelated_state": dict(unrelated)}


def cleanup_runtime(root: Path, *, env: Mapping[str, str], effectors: RuntimeEffectors,
                    armed: bool = False) -> dict[str, Any]:
    if not armed:
        raise RuntimeError("runtime cleanup requires explicit execution arm")
    root = exact_private_root(root, env=env)
    state = load_private_state(root, env=env)
    if (state["runtime_counters"]["establish"] != 1
            and state["runtime_counters"]["secret_provision"] != 1):
        raise RuntimeError("runtime cleanup requires one attempted runtime")
    state = _count_runtime(state, "cleanup")
    _stage_state(root, state, env=env)
    try:
        uninstall = _expect(effectors.uninstall_service(root, state), unit=UNIT, uninstalled=True)
        census = effectors.runtime_census(root, state)
        retired = retire_webhook_environment(root)
        if not retired:
            raise RuntimeError("webhook secret environment was not retired")
        state = _count_runtime(state, "secret_retirement")
        state.update({"secret_retired": True, "secret_retirement_evidence": {"artifacts_absent": True}})
        _stage_state(root, state, env=env)
        unrelated = effectors.unrelated_state(root, state)
        evidence = _validate_cleanup_census(census, unrelated)
        state.update({"phase": "runtime_cleaned",
                      "runtime_cleanup_evidence": {"uninstall": uninstall, **evidence}})
        _stage_state(root, state, env=env)
        return receipt_for(state)
    except Exception:
        state = {**state, "phase": "runtime_cleanup_uncertain"}
        _stage_state(root, state, env=env)
        raise


def cleanup_interlock(state: Mapping[str, Any]) -> tuple[bool, str]:
    _validate_counters(state["counters"])
    _validate_runtime_counters(state["runtime_counters"])
    runtime = state["runtime_counters"]
    if state.get("requires_exact_readback"):
        return False, "ambiguous provider state"
    if state["counters"]["redelivery"] != 0 or state["counters"]["dispatch"] != 0:
        return False, "forbidden effect counter is nonzero"
    if state["counters"]["create"] == 1 and not (state["counters"]["delete"] == 1
            and state.get("delete_readback_absent") is True and type(state.get("deleted_hook_id")) is int):
        return False, "created hook lacks exact deletion readback"
    if (runtime["establish"], runtime["cleanup"], runtime["secret_provision"], runtime["secret_retirement"]) != (1, 1, 1, 1):
        return False, "runtime or secret lifecycle is incomplete"
    if state.get("secret_retired") is not True or not isinstance(state.get("runtime_cleanup_evidence"), Mapping):
        return False, "runtime cleanup evidence is absent"
    return True, "safe"


def cleanup_local(root: Path, *, env: Mapping[str, str] | None = None,
                  armed: bool = False) -> dict[str, Any]:
    if not armed:
        raise RuntimeError("local cleanup requires explicit execution arm")
    root = exact_private_root(root, env=env)
    state = load_private_state(root, env=env)
    safe, reason = cleanup_interlock(state)
    result = {"safe": safe, "reason": reason, "root": str(root), "root_removed": False}
    state = {**state, "phase": "cleaned" if safe else "cleanup_interlocked"}
    stage_receipt(receipt_for(state, cleanup=result), Path(state["receipt"]), root=root)
    write_private_state(root, state, env=env)
    if safe:
        shutil.rmtree(root)
        result["root_removed"] = True
        stage_receipt(receipt_for(state, cleanup=result), Path(state["receipt"]), secrets=())
    return result


def preflight() -> dict[str, Any]:
    return {"phase": "read_only_preflight", "identity": asdict(frozen_identity()),
            "counters": {name: 0 for name in _COUNTERS},
            "runtime_counters": {name: 0 for name in _RUNTIME_COUNTERS},
            "dispatch": "disabled", "provider_transport": "absent", "network": "absent"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "prepare", "cleanup"), nargs="?", default="preflight")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    if args.command == "preflight":
        print(json.dumps(preflight(), sort_keys=True))
        return 0
    if not args.execute or args.root is None:
        print("P53-C6 refuses effectful local phases without --execute and --root", file=sys.stderr)
        return 2
    if args.command == "prepare":
        if args.receipt is None:
            print("prepare requires --receipt outside the exact private root", file=sys.stderr)
            return 2
        print(json.dumps(prepare_local(args.root, args.receipt, armed=True), sort_keys=True))
        return 0
    print(json.dumps(cleanup_local(args.root, armed=True), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
