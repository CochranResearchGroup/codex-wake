#!/usr/bin/env python3
"""Provider-free installed-wheel smoke for the closed source catalogue."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.records import WakePath
from codex_wake.signal_records import build_signal_record
from codex_wake.signal_support import export_signal_support, signal_readiness
from codex_wake.signals import (
    ArmContext,
    ArmedSignal,
    Eq,
    InMemorySignalModule,
    Resume,
    ScriptedSourceAdapter,
    SignalRequest,
    SourceAnchor,
    SourceContract,
    WakeId,
    WakeIntent,
)
from codex_wake.source_registry import (
    BuiltinSourceRegistration,
    BuiltinSourceRegistry,
    ReconstructionContext,
    builtin_source_registry,
)


EXPECTED_REGISTRATIONS = (
    "local-filesystem",
    "local-process-exit",
    "local-user-systemd",
    "github-ci",
)


def _fixture_arm() -> tuple[ArmedSignal, WakeIntent]:
    spec = SignalRequest(
        1,
        "memory",
        "installed-fixture",
        "occurrence",
        "job.completed",
        "job:installed-smoke",
        "occurs",
        (Eq("result", "ready"),),
    )
    intent = WakeIntent(
        spec,
        Resume("Provider-free installed smoke.", Path("/tmp"), {"transport": "tmux"}),
        max_attempts=1,
    )
    adapter = ScriptedSourceAdapter(
        SourceContract(
            "memory",
            "installed-fixture",
            frozenset({"job.completed"}),
            frozenset({"job:installed-smoke"}),
            {"result": str},
        ),
        anchor=SourceAnchor(0, "fixture:0", {}, "local_journal"),
    )
    armed = InMemorySignalModule().arm(
        WakeId("wake_installed_fixture"),
        spec,
        ArmContext(
            "installed-fixture",
            "installed-fixture",
            datetime(2026, 9, 15, tzinfo=UTC),
            None,
            intent.resume,
            adapter,
        ),
    )
    if not isinstance(armed, ArmedSignal):
        raise RuntimeError("fixture arm was not accepted")
    return armed, intent


def run_smoke() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="codex-wake-source-registry-") as tmp:
        base = Path(tmp)
        wake_root = base / "wake"
        support_path = base / "support.json"

        inventory = builtin_source_registry().inventory
        inventory_ids = tuple(item.registration_id for item in inventory)
        if inventory_ids != EXPECTED_REGISTRATIONS:
            raise RuntimeError("installed built-in inventory does not match the closed catalogue")

        readiness = signal_readiness(wake_root)
        readiness_ids = tuple(
            item["registration_id"] for item in readiness["builtin_inventory"]
        )
        if readiness_ids != inventory_ids or wake_root.exists():
            raise RuntimeError("readiness inventory widened authority or created runtime state")

        support_result = export_signal_support(
            wake_root,
            support_path,
            max_bytes=16_384,
        )
        support = json.loads(support_path.read_text(encoding="utf-8"))
        if support["signal_readiness"]["builtin_inventory"] != readiness["builtin_inventory"]:
            raise RuntimeError("support inventory diverges from readiness")
        if wake_root.exists():
            raise RuntimeError("support inspection created a wake root")

        armed, intent = _fixture_arm()
        payload, _ = build_signal_record(
            armed,
            intent.resume,
            journal_uuid="installed-fixture",
            revision=1,
        )
        candidate = WakePath(
            base / "pending" / f"{armed.wake_id}.json",
            json.loads(payload),
        )
        sentinel = object()
        factory_calls = 0

        def construct(context, candidates):
            nonlocal factory_calls
            factory_calls += 1
            if context.root != wake_root or tuple(item.armed for item in candidates) != (armed,):
                raise RuntimeError("fixture reconstruction received the wrong candidate")
            return (sentinel,)

        fixture_registry = BuiltinSourceRegistry((
            BuiltinSourceRegistration(
                "installed-fixture",
                frozenset({("memory", "job.completed")}),
                construct,
            ),
        ))
        restored = fixture_registry.reconstruct(
            ReconstructionContext(wake_root, lambda wake_id: armed if wake_id == armed.wake_id else None),
            (candidate,),
        )
        if restored != (sentinel,) or factory_calls != 1 or wake_root.exists():
            raise RuntimeError("provider-free fixture reconstruction failed")

        receipt = {
            "inventory_ids": list(inventory_ids),
            "ownership_pairs": sum(len(item.ownership) for item in inventory),
            "journal_exists": readiness["journal"]["exists"],
            "readiness_status": readiness["status"],
            "support_bytes": support_result.size_bytes,
            "support_sha256": support_result.sha256,
            "fixture_factory_calls": factory_calls,
            "fixture_runner_count": len(restored),
            "wake_root_created": wake_root.exists(),
        }
        if hashlib.sha256(support_path.read_bytes()).hexdigest() != support_result.sha256:
            raise RuntimeError("support receipt digest does not match")

    receipt["temporary_root_removed"] = not base.exists()
    if not receipt["temporary_root_removed"]:
        raise RuntimeError("temporary smoke root was not removed")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    receipt = run_smoke()
    print(json.dumps(receipt, sort_keys=True) if args.json else "source registry smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
