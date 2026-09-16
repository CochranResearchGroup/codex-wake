#!/usr/bin/env python3
"""Provider-free P53-C6 GitHub webhook qualification lifecycle contract.

This runner deliberately has no GitHub client, subprocess, network, service,
or dispatch implementation.  Its default command is a read-only rendering of
the frozen preflight.  The two local filesystem phases require both
``--execute`` and an exact owner-only P53-C6 private root.  A primary owner
must separately orchestrate any authorized provider lifecycle through injected
request and response seams.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


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
RECEIPT_VERSION = 1
PRIVATE_ROOT_PREFIX = "p53-c6-live-github-"
_COUNTERS = ("create", "trigger", "delete", "redelivery", "dispatch")


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


def frozen_identity() -> FrozenIdentity:
    """Return the plan-locked P53-C6 identity without reading the environment."""
    return FrozenIdentity()


def build_provider_request(action: str, *, secret: str | None = None,
                           hook_id: int | None = None) -> ProviderRequest:
    """Build one provider request only; callers own transport and authorization.

    The optional secret is held only in the returned in-memory request.  Receipt
    functions below redact it and never serialize it into P53-C6 state.
    """
    if action == "create":
        if type(secret) is not str or not secret:
            raise ValueError("create request requires a non-empty in-memory secret")
        return ProviderRequest(
            action, "POST", f"/repos/{REPOSITORY}/hooks", {
                "name": "web", "active": True, "events": ["workflow_run"],
                "config": {"url": CALLBACK_URL, "content_type": "json",
                           "insecure_ssl": "0", "secret": secret},
            },
        )
    if action == "trigger":
        # The plan owns the trigger through an already-green PR merge.  No
        # GitHub request is constructed, preventing an accidental direct merge.
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
    return {
        "hook_id": response.get("id"), "active": response.get("active"),
        "events": response.get("events"), "url": config.get("url"),
        "content_type": config.get("content_type"),
        "insecure_ssl": str(config.get("insecure_ssl")),
    }


def validate_hook_response(response: Mapping[str, Any]) -> dict[str, Any]:
    """Purely validate the exact created-hook readback; accept no drift."""
    observed = _hook_projection(response)
    expected = {
        "active": True, "events": ["workflow_run"], "url": CALLBACK_URL,
        "content_type": "json", "insecure_ssl": "0",
    }
    if (type(observed["hook_id"]) is not int or observed["hook_id"] <= 0
            or any(observed[key] != value for key, value in expected.items())):
        raise RuntimeError("hook response mismatch")
    return observed


def sanitize_for_receipt(value: Any, *, secrets: tuple[str, ...] = ()) -> Any:
    """Return a recursively redacted public receipt value."""
    hidden = ("secret", "token", "authorization", "payload", "body", "environment")
    if isinstance(value, Mapping):
        return {
            str(key): "[redacted]" if (
                not str(key).lower().endswith("_ref")
                and any(part in str(key).lower() for part in hidden)
            )
            else sanitize_for_receipt(item, secrets=secrets)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_for_receipt(item, secrets=secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[redacted]")
    return value


def sanitized_request_summary(request: ProviderRequest, *, secrets: tuple[str, ...] = ()) -> dict[str, Any]:
    serialized = json.dumps(request.body, sort_keys=True, separators=(",", ":"))
    return {
        "action": request.action, "method": request.method, "path": request.path,
        "request_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "body": sanitize_for_receipt(request.body, secrets=secrets),
    }


def new_state(root: Path, receipt: Path) -> dict[str, Any]:
    return {
        "schema_version": RECEIPT_VERSION, "source": SOURCE,
        "root": str(root.resolve()), "receipt": str(receipt.resolve()),
        "phase": "prepared", "requires_exact_readback": False,
        "counters": {name: 0 for name in _COUNTERS},
        "deleted_hook_id": None, "delete_readback_absent": False,
    }


def _validate_counters(value: Mapping[str, Any]) -> None:
    if set(value) != set(_COUNTERS) or any(type(value[name]) is not int or value[name] < 0 for name in _COUNTERS):
        raise RuntimeError("lifecycle counters are invalid")


def record_attempt(state: Mapping[str, Any], action: str) -> dict[str, Any]:
    """Record one allowed bound; retries, redelivery, and dispatch fail closed."""
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
    if action == "trigger" and type(state.get("hook_id")) is not int:
        raise RuntimeError("trigger requires exact created-hook readback")
    if action == "delete" and type(state.get("hook_id")) is not int:
        raise RuntimeError("delete requires exact created-hook readback")
    updated = dict(state)
    updated["counters"] = {**counters, action: 1}
    updated["phase"] = f"{action}_attempted"
    return updated


def record_provider_result(state: Mapping[str, Any], action: str, *,
                           response: Mapping[str, Any] | None,
                           ambiguous: bool = False) -> dict[str, Any]:
    """Record only transport-independent result facts, preserving ambiguity."""
    if action not in {"create", "delete"}:
        raise ValueError("only provider hook writes have provider results")
    counters = state.get("counters")
    if not isinstance(counters, Mapping) or counters.get(action) != 1:
        raise RuntimeError("provider result requires exactly one recorded attempt")
    updated = dict(state)
    if ambiguous:
        updated.update({"phase": "provider_write_ambiguous", "requires_exact_readback": True,
                        "ambiguous_action": action})
        return updated
    if response is None:
        raise RuntimeError("provider result is absent without an ambiguity classification")
    if action == "create":
        observed = validate_hook_response(response)
        updated.update({"phase": "hook_created_readback", "hook_id": observed["hook_id"],
                        "hook_readback": observed})
    else:
        if response.get("absent") is not True:
            raise RuntimeError("delete readback must prove exact hook absence")
        expected_id = state.get("hook_id")
        if type(expected_id) is not int or response.get("hook_id") != expected_id:
            raise RuntimeError("delete readback hook identity mismatch")
        updated.update({"phase": "hook_deleted_readback", "deleted_hook_id": expected_id,
                        "delete_readback_absent": True})
    return updated


def exact_private_root(root: Path) -> Path:
    if not root.is_absolute() or root.is_symlink() or not root.name.startswith(PRIVATE_ROOT_PREFIX):
        raise RuntimeError("exact private root is required")
    resolved = root.resolve()
    if not resolved.exists() or not resolved.is_dir() or resolved.stat().st_uid != os.getuid() or resolved.stat().st_mode & 0o077:
        raise RuntimeError("exact private root ownership or mode is unsafe")
    return resolved


def _state_path(root: Path) -> Path:
    return root / STATE_FILE


def write_private_state(root: Path, state: Mapping[str, Any]) -> None:
    root = exact_private_root(root)
    if state.get("source") != SOURCE or state.get("root") != str(root):
        raise RuntimeError("private state identity is invalid")
    path = _state_path(root)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def load_private_state(root: Path) -> dict[str, Any]:
    root = exact_private_root(root)
    path = _state_path(root)
    if not path.is_file() or path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise RuntimeError("private state ownership or mode is unsafe")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("source") != SOURCE or value.get("root") != str(root):
        raise RuntimeError("private state identity is invalid")
    _validate_counters(value.get("counters", {}))
    return value


def stage_receipt(receipt: Mapping[str, Any], destination: Path) -> None:
    destination = destination.resolve()
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(json.dumps(sanitize_for_receipt(receipt), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)


def receipt_for(state: Mapping[str, Any], *, cleanup: Mapping[str, Any] | None = None) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_VERSION, "source": SOURCE, "unit": UNIT,
        "listener": LISTENER, "phase": state["phase"],
        "identity": asdict(frozen_identity()), "counters": dict(state["counters"]),
        "requires_exact_readback": state["requires_exact_readback"],
        "dispatch": "disabled", "provider_transport": "primary_owned_injected_only",
    }
    if cleanup is not None:
        receipt["cleanup"] = dict(cleanup)
    return receipt


def prepare_local(root: Path, receipt: Path) -> dict[str, Any]:
    """Stage only private local state; no service, secret, or provider operation."""
    root = exact_private_root(root)
    receipt = receipt.resolve()
    if receipt.is_relative_to(root):
        raise RuntimeError("receipt must remain outside the private root")
    state = new_state(root, receipt)
    write_private_state(root, state)
    staged = receipt_for(state)
    stage_receipt(staged, receipt)
    return staged


def cleanup_interlock(state: Mapping[str, Any]) -> tuple[bool, str]:
    counters = state["counters"]
    _validate_counters(counters)
    if state.get("requires_exact_readback"):
        return False, "ambiguous provider state"
    if counters["redelivery"] != 0 or counters["dispatch"] != 0:
        return False, "forbidden effect counter is nonzero"
    if counters["create"] == 1 and not (
        counters["delete"] == 1 and state.get("delete_readback_absent") is True
        and type(state.get("deleted_hook_id")) is int and state["deleted_hook_id"] > 0
    ):
        return False, "created hook lacks exact deletion readback"
    return True, "safe"


def cleanup_local(root: Path) -> dict[str, Any]:
    """Remove only an exact private root after the pure cleanup interlock passes."""
    root = exact_private_root(root)
    state = load_private_state(root)
    safe, reason = cleanup_interlock(state)
    result = {"safe": safe, "reason": reason, "root": str(root), "root_removed": False}
    receipt = Path(state["receipt"])
    state = {**state, "phase": "cleaned" if safe else "cleanup_interlocked"}
    stage_receipt(receipt_for(state, cleanup=result), receipt)
    if safe:
        shutil.rmtree(root)
        result["root_removed"] = True
        # Bind the externally retained receipt to the completed removal.
        stage_receipt(receipt_for(state, cleanup=result), receipt)
    return result


def preflight() -> dict[str, Any]:
    """Read-only frozen configuration receipt; this is the default CLI action."""
    return {
        "phase": "read_only_preflight", "identity": asdict(frozen_identity()),
        "counters": {name: 0 for name in _COUNTERS}, "dispatch": "disabled",
        "provider_transport": "absent", "network": "absent",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "prepare", "cleanup"), nargs="?", default="preflight")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    if args.command == "preflight":
        if args.execute or args.root or args.receipt:
            parser.error("preflight is read-only and accepts no effectful options")
        print(json.dumps(preflight(), sort_keys=True))
        return 0
    if not args.execute or args.root is None:
        print("P53-C6 refuses effectful local phases without --execute and --root", file=sys.stderr)
        return 2
    if args.command == "prepare":
        if args.receipt is None:
            print("prepare requires --receipt outside the exact private root", file=sys.stderr)
            return 2
        print(json.dumps(prepare_local(args.root, args.receipt), sort_keys=True))
        return 0
    print(json.dumps(cleanup_local(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
