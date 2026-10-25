"""Owned installed CLI/MCP renewal acceptance against injected native protocol.

No provider requests, real Codex sessions, shared services or production policies.
Uses the configured qualified clock; transcript accounting/native controls are
explicit fixtures. Run with the installed candidate Python and --prefix.
"""

import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import tempfile
import time

from mcp import Client, StdioServerParameters
from mcp.types import RequestParamsMeta
from websockets.sync.server import unix_serve

import codex_wake
from codex_wake.lifecycle_budget import trusted_upper
from codex_wake.native_protocol import native_request

OWNED = "00000000-0000-7000-8000-000000000346"
PEER = "00000000-0000-7000-8000-000000000347"
TASK = "renewal-acceptance"


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def require(condition, label, value=None):
    if not condition:
        raise AssertionError(
            label
            + (": " + json.dumps(value, sort_keys=True) if value is not None else "")
        )


async def qualify(prefix, source, output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    package = Path(codex_wake.__file__).parent.resolve()
    require(
        package.is_relative_to(prefix),
        "candidate Python must import installed package from --prefix",
    )
    matched = []
    for path in sorted((source / "src/codex_wake").glob("*.py")):
        require(
            path.read_bytes() == (package / path.name).read_bytes(),
            "installed source mismatch",
            path.name,
        )
        matched.append(path.name)
    report = dict(
        status="INCOMPLETE",
        source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=source, text=True
        ).strip(),
        installed_prefix=str(prefix),
        installed_version=codex_wake.__version__,
        matched_python_files=len(matched),
        installed_module=str(package),
        clock="configured qualified UTC",
        native_protocol="injected owned Unix websocket",
        native_frontend_acceptance=False,
        external_provider_calls=0,
        model_turns_started=0,
        shared_service_mutations=0,
    )
    root = output / "wake"
    root.mkdir(mode=0o700)
    home = output / "home"
    (home / "sessions").mkdir(mode=0o700, parents=True)
    bus = output / "bus"
    executable = prefix / "bin/python"
    cli = prefix / "bin/codex-wake"
    mcp = prefix / "bin/codex-wake-mcp"
    env = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "CODEX_THREAD_ID",
        "TMUX",
        "TMUX_PANE",
        "CODEX_WAKE_A2A_CAPABILITY",
        "CODEX_WAKE_A2A_BUS_ROOT",
        "CODEX_WAKE_WAKE_ROOT",
        "CODEX_WAKE_SENDER_RECEIPT_AUTHORITY",
    ):
        env.pop(key, None)
    # Keep the configured read-only trusted clock endpoint; isolate writable XDG state.
    for key, child in (
        ("XDG_STATE_HOME", "state"),
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_RUNTIME_DIR", "run"),
    ):
        env[key] = str(output / child)
    created = int(trusted_upper()) - 2
    timestamp = datetime.fromtimestamp(created, timezone.utc).isoformat()
    mutex = threading.Lock()
    requests = []
    goals = {
        thread: dict(
            threadId=thread,
            createdAt=created,
            status="paused",
            objective="Owned injected " + thread,
        )
        for thread in (OWNED, PEER)
    }
    native_turns = {thread: [] for thread in goals}
    for thread, tokens in ((OWNED, 100), (PEER, 20)):
        rows = [
            dict(
                type="session_meta",
                payload=dict(id=thread, session_id=thread, source="cli"),
            ),
            dict(
                type="event_msg",
                payload=dict(
                    type="thread_goal_updated",
                    threadId=thread,
                    goal=deepcopy(goals[thread]),
                ),
            ),
            dict(
                type="event_msg",
                payload=dict(type="task_started", turn_id="fixture-work"),
            ),
            dict(
                type="token_usage_record",
                payload=dict(
                    thread_id=thread,
                    turn_id="fixture-work",
                    root_turn_id="fixture-work",
                    session_id=thread,
                    response_id="fixture-response",
                    usage=dict(
                        input_tokens=tokens - 2,
                        cached_input_tokens=0,
                        output_tokens=2,
                        total_tokens=tokens,
                    ),
                    turn_token_usage={},
                    thread_token_usage={},
                ),
            ),
            dict(
                type="event_msg",
                payload=dict(type="task_complete", turn_id="fixture-work"),
            ),
        ]
        (home / "sessions" / (thread + ".jsonl")).write_text(
            "".join(json.dumps(dict(timestamp=timestamp, **row)) + "\n" for row in rows)
        )
    socket_home = tempfile.TemporaryDirectory(prefix="cw346-")
    endpoint = Path(socket_home.name) / "native.sock"
    policy = output / "policy.json"
    save(
        policy,
        dict(
            version=1,
            callers={
                thread: dict(
                    app_server="unix://" + str(endpoint),
                    codex_path=str(executable),
                    codex_home=str(home),
                    allocation_id="fixture-" + thread,
                    max_tokens=1000,
                    max_seconds=1200,
                    rpc_timeout=2,
                )
                for thread in goals
            },
        ),
    )
    harness = output / "harness.json"
    save(harness, dict(version=1, controllers={OWNED: [TASK], PEER: [TASK]}))

    def handler(ws):
        for raw in ws:
            message = json.loads(raw)
            if "id" not in message:
                continue
            method = message["method"]
            params = message.get("params", {})
            with mutex:
                if method == "initialize":
                    result = {}
                else:
                    thread = params.get("threadId")
                    require(thread in goals, "foreign target", params)
                    requests.append(dict(method=method, params=params))
                    if method == "thread/goal/get":
                        result = dict(goal=deepcopy(goals[thread]))
                    elif method == "thread/read":
                        result = dict(
                            thread=dict(id=thread, turns=deepcopy(native_turns[thread]))
                        )
                    elif method == "thread/turns/list":
                        result = dict(
                            data=deepcopy(native_turns[thread]), nextCursor=None
                        )
                    elif method == "thread/goal/set":
                        require(
                            params.get("status") in ("active", "paused"),
                            "unexpected control",
                            params,
                        )
                        goals[thread]["status"] = params["status"]
                        result = dict(goal=deepcopy(goals[thread]))
                    elif method.startswith("thread/notice/"):
                        ws.send(
                            json.dumps(
                                dict(
                                    id=message["id"],
                                    error=dict(
                                        code=-32601,
                                        message="injected presenter unsupported",
                                    ),
                                )
                            )
                        )
                        continue
                    else:
                        raise AssertionError("unexpected native request " + method)
            ws.send(json.dumps(dict(id=message["id"], result=result)))

    command_records = []

    def invoke(words, expected=0):
        command = [str(cli), *words]
        result = subprocess.run(
            command, env=env, cwd=output, text=True, capture_output=True, timeout=30
        )
        command_records.append(
            dict(
                arguments=words,
                exit_code=result.returncode,
                stderr=result.stderr[-1000:],
            )
        )
        require(
            result.returncode == expected,
            "installed CLI exit",
            dict(arguments=words, stdout=result.stdout, stderr=result.stderr),
        )
        return json.loads(result.stdout)

    operator = invoke(["a2a", "configure", "--bus-root", str(bus), "--json"])[
        "operator_capability_file"
    ]
    auth = ["--bus-root", str(bus), "--operator-capability", operator]
    common = output / "common-permissions.json"
    save(common, {"version": 1, "global": {"actions": {"attention.respond": "allow"}}})
    invoke(
        [
            "--wake-root",
            str(root),
            "permissions",
            "configure",
            "--file",
            str(common),
            "--expected-revision",
            "0",
            *auth,
        ]
    )
    base = ["--wake-root", str(root), "goal-limits"]

    def goal_cli(verb, thread=OWNED, *extra, expected=0):
        return invoke(
            [
                *base,
                verb,
                "--policy",
                str(policy),
                "--caller-thread-id",
                thread,
                *auth,
                "--json",
                *extra,
            ],
            expected,
        )

    def rpc(method, params):
        return native_request(
            "unix://" + str(endpoint), str(executable), method, params, 3
        )

    async def until(predicate, seconds=12):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            value = goal_cli("show")
            if predicate(value):
                return value
            require(watcher.poll() is None, "owned watcher exited")
            await asyncio.sleep(0.05)
        raise AssertionError("bounded acceptance observation timed out")

    watcher = None
    log = (output / "watcher.log").open("w")
    try:
        with unix_serve(handler, str(endpoint)) as server:
            serving = threading.Thread(target=server.serve_forever, daemon=True)
            serving.start()
            watcher = subprocess.Popen(
                [
                    str(cli),
                    "--wake-root",
                    str(root),
                    "goal-limits",
                    "watch",
                    "--interval",
                    ".2",
                ],
                env=env,
                cwd=output,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            await until(lambda value: value.get("controller", {}).get("fresh"))
            initial = goal_cli(
                "set",
                OWNED,
                "--token-limit",
                "100",
                "--time-limit-seconds",
                "120",
                expected=2,
            )
            peer = goal_cli(
                "set", PEER, "--token-limit", "500", "--time-limit-seconds", "600"
            )
            await until(lambda value: value.get("state") == "stopped")
            peer_before = goal_cli("show", PEER)
            with mutex:
                peer_goal_before = deepcopy(goals[PEER])
            params = StdioServerParameters(
                command=str(mcp),
                args=[
                    "--wake-root",
                    str(root),
                    "--goal-limits-policy",
                    str(policy),
                    "--harness-policy",
                    str(harness),
                ],
                env=env,
            )
            async with Client(params, mode="legacy", read_timeout_seconds=30) as client:

                async def call(name, arguments, *, expected_error=False):
                    metadata = dict(
                        threadId=OWNED,
                        sessionId=OWNED,
                        callId="owned-installed-" + name,
                        **{
                            "x-codex-turn-metadata": dict(
                                thread_id=OWNED,
                                session_id=OWNED,
                                turn_id="operator-request",
                            )
                        },
                    )
                    reply = await client.call_tool(
                        name,
                        dict(caller_thread_id=OWNED, task_id=TASK, **arguments),
                        meta=RequestParamsMeta(**metadata),
                    )
                    value = json.loads(reply.content[0].text)
                    require(
                        bool(reply.is_error) == expected_error,
                        "installed MCP result",
                        value,
                    )
                    return value

                catalog = await client.list_tools()
                names = {tool.name for tool in catalog.tools}
                require(
                    {
                        "wake_goal_limits_extend",
                        "wake_goal_limits_reset",
                        "wake_goal_limits_apply_renewal",
                    }
                    <= names,
                    "installed MCP catalog",
                )
                now = trusted_upper()
                proposal = await call(
                    "wake_goal_limits_extend",
                    dict(
                        operation_id="installed-extension",
                        token_limit=150,
                        deadline=now + 300,
                        expires_at=now + 180,
                        resume=True,
                    ),
                )
                require(
                    proposal["proposal"]["old"]["used_tokens"] == 100,
                    "extension original spending",
                    proposal,
                )
                require(
                    proposal["proposal"]["new"]["remaining_tokens"] == 50,
                    "extension proposal remaining",
                    proposal,
                )
                denied = await call(
                    "wake_goal_limits_apply_renewal",
                    dict(
                        proposal_id=proposal["proposal_id"],
                        fingerprint=proposal["fingerprint"],
                    ),
                    expected_error=True,
                )
                require(
                    goal_cli("show")["token_limit"] == 100,
                    "unapproved model change affected authority",
                )
                row = proposal["attention"]
                response = invoke(
                    [
                        "--wake-root",
                        str(root),
                        "attention",
                        "respond",
                        *auth,
                        "--request-id",
                        row["request_id"],
                        "--choice",
                        "accept",
                        "--expected-revision",
                        str(row["revision"]),
                        "--fingerprint",
                        row["fingerprint"],
                        "--json",
                    ]
                )
                require(
                    response["status"] == "responded",
                    "public operator response",
                    response,
                )
                applied = await call(
                    "wake_goal_limits_apply_renewal",
                    dict(
                        proposal_id=proposal["proposal_id"],
                        fingerprint=proposal["fingerprint"],
                    ),
                )
                require(
                    applied["status"] == "applied"
                    and applied["new"]["used_tokens"] == 100,
                    "approved extension",
                    applied,
                )
                acknowledgement = await until(
                    lambda value: value.get("poll_ack", {}).get("enrollment_revision")
                    == value.get("enrollment_revision")
                    and value.get("enrollment_revision", 0)
                    > initial.get("enrollment_revision", 1)
                )
                resumed = await call(
                    "wake_goal_limits_apply_renewal",
                    dict(
                        proposal_id=proposal["proposal_id"],
                        fingerprint=proposal["fingerprint"],
                    ),
                )
                require(
                    resumed.get("resumed") is True,
                    "approved resume verification",
                    resumed,
                )
                require(
                    rpc("thread/goal/get", dict(threadId=OWNED))["goal"]["status"]
                    == "active",
                    "native resume readback",
                )
                repeated = await call(
                    "wake_goal_limits_apply_renewal",
                    dict(
                        proposal_id=proposal["proposal_id"],
                        fingerprint=proposal["fingerprint"],
                    ),
                )
                require(repeated == resumed, "duplicate resume not idempotent")
                # Explicit operator pause prepares the independently authorized reset.
                rpc("thread/goal/set", dict(threadId=OWNED, status="paused"))
                reset = goal_cli(
                    "reset",
                    OWNED,
                    "--operation-id",
                    "installed-reset",
                    "--token-limit",
                    "80",
                    "--remaining-seconds",
                    "240",
                    "--apply",
                )
                reset_status = await until(
                    lambda value: value["generation"] != initial["generation"]
                    and value["used_tokens"] == 0
                )
                require(
                    reset_status["lifetime_used_tokens"] == 100,
                    "reset lifetime preservation",
                    reset_status,
                )
                require(
                    reset["status"] == "applied" and not reset["resumed"],
                    "apply-only reset resumed",
                    reset,
                )
                require(
                    rpc("thread/goal/get", dict(threadId=OWNED))["goal"]["status"]
                    == "paused",
                    "reset must leave paused",
                )
                peer_after = goal_cli("show", PEER)
                for key in (
                    "allocation_id",
                    "generation",
                    "token_limit",
                    "used_tokens",
                    "deadline",
                    "time_origin",
                    "enrollment_revision",
                    "state",
                    "reason",
                    "stop_latched",
                    "effects",
                    "checkpoint",
                ):
                    require(
                        peer_after.get(key) == peer_before.get(key),
                        "peer budget changed",
                        key,
                    )
                with mutex:
                    require(goals[PEER] == peer_goal_before, "peer native goal changed")
                    require(
                        not any(
                            row["params"].get("threadId") == PEER
                            and row["method"]
                            not in (
                                "thread/goal/get",
                                "thread/read",
                                "thread/turns/list",
                            )
                            for row in requests
                        ),
                        "peer received native effects",
                    )
                    require(
                        not any(row["method"] == "turn/start" for row in requests),
                        "new model turn dispatched",
                    )
                report.update(
                    status="PASS",
                    startup_enrollment=initial,
                    extension_proposal=proposal,
                    model_self_increase_denied=denied,
                    operator_response=response,
                    extension=applied,
                    new_revision_ack=acknowledgement,
                    resume=resumed,
                    reset=reset,
                    reset_status=reset_status,
                    peer_unchanged=True,
                    peer_before=peer_before,
                    peer_after=peer_after,
                    public_stdio_mcp_tools=len(names),
                    native_requests=deepcopy(requests),
                    cli_commands=command_records,
                )
                save(output / "receipt.json", report)
            server.shutdown()
            serving.join(timeout=3)
    except BaseException as error:
        report["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        report["cli_commands"] = command_records
        report["native_requests"] = deepcopy(requests)
        socket_home.cleanup()
        if watcher is not None:
            if watcher.poll() is None:
                watcher.terminate()
                try:
                    watcher.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    watcher.kill()
                    watcher.wait(timeout=3)
            report["watcher_cleanup"] = dict(
                pid=watcher.pid, exit_code=watcher.returncode, alive=False
            )
        log.close()
        save(output / "receipt.json", report)
    require(report["status"] == "PASS", "acceptance incomplete")
    print(
        json.dumps(
            dict(
                status=report["status"],
                receipt=str(output / "receipt.json"),
                source_commit=report["source_commit"],
                installed_prefix=str(prefix),
                peer_unchanged=report["peer_unchanged"],
                native_frontend_acceptance=False,
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument(
        "--source-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    asyncio.run(
        qualify(
            options.prefix.resolve(),
            options.source_root.resolve(),
            options.output.resolve(),
        )
    )
