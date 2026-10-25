"""Opt-in, isolated two-thread scoped MCP reload acceptance; zero model turns.

This is a runtime probe, never part of default tests. Only the supplied empty
fixture root, its private native server, and identity-owned children are changed.
"""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import stat
import subprocess
import time

from codex_wake.native_protocol import native_request


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def _sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _private_network():
    namespace = os.readlink("/proc/self/ns/net")
    parent_namespace = os.environ.get("CODEX_WAKE_QUALIFICATION_PARENT_NETNS")
    if not parent_namespace:
        parent_namespace = os.readlink("/proc/1/ns/net")
    if namespace == parent_namespace or {name for _, name in socket.if_nameindex()} != {
        "lo"
    }:
        raise RuntimeError(
            "managed qualification requires an isolated loopback-only network namespace"
        )
    routes = Path("/proc/net/route").read_text().splitlines()[1:]
    if any(line.split()[0] != "lo" for line in routes if line.strip()):
        raise RuntimeError("private network namespace has an external route")
    return dict(
        namespace=namespace,
        parent_namespace=parent_namespace,
        interfaces=["lo"],
        external_routes=0,
    )


class ManagedFixture:
    """Exercise only documented lifecycle commands against the owned fixed path."""

    def __init__(self, root, home, env, receipt):
        self.root, self.home, self.env, self.receipt = root, home, env, receipt
        self.current = home / "packages/standalone/current"
        self.current.parent.mkdir(mode=0o700, parents=True)
        self.pid = None
        self.cli = None
        self.records = receipt.setdefault("managed_lifecycle", {})

    def stage(self, source, label, code_mode_host=None):
        source = source.resolve(strict=True)
        digest = _sha256(source)
        bundle = self.current.parent / "releases" / (label + "-" + digest[:16])
        package = source.parent.parent
        if source.parent.name == "bin" and (package / "codex-package.json").is_file():
            shutil.copytree(package, bundle, symlinks=True)
            if not (bundle / "codex").exists():
                (bundle / "codex").symlink_to("bin/codex")
            kind = "complete_reference_package"
        else:
            bundle.mkdir(mode=0o700, parents=True)
            shutil.copy2(source, bundle / "codex")
            kind = "legacy_fixed_path_cli"
        if code_mode_host is not None:
            helper = code_mode_host.resolve(strict=True)
            shutil.copy2(helper, bundle / "codex-code-mode-host")
            self.records[label + "_code_mode_host"] = dict(
                source=str(helper),
                installed=str(bundle / "codex-code-mode-host"),
                sha256=_sha256(helper),
                managed_session_execution_proven=False,
            )
        staged = bundle / "codex"
        if _sha256(staged) != digest:
            raise RuntimeError("staged CLI bytes differ")
        temporary = self.current.with_name("current.new")
        temporary.symlink_to(bundle)
        os.replace(temporary, self.current)
        self.cli = staged
        self.records[label + "_artifact"] = dict(
            source=str(source), installed=str(staged), sha256=digest, kind=kind
        )
        return staged

    def command(self, verb, label):
        argv = [str(self.cli), "app-server", "daemon", verb]
        result = subprocess.run(
            argv,
            env=self.env,
            cwd=self.root / "workspace",
            capture_output=True,
            text=True,
            timeout=25,
            start_new_session=True,
        )
        (self.root / (label + ".stdout")).write_text(result.stdout)
        (self.root / (label + ".stderr")).write_text(result.stderr)
        self.records[label] = dict(argv=argv, exit_code=result.returncode)
        if result.returncode:
            raise RuntimeError("managed " + verb + " refused: " + result.stderr[-1500:])
        value = json.loads(result.stdout)
        self.records[label]["result"] = value
        return value

    def start(self, label):
        value = self.command("start", label + "_start")
        self.pid = value.get("pid")
        if value.get("status") != "started" or type(self.pid) is not int:
            raise RuntimeError("new private managed daemon was not started")
        identity = self.identity(self.pid)
        expected = _sha256(self.cli)
        if identity is None or identity["sha256"] != expected:
            raise RuntimeError("managed process executable does not match staged CLI")
        self.records[label + "_process"] = identity
        return "unix://" + str(Path(value["socketPath"]).resolve(strict=True))

    @staticmethod
    def identity(pid):
        try:
            executable = Path("/proc", str(pid), "exe")
            return dict(
                pid=pid,
                exe=os.readlink(executable),
                sha256=_sha256(executable),
                start_ticks=Path("/proc", str(pid), "stat").read_text().split()[21],
            )
        except (FileNotFoundError, ProcessLookupError):
            return None

    def request(self, endpoint, method, params):
        """Retain exact private-fixture JSON-RPC errors, including rollback parsing."""
        from websockets.sync.client import unix_connect

        path = Path(endpoint.removeprefix("unix://"))
        info = path.stat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
            raise RuntimeError("private managed endpoint ownership differs")
        deadline = time.monotonic() + 8
        with unix_connect(
            str(path),
            open_timeout=8,
            close_timeout=1,
            compression=None,
            max_size=32 * 1024 * 1024,
        ) as ws:

            def exchange(identifier, name, body):
                ws.send(json.dumps(dict(id=identifier, method=name, params=body)))
                while True:
                    reply = json.loads(
                        ws.recv(timeout=max(0.01, deadline - time.monotonic()))
                    )
                    if reply.get("id") != identifier:
                        continue
                    self.records.setdefault("rpc", []).append(
                        dict(method=name, params=body, response=reply)
                    )
                    if "error" in reply:
                        raise RuntimeError(
                            "managed RPC refused "
                            + name
                            + ": "
                            + json.dumps(reply["error"])
                        )
                    return reply["result"]

            exchange(
                1,
                "initialize",
                dict(
                    clientInfo=dict(
                        name="owned_managed_qualification", version="0.0.0"
                    ),
                    capabilities=dict(experimentalApi=True),
                ),
            )
            ws.send(json.dumps(dict(method="initialized")))
            return exchange(2, method, params)

    def stop(self, label):
        value = self.command("stop", label + "_stop")
        until = time.monotonic() + 5
        while (
            self.pid
            and self.identity(self.pid) is not None
            and time.monotonic() < until
        ):
            time.sleep(0.05)
        after = self.identity(self.pid) if self.pid else None
        self.records[label + "_process_after"] = after
        if value.get("status") not in ("stopped", "notRunning") or after is not None:
            raise RuntimeError("owned managed daemon stop unverified")
        self.pid = None

    def notice_history(self, native, event, text, selected):
        turns = native["turns"]
        if selected:
            if len(turns) != 1:
                raise RuntimeError("expected exactly one synthetic notice container")
            turn = turns[0]
            if (
                not {"startedAt", "completedAt", "durationMs", "error"} <= set(turn)
                or any(
                    turn[key] is not None
                    for key in ("startedAt", "completedAt", "durationMs", "error")
                )
                or turn.get("status") != "completed"
                or len(turn.get("items", [])) != 1
                or turn["items"][0].get("type") != "agentMessage"
                or turn["items"][0].get("text") != text
            ):
                raise RuntimeError("unexpected native turn or notice items")
        elif turns:
            raise RuntimeError("peer acquired a native turn/container")
        path = Path(native["path"]).resolve(strict=True)
        if not path.is_relative_to((self.home / "sessions").resolve()):
            raise RuntimeError("notice rollout escaped private home")
        rows = []
        with path.open() as source:
            for line in source:
                rows.append(json.loads(line))
        messages = 0
        displays = 0
        for row in rows:
            payload = row.get("payload", {})
            if row["type"] == "session_meta":
                continue
            if (
                row["type"] == "event_msg"
                and payload.get("type") == "thread_goal_updated"
            ):
                continue
            if (
                row["type"] == "event_msg"
                and payload.get("type") == "agent_message"
                and selected
                and payload.get("message") == text
            ):
                displays += 1
                continue
            expected_context = (
                '<codex_internal_context source="external_supervision">\n'
                + text
                + "\n</codex_internal_context>"
            )
            if (
                row["type"] == "response_item"
                and selected
                and payload.get("type") == "message"
                and payload.get("id") == event
                and payload.get("role") == "user"
                and payload.get("content")
                == [dict(type="input_text", text=expected_context)]
            ):
                messages += 1
                continue
            raise RuntimeError(
                "unexpected rollout record; model-turn absence unverified: "
                + row["type"]
                + "/"
                + str(payload.get("type"))
            )
        if (messages, displays) != ((1, 1) if selected else (0, 0)):
            raise RuntimeError("notice context/display count differs")
        return dict(
            model_turn_starts=0,
            synthetic_notice_containers=len(turns),
            model_requests_or_completions=0,
            usage_events=0,
            rollout_sha256=_sha256(path),
            notice_marker_present=selected,
            raw_record_types=[row["type"] for row in rows],
        )

    def rollback(self, reference, verify):
        before = {
            str(p.relative_to(self.home)): _sha256(p)
            for p in (self.home / "sessions").rglob("*.jsonl")
        }
        self.records["rollback_rollout_hashes_before"] = before
        self.stage(reference, "rollback")
        try:
            endpoint = self.start("rollback")
            self.command("version", "rollback_version")
            verify(endpoint)
        finally:
            try:
                self.stop("rollback")
            finally:
                after = {
                    str(p.relative_to(self.home)): _sha256(p)
                    for p in (self.home / "sessions").rglob("*.jsonl")
                }
                self.records["rollback_rollout_hashes_after"] = after
                self.records["rollback_rollouts_unchanged"] = before == after
        if before != after:
            raise RuntimeError("rollback lifecycle changed private rollouts")


