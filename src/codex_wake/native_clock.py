"""Acquire UTC bounds and authenticated host elapsed evidence without guest UTC."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
import ipaddress
import json
import math
import os
from pathlib import Path
import ssl
import subprocess
import urllib.request
from urllib.parse import urlsplit
from uuid import UUID


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("clock_redirect_refused")


def configuration():
    if "CODEX_WAKE_STABLE_TIME_CONFIG" in os.environ:
        return os.environ["CODEX_WAKE_STABLE_TIME_CONFIG"] or None
    default = Path.home() / ".config" / "codex-wake" / "stable-time-client.json"
    return str(default) if default.is_file() else None


def snapshot():
    """One bounded observation; counter-only evidence is never labeled UTC."""
    config_path = configuration()
    if not config_path:
        from .time_inspection import network_time_decision
        from .time_provider import require_time_decision
        try:
            decision = require_time_decision(network_time_decision())
            return {"utc": asdict(decision), "counter": None, "reason": "bounded_utc"}
        except (OSError, ValueError, TypeError):
            return {"utc": None, "counter": None, "reason": "clock_unavailable"}
    try:
        config = json.loads(Path(config_path).read_text())
        origin = config["url"]
        parsed = urlsplit(origin)
        if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ("", "/")
                or not (parsed.hostname == "localhost" or ipaddress.ip_address(parsed.hostname).is_loopback)):
            raise ValueError("clock_origin_refused")
        token = Path(config["token_file"]).read_text().strip()
        if len(token) != 64 or any(x not in "0123456789abcdefABCDEF" for x in token):
            raise ValueError("clock_credentials_invalid")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cafile=config["ca_file"])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=context))
        request = urllib.request.Request(origin.rstrip("/") + "/v1/time", headers={"Authorization": "Bearer " + token})
        with opener.open(request, timeout=3) as stream:
            body = stream.read(1048577)
        if len(body) > 1048576:
            raise ValueError("clock_response_too_large")
        response = json.loads(body)
        from .host_counter import read_counter
        counter, frequency = read_counter()
        return from_response(response, counter=counter, frequency=frequency)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, subprocess.SubprocessError):
        return {"utc": None, "counter": None, "reason": "clock_unavailable_or_invalid"}


def from_response(response, *, counter, frequency):
    """Validate the authenticated service contract and native counter handoff."""
    if not isinstance(response, dict) or response.get("contract_version") not in ("1.0", "2.0"):
        raise ValueError("invalid_clock_contract")
    version_two = response["contract_version"] == "2.0"
    epoch = response["epoch"]
    if str(UUID(epoch)) != epoch:
        raise ValueError("invalid_clock_epoch")
    policy = response["counter_policy"]
    rate, max_age = policy["rate_ppm"], policy["maximum_age_ns"]
    measurement = response["measurement"]
    if any(not isinstance(measurement.get(key), str) or not measurement[key].isascii()
           or not measurement[key].isdigit() or len(measurement[key]) > 20
           or int(measurement[key]) > 18446744073709551615 for key in ('counter', 'frequency_hz')):
        raise ValueError('invalid_counter_wire_format')
    measured, measured_frequency = int(measurement["counter"]), int(measurement["frequency_hz"])
    if (any(type(x) is not int for x in (rate, max_age, counter, frequency))
            or not 0 <= rate <= 5000 or not 0 < max_age <= (300000000000 if version_two else 10000000000)
            or frequency <= 0 or frequency != measured_frequency or counter < measured or measured < 0
            or response.get("time_scale") != "UTC-step; announced-leaps-unavailable"):
        raise ValueError("invalid_counter_evidence")
    elapsed = Decimal(counter - measured + 1) * 1000000 / (Decimal(frequency) * (1000000 - rate))
    if elapsed * 1000000000 > max_age:
        raise ValueError("counter_handoff_expired")
    host = {"epoch": epoch, "counter": counter, "frequency": frequency, "rate_ppm": rate}
    if response.get("status") == "unavailable":
        if (response.get("authentication") != "NTS-required" or response.get('estimate') is not None
                or (version_two and response.get('bound') != 'unbounded')):
            raise ValueError("invalid_unavailable_contract")
        return {"utc": None, "counter": host, "reason": "authenticated_counter_only"}
    if response.get("status") not in ("qualified_live", "qualified_holdover") or response.get("authentication") != "NTS-verified":
        raise ValueError("utc_authentication_unqualified")
    if version_two and (response.get('bound') != 'finite' or response.get('best_effort') is not None):
        raise ValueError('inconsistent_finite_result')
    operators = response["operators"]
    age = response["acquisition_age_ns"]
    generation = response["evidence_generation"]
    if (not isinstance(operators, list) or not 2 <= len(operators) <= 4
            or any(not isinstance(x, str) or not x.strip() for x in operators) or len(set(operators)) != len(operators)
            or type(age) is not int or not 0 <= age <= max_age or Decimal(age) + elapsed * 1000000000 > max_age
            or type(generation) is not int or generation <= 0):
        raise ValueError("invalid_utc_provenance")
    def stamp(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone_required")
        return parsed.timestamp()
    estimate = response["estimate"]
    lower, middle, upper = (stamp(estimate[x]) for x in ("earliest_utc", "utc", "latest_utc"))
    radius = estimate["maximum_error_ns"]
    if (type(radius) is not int or radius < 0 or (not version_two and radius >= 100000000) or not lower <= middle <= upper
            or type(estimate.get('maximum_error_ms')) not in (int, float)
            or estimate.get('maximum_error_ms') != radius / 1000000
            or response.get('reason') is not None
            or max(middle - lower, upper - middle) > radius / 1000000000 + .000002):
        raise ValueError("inconsistent_utc_bounds")
    utc = {"status": "network", "sources": ["stable-time:" + x for x in operators],
           "lower": math.nextafter(lower - .000001, -math.inf),
           "upper": math.nextafter(upper + float(elapsed) + .000001, math.inf), "reason": ""}
    return {"utc": utc, "counter": host, "reason": "authenticated_utc"}
