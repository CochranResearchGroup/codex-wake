"""A replacement's exhaustion exception must retain independent fault fences.

The watcher replacement and initial exhaustion run through public supervision.
Fault flags are injected at the persisted receipt boundary: they represent prior
observation/control failures or winddown state surviving graceful replacement.
No accounting, controller identity, native pause proof or renewal result is mocked.
"""

import json
import tempfile
import time
import unittest
from unittest.mock import patch

from codex_wake.goal_renewal import RenewalError, apply, propose
from codex_wake.goal_supervision import _lock, _name, _save, enroll, poll, show
from codex_wake.session_permissions import Principal
import test_goal_supervision as fixture_module

THREAD = fixture_module.THREAD
NOW = fixture_module.NOW


class GoalWatcherRestartFaultTests(unittest.TestCase):
    fixture = fixture_module.GoalSupervisionTests.fixture
    controller = fixture_module.GoalSupervisionTests.controller

    def test_replacement_faults_block_both_proposal_and_application(self):
        for fault in ("observation_error", "control_error", "winddown_reason"):
            for stage in ("propose", "apply"):
                with (
                    self.subTest(fault=fault, stage=stage),
                    tempfile.TemporaryDirectory() as directory,
                    patch(
                        "codex_wake.lifecycle_budget.trusted_upper", return_value=NOW
                    ),
                ):
                    root, policy, _, native, _ = self.fixture(directory)
                    with self.controller(root) as old:
                        enroll(root, policy, THREAD, 40, 120)
                        first = poll(root)[0]["first_stop"]
                        old.terminate()
                        old.wait(timeout=8)
                    self.assertEqual(
                        show(root, policy, THREAD)["reason"], "controller_stopped"
                    )
                    with self.controller(root):
                        until = time.monotonic() + 3
                        while True:
                            current = show(root, policy, THREAD)
                            if (
                                current["controller"]["fresh"]
                                and current["reason"] == "allocation_exhausted"
                            ):
                                break
                            if time.monotonic() > until:
                                self.fail(
                                    "replacement watcher did not finish its first poll"
                                )
                            time.sleep(0.01)
                        self.assertNotEqual(
                            current["controller"]["generation"],
                            first["controller_generation"],
                        )
                        principal = Principal(THREAD, "operator")
                        arguments = dict(
                            principal=principal,
                            operation_id="fault-extension",
                            mode="extend",
                            token_limit=90,
                            remaining_seconds=180,
                            expires_at=NOW + 60,
                        )
                        packet = (
                            propose(root, policy, THREAD, **arguments)
                            if stage == "apply"
                            else None
                        )
                        # Model the exact durable state read after a graceful
                        # replacement: original stop proof plus a retained fault.
                        path = root / "goal-supervision" / (_name(THREAD) + ".json")
                        with _lock(path.parent, path.stem):
                            receipt = json.loads(path.read_text())
                            receipt.update(
                                reason="controller_stopped",
                                **{fault: "retained-independent-fault"},
                            )
                            _save(path, receipt)
                        before = show(root, policy, THREAD)
                        with self.assertRaisesRegex(
                            RenewalError, "different current supervision fault"
                        ):
                            if stage == "propose":
                                propose(root, policy, THREAD, **arguments)
                            else:
                                apply(
                                    root,
                                    policy,
                                    THREAD,
                                    packet["proposal_id"],
                                    principal=principal,
                                    expected_fingerprint=packet["fingerprint"],
                                    explicit=True,
                                )
                        after = show(root, policy, THREAD)
                        self.assertEqual(after["token_limit"], before["token_limit"])
                        self.assertEqual(after["used_tokens"], 40)
                        self.assertEqual(after["first_stop"], first)
                        self.assertEqual(native["goal"]["status"], "paused")
