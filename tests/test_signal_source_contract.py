from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime

from codex_wake.runtime_signals import (
    RUNTIME_DEGRADATION_CODES, RuntimeCapability, RuntimeDiagnostic,
    RuntimeDiagnosticCode, RuntimeHealthState, RuntimeRecoveryMode,
    RuntimeSourceDescriptor, RuntimeSourceRegistry,
)


def tracer_payload():
    return {"version": 1, "kind": "tracer.state", "resource": {"identity": "fixture-1"}, "target_state": "ready"}


class RuntimeSourceContractTests(unittest.TestCase):
    def test_closed_descriptor_rejects_unknown_fields_types_and_widening(self):
        payload = tracer_payload()
        descriptor = RuntimeSourceDescriptor.parse(payload)
        self.assertEqual(descriptor.payload(), payload)
        for changed in (
            {**payload, "version": True}, {**payload, "version": 2},
            {**payload, "kind": "command"}, {**payload, "command": "execute"},
            {**payload, "target_state": "*"},
            {**payload, "resource": {"identity": "*"}},
            {**payload, "resource": {"identity": "fixture-1", "env": "private"}},
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                RuntimeSourceDescriptor.parse(changed)

    def test_exact_authorization_is_live_and_exception_or_truthy_value_denies(self):
        allowed = {RuntimeSourceDescriptor.parse(tracer_payload()).fingerprint}
        registry = RuntimeSourceRegistry({"tracer.state": lambda d: d.fingerprint in allowed})
        descriptor = RuntimeSourceDescriptor.parse(tracer_payload())
        self.assertTrue(registry.authorized(descriptor))
        other = RuntimeSourceDescriptor.parse({**tracer_payload(), "resource": {"identity": "fixture-2"}})
        self.assertFalse(registry.authorized(other))
        allowed.clear()
        self.assertFalse(registry.authorized(descriptor))
        self.assertFalse(RuntimeSourceRegistry({}).authorized(descriptor))
        self.assertFalse(RuntimeSourceRegistry({"tracer.state": lambda d: 1}).authorized(descriptor))
        def broken(d):
            raise RuntimeError("private-backend-body")
        self.assertFalse(RuntimeSourceRegistry({"tracer.state": broken}).authorized(descriptor))

    def test_process_and_systemd_descriptors_freeze_only_safe_exact_identity(self):
        process = {"version": 1, "kind": "process.exit", "resource": {
            "boot_id": "01234567-89ab-cdef-0123-456789abcdef", "pid": 123,
            "start_time_ticks": 456, "owner_uid": 1000}, "target_state": "terminated"}
        systemd = {"version": 1, "kind": "systemd.unit", "resource": {
            "manager": "user", "owner_uid": 1000, "unit": "build.service"}, "target_state": "failed"}
        for payload in (process, systemd):
            descriptor = RuntimeSourceDescriptor.parse(payload)
            payload["resource"]["owner_uid"] = 2000
            self.assertEqual(descriptor.resource["owner_uid"], 1000)
            with self.assertRaises(TypeError):
                descriptor.resource["owner_uid"] = 2000
        for resource in ({**systemd["resource"], "manager": "system"},
                         {**systemd["resource"], "unit": "*.service"},
                         {**systemd["resource"], "unit": "-danger.service"}):
            with self.assertRaises(ValueError):
                RuntimeSourceDescriptor.parse({**systemd, "resource": resource})
        with self.assertRaises(ValueError):
            RuntimeSourceDescriptor.parse({**process, "resource": {**process["resource"], "pid": True}})

    def test_registry_is_closed_and_exposes_bounded_capabilities(self):
        with self.assertRaises(ValueError):
            RuntimeSourceRegistry({"shell": lambda d: True})
        registry = RuntimeSourceRegistry({})
        self.assertEqual(set(registry.capabilities), {"process.exit", "systemd.unit", "tracer.state"})
        self.assertEqual(registry.capabilities["systemd.unit"].recovery, "state_recheck")
        self.assertFalse(registry.capabilities["tracer.state"].production)

    def test_diagnostics_have_closed_serialized_codes_health_and_recovery(self):
        observed_at = datetime(2026, 9, 15, tzinfo=UTC)
        for code in RuntimeDiagnosticCode:
            with self.subTest(code=code):
                diagnostic = RuntimeDiagnostic(code, "a" * 64, observed_at)
                payload = json.loads(json.dumps(diagnostic.payload()))
                expected_health = ({
                    RuntimeDiagnosticCode.NOT_OBSERVED: "unobserved",
                    RuntimeDiagnosticCode.READY: "ready",
                    RuntimeDiagnosticCode.SOURCE_UNSUPPORTED: "unsupported",
                    RuntimeDiagnosticCode.AUTHORIZATION_DENIED: "invalidated",
                    RuntimeDiagnosticCode.OBSERVATION_UNAVAILABLE: "unavailable",
                    RuntimeDiagnosticCode.OBSERVATION_AMBIGUOUS: "invalidated",
                    RuntimeDiagnosticCode.BASELINE_MATCHES: "invalidated",
                    RuntimeDiagnosticCode.RESOURCE_LIMIT: "unavailable",
                    RuntimeDiagnosticCode.ANCHOR_INVALID: "invalidated",
                    RuntimeDiagnosticCode.REQUEST_INVALID: "invalidated",
                    RuntimeDiagnosticCode.CHECKPOINT_UNAVAILABLE: "unavailable",
                    RuntimeDiagnosticCode.CHECKPOINT_INVALID: "invalidated",
                    RuntimeDiagnosticCode.INGEST_UNAVAILABLE: "unavailable",
                    RuntimeDiagnosticCode.PUBLICATION_UNAVAILABLE: "unavailable",
                }[code])
                self.assertEqual(payload["health"], expected_health)
                self.assertEqual(payload["recovery"], "state_recheck")
                self.assertEqual(RuntimeDiagnostic.parse(payload), diagnostic)
                self.assertIsInstance(diagnostic.health, RuntimeHealthState)
                self.assertIsInstance(diagnostic.recovery, RuntimeRecoveryMode)
        self.assertIsInstance(RUNTIME_DEGRADATION_CODES, frozenset)
        self.assertEqual({state.value for state in RuntimeHealthState},
            {"unobserved", "ready", "unavailable", "invalidated", "unsupported"})

    def test_unknown_diagnostic_values_and_health_mismatches_are_rejected(self):
        valid = RuntimeDiagnostic("RUNTIME_READY", "a" * 64, None).payload()
        for changed in ({**valid, "code": "private-backend-error"},
                        {**valid, "health": "degraded"},
                        {**valid, "health": "arbitrary"},
                        {**valid, "recovery": "lossless_magic"},
                        {**valid, "source_fingerprint": "private-command-line"},
                        {**valid, "observed_at": "2026-09-15T00:00:00"},
                        {**valid, "raw_backend": "private"},
                        {**valid, "version": True}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                RuntimeDiagnostic.parse(changed)
        with self.assertRaises(ValueError):
            RuntimeDiagnostic("UNKNOWN", "a" * 64, None)

    def test_capability_metadata_is_immutable_validated_and_sanitized(self):
        registry = RuntimeSourceRegistry({})
        for kind, capability in registry.capabilities.items():
            payload = json.loads(json.dumps(capability.payload()))
            self.assertEqual(payload, {"version": 1, "target_states": sorted(capability.target_states),
                "recovery": "state_recheck", "production": kind != "tracer.state",
                "health_states": sorted(state.value for state in RuntimeHealthState),
                "diagnostic_codes": sorted(code.value for code in RuntimeDiagnosticCode)})
        for kwargs in ({"recovery": "anything"}, {"production": "yes"},
                       {"target_states": {"ready"}}, {"target_states": frozenset({"raw-prompt"})}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                RuntimeCapability(**{"target_states": frozenset({"ready"}), **kwargs})
        with self.assertRaises(TypeError):
            registry.capabilities["shell"] = RuntimeCapability(frozenset({"ready"}))
