"""Owned real-native, installed-Wake and stock-TUI goal-limit journey.

Runs only a localhost Responses fixture: at most six POSTs and 180 seconds.
Requires an explicitly pinned development app-server with thread/notice support.
It never replaces shared runtimes or reads provider credentials.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time

import codex_wake
from codex_wake.lifecycle_budget import trusted_upper
from codex_wake.native_protocol import native_request
from codex_wake.process import process_identity


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def qualify(options):
    base = options.output.resolve()
    base.mkdir(mode=0o700, parents=True, exist_ok=False)
    prefix = options.prefix.resolve()
    appserver = options.app_server.resolve()
    tui = options.tui.absolute()
    require(
        digest(appserver) == options.app_server_sha256,
        "pinned native app-server hash mismatch",
    )
    package = Path(codex_wake.__file__).resolve().parent
    require(
        package.is_relative_to(prefix),
        "run this script with the candidate installed prefix Python",
    )
    source = options.source_root.resolve()
    for path in (source / "src/codex_wake").glob("*.py"):
        require(
            path.read_bytes() == (package / path.name).read_bytes(),
            "installed source mismatch: " + path.name,
        )
    home = base / "home"
    home.mkdir(mode=0o700)
    workspace = base / "workspace"
    workspace.mkdir(mode=0o700)
    root = base / "wake"
    root.mkdir(mode=0o700)
    owned = tempfile.TemporaryDirectory(prefix="cw346-native-")
    socket_dir = Path(owned.name)
    alias = socket_dir / "native.sock"
    tmux_socket = socket_dir / "tmux.sock"
    expiry = time.monotonic() + 180
    report = dict(
        verdict="INCOMPLETE",
        started_at=datetime.now(timezone.utc).isoformat(),
        source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=source, text=True
        ).strip(),
        wake_prefix=str(prefix),
        wake_version=codex_wake.__version__,
        native_app_server=str(appserver),
        app_server_sha256=digest(appserver),
        stock_tui=str(tui),
        tui_sha256=digest(tui),
        provider="owned localhost Responses fixture",
        external_provider_calls=0,
        http_request_cap=6,
        native_frontend_acceptance=True,
        shared_runtime_replaced=False,
    )

    def save(name, value):
        path = base / name
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        path.chmod(0o600)

    def bounded():
        require(time.monotonic() < expiry, "180-second packet bound exhausted")

    mutex = threading.Lock()
    calls = []
    stream_open = threading.Event()
    finish = threading.Event()
    operator_open = threading.Event()
    operator_release = threading.Event()
    approved_application = {}
    policy = base / "policy.json"
    harness = base / "harness.json"
    stream_disconnected = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_error(404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024 * 1024:
                self.send_error(413)
                return
            body = self.rfile.read(length)
            with mutex:
                number = len(calls) + 1
                calls.append(
                    dict(
                        number=number,
                        path=self.path,
                        body_sha256=hashlib.sha256(body).hexdigest(),
                        operator_reply=b"Operator status question while the campaign stays paused."
                        in body,
                    )
                )
            save("response-request-" + str(number) + ".json", json.loads(body))
            if number > 6:
                self.send_error(429)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()

            def emit(value):
                self.wfile.write(
                    (
                        "event: "
                        + value["type"]
                        + "\ndata: "
                        + json.dumps(value)
                        + "\n\n"
                    ).encode()
                )
                self.wfile.flush()

            try:
                emit(
                    dict(
                        type="response.created",
                        response=dict(id="local-response-" + str(number)),
                    )
                )
                text = None
                item = None
                if number == 1:
                    text = "LOCAL FIXTURE READY"
                elif number in (2, 4, 5):
                    if number == 2:
                        name = "wake_goal_limits_set"
                        arguments = dict(
                            caller_thread_id=thread,
                            token_limit=1000,
                            time_limit_seconds=30,
                            checkpoint_token_percent=5,
                            checkpoint_seconds=5,
                        )
                    elif number == 4:
                        operator_open.set()
                        name = "wake_goal_limits_extend"
                        arguments = dict(
                            caller_thread_id=thread,
                            task_id="renewal-acceptance",
                            operation_id="native-extension",
                            token_limit=1500,
                            remaining_seconds=45,
                        )
                    else:
                        while (
                            not operator_release.wait(0.1)
                            and not finish.is_set()
                            and time.monotonic() < expiry
                        ):
                            self.wfile.write(
                                b": waiting exact public operator acceptance\n\n"
                            )
                            self.wfile.flush()
                        require(
                            bool(approved_application),
                            "exact approved application unavailable",
                        )
                        name = "wake_goal_limits_apply_renewal"
                        arguments = dict(
                            caller_thread_id=thread,
                            task_id="renewal-acceptance",
                            **approved_application,
                        )
                    advertised = json.loads(body).get("tools", [])
                    namespace = next(
                        (
                            tool["name"]
                            for tool in advertised
                            if tool.get("type") == "namespace"
                            and any(
                                value.get("name") == name
                                for value in tool.get("tools", [])
                            )
                        ),
                        None,
                    )
                    flat = next(
                        (
                            tool["name"]
                            for tool in advertised
                            if tool.get("type") == "function"
                            and (
                                tool.get("name") == name
                                or tool.get("name", "").endswith("__" + name)
                            )
                        ),
                        None,
                    )
                    require(
                        namespace is not None or flat is not None,
                        "actual advertised native MCP tool unavailable: " + name,
                    )
                    item = dict(
                        type="function_call",
                        name=name if namespace else flat,
                        call_id="owned-native-tool-" + str(number),
                        arguments=json.dumps(arguments),
                    )
                    if namespace:
                        item["namespace"] = namespace
                elif number == 3:
                    stream_open.set()
                    while not finish.wait(0.2) and time.monotonic() < expiry:
                        self.wfile.write(b": local fixture pending\n\n")
                        self.wfile.flush()
                elif number == 6:
                    text = "OPERATOR REPLY AFTER PAUSE"
                else:
                    raise AssertionError("unexpected localhost response number")
                if item:
                    emit(dict(type="response.output_item.done", item=item))
                if text:
                    emit(
                        dict(
                            type="response.output_item.done",
                            item=dict(
                                type="message",
                                role="assistant",
                                id="local-message-" + str(number),
                                content=[dict(type="output_text", text=text)],
                            ),
                        )
                    )
                emit(
                    dict(
                        type="response.completed",
                        response=dict(
                            id="local-response-" + str(number),
                            usage=dict(
                                input_tokens=20,
                                input_tokens_details=dict(cached_tokens=10),
                                output_tokens=0,
                                output_tokens_details=None,
                                total_tokens=20,
                            ),
                        ),
                    )
                )
            except (BrokenPipeError, ConnectionResetError):
                stream_disconnected.set()
            except BaseException as error:
                report["fixture_error"] = type(error).__name__ + ": " + str(error)
                raise
            finally:
                self.close_connection = True

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    http.daemon_threads = True
    http_thread = threading.Thread(target=http.serve_forever, daemon=True)
    http_thread.start()
    port = http.server_address[1]
    config = 'model="mock-model"\nmodel_provider="local_fixture"\napproval_policy="never"\nsandbox_mode="danger-full-access"\n'
    config += (
        '[model_providers.local_fixture]\nname="Local fixture only"\nbase_url="http://127.0.0.1:'
        + str(port)
        + '/v1"\nwire_api="responses"\nrequires_openai_auth=false\nrequest_max_retries=0\nstream_max_retries=0\nsupports_websockets=false\n'
    )
    config += (
        "[features]\ncode_mode=false\n[mcp_servers.wake]\ncommand="
        + json.dumps(str(prefix / "bin/codex-wake-mcp"))
        + "\nargs="
        + json.dumps(
            [
                "--wake-root",
                str(root),
                "--goal-limits-root",
                str(root),
                "--goal-limits-policy",
                str(policy),
                "--harness-policy",
                str(harness),
            ]
        )
        + "\n"
    )
    config += "[projects." + json.dumps(str(workspace)) + ']\ntrust_level="trusted"\n'
    (home / "config.toml").write_text(config)
    (home / "config.toml").chmod(0o600)
    env = dict(
        os.environ,
        CODEX_HOME=str(home),
        TERM="xterm-256color",
        OPENAI_BASE_URL="http://127.0.0.1:" + str(port) + "/v1",
    )
    for key in (
        "CODEX_THREAD_ID",
        "PYTHONPATH",
        "OPENAI_API_KEY",
        "CHATGPT_ACCESS_TOKEN",
        "CODEX_API_KEY",
        "TMUX",
        "TMUX_PANE",
        "CODEX_WAKE_A2A_CAPABILITY",
        "CODEX_WAKE_A2A_BUS_ROOT",
        "CODEX_WAKE_WAKE_ROOT",
        "CODEX_WAKE_SENDER_RECEIPT_AUTHORITY",
    ):
        env.pop(key, None)
    cli = prefix / "bin/codex-wake"
    command_receipts = []

    def invoke(words, expected=0):
        bounded()
        value = subprocess.run(
            [str(cli), *words],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        command_receipts.append(
            dict(
                arguments=words, exit_code=value.returncode, stderr=value.stderr[-500:]
            )
        )
        require(
            value.returncode == expected,
            "installed CLI failed "
            + json.dumps(
                dict(arguments=words, stdout=value.stdout, stderr=value.stderr)
            ),
        )
        return json.loads(value.stdout)

    bus = base / "bus"
    operator = invoke(["a2a", "configure", "--bus-root", str(bus), "--json"])[
        "operator_capability_file"
    ]
    auth = ["--bus-root", str(bus), "--operator-capability", operator]
    common = base / "common.json"
    save(
        "common.json",
        {"version": 1, "global": {"actions": {"attention.respond": "allow"}}},
    )
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
    native = None
    watcher = None
    ui_started = False
    ui_count = 0
    pane_pids = []
    tmux_pid = None
    nlog = (base / "native.log").open("w")
    wlog = (base / "watcher.log").open("w")

    def tmux(*words, check=True):
        value = subprocess.run(
            ["tmux", "-S", str(tmux_socket), *words],
            env=env,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if check:
            require(value.returncode == 0, "owned tmux failed " + value.stderr)
        return value.stdout

    def capture(name):
        text = tmux("capture-pane", "-t", "ux:0.0", "-p", "-S", "-3000")
        (base / name).write_text(text)
        return text

    def attach(endpoint, thread):
        nonlocal ui_started, ui_count, tmux_pid
        command = [
            "env",
            "CODEX_HOME=" + str(home),
            "TERM=xterm-256color",
            str(tui),
            "--remote",
            endpoint,
            "--no-alt-screen",
            "resume",
            thread,
        ]
        # Private tmux server/environment never addresses another user's pane.
        tmux(
            "new-session",
            "-d",
            "-s",
            "ux",
            "-x",
            "160",
            "-y",
            "55",
            shlex.join(command),
        )
        ui_started = True
        ui_count += 1
        tmux_pid = int(tmux("display-message", "-p", "#{pid}").strip())
        pane_pids.append(
            int(tmux("display-message", "-t", "ux:0.0", "-p", "#{pane_pid}").strip())
        )

    def wait(predicate, label, seconds=12):
        end = min(expiry, time.monotonic() + seconds)
        last = None
        while time.monotonic() < end:
            bounded()
            last = predicate()
            if last:
                return last
            if native and native.poll() is not None:
                raise AssertionError("owned native exited before " + label)
            if watcher and watcher.poll() is not None:
                raise AssertionError("owned watcher exited before " + label)
            time.sleep(0.08)
        raise AssertionError(label + " unavailable within bounded observation")

    try:
        native = subprocess.Popen(
            [
                str(appserver),
                "--listen",
                "unix://" + str(alias),
                "--session-source",
                "cli",
            ],
            cwd=workspace,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=nlog,
            stderr=nlog,
            start_new_session=True,
        )
        report.update(
            native_pid=native.pid, native_identity=process_identity(native.pid)
        )
        wait(
            lambda: alias.exists() and stat.S_ISSOCK(alias.stat().st_mode),
            "native physical socket",
            10,
        )
        physical = alias.resolve(strict=True)
        info = physical.lstat()
        require(
            info.st_uid == os.geteuid() and stat.S_ISSOCK(info.st_mode),
            "owned physical native socket required",
        )
        require(
            physical.parent.stat().st_uid == os.geteuid()
            and physical.parent.stat().st_mode & 0o077 == 0,
            "private native socket directory required",
        )
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            connection.connect(str(physical))
            pid, uid, _ = struct.unpack(
                "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
            )
        require(
            pid == native.pid and uid == os.geteuid(),
            "physical peer must be this exact owned native child",
        )
        endpoint = "unix://" + str(physical)
        report["endpoint"] = endpoint

        def rpc(method, params):
            bounded()
            return native_request(endpoint, str(tui), method, params, 3)

        save(
            "policy.json",
            dict(
                version=2,
                native_caller_binding=True,
                allocations={},
                self_enrollment=dict(
                    app_server=endpoint,
                    codex_path=str(tui),
                    codex_home=str(home),
                    max_tokens=2000,
                    max_seconds=180,
                    rpc_timeout=3,
                ),
            ),
        )
        save("harness.json", dict(version=1, controllers={}))
        thread = rpc(
            "thread/start",
            dict(cwd=str(workspace), historyMode="legacy", experimentalRawEvents=True),
        )["thread"]["id"]
        peer = rpc(
            "thread/start",
            dict(cwd=str(workspace), historyMode="legacy", experimentalRawEvents=True),
        )["thread"]["id"]
        rpc(
            "thread/name/set",
            dict(threadId=thread, name="Owned goal-limit UX acceptance"),
        )
        for selected in (thread, peer):
            rpc(
                "thread/notice/read",
                dict(threadId=selected, eventId="qualification-materialize-only"),
            )
        peer_goal = rpc(
            "thread/goal/set",
            dict(
                threadId=peer,
                objective="Unrelated owned acceptance peer",
                status="blocked",
                tokenBudget=1000000,
            ),
        )["goal"]
        peer_before = rpc("thread/read", dict(threadId=peer, includeTurns=True))[
            "thread"
        ]
        report.update(
            thread_id=thread,
            peer_thread_id=peer,
            peer_goal_before=peer_goal,
            peer_before=peer_before,
        )
        attach(endpoint, thread)
        wait(
            lambda: "context left" in capture("tui-initial.txt")
            or "mock-model" in capture("tui-initial.txt").lower(),
            "stock TUI attachment",
            15,
        )
        goal = rpc(
            "thread/goal/set",
            dict(
                threadId=thread,
                objective="Owned goal-limit UX journey",
                status="blocked",
                tokenBudget=1000000,
            ),
        )["goal"]
        first = rpc(
            "turn/start",
            dict(
                threadId=thread,
                input=[
                    dict(
                        type="text", text="Local transport fixture: respond READY only."
                    )
                ],
            ),
        )
        wait(
            lambda: any(
                turn["id"] == first["turn"]["id"] and turn["status"] == "completed"
                for turn in rpc(
                    "thread/read", dict(threadId=thread, includeTurns=True)
                )["thread"]["turns"]
            ),
            "first nonzero native response",
            15,
        )
        save(
            "harness.json",
            dict(version=1, controllers={thread: ["renewal-acceptance"]}),
        )

        def goal_cli(verb, *extra, expected=0):
            return invoke(
                [
                    "--wake-root",
                    str(root),
                    "goal-limits",
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
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            stdout=wlog,
            stderr=wlog,
            start_new_session=True,
        )
        report.update(
            watcher_pid=watcher.pid,
            watcher_identity=process_identity(watcher.pid),
            goal_before=goal,
        )
        wait(
            lambda: goal_cli("show").get("controller", {}).get("fresh"),
            "fresh independent watcher",
        )
        wait(
            lambda: trusted_upper() >= goal["createdAt"],
            "qualified original native goal time",
        )
        rpc(
            "thread/goal/set",
            dict(threadId=thread, status="active", tokenBudget=1000000),
        )
        wait(
            lambda: stream_open.is_set(),
            "actual native MCP enrollment continuation",
            15,
        )

        def tool_result(name):
            read = rpc("thread/read", dict(threadId=thread, includeTurns=True))[
                "thread"
            ]
            items = [
                item
                for turn in read["turns"]
                for item in turn["items"]
                if item["type"] == "mcpToolCall"
                and item.get("tool") == name
                and item.get("status") == "completed"
            ]
            if not items:
                return None
            item = items[-1]
            save("native-tool-" + name + ".json", item)
            require(
                not item.get("error"),
                "genuine native MCP tool failed: " + json.dumps(item),
            )
            result = item.get("result") or {}
            if isinstance(result.get("structuredContent"), dict):
                return result["structuredContent"]
            for part in result.get("content", []):
                if part.get("type") == "text":
                    value = json.loads(part["text"])
                    require(
                        "error" not in value,
                        "genuine native MCP returned an error: " + json.dumps(value),
                    )
                    return value
            raise AssertionError("native MCP result content unavailable")

        enrolled = wait(
            lambda: tool_result("wake_goal_limits_set"),
            "genuine native enrollment result",
        )
        require(
            enrolled["state"] in ("armed", "checkpoint_requested"),
            "native enrollment did not arm",
        )
        require(
            "callers" not in json.loads(policy.read_text()),
            "native enrollment required a per-session caller grant",
        )
        require(
            enrolled["used_tokens"] > 0,
            "native first response must qualify nonzero original history",
        )
        startup = wait(
            lambda: (value if (value := goal_cli("show")).get("poll_ack") else None),
            "startup first poll",
        )

        def notice(kind):
            rows = goal_cli("notices")["notices"]
            return next(
                (
                    row
                    for row in reversed(rows)
                    if row["identity"]["kind"] == kind
                    and row["delivery"]["state"] == "recorded"
                ),
                None,
            )

        startup_event = wait(lambda: notice("engagement"), "native startup append")
        wait(
            lambda: "External goal watcher engaged" in capture("tui-startup.txt"),
            "visible startup card",
        )
        require(
            capture("tui-startup.txt").count(startup_event["event_id"]) == 1,
            "startup card must render once",
        )
        report.update(enrolled=enrolled, startup=startup, startup_event=startup_event)
        before_active_calls = len(calls)
        wait(lambda: stream_open.is_set(), "owned active native stream", 8)
        active = rpc("thread/read", dict(threadId=thread, includeTurns=True))["thread"]
        active_ids = [
            turn["id"] for turn in active["turns"] if turn["status"] == "inProgress"
        ]
        require(len(active_ids) == 1, "exactly one active native work turn required")
        stopped = wait(
            lambda: (
                value if (value := goal_cli("show")).get("state") == "stopped" else None
            ),
            "real hard stop",
            40,
        )
        require(
            stopped.get("stop_proof") is True, "native pause/interrupt proof required"
        )
        require(
            rpc("thread/goal/get", dict(threadId=thread))["goal"]["status"] == "paused",
            "native goal not paused",
        )
        final_turns = rpc("thread/read", dict(threadId=thread, includeTurns=True))[
            "thread"
        ]["turns"]
        require(
            any(
                turn["id"] == active_ids[0] and turn["status"] == "interrupted"
                for turn in final_turns
            ),
            "captured native work not interrupted",
        )
        stop_event = wait(lambda: notice("stop"), "native stop append")
        wait(
            lambda: "Goal paused." in capture("tui-stop.txt"),
            "visible interrupting stop notice",
        )
        require(
            capture("tui-stop.txt").count(stop_event["event_id"]) == 1,
            "stop notice must render exactly once",
        )
        require(
            stop_event["proof"]["model_context"]["state"] == "available",
            "native stop unavailable to model context",
        )
        calls_after_stop = len(calls)
        require(
            calls_after_stop == before_active_calls,
            "notice delivery dispatched a fresh model turn",
        )
        report.update(
            stopped=stopped,
            stop_event=stop_event,
            active_turn_id=active_ids[0],
            http_calls_at_stop=calls_after_stop,
        )
        tmux("kill-session", "-t", "ux")
        ui_started = False
        attach(endpoint, thread)
        wait(
            lambda: stop_event["event_id"] in capture("tui-reconnected.txt"),
            "reconnected stop transcript",
            15,
        )
        require(
            capture("tui-reconnected.txt").count(stop_event["event_id"]) == 1,
            "reconnect duplicated stop notice",
        )
        # A later operator reply must remain usable while the campaign stays stopped.
        operator_turn = rpc(
            "turn/start",
            dict(
                threadId=thread,
                input=[
                    dict(
                        type="text",
                        text="Operator status question while the campaign stays paused.",
                    )
                ],
            ),
        )["turn"]["id"]
        wait(lambda: operator_open.is_set(), "later operator stream", 8)
        observed = goal_cli("show")
        heartbeat = observed["controller"]["observed_boottime"]
        wait(
            lambda: goal_cli("show")["controller"]["observed_boottime"]
            >= heartbeat + 0.4,
            "watcher observes operator reply",
        )
        turns = rpc("thread/read", dict(threadId=thread, includeTurns=True))["thread"][
            "turns"
        ]
        require(
            any(
                turn["id"] == operator_turn and turn["status"] == "inProgress"
                for turn in turns
            ),
            "watcher interrupted later operator reply",
        )
        spent = goal_cli("show")["used_tokens"]
        proposal = wait(
            lambda: tool_result("wake_goal_limits_extend"),
            "genuine active operator MCP proposal",
            15,
        )
        row = proposal["attention"]
        accepted = invoke(
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
        approved_application.update(
            proposal_id=proposal["proposal_id"], fingerprint=proposal["fingerprint"]
        )
        operator_release.set()
        extended = wait(
            lambda: tool_result("wake_goal_limits_apply_renewal"),
            "genuine active operator MCP apply",
            15,
        )
        wait(
            lambda: any(
                turn["id"] == operator_turn and turn["status"] == "completed"
                for turn in rpc(
                    "thread/read", dict(threadId=thread, includeTurns=True)
                )["thread"]["turns"]
            ),
            "later operator reply completion",
            10,
        )
        wait(
            lambda: "OPERATOR REPLY AFTER PAUSE" in capture("tui-operator-reply.txt"),
            "visible operator reply",
            10,
        )
        require(
            extended["new"]["used_tokens"] >= spent > 0,
            "extension lost nonzero cumulative usage",
        )
        require(
            rpc("thread/goal/get", dict(threadId=thread))["goal"]["status"] == "paused",
            "apply-only extension resumed native goal",
        )
        revision = wait(
            lambda: (
                value
                if (value := goal_cli("show")).get("enrollment_revision")
                == extended["new"]["revision"]
                else None
            ),
            "renewed revision first poll",
        )
        wait(
            lambda: len(
                [
                    event
                    for event in goal_cli("notices")["notices"]
                    if event["identity"]["kind"] == "engagement"
                    and event["delivery"]["state"] == "recorded"
                ]
            )
            >= 2,
            "renewed startup append",
        )
        capture("tui-extension.txt")
        reset = goal_cli(
            "reset",
            "--operation-id",
            "native-reset",
            "--token-limit",
            "1000",
            "--remaining-seconds",
            "45",
            "--apply",
        )
        reset_state = wait(
            lambda: (
                value
                if (value := goal_cli("show")).get("generation")
                != enrolled["generation"]
                and value.get("poll_ack")
                else None
            ),
            "reset new-window first poll",
        )
        require(
            reset_state["used_tokens"] == 0
            and reset_state["lifetime_used_tokens"] >= spent,
            "reset erased lifetime accounting",
        )
        require(
            rpc("thread/goal/get", dict(threadId=thread))["goal"]["status"] == "paused",
            "reset apply-only must leave native goal paused",
        )
        events = wait(
            lambda: (
                [
                    event
                    for event in goal_cli("notices")["notices"]
                    if event["identity"]["kind"] == "engagement"
                    and event["delivery"]["state"] == "recorded"
                ]
                if len(
                    [
                        event
                        for event in goal_cli("notices")["notices"]
                        if event["identity"]["kind"] == "engagement"
                        and event["delivery"]["state"] == "recorded"
                    ]
                )
                >= 3
                else None
            ),
            "reset startup append",
        )
        wait(
            lambda: capture("tui-reset.txt").count("External goal watcher engaged")
            >= 3,
            "visible startup cards for renewed revisions",
        )
        peer_after = rpc("thread/read", dict(threadId=peer, includeTurns=True))[
            "thread"
        ]
        require(
            rpc("thread/goal/get", dict(threadId=peer))["goal"] == peer_goal,
            "unrelated native peer goal changed",
        )
        require(
            peer_after["turns"] == peer_before["turns"],
            "unrelated native peer turns changed",
        )
        require(len(calls) <= 6, "localhost fixture request cap exceeded")
        report.update(
            verdict="PASS_REAL_NATIVE_INSTALLED_TUI_JOURNEY",
            operator_reply_preserved=True,
            operator_turn_id=operator_turn,
            extension_proposal=proposal,
            operator_acceptance=accepted,
            extension=extended,
            extended_revision=revision,
            reset=reset,
            reset_state=reset_state,
            peer_after=peer_after,
            peer_unchanged=True,
            notification_started_no_model_turn=True,
            genuine_native_mcp_enrollment=True,
            genuine_native_mcp_operator_renewal=True,
            no_per_session_caller_grant=True,
            engagement_events=[event["event_id"] for event in events],
            ui_attachments=ui_count,
        )
    except BaseException as error:
        report.update(
            verdict="FAILED_PACKET", error=type(error).__name__ + ": " + str(error)
        )
        if ui_started:
            try:
                capture("tui-failure.txt")
            except Exception:
                pass
    finally:
        finish.set()
        operator_release.set()
        groups = []
        for pid in [
            native.pid if native else None,
            watcher.pid if watcher else None,
            *pane_pids,
            tmux_pid,
        ]:
            if pid:
                try:
                    groups.append(os.getpgid(pid))
                except ProcessLookupError:
                    pass
        try:
            tmux("kill-server", check=False)
        except Exception:
            pass
        for name, process in (("watcher", watcher), ("native", native)):
            if process is not None:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=3)
                report[name + "_cleanup"] = dict(
                    pid=process.pid,
                    exit_code=process.returncode,
                    identity_after=process_identity(process.pid),
                )
        http.shutdown()
        http.server_close()
        http_thread.join(timeout=2)
        nlog.close()
        wlog.close()
        rows = []
        for line in subprocess.check_output(
            ["ps", "-eo", "pid,ppid,pgid,args"], text=True
        ).splitlines()[1:]:
            fields = line.split(None, 3)
            if len(fields) == 4 and int(fields[2]) in groups:
                rows.append(
                    dict(
                        pid=int(fields[0]),
                        ppid=int(fields[1]),
                        pgid=int(fields[2]),
                        executable=fields[3].split(None, 1)[0],
                    )
                )
        report.update(
            http_calls=deepcopy(calls),
            stream_disconnected=stream_disconnected.is_set(),
            elapsed_seconds=180 - max(0, expiry - time.monotonic()),
            commands=command_receipts,
            final_owned_process_census=rows,
        )
        if rows:
            report.update(
                verdict="FAILED_PACKET",
                cleanup_error="owned process group remains populated",
            )
        save("receipt.json", report)
        owned.cleanup()
    print(
        json.dumps(
            dict(
                verdict=report["verdict"],
                error=report.get("error"),
                http_calls=len(calls),
                receipt=str(base / "receipt.json"),
            )
        )
    )
    return 0 if report["verdict"] == "PASS_REAL_NATIVE_INSTALLED_TUI_JOURNEY" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument(
        "--source-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--app-server", type=Path, required=True)
    parser.add_argument("--app-server-sha256", required=True)
    parser.add_argument("--tui", type=Path, required=True)
    raise SystemExit(qualify(parser.parse_args()))
