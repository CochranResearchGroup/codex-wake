#!/usr/bin/env python3
"""Installed MCP request/reply on a private bus; no native turns or notifications."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time

from mcp import Client, StdioServerParameters
from websockets.sync.server import unix_serve


async def smoke(cli, mcp_command):
    started = time.monotonic()
    methods, calls = [], []
    children = Path(f"/proc/self/task/{os.getpid()}/children")
    children_before = children.read_text().split()
    with tempfile.TemporaryDirectory(prefix="wake-mcp-smoke-") as directory:
        root = Path(directory)
        roots = [root / "sender", root / "recipient"]
        for cwd in roots:
            cwd.mkdir()
        home, socket, bus = root / "codex", root / "runtime.sock", root / "bus"
        home.mkdir()
        ids = ["00000000-0000-7000-8000-000000000011", "00000000-0000-7000-8000-000000000012"]
        threads = {identifier: dict(id=identifier, name="MCP fixture", cwd=str(cwd),
                    modelProvider="fixture", parentThreadId=None, status=dict(type="idle"))
                   for identifier, cwd in zip(ids, roots)}

        def handle(connection):
            for raw in connection:
                request = json.loads(raw)
                method = request["method"]
                methods.append(method)
                if method == "initialized":
                    continue
                if method == "initialize":
                    value = dict(codexHome=str(home), userAgent="fixture")
                elif method == "thread/loaded/list":
                    value = dict(data=ids, nextCursor=None)
                elif method == "thread/read":
                    assert request["params"]["includeTurns"] is False
                    value = dict(thread=threads[request["params"]["threadId"]])
                else:
                    raise AssertionError("unexpected runtime effect: " + method)
                connection.send(json.dumps(dict(id=request["id"], result=value)))

        tools = root / "bin"
        tools.mkdir()
        tmux = tools / "tmux"
        tmux.write_text("#!/bin/sh\nexit 0\n")
        tmux.chmod(0o700)
        env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ.get("PATH", ""))
        for key in ("PYTHONPATH", "TMUX", "TMUX_PANE", "CODEX_THREAD_ID", "CODEX_WAKE_A2A_CAPABILITY",
                    "CODEX_WAKE_A2A_BUS_ROOT", "CODEX_WAKE_WAKE_ROOT", "CODEX_WAKE_SENDER_RECEIPT_AUTHORITY"):
            env.pop(key, None)

        def invoke(arguments):
            result = subprocess.run([cli, "a2a", *arguments, "--bus-root", str(bus), "--json"],
                cwd=roots[0], env=env, capture_output=True, text=True, timeout=15)
            assert result.returncode == 0, (result.stdout, result.stderr)
            return json.loads(result.stdout)

        with unix_serve(handle, path=str(socket)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                operator = invoke(["configure", "--allow-cross-root"])["operator_capability_file"]
                capabilities = [invoke(["enroll", str(cwd), "--thread", "thread:" + identifier,
                    "--app-server", "unix://" + str(socket), "--operator-capability", operator])["actor_capability_file"]
                    for identifier, cwd in zip(ids, roots)]

                def parameters(actor, capability=None, inherited_pane=None):
                    # Stock Codex does not supply a current thread in MCP startup env.
                    environment = dict(env)
                    if inherited_pane:
                        environment["TMUX_PANE"] = inherited_pane
                    return StdioServerParameters(command=mcp_command,
                        args=["--bus-root", str(bus), "--capability", capability or capabilities[actor],
                              "--app-server", "unix://" + str(socket)], cwd=roots[actor], env=environment)

                async def call(client, name, arguments, error=False):
                    actor = 0 if client is sender else 1
                    response = await client.call_tool(name, {**arguments, "caller_thread_id": ids[actor]})
                    value = json.loads(response.content[0].text)
                    assert response.is_error == error, (name, value)
                    calls.append({"tool": name, "is_error": response.is_error})
                    return value

                async with Client(parameters(0), mode="legacy") as sender, Client(parameters(1), mode="legacy") as recipient:
                    discovered = [tool.name for tool in (await sender.list_tools()).tools]
                    assert len(discovered) == 14
                    current = await call(sender, "wake_sessions_current", {})
                    assert current["session"]["thread_id"] == ids[0]
                    admission = await call(sender, "wake_messages_send", {
                        "to": "thread:" + ids[1], "body": "Private MCP fixture request",
                        "idempotency_key": "mcp-request", "delivery": "inbox"})
                    identifier = admission["message"]["message_id"]
                    same = await call(sender, "wake_messages_send", {
                        "to": "thread:" + ids[1], "body": "Private MCP fixture request",
                        "idempotency_key": "mcp-request", "delivery": "inbox"})
                    assert same["deduplicated"] and same["message"]["message_id"] == identifier
                    shared_denial = await sender.call_tool("wake_messages_read", {
                        "caller_thread_id": ids[1], "message_id": identifier})
                    refusal = json.loads(shared_denial.content[0].text)
                    assert shared_denial.is_error and refusal["error"]["code"] == "authorization_denied"
                    assert "body" not in refusal
                    calls.append({"tool": "wake_messages_read", "is_error": True, "shared_connection_child_claim": True})
                    async with Client(parameters(1, capabilities[0], "%inherited"), mode="legacy") as denied:
                        refusal = await call(denied, "wake_messages_read", {"message_id": identifier}, error=True)
                        assert refusal["error"]["code"] == "authorization_denied" and "body" not in refusal
                    body = await call(recipient, "wake_messages_read", {"message_id": identifier})
                    assert body["body"] == "Private MCP fixture request" and body["peer_content_trust"] == "untrusted"
                    claim = await call(recipient, "wake_messages_ack", {"message_id": identifier, "outcome": "accepted"})
                    assert claim["claimed"]
                    repeated = await call(recipient, "wake_messages_ack", {"message_id": identifier, "outcome": "accepted"})
                    assert not repeated["claimed"] and repeated["receipt_id"] == claim["receipt_id"]
                    reply = await call(recipient, "wake_messages_reply", {
                        "message_id": identifier, "body": "Private MCP fixture result", "idempotency_key": "mcp-reply",
                        "delivery": "inbox", "outcome": "completed", "evidence": "/fixture/result"})
                    assert reply["message"]["in_reply_to"] == identifier
                    returned = await call(sender, "wake_messages_read", {"message_id": reply["message"]["message_id"]})
                    assert returned["body"] == "Private MCP fixture result"
                    reconciled = await call(recipient, "wake_messages_reconcile", {"message_id": identifier})
                    assert reconciled["processing_reconciliation"]["state"] == "known_terminal", reconciled
            finally:
                server.shutdown()
                worker.join(timeout=3)
                assert not worker.is_alive()
    assert children.read_text().split() == children_before
    return dict(status="PASS", tools=discovered, calls=calls, elapsed_seconds=time.monotonic() - started,
                runtime_methods=sorted(set(methods)), owned_fixture_removed=not root.exists(),
                children_after=len(children_before), native_turns=0, notifications=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--mcp", required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    result = asyncio.run(smoke(args.cli, args.mcp))
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