def execute(
    root,
    prefix,
    app_server=None,
    previous_prefix=None,
    wake_workflow=False,
    managed_cli=None,
    rollback_cli=None,
    code_mode_host=None,
):
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    home = root / "home"
    home.mkdir(mode=0o700)
    workspace = root / "workspace"
    workspace.mkdir(mode=0o700)
    wake_root = root / "wake"
    wake_root.mkdir(mode=0o700)
    codex = Path(
        subprocess.check_output(["which", "codex"], text=True).strip()
    ).resolve()
    python = prefix / "bin/python"
    cli = prefix / "bin/codex-wake"
    profiles = root / "profiles.json"
    write(profiles, dict(version=1, profiles={}, callers={}))
    toy = root / "toy.py"
    toy_pids = root / "toy-pids.jsonl"
    toy.write_text("""import json,sys,os
version=sys.argv[1]
with open(sys.argv[2],'a') as f:f.write(json.dumps(dict(pid=os.getpid(),version=version))+'\\n')
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r:continue
 method=r['method']
 if method=='initialize':v=dict(protocolVersion=r['params']['protocolVersion'],capabilities={'tools':{}},serverInfo=dict(name='owned-shared-refresh-toy',version=version))
 elif method=='tools/list':v={'tools':[dict(name=name,description=name+' '+version,inputSchema={'type':'object','properties':{},'additionalProperties':False},annotations={'readOnlyHint':True}) for name in (['version','extra_v2'] if version=='v2' else ['version'])]}
 elif method=='tools/call':v={'content':[{'type':'text','text':version}],'isError':False}
 else:v={}
 print(json.dumps(dict(jsonrpc='2.0',id=r['id'],result=v)),flush=True)
""")

    def config(version):
        active_prefix = (
            previous_prefix if version == "v1" and previous_prefix else prefix
        )
        (home / "config.toml").write_text(
            'model = "gpt-5.4"\nmodel_provider = "owned_no_provider"\napproval_policy = "never"\n'
            + '[model_providers.owned_no_provider]\nname = "Owned no-provider fixture"\nbase_url = "http://127.0.0.1:1/v1"\nwire_api = "responses"\nrequires_openai_auth = false\nsupports_websockets = false\nrequest_max_retries = 0\nstream_max_retries = 0\n'
            + "[projects."
            + json.dumps(str(workspace))
            + ']\ntrust_level = "trusted"\n'
            + "[mcp_servers.toy]\ncommand = "
            + json.dumps(str(python))
            + "\nargs = "
            + json.dumps([str(toy), version, str(toy_pids)])
            + "\n"
            + "[mcp_servers.wake_lifecycle]\ncommand = "
            + json.dumps(str(active_prefix / "bin/codex-wake-mcp"))
            + "\nargs = "
            + json.dumps(
                [
                    "--cli",
                    str(active_prefix / "bin/codex-wake"),
                    "--wake-root",
                    str(wake_root),
                    "--lifecycle-profiles",
                    str(profiles),
                    "--call-timeout",
                    "15",
                ]
            )
            + "\n"
        )

    config("v1")
    env = dict(os.environ, CODEX_HOME=str(home), XDG_STATE_HOME=str(root / "state"))
    for key in (
        "CODEX_THREAD_ID",
        "TMUX",
        "TMUX_PANE",
        "CODEX_WAKE_A2A_CAPABILITY",
        "CODEX_WAKE_A2A_BUS_ROOT",
        "CODEX_WAKE_SENDER_RECEIPT_AUTHORITY",
        "PYTHONPATH",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "CODEX_API_KEY",
        "AZURE_OPENAI_API_KEY",
    ):
        env.pop(key, None)
    receipt = dict(
        state="preparing",
        root=str(root),
        prefix=str(prefix),
        codex=str(codex),
        model_turn_limit=0,
        authority="Issues318/319 disposable two-thread scoped reload acceptance",
    )
    managed = None
    if managed_cli:
        if app_server or previous_prefix or wake_workflow or not rollback_cli:
            raise ValueError(
                "managed mode requires rollback-cli and excludes other runtime modes"
            )
        receipt["network_isolation"] = _private_network()
        env = {
            key: value
            for key, value in os.environ.items()
            if key in ("PATH", "LANG", "LC_ALL", "TERM", "TZ")
        }
        env.update(
            CODEX_HOME=str(home),
            HOME=str(root / "user-home"),
            XDG_STATE_HOME=str(root / "state"),
            XDG_CONFIG_HOME=str(root / "config"),
            XDG_CACHE_HOME=str(root / "cache"),
            XDG_DATA_HOME=str(root / "data"),
        )
        Path(env["HOME"]).mkdir(mode=0o700)
        managed = ManagedFixture(root, home, env, receipt)
    server = None
    watcher = None
    native_log = (root / "native.log").open("w")
    watch_log = (root / "watch.log").open("w")
    started = time.monotonic()

    def request(method, params):
        if time.monotonic() - started > 100:
            raise TimeoutError("owned probe attempt budget exhausted")
        return (
            managed.request(endpoint, method, params)
            if managed
            else native_request(endpoint, str(codex), method, params, 8)
        )

    def snapshot(thread):
        return dict(
            goal=request("thread/goal/get", {"threadId": thread})["goal"],
            native=request("thread/read", {"threadId": thread, "includeTurns": True})[
                "thread"
            ],
            catalog=request(
                "mcpServerStatus/list",
                {
                    "threadId": thread,
                    "serverName": "toy",
                    "detail": "toolsAndAuthOnly",
                    "runtimeOnly": True,
                },
            ),
            behavior=request(
                "mcpServer/tool/call",
                {
                    "threadId": thread,
                    "server": "toy",
                    "tool": "version",
                    "arguments": {},
                },
            ),
        )

    def emit():
        write(root / "receipt.json", receipt)

    try:
        if managed:
            codex = managed.stage(managed_cli, "candidate", code_mode_host)
            endpoint = managed.start("candidate")
            receipt.update(server_pid=managed.pid, endpoint=endpoint, codex=str(codex))
            managed.command("version", "candidate_version")
        else:
            server = subprocess.Popen(
                ([str(app_server)] if app_server else [str(codex), "app-server"])
                + ["--listen", "unix://" + str(root / "native.sock")],
                env=env,
                stdout=native_log,
                stderr=native_log,
                start_new_session=True,
            )
            until = time.monotonic() + 15
            while (
                not (root / "native.sock").exists()
                and server.poll() is None
                and time.monotonic() < until
            ):
                time.sleep(0.05)
            endpoint = "unix://" + str((root / "native.sock").resolve(strict=True))
            receipt.update(server_pid=server.pid, endpoint=endpoint)
        threads = [
            request("thread/start", {"cwd": str(workspace), "ephemeral": False})[
                "thread"
            ]["id"]
            for _ in range(2)
        ]
        receipt["threads"] = threads
        emit()
        for thread in threads:
            request(
                "thread/goal/set",
                dict(
                    threadId=thread,
                    objective="Owned zero-turn shared refresh acceptance",
                    status="paused",
                    tokenBudget=1000,
                    origin="automatic",
                ),
            )
        receipt["before"] = {thread: snapshot(thread) for thread in threads}
        if any(
            value["behavior"].get("content") != [{"type": "text", "text": "v1"}]
            for value in receipt["before"].values()
        ):
            raise RuntimeError("startup toy v1 proof failed")
        config("v2")
        receipt["capability"] = request(
            "thread/mcpServer/reload", dict(threadId=threads[0], dryRun=True)
        )
        if receipt["capability"] != {"threadId": threads[0], "queued": False}:
            raise RuntimeError("scoped read-only capability proof failed")
        receipt["after_inspection"] = {thread: snapshot(thread) for thread in threads}
        if receipt["after_inspection"] != receipt["before"]:
            raise RuntimeError("inspection changed a thread")
        if wake_workflow:
            from codex_wake.a2a_bus import BusStore
            from codex_wake.session_permissions import PermissionStore, Principal

            PermissionStore(wake_root).configure(
                {"version": 1}, Principal("operator", "operator"), expected_revision=0
            )
            bus, capability = BusStore.configure(root / "operator-bus")
            checkpoint = workspace / "checkpoint.json"
            write(
                checkpoint,
                dict(
                    source_thread_id=threads[0],
                    objective="Keep exact goal",
                    authority="User-approved scoped refresh proof",
                    next_packet="Inspect refreshed resource",
                    pending_obligations=[],
                ),
            )
            write(
                profiles,
                dict(
                    version=1,
                    callers={},
                    profiles={
                        "owned": dict(
                            refresh_mode="thread_mcp_idle",
                            scope_approval="Exact selected thread only",
                            cwd=str(workspace),
                            app_server=endpoint,
                            codex_path=str(codex),
                            timeout=4,
                            resources={
                                "toy": dict(
                                    kind="mcp",
                                    server="toy",
                                    tool="version",
                                    arguments={},
                                    read_only=True,
                                    expected_content=[dict(type="text", text="v2")],
                                ),
                                "wake": dict(
                                    kind="mcp_catalog",
                                    server="wake_lifecycle",
                                    version=subprocess.check_output(
                                        [str(cli), "--version"], text=True
                                    )
                                    .strip()
                                    .split()[-1],
                                    tools={"wake_permissions_show": []},
                                ),
                            },
                        )
                    },
                ),
            )
            watcher = subprocess.Popen(
                [
                    str(cli),
                    "--wake-root",
                    str(wake_root),
                    "sessions",
                    "refresh-watch",
                    "--interval",
                    "0.1",
                ],
                env=env,
                stdout=watch_log,
                stderr=watch_log,
                start_new_session=True,
            )
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                heartbeat = wake_root / "shared-refresh/controller.json"
                if heartbeat.exists() and json.loads(heartbeat.read_text()).get(
                    "active"
                ):
                    break
                time.sleep(0.05)
            expiry = datetime.fromtimestamp(time.time() + 45, timezone.utc).isoformat()
            argv = [
                str(cli),
                "--wake-root",
                str(wake_root),
                "sessions",
                "refresh",
                "--profiles",
                str(profiles),
                "--profile",
                "owned",
                "--thread-id",
                threads[0],
                "--caller-thread-id",
                threads[0],
                "--scope",
                "current_connection",
                "--bus-root",
                str(bus.root),
                "--operator-capability",
                str(capability),
                "--checkpoint",
                "checkpoint.json",
                "--checkpoint-sha256",
                hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                "--resource",
                "toy",
                "--resource",
                "wake",
                "--expires-at",
                expiry,
                "--intent",
                "owned-scoped-refresh",
                "--json",
            ]
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                process = subprocess.run(
                    argv, env=env, text=True, capture_output=True, timeout=15
                )
                value = json.loads(process.stdout)
                receipt["wake_refresh"] = value
                if process.returncode or value.get("state") in (
                    "completed",
                    "blocked",
                    "expired",
                ):
                    break
                time.sleep(0.1)
            if process.returncode or value.get("state") != "completed":
                raise RuntimeError("Wake workflow incomplete: " + str(value))
        else:
            receipt["admission"] = request(
                "thread/mcpServer/reload", dict(threadId=threads[0])
            )
            if receipt["admission"] != {"threadId": threads[0], "queued": True}:
                raise RuntimeError("scope admission mismatch")
        until = time.monotonic() + 15
        while time.monotonic() < until:
            selected = snapshot(threads[0])
            if selected["behavior"].get("content") == [{"type": "text", "text": "v2"}]:
                break
            time.sleep(0.05)
        receipt["after"] = {thread: snapshot(thread) for thread in threads}
        receipt["same_threads"] = all(
            receipt["after"][thread]["native"]["id"] == thread for thread in threads
        )
        receipt["goals_unchanged"] = all(
            receipt["before"][thread]["goal"] == receipt["after"][thread]["goal"]
            for thread in threads
        )
        receipt["model_turns"] = sum(
            len(value["native"]["turns"]) for value in receipt["after"].values()
        )
        receipt["selected_v2_peer_v1"] = receipt["after"][threads[0]]["behavior"].get(
            "content"
        ) == [{"type": "text", "text": "v2"}] and receipt["after"][threads[1]][
            "behavior"
        ].get("content") == [{"type": "text", "text": "v1"}]
        receipt["selected_new_catalog_peer_unchanged"] = (
            "extra_v2" in receipt["after"][threads[0]]["catalog"]["data"][0]["tools"]
            and "extra_v2"
            not in receipt["after"][threads[1]]["catalog"]["data"][0]["tools"]
        )
        receipt["toy_processes"] = [
            json.loads(line) for line in toy_pids.read_text().splitlines()
        ]
        receipt["exact_toy_startups"] = sorted(
            row["version"] for row in receipt["toy_processes"]
        ) == ["v1", "v1", "v2"]
        if previous_prefix:

            def wake_version(section, thread):
                return next(
                    row["serverInfo"]["version"]
                    for row in receipt[section][thread]["catalog"]["data"]
                    if row["name"] == "wake_lifecycle"
                )

            receipt["selected_wake_version"] = wake_version("after", threads[0])
            receipt["peer_wake_version"] = wake_version("after", threads[1])
            if receipt["selected_wake_version"] == receipt["peer_wake_version"]:
                raise RuntimeError(
                    "selected Wake process did not upgrade independently"
                )
            if receipt["peer_wake_version"] != wake_version("before", threads[1]):
                raise RuntimeError("peer Wake process changed")
        if not all(
            (
                receipt["exact_toy_startups"],
                receipt["same_threads"],
                receipt["goals_unchanged"],
                receipt["model_turns"] == 0,
                receipt["selected_v2_peer_v1"],
                receipt["selected_new_catalog_peer_unchanged"],
            )
        ):
            raise RuntimeError("continuity or v2 proof failed")
        if managed:
            event = (
                "managed_notice_" + hashlib.sha256(str(root).encode()).hexdigest()[:16]
            )
            text = (
                "Owned managed no-turn notice. [External supervision event "
                + event
                + "]"
            )
            appended = request(
                "thread/notice/append",
                dict(threadId=threads[0], eventId=event, text=text),
            )
            selected = request(
                "thread/notice/read", dict(threadId=threads[0], eventId=event)
            )
            peer = request(
                "thread/notice/read", dict(threadId=threads[1], eventId=event)
            )
            if (
                appended.get("recorded") is not True
                or selected.get("notice") != dict(eventId=event, text=text)
                or selected.get("modelContextAvailable") is not True
                or peer.get("notice") is not None
            ):
                raise RuntimeError(
                    "managed notice context or peer isolation unverified"
                )
            receipt["managed_notice"] = dict(
                event_id=event, append=appended, selected=selected, peer=peer
            )
            final = {
                thread: request(
                    "thread/read", dict(threadId=thread, includeTurns=True)
                )["thread"]
                for thread in threads
            }
            receipt["managed_notice_history"] = {
                thread: managed.notice_history(
                    native, event, text, thread == threads[0]
                )
                for thread, native in final.items()
            }
            for thread in threads:
                if (
                    request("thread/goal/get", dict(threadId=thread))["goal"]
                    != receipt["after"][thread]["goal"]
                ):
                    raise RuntimeError(
                        "notice changed goal identity, counters or deadlines"
                    )
            receipt["model_turns"] = sum(
                value["model_turn_starts"]
                for value in receipt["managed_notice_history"].values()
            )
        receipt["state"] = "passed"
    except Exception as exc:
        receipt.update(state="failed", error=type(exc).__name__ + ": " + str(exc))
    finally:
        if managed:
            try:
                managed.stop("candidate")
                if receipt["state"] == "passed":

                    def verify_rollback(rollback_endpoint):
                        observed = {}
                        receipt["rollback_threads"] = observed
                        for thread in receipt["threads"]:
                            native = managed.request(
                                rollback_endpoint,
                                "thread/read",
                                dict(threadId=thread, includeTurns=True),
                            )["thread"]
                            goal = managed.request(
                                rollback_endpoint,
                                "thread/goal/get",
                                dict(threadId=thread),
                            )["goal"]
                            expected = receipt["after"][thread]["goal"]
                            row = dict(
                                native=native,
                                goal=goal,
                                goal_comparison_keys=sorted(expected),
                            )
                            observed[thread] = row
                            if (
                                native["id"] != thread
                                or not set(expected) <= set(goal)
                                or any(
                                    goal[key] != value
                                    for key, value in expected.items()
                                )
                            ):
                                raise RuntimeError(
                                    "rollback conversation, goal identity, counters or deadlines differ"
                                )
                            row["history"] = managed.notice_history(
                                native,
                                receipt["managed_notice"]["event_id"],
                                receipt["managed_notice"]["selected"]["notice"]["text"],
                                thread == receipt["threads"][0],
                            )
                        receipt["rollback_conversations_readable"] = True

                    managed.rollback(rollback_cli, verify_rollback)
            except Exception as exc:
                receipt.update(
                    state="failed",
                    managed_cleanup_error=type(exc).__name__ + ": " + str(exc),
                )
        for process in (watcher, server):
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
        native_log.close()
        watch_log.close()
        remaining = []
        denied = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                if (
                    managed
                    and str(root).encode() not in (entry / "cmdline").read_bytes()
                ):
                    continue
                if entry.stat().st_uid == os.getuid() and (
                    "CODEX_HOME=" + str(home)
                ).encode() in (entry / "environ").read_bytes().split(b"\0"):
                    remaining.append(int(entry.name))
            except PermissionError:
                denied.append(int(entry.name))
            except (FileNotFoundError, ProcessLookupError):
                pass
        toy_survivors = []
        if toy_pids.exists():
            for line in toy_pids.read_text().splitlines():
                pid = json.loads(line)["pid"]
                try:
                    if str(toy).encode() in Path(
                        "/proc", str(pid), "cmdline"
                    ).read_bytes().split(b"\0"):
                        toy_survivors.append(pid)
                except (FileNotFoundError, ProcessLookupError):
                    pass
        receipt["cleanup"] = dict(
            toy_process_survivors=toy_survivors,
            server_exit=server.poll() if server else None,
            watcher_exit=watcher.poll() if watcher else None,
            private_home_processes=remaining,
            denied_environment_pids=denied,
        )
        if remaining or toy_survivors:
            receipt.update(state="failed", cleanup_error="owned processes remain")
        receipt["elapsed_seconds"] = time.monotonic() - started
        emit()
    print(
        json.dumps(
            {
                key: receipt.get(key)
                for key in (
                    "state",
                    "error",
                    "root",
                    "model_turns",
                    "cleanup",
                    "elapsed_seconds",
                )
            }
        )
    )
    return 0 if receipt["state"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--app-server", type=Path)
    parser.add_argument("--previous-prefix", type=Path)
    parser.add_argument("--wake-workflow", action="store_true")
    parser.add_argument("--managed-cli", type=Path)
    parser.add_argument("--rollback-cli", type=Path)
    parser.add_argument("--code-mode-host", type=Path)
    args = parser.parse_args()
    raise SystemExit(
        execute(
            args.root.resolve(),
            args.prefix.resolve(),
            args.app_server,
            args.previous_prefix,
            args.wake_workflow,
            args.managed_cli,
            args.rollback_cli,
            args.code_mode_host,
        )
    )
