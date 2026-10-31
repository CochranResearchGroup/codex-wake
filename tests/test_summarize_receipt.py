"""Public summary CLI: decisive aggregates survive large private receipts."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/summarize_receipt.py"


class SummaryCLI(unittest.TestCase):
    def invoke(self, value, *args):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            original = json.dumps(value).encode()
            path.write_bytes(original)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), *args], capture_output=True
            )
            self.assertEqual(path.read_bytes(), original)
            return result

    def test_large_validation_preserves_critical_states_and_private_bytes(self):
        rows = [
            dict(name=f"check-{i}", status="PASS", required=True) for i in range(2000)
        ]
        rows += [
            dict(
                name="secret-password",
                status=state,
                required=True,
                stdout="PRIVATE",
                stderr="PRIVATE",
            )
            for state in ["FAIL", "INVALIDATED", "BLOCKED"]
        ]
        result = self.invoke(
            dict(
                schema=1,
                status="FAIL",
                qualified=False,
                checks=rows,
                actions=[],
                failure={"reason": "PRIVATE"},
            )
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLessEqual(len(result.stdout), 8192)
        out = json.loads(result.stdout)
        self.assertEqual(
            out["counts"]["status"],
            {"PASS": 2000, "FAIL": 1, "INVALIDATED": 1, "BLOCKED": 1},
        )
        self.assertEqual(out["failure_count"], 1)
        self.assertEqual(out["unknown_count"], 1)
        self.assertEqual(out["invalidated_count"], 1)
        self.assertFalse(out["qualified"])
        self.assertTrue(out["truncated"])
        self.assertEqual(out["omitted_count"] + len(out["entries"]), 2003)
        self.assertNotIn(b"PRIVATE", result.stdout)
        self.assertNotIn(b"secret-password", result.stdout)

    def test_cleanup_drilldown_is_exact_deterministic_and_bounded(self):
        rows = [
            dict(
                id=f"item-{i}",
                path="/private/PASSWORD",
                head="abc",
                action="retain",
                disposition="retained",
                reasons=["SECRET"],
            )
            for i in range(1000)
        ]
        rows += [
            dict(
                id="unknown",
                path="/private",
                head="def",
                action="retain",
                disposition="retained_unknown",
                reasons=["SECRET"],
            ),
            dict(
                id="failed",
                path="/private",
                head="def",
                action="remove",
                disposition="failed",
                reasons=[],
            ),
        ]
        value = dict(
            schema="codex-wake.cleanup.v1",
            kind="result",
            status="HELD",
            repository="/private",
            entries=rows,
        )
        result = self.invoke(value)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(
            out["counts"]["disposition"],
            {"retained": 1000, "retained_unknown": 1, "failed": 1},
        )
        self.assertEqual(out["failure_count"], 1)
        self.assertEqual(out["unknown_count"], 1)
        self.assertLessEqual(len(result.stdout), 8192)
        self.assertNotIn(b"PASSWORD", result.stdout)
        self.assertNotIn(b"SECRET", result.stdout)
        first = self.invoke(value, "--entry", "unknown")
        named = json.loads(first.stdout)
        self.assertEqual(len(named["entries"]), 1)
        self.assertEqual(named["entries"][0]["disposition"], "retained_unknown")
        self.assertEqual(named["omitted_count"], 1001)
        self.assertEqual(
            named["entries"],
            json.loads(self.invoke(value, "--entry", named["entries"][0]["id"]).stdout)[
                "entries"
            ],
        )
        self.assertNotEqual(self.invoke(value, "--entry", "missing").returncode, 0)
        self.assertNotEqual(self.invoke(value, "--max-bytes", "64").returncode, 0)

    def test_malformed_unsupported_and_ambiguous_receipts_are_rejected(self):
        for value in [
            None,
            {},
            dict(schema=2),
            dict(schema=True),
            dict(schema=1, status="PASS", checks=[], actions="bad"),
            dict(
                schema=1,
                status="PASS",
                checks=[dict(name="x", status="invented")],
                actions=[],
            ),
            dict(
                schema="codex-wake.cleanup.v1",
                kind="plan",
                status="PASS",
                repository="x",
                entries=[{}],
            ),
        ]:
            with self.subTest(value=value):
                result = self.invoke(value)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")
        value = dict(
            schema=1,
            status="FAIL",
            checks=[
                dict(name="same", status="FAIL"),
                dict(name="same", status="BLOCKED"),
            ],
            actions=[],
        )
        self.assertNotEqual(self.invoke(value, "--entry", "same").returncode, 0)


if __name__ == "__main__":
    unittest.main()
