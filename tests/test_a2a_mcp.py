"""Protocol tests for the optional actor-scoped agent exchange MCP."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("mcp"), "install codex-wake[mcp] for MCP tests")
class AgentExchangeMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_preserves_intent_and_does_not_retry_or_run_invalid_input(self):
        for startup_delay in (0, 0.2):
            with self.subTest(startup_delay=startup_delay):
                await self.timeout_case(startup_delay)

    async def timeout_case(self, startup_delay):
        from mcp import Client, StdioServerParameters
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "called"
            cli = root / "slow-cli"
            cli.write_text(f"#!{sys.executable}\nimport pathlib,time\n"
                           f"time.sleep({startup_delay})\n"
                           f"p=pathlib.Path({str(marker)!r})\nwith p.open('a') as f:f.write('called\\n')\n"
                           "time.sleep(2)\nwith p.open('a') as f:f.write('finished\\n')\n")
            cli.chmod(0o700)
            parameters = StdioServerParameters(command=sys.executable,
                args=["-m", "codex_wake.mcp_server", "--cli", str(cli), "--call-timeout", "0.1"],
                cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "src")))
            async with Client(parameters, mode="legacy") as client:
                invalid = await client.call_tool("wake_messages_send", {"to": "thread:fixture"})
                self.assertTrue(invalid.is_error)
                self.assertFalse(marker.exists())
                uncertain = await client.call_tool("wake_messages_send", {
                    "to": "thread:fixture", "body": "fixture", "idempotency_key": "original-intent",
                    "delivery": "inbox", "caller_thread_id": "00000000-0000-7000-8000-000000000011"})
                value = json.loads(uncertain.content[0].text)
                self.assertTrue(uncertain.is_error)
                self.assertEqual(value["error"]["code"], "effect_uncertain")
                self.assertEqual(value["idempotency_key"], "original-intent")
                self.assertTrue(value["reconciliation_required"])
                # Timeout includes interpreter startup, so it cannot promise
                # the child began. Any observed start must still be singular.
                observed = marker.read_text().splitlines() if marker.exists() else []
                self.assertIn(observed, ([], ['called']))

    async def test_discovery_has_explicit_actor_tools_without_operator_escape(self):
        from mcp import Client, StdioServerParameters
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        parameters = StdioServerParameters(command=sys.executable,
            args=["-m", "codex_wake.mcp_server"], cwd=ROOT, env=env)
        async with Client(parameters, mode="legacy") as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            self.assertIn("wake_messages_send", tools)
            self.assertIn("wake_messages_arm_reply", tools)
            self.assertIn("wake_sessions_resolve", tools)
            self.assertNotIn("wake_operator", tools)
            self.assertFalse(tools["wake_messages_send"].annotations.read_only_hint)
            self.assertFalse(tools["wake_messages_read"].annotations.read_only_hint)
            self.assertFalse(tools["wake_messages_show"].annotations.read_only_hint)
            self.assertNotIn("capability", tools["wake_messages_send"].input_schema["properties"])
            result = await client.call_tool("wake_messages_send", {
                "to": "thread:fixture", "body": "test", "idempotency_key": "fixture",
                "capability": "/caller/chosen/credential",
                "caller_thread_id": "00000000-0000-7000-8000-000000000011"})
            self.assertTrue(result.is_error)
            self.assertEqual(json.loads(result.content[0].text)["error"]["code"], "invalid_argument")


if __name__ == "__main__":
    unittest.main()
