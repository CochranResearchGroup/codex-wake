from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/managed_webhook_provider_free_qualification.py"
SPEC = importlib.util.spec_from_file_location("managed_webhook_provider_free_qualification", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
qualification = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualification)


class ManagedWebhookProviderFreeQualificationTests(unittest.TestCase):
    def test_fixture_proves_planes_cleanup_census_and_zero_external_effects(self) -> None:
        receipt = qualification.run_qualification()
        self.assertEqual(receipt["qualification"], "managed_webhook_c3_provider_free")
        self.assertEqual(receipt["planes"]["provider_object"], "EXACT")
        self.assertEqual(receipt["planes"]["provider_delivery"], "UNPROVEN")
        self.assertEqual(receipt["planes"]["dispatch"], "NOT_INCLUDED")
        self.assertEqual(receipt["cleanup"]["mode"], "applied_to_fixtures")
        self.assertEqual(receipt["cleanup"]["eligibility"], "ELIGIBLE_FOR_EXPLICIT_PLAN")
        self.assertEqual(receipt["cleanup"]["disable_tombstone"], "DISABLED_PROVEN")
        self.assertEqual(receipt["cleanup"]["delete_tombstone"], "DELETED_PROVEN")
        self.assertTrue(receipt["cleanup"]["tombstone_retained"])
        self.assertEqual(receipt["local_absence_census"]["state"], "PROVEN_ABSENT")
        self.assertTrue(receipt["local_absence_census"]["unit_file_present"])
        self.assertEqual(receipt["local_absence_census"]["pid_entries"], 0)
        self.assertTrue(receipt["rotation"]["apply_supported"] is False)
        self.assertEqual(receipt["rotation"]["mode"], "preview_only")
        self.assertEqual(receipt["rotation"]["lifecycle_execution"], "not_included")
        for name, count in receipt["effect_counters"].items():
            with self.subTest(name=name):
                self.assertEqual(count, 0)
        self.assertEqual(receipt["fixture_counters"]["provider_disable_calls"], 1)
        self.assertEqual(receipt["fixture_counters"]["provider_delete_calls"], 1)
        self.assertEqual(receipt["fixture_counters"]["local_disable_calls"], 1)
        self.assertEqual(receipt["fixture_counters"]["local_delete_calls"], 1)
        self.assertGreater(receipt["fixture_counters"]["systemd_read_calls"], 0)
        self.assertTrue(receipt["sentinels_unchanged"])
        self.assertEqual(receipt["retention_scope"], "wake_root_product_paths")
        self.assertTrue(receipt["temporary_root_removed"])


if __name__ == "__main__":
    unittest.main()
