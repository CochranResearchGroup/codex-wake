"""Durable native scheduling intent, independent of acquisition availability."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
from datetime import UTC, datetime
import math
import re

from .records import WakeError, WakeLifecycleLock, all_records, parse_duration, write_record

SCHEMA_VERSION = 6


def _save(root, record):
    return write_record(root, record)


def _request(args, root):
    from .app_server import resolve_codex_cmd
    from .cli import normalize_prompt
    from .network_wakes import precise_deadline

    root = Path(root).resolve()
    prompt = normalize_prompt(args.prompt)
    ttl = parse_duration(args.ttl).total_seconds()
    if args.native_command == "after":
        schedule = {"kind": "after", "delay_seconds": parse_duration(args.trigger).total_seconds()}
        predicate = {"type": "not_before", "due_at": None}
    elif args.native_command == "at":
        due = precise_deadline(args.trigger).isoformat().replace("+00:00", "Z")
        schedule = {"kind": "at", "due_at": due}
        predicate = {"type": "not_before", "due_at": due}
    else:
        schedule = {"kind": "file", "path": str(Path(args.trigger).resolve())}
        predicate = {"type": "file_exists", "path": schedule["path"]}
    tolerance = getattr(args, "time_tolerance", None)
    tolerance = parse_duration(tolerance).total_seconds() if tolerance else max(1.0, min(300.0, schedule.get("delay_seconds", 0) / 50))
    if tolerance > 300:
        raise WakeError("native time tolerance must be at most 5m")
    stop = getattr(args, "stop_at", None)
    stop = precise_deadline(stop).isoformat().replace("+00:00", "Z") if stop else None
    target = {"transport": "native", "thread_id": args.thread_id,
              "codex_cmd": resolve_codex_cmd(args.codex_path, required=True),
              "endpoint": args.endpoint, "expires_at": None,
              "resume_policy": "same_thread" if args.resume_missing else "hold"}
    content = {"root": str(root), "cwd": str(Path.cwd().resolve()), "target": target,
               "schedule": schedule, "ttl_seconds": ttl, "prompt": prompt,
               "tolerance_seconds": tolerance, "stop_at": stop}
    key = getattr(args, "idempotency_key", None)
    if key is not None and (not key.strip() or len(key) > 200):
        raise WakeError("idempotency key must contain 1..200 characters")
    fingerprint = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    lock = hashlib.sha256((str(root) + "\n" + key).encode()).hexdigest() if key else fingerprint
    return root, content, predicate, fingerprint, key, lock


def _existing(root, fingerprint, key):
    for item in all_records(root, include_archive=key is not None):
        intent = item.record.get("scheduling_intent", {})
        if not isinstance(intent, dict):
            continue
        matches = intent.get("idempotency_key") == key if key else intent.get("fingerprint") == fingerprint and item.record.get("status") in {"pending", "firing"}
        if matches and intent.get("canonical_root") == str(root):
            if intent.get("fingerprint") != fingerprint:
                raise WakeError("idempotency_conflict: original scheduling request differs")
            if not valid_record(item.record):
                raise WakeError("original scheduling intent is invalid; reconcile instead of retrying")
            return item
    return None


def _receipt(args, record, path, deduplicated):
    if getattr(args, 'require_monitor', False):
        from .signal_records import probe_managed_reader_capability
        reader = probe_managed_reader_capability(Path(record['scheduling_intent']['canonical_root']))
        if reader is None or 6 not in reader.schema_versions:
            raise WakeError(f"schema6 intent retained as {record['id']}; active compatible worker unavailable; upgrade the owning worker")
    intent = record['scheduling_intent']
    unanchored = (intent['schedule']['kind'] != 'at' and intent.get('counter_anchor') is None
                  and intent.get('utc_anchor') is None)
    recovery = 'requires_original_clock_evidence' if unanchored else 'on_monitor_poll'
    value = {"id": record["id"], "path": str(path), "status": record["status"],
             "time_recovery": record["time_recovery"], "deduplicated": deduplicated,
             "automatic_recovery": recovery, "requires_original_clock_evidence": unanchored,
             "requires_worker_schema": 6}
    if getattr(args, "as_json", False):
        print(json.dumps(value, sort_keys=True))
    else:
        print(f"{record['id']} {path} state={record['time_recovery']['state']} reason={record['time_recovery']['reason']} recovery={recovery} requires_worker_schema=6")
    return 0


def existing_receipt(args, root):
    root, content, predicate, fingerprint, key, lock = _request(args, root)
    with WakeLifecycleLock(root, "native-intent-" + lock):
        found = _existing(root, fingerprint, key)
        if found:
            return _receipt(args, found.record, found.path, True)
    return None


def retain(args, root):
    from .native_clock import snapshot
    root, content, predicate, fingerprint, key, lock = _request(args, root)
    with WakeLifecycleLock(root, "native-intent-" + lock):
        found = _existing(root, fingerprint, key)
        if found:
            return _receipt(args, found.record, found.path, True)
        clock = snapshot()
        record = {"schema_version": SCHEMA_VERSION, "id": "wake_intent_" + uuid4().hex,
                  "created_at": "", "updated_at": "", "cwd": content["cwd"],
                  "target": content["target"], "predicate": predicate, "prompt": content["prompt"],
                  "status": "pending", "attempts": 0, "max_attempts": 3,
                  "ack_timeout_seconds": 30, "next_attempt_at": None,
                  "events": [{"at": None, "type": "intent_retained", "message": "Scheduling request retained independently of UTC precision"}],
                  "scheduling_intent": {"fingerprint": fingerprint, "idempotency_key": key,
                                        "canonical_root": str(root), "schedule": content["schedule"],
                                        "ttl_seconds": content["ttl_seconds"], "tolerance_seconds": content["tolerance_seconds"],
                                        "stop_at": content["stop_at"],
                                        "counter_anchor": clock.get("counter") if valid_counter(clock.get("counter")) else None,
                                        "utc_anchor": clock.get("utc") if valid_utc(clock.get("utc")) else None,
                                        "origin_state": "at_request" if valid_counter(clock.get("counter")) or valid_utc(clock.get("utc")) else "awaiting_qualified_clock"},
                  "time_recovery": {"state": "pending_time", "reason": "scheduling_time_unavailable",
                                    "alert": "Retained intent needs an active monitor to recover; no dispatch authorized"}}
        if content['schedule']['kind'] != 'at' and record['scheduling_intent']['origin_state'] == 'awaiting_qualified_clock':
            record['time_recovery'] = eligibility(record, clock)
        path = _save(root, record)
        return _receipt(args, record, path, False)


def valid_utc(value):
    return (isinstance(value, dict) and value.get("status") in {"network", "windows"}
            and isinstance(value.get("sources"), (tuple, list))
            and all(isinstance(x, str) and x for x in value["sources"])
            and len(set(value["sources"])) == len(value["sources"])
            and len(value["sources"]) >= (2 if value["status"] == "network" else 1)
            and all(type(value.get(key)) in (int, float) and math.isfinite(value[key]) for key in ("lower", "upper"))
            and 0 < value["lower"] <= value["upper"] and value["upper"] - value["lower"] <= 300)


def valid_counter(value):
    return (isinstance(value, dict) and isinstance(value.get("epoch"), str)
            and 0 < len(value["epoch"]) <= 200
            and all(type(value.get(key)) is int for key in ("counter", "frequency", "rate_ppm"))
            and 0 <= value["counter"] <= 18446744073709551615 and 0 < value["frequency"] <= 18446744073709551615
            and 0 <= value["rate_ppm"] <= 5000)


def valid_record(record):
    from .network_wakes import precise_deadline
    try:
        intent = record["scheduling_intent"]
        schedule = intent["schedule"]
        target = record["target"]
        if (record.get("schema_version") != 6 or record["status"] not in {"pending", "firing", "submitted", "failed", "cancelled", "expired", "archived"}
                or not isinstance(record["id"], str) or not re.fullmatch(r'wake_intent_[0-9a-f]{32}', record['id'])
                or not isinstance(record.get('events'), list) or any(not isinstance(event, dict) for event in record['events'])
                or not isinstance(intent.get('fingerprint'), str) or not re.fullmatch(r'[0-9a-f]{64}', intent['fingerprint'])
                or intent.get('origin_state') not in {'at_request', 'awaiting_qualified_clock'}
                or type(record["attempts"]) is not int or record["attempts"] < 0
                or not isinstance(record["prompt"], str) or not record["prompt"].strip()
                or target["transport"] != "native" or str(UUID(target["thread_id"])) != target["thread_id"]
                or not target["endpoint"].startswith("unix://") or not Path(target["codex_cmd"]).is_absolute()
                or not Path(intent["canonical_root"]).is_absolute()
                or type(intent["ttl_seconds"]) not in (int, float) or not math.isfinite(intent["ttl_seconds"]) or intent["ttl_seconds"] <= 0
                or type(intent["tolerance_seconds"]) not in (int, float) or not 0 < intent["tolerance_seconds"] <= 300
                or not isinstance(record["time_recovery"], dict)):
            return False
        if intent.get("counter_anchor") is not None and not valid_counter(intent["counter_anchor"]):
            return False
        if intent.get("utc_anchor") is not None and not valid_utc(intent["utc_anchor"]):
            return False
        if intent.get("stop_at") is not None:
            precise_deadline(intent["stop_at"])
        delivery = record.get('native_delivery')
        if delivery is not None:
            if not isinstance(delivery, dict) or delivery.get('state') not in {'uncertain', 'accepted'}:
                return False
            if str(UUID(delivery['submission_id'])) != delivery['submission_id']:
                return False
        if schedule["kind"] == "after":
            return type(schedule["delay_seconds"]) in (int, float) and math.isfinite(schedule["delay_seconds"]) and schedule["delay_seconds"] > 0
        if schedule["kind"] == "at":
            precise_deadline(schedule["due_at"])
            return True
        return schedule["kind"] == "file" and Path(schedule["path"]).is_absolute()
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return False


def eligibility(record, clock):
    """Pure conservative bounds; never manufacture UTC from a counter."""
    intent = record["scheduling_intent"]
    schedule = intent["schedule"]
    kind = schedule["kind"]
    origin = intent.get("counter_anchor")
    observed = clock.get("counter")
    delay = schedule.get("delay_seconds", 0)
    utc = clock.get("utc")
    result = {"state": "pending_time", "reason": clock.get("reason", "clock_unavailable"), "alert": "Trusted scheduling time unavailable; original intent retained"}
    stop_remaining = None
    if intent.get("stop_at"):
        if not valid_utc(utc):
            return dict(result, reason="absolute_stop_time_unavailable")
        from .network_wakes import precise_deadline
        stop = precise_deadline(intent["stop_at"]).timestamp()
        if utc["lower"] >= stop:
            return dict(result, state="missed_deadline", reason="stop_reached", alert="Monitoring stop reached; dispatch prohibited")
        if utc["upper"] >= stop:
            return dict(result, reason="stop_boundary_uncertain")
        stop_remaining = stop - utc["upper"]
    if kind != 'at' and not valid_counter(origin) and not valid_utc(intent.get('utc_anchor')):
        return dict(result, reason='relative_origin_unanchored',
                    alert='Original relative origin unavailable; reconcile the original deadline before creating a replacement intent')
    continuous = (valid_counter(origin) and valid_counter(observed)
                  and observed['epoch'] == origin['epoch'] and observed['frequency'] == origin['frequency']
                  and observed['counter'] >= origin['counter'])
    if kind != "at" and valid_counter(origin) and valid_counter(observed) and not continuous:
        if not (valid_utc(utc) and valid_utc(intent.get('utc_anchor'))):
            return dict(result, reason="counter_continuity_lost", alert="Original relative clock continuity lost; no rebase or dispatch authorized")
    # A saved UTC origin lets recovered UTC qualify the original deadline even
    # when accumulated counter rate error no longer fits this wake's precision.
    if kind != "at" and continuous and not (valid_utc(utc) and valid_utc(intent.get('utc_anchor'))):
        delta = observed["counter"] - origin["counter"]
        rate = max(origin["rate_ppm"], observed["rate_ppm"]) / 1000000
        lower = max(0.0, math.nextafter((delta - 1) / (origin["frequency"] * (1 + rate)), -math.inf))
        upper = math.nextafter((delta + 1) / (origin["frequency"] * (1 - rate)), math.inf)
        due, expiry, mode = delay, delay + intent["ttl_seconds"], "host_counter"
    elif valid_utc(utc):
        lower, upper = utc.get("lower"), utc.get("upper")
        if not all(type(x) in (int, float) and math.isfinite(x) for x in (lower, upper)) or lower > upper:
            return dict(result, reason="invalid_utc_bounds")
        if kind == "at":
            from .network_wakes import precise_deadline
            due = precise_deadline(schedule["due_at"]).timestamp()
        else:
            anchor = intent.get("utc_anchor")
            if not isinstance(anchor, dict):
                return dict(result, reason="relative_origin_unanchored")
            due = anchor["upper"] + delay
        expiry, mode = due + intent["ttl_seconds"], "bounded_utc"
    else:
        return result
    base = {"state": "pending", "reason": "not_due", "alert": None, "mode": mode, "lower": lower, "upper": upper, "expires": expiry, "dispatch_window_seconds": min(expiry - upper, stop_remaining) if stop_remaining is not None else expiry - upper}
    if lower >= expiry:
        return dict(base, state="missed_deadline", reason="expiry_reached", alert="Wake deadline missed; original intent retained without dispatch")
    if upper >= expiry:
        return dict(base, state="pending_time", reason="expiry_boundary_uncertain", alert="Expiry eligibility uncertain; no dispatch authorized")
    if upper - lower > intent["tolerance_seconds"]:
        return dict(base, state="pending_time", reason="precision_unavailable", alert="Clock bounds exceed this request tolerance; intent retained")
    if lower < due or (kind == "file" and not Path(schedule["path"]).exists()):
        return base
    return dict(base, state="due", reason="not_before_and_expiry_established")


def evaluate(root, identifier, clock):
    from .records import find_record, replace_record
    with WakeLifecycleLock(root, identifier):
        found = find_record(root, identifier)
        record = dict(found.record)
        if not valid_record(record) or record["status"] != "pending" or record["scheduling_intent"]["canonical_root"] != str(Path(root).resolve()):
            return "pending"
        verdict = eligibility(record, clock)
        previous = record["time_recovery"]
        record["time_recovery"] = verdict
        if any(previous.get(key) != verdict.get(key) for key in ("state", "reason", "mode")):
            record["events"] = list(record["events"]) + [{"at": None, "type": "time_recovery", "message": verdict["reason"]}]
        if verdict["state"] == "due":
            record["status"] = "firing"
        elif verdict["state"] == "missed_deadline":
            record["status"] = "failed"
        path = _save(root, record)
        if found.path != path:
            found.path.unlink(missing_ok=True)
        return record["status"]


def dispatch(root, found, clock_provider=None, *, runtime_adapter=None):
    from .records import find_record
    from .native_delivery import dispatch_native, reconcile_native
    from .native_clock import snapshot
    from .injector import DispatchResult
    provider = clock_provider or snapshot
    with WakeLifecycleLock(root, found.record["id"]):
        active = find_record(root, found.record["id"])
        record = active.record
        if (not valid_record(record) or record["status"] != "firing" or record != found.record
                or record["scheduling_intent"]["canonical_root"] != str(Path(root).resolve())):
            return DispatchResult("skipped", "native intent changed or root does not match")
        if record.get("native_delivery", {}).get("state") == "uncertain":
            return reconcile_native(root, active, None, runtime_adapter=runtime_adapter)
        return dispatch_native(root, active, None, clock_provider=provider, runtime_adapter=runtime_adapter)


def dispatch_gate(record, clock):
    verdict = eligibility(record, clock)
    # Reserve the bounded queue handoff and runtime-read budget before admitting
    # an effect. This is elapsed/UTC eligibility, never a fabricated timestamp.
    if verdict["state"] == "due" and verdict["dispatch_window_seconds"] <= 35:
        return dict(verdict, state="pending_time", reason="dispatch_window_uncertain", alert="Insufficient bounded dispatch window before expiry")
    return verdict
