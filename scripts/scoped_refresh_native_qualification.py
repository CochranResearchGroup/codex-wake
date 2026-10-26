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
import struct
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


def expected_toy_startup_versions(modern_managed_update):
    # Modern mode also loads the pre-update baseline as a resident thread.
    return ["v1"] * (3 if modern_managed_update else 2) + ["v2"]


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

    def command(self, verb, label, *arguments):
        argv = [str(self.cli), "app-server", "daemon", verb, *arguments]
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
            if (
                isinstance(self, ModernManagedFixture)
                and row["type"] == "event_msg"
                and payload.get("type") == "thread_settings_applied"
                and set(payload) == {"type", "thread_id", "thread_settings"}
                and payload["thread_id"] == native["id"]
                and isinstance(payload["thread_settings"], dict)
                and payload["thread_settings"].get("cwd")
                == str(self.root / "workspace")
                and payload["thread_settings"].get("model_provider_id")
                == "owned_no_provider"
            ):
                # Upstream settings checkpoints contain configuration, not turns.
                # Unknown events and all model activity remain rejected below.
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


class ModernManagedFixture(ManagedFixture):
    """Use the real complete-package updater; never select a package manually."""

    def __init__(self, root, home, env, receipt):
        super().__init__(root, home, env, receipt)
        self.current = home / "packages/app-server-daemon/current"
        self.reference_cli = None
        self.candidate_attempted = False
        self.effect_unknown = False

    @staticmethod
    def package_files(package):
        files = {}
        for path in package.rglob("*"):
            relative = path.relative_to(package)
            if (
                relative == Path("codex")
                and path.is_symlink()
                and os.readlink(path) == "bin/codex"
            ):
                continue  # The upstream Unix installer adds this compatibility alias.
            if path.is_symlink():
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(package.resolve()) or resolved.is_dir():
                    raise RuntimeError(
                        "modern package contains an escaping or directory symlink"
                    )
            if path.is_file():
                files[str(relative)] = dict(
                    sha256=_sha256(path), mode=stat.S_IMODE(path.stat().st_mode)
                )
        return files

    def notice_history(self, native, event, text, selected):
        if native.get("historyMode") != "paginated":
            raise RuntimeError("modern notice history must remain paginated")
        turn_page = self.request(
            self.endpoint,
            "thread/turns/list",
            dict(
                threadId=native["id"],
                limit=100,
                sortDirection="asc",
                itemsView="notLoaded",
            ),
        )
        if turn_page.get("nextCursor") is not None:
            raise RuntimeError("unexpected additional modern display-turn page")
        expected_turn_count = 1 if selected else 0
        if len(native["turns"]) > expected_turn_count:
            raise RuntimeError("unexpected native display-turn containers")
        if len(turn_page["data"]) != expected_turn_count:
            raise RuntimeError("modern display-turn count differs")
        for turn in turn_page["data"] + native["turns"]:
            if not (
                selected
                and turn.get("id") == event
                and turn.get("rootTurnId") == event
                and turn.get("status") == "completed"
                and all(
                    key in turn and turn[key] is None
                    for key in ("error", "startedAt", "completedAt", "durationMs")
                )
                and all(
                    item.get("type") == "agentMessage"
                    and item.get("id") == event
                    and item.get("text") == text
                    for item in turn.get("items", [])
                )
            ):
                raise RuntimeError(
                    "modern display turn identity or lifecycle fields differ"
                )
        if any(turn.get("items") for turn in turn_page["data"]):
            raise RuntimeError(
                "notLoaded display-turn page unexpectedly contains items"
            )
        page = self.request(
            self.endpoint,
            "thread/items/list",
            dict(threadId=native["id"], limit=100, sortDirection="asc"),
        )
        entries = page["data"]
        if page.get("nextCursor") is not None:
            raise RuntimeError("unexpected additional modern notice history page")
        if selected:
            if len(entries) != 1:
                raise RuntimeError("expected one canonical paginated notice item")
            entry = entries[0]
            item = entry["item"]
            if (
                entry.get("turnId") != event
                or entry.get("startedAtMs") is not None
                or not isinstance(entry.get("completedAtMs"), int)
                or item.get("type") != "agentMessage"
                or item.get("id") != event
                or item.get("text") != text
            ):
                raise RuntimeError(
                    "canonical paginated notice identity or content differs"
                )
        elif entries:
            raise RuntimeError("peer or baseline acquired a paginated item")
        path = Path(native["path"]).resolve(strict=True)
        if not path.is_relative_to((self.home / "sessions").resolve()):
            raise RuntimeError("modern notice rollout escaped private home")
        raw = path.read_bytes()
        rows = [json.loads(line) for line in raw.splitlines()]
        contexts = displays = completions = 0
        expected_context = (
            '<codex_internal_context source="external_supervision">\n'
            + text
            + "\n</codex_internal_context>"
        )
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
                and payload.get("type") == "thread_settings_applied"
            ):
                # Reuse the strict owner/workspace/provider append validator.
                self.preserve_prefix(b"", json.dumps(row).encode(), native["id"])
                continue
            if (
                selected
                and row["type"] == "response_item"
                and payload.get("type") == "message"
                and payload.get("id") == event
                and payload.get("role") == "user"
                and payload.get("content")
                == [dict(type="input_text", text=expected_context)]
            ):
                contexts += 1
                continue
            if (
                selected
                and row["type"] == "event_msg"
                and payload.get("type") == "item_completed"
                and payload.get("thread_id") == native["id"]
                and payload.get("turn_id") == event
                and payload.get("item")
                == dict(
                    type="AgentMessage",
                    id=event,
                    content=[dict(type="Text", text=text)],
                )
                and isinstance(payload.get("completed_at_ms"), int)
                and payload["completed_at_ms"] == entries[0]["completedAtMs"]
            ):
                displays += 1
                continue
            if (
                selected
                and row["type"] == "event_msg"
                and payload
                == dict(
                    type="task_complete",
                    root_turn_id=event,
                    turn_id=event,
                    last_agent_message=None,
                )
            ):
                completions += 1
                continue
            raise RuntimeError("unexpected modern raw history event or model activity")
        if (contexts, displays, completions) != ((1, 1, 1) if selected else (0, 0, 0)):
            raise RuntimeError("modern notice context/display count differs")
        return dict(
            model_turn_starts=0,
            synthetic_notice_containers=0,
            canonical_paginated_notice_items=len(entries),
            completed_display_containers=len(turn_page["data"]),
            paginated_turns=turn_page,
            paginated_items=page,
            model_requests_or_completions=0,
            usage_events=0,
            rollout_sha256=_sha256(path),
            notice_marker_present=selected,
            raw_record_types=[row["type"] for row in rows],
            raw_rollout_text=raw.decode("utf-8"),
        )

    def preserve_prefix(self, before, after, thread):
        if not after.startswith(before):
            raise RuntimeError("modern rollout was rewritten or truncated")
        appended = after[len(before) :]
        for line in appended.splitlines():
            row = json.loads(line)
            payload = row.get("payload", {})
            if not (
                row.get("type") == "event_msg"
                and payload.get("type") == "thread_settings_applied"
                and set(payload) == {"type", "thread_id", "thread_settings"}
                and payload["thread_id"] == thread
                and isinstance(payload["thread_settings"], dict)
                and payload["thread_settings"].get("cwd")
                == str(self.root / "workspace")
                and payload["thread_settings"].get("model_provider_id")
                == "owned_no_provider"
            ):
                raise RuntimeError(
                    "modern rollout appended a non-settings or foreign event"
                )
        return dict(
            original_bytes_preserved=True,
            appended_settings_events=len(appended.splitlines()),
        )

    def copy_package(self, source, label):
        source = source.resolve(strict=True)
        package = source.parent.parent
        if (
            source.parent.name != "bin"
            or not (package / "codex-package.json").is_file()
        ):
            raise RuntimeError("modern managed mode requires a complete packaged CLI")
        metadata = json.loads((package / "codex-package.json").read_text())
        if metadata.get("entrypoint") != "bin/codex":
            raise RuntimeError(
                "modern managed mode requires the codex package entrypoint"
            )
        before = self.package_files(package)
        required = {
            "codex-package.json",
            "bin/codex",
            "bin/codex-code-mode-host",
            "codex-path/rg",
            "codex-resources/bwrap",
        }
        if not required <= before.keys():
            raise RuntimeError("modern managed input package is incomplete")
        bundle = self.root / "caller-packages" / (label + "-" + _sha256(source)[:16])
        bundle.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copytree(package, bundle, symlinks=True)
        if (
            self.package_files(bundle) != before
            or self.package_files(package) != before
        ):
            raise RuntimeError("modern caller package changed while copying")
        self.records[label + "_artifact"] = dict(
            source=str(source),
            installed=str(bundle / "bin/codex"),
            sha256=_sha256(source),
            kind="complete_modern_caller_package",
            metadata=metadata,
            files=before,
        )
        return bundle / "bin/codex"

    def updaters(self):
        identities = []
        marker = ("CODEX_HOME=" + str(self.home)).encode()
        for process in Path("/proc").iterdir():
            if not process.name.isdigit():
                continue
            try:
                command = (process / "cmdline").read_bytes().split(b"\0")
                if (
                    b"pid-update-loop" not in command
                    or str(self.root).encode() not in command[0]
                ):
                    continue
                if marker not in (process / "environ").read_bytes().split(b"\0"):
                    continue
                identity = self.identity(int(process.name))
                if identity is not None:
                    identities.append(identity)
            except (OSError, PermissionError):
                continue
        return identities

    def running(self, label):
        value = self.command("version", label + "_version")
        if value.get("status") != "running":
            raise RuntimeError("modern managed daemon is not running")
        advertised = Path(value["socketPath"])
        expected_socket = self.home / "app-server-control/app-server-control.sock"
        if advertised != expected_socket:
            raise RuntimeError(
                "modern managed socket rendezvous differs from private home"
            )
        # Modern Codex exposes an owned rendezvous symlink to its protected socket.
        # The target may live in the per-user shared socket directory; bind the
        # actual peer to the private home and exact invoking executable below.
        endpoint_path = advertised.resolve(strict=True)
        socket_info = endpoint_path.stat()
        if not stat.S_ISSOCK(socket_info.st_mode) or socket_info.st_uid != os.geteuid():
            raise RuntimeError("modern managed socket ownership differs")
        self.records[label + "_socket"] = dict(
            advertised=str(advertised), resolved=str(endpoint_path)
        )
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(5)
            connection.connect(str(endpoint_path))
            pid, uid, _ = struct.unpack(
                "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
            )
        if uid != os.geteuid():
            raise RuntimeError("modern daemon peer owner differs")
        marker = ("CODEX_HOME=" + str(self.home)).encode()
        if marker not in Path("/proc", str(pid), "environ").read_bytes().split(b"\0"):
            raise RuntimeError("modern daemon peer does not own the private home")
        identity = self.identity(pid)
        expected = _sha256(self.cli)
        if identity is None or identity["sha256"] != expected:
            raise RuntimeError(
                "modern daemon executable differs from the invoking package"
            )
        selected = Path(value["managedCodexPath"]).resolve(strict=True)
        if not selected.is_relative_to(
            (self.home / "packages/app-server-daemon/releases").resolve()
        ):
            raise RuntimeError(
                "modern daemon was not selected through the dedicated package root"
            )
        if self.package_files(selected.parent.parent) != self.package_files(
            self.cli.parent.parent
        ):
            raise RuntimeError("selected modern package bytes or file modes differ")
        self.pid = pid
        self.records[label + "_process"] = identity
        self.records[label + "_selected_package"] = str(selected.parent.parent)
        self.endpoint = "unix://" + str(endpoint_path)
        return self.endpoint

    def select_from_cli(self, label):
        old = self.identity(self.pid) if self.pid else None
        old_updaters = self.updaters()
        self.records[label + "_updaters_before"] = old_updaters
        try:
            result = self.command("update", label + "_update", "--from-cli", "--yes")
        except subprocess.TimeoutExpired:
            self.effect_unknown = True
            self.records[label + "_effect"] = "unknown_after_cli_timeout"
            raise
        if result.get("status") != "updated":
            raise RuntimeError("modern --from-cli installation did not report updated")
        endpoint = self.running(label)
        if old is not None:
            until = time.monotonic() + 5
            while time.monotonic() < until:
                observed = self.identity(old["pid"])
                if observed is None or observed["start_ticks"] != old["start_ticks"]:
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError("old private managed daemon survived replacement")
        remaining_updaters = self.updaters()
        marker = self.current.parent / "auto-update-version"
        self.records[label + "_pin"] = dict(
            latest_marker_present=marker.exists(), updaters_after=remaining_updaters
        )
        if marker.exists() or remaining_updaters:
            raise RuntimeError("the built-in explicit package pin is unverified")
        return endpoint

    def seed(self, reference):
        self.reference_cli = self.copy_package(reference, "reference")
        self.cli = self.reference_cli
        super().start("reference_seed")
        return self.select_from_cli("reference_pin")

    def install_candidate(self, candidate):
        self.cli = self.copy_package(candidate, "candidate")
        self.candidate_attempted = True
        return self.select_from_cli("candidate")

    def rollback(self, reference, verify):
        del (
            reference
        )  # Reuse the initial frozen reference package, not a moving host link.
        before = {
            str(path.relative_to(self.home)): _sha256(path)
            for path in (self.home / "sessions").rglob("*.jsonl")
        }
        raw_before = {
            str(path.relative_to(self.home)): path.read_bytes()
            for path in (self.home / "sessions").rglob("*.jsonl")
        }
        self.records["rollback_rollout_hashes_before"] = before
        self.cli = self.reference_cli
        try:
            endpoint = self.select_from_cli("rollback")
            verify(endpoint)
        finally:
            try:
                self.stop("rollback")
            finally:
                after = {
                    str(path.relative_to(self.home)): _sha256(path)
                    for path in (self.home / "sessions").rglob("*.jsonl")
                }
                self.records["rollback_rollout_hashes_after"] = after
                self.records["rollback_rollouts_unchanged"] = before == after
        if set(before) != set(after):
            raise RuntimeError("modern rollback changed the rollout file set")
        self.records["rollback_rollout_prefixes"] = {
            name: self.preserve_prefix(
                raw,
                (self.home / name).read_bytes(),
                json.loads(raw.splitlines()[0])["payload"]["id"],
            )
            for name, raw in raw_before.items()
        }

    def cleanup_failed_updaters(self):
        """Failure cleanup is not evidence that the real installer pinned correctly."""
        identities = self.updaters()
        self.records["failed_fixture_updater_cleanup"] = identities
        for original in identities:
            observed = self.identity(original["pid"])
            if observed is None or observed["start_ticks"] != original["start_ticks"]:
                continue
            os.kill(original["pid"], signal.SIGTERM)
            until = time.monotonic() + 5
            while time.monotonic() < until:
                observed = self.identity(original["pid"])
                if (
                    observed is None
                    or observed["start_ticks"] != original["start_ticks"]
                ):
                    break
                time.sleep(0.05)
            else:
                observed = self.identity(original["pid"])
                if (
                    observed is not None
                    and observed["start_ticks"] == original["start_ticks"]
                ):
                    os.kill(original["pid"], signal.SIGKILL)


def execute(
    root,
    prefix,
    app_server=None,
    previous_prefix=None,
    wake_workflow=False,
    managed_cli=None,
    rollback_cli=None,
    code_mode_host=None,
    modern_managed_update=False,
):
    if modern_managed_update and (
        not managed_cli
        or not rollback_cli
        or app_server
        or previous_prefix
        or wake_workflow
        or code_mode_host
    ):
        raise ValueError(
            "modern managed update requires complete managed-cli/rollback-cli packages only"
        )
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

    def config(version, include_mcp=True):
        active_prefix = (
            previous_prefix if version == "v1" and previous_prefix else prefix
        )
        base = (
            'model = "gpt-5.4"\nmodel_provider = "owned_no_provider"\napproval_policy = "never"\n'
            + '[model_providers.owned_no_provider]\nname = "Owned no-provider fixture"\nbase_url = "http://127.0.0.1:1/v1"\nwire_api = "responses"\nrequires_openai_auth = false\nsupports_websockets = false\nrequest_max_retries = 0\nstream_max_retries = 0\n'
            + "[projects."
            + json.dumps(str(workspace))
            + ']\ntrust_level = "trusted"\n'
        )
        mcp = (
            "[mcp_servers.toy]\ncommand = "
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
        (home / "config.toml").write_text(base + (mcp if include_mcp else ""))

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
        modern_managed_update=modern_managed_update,
        nonzero_accounting_proven=False,
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
        fixture = ModernManagedFixture if modern_managed_update else ManagedFixture
        managed = fixture(root, home, env, receipt)
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

    def baseline_snapshot(active_endpoint):
        thread = receipt["baseline_thread_id"]
        native = managed.request(
            active_endpoint, "thread/read", dict(threadId=thread, includeTurns=True)
        )["thread"]
        goal = managed.request(
            active_endpoint, "thread/goal/get", dict(threadId=thread)
        )["goal"]
        return dict(
            native=native,
            goal=goal,
            history=managed.notice_history(native, "", "", False),
        )

    def verify_baseline(active_endpoint, label):
        expected = receipt["baseline_reference"]
        observed = baseline_snapshot(active_endpoint)
        receipt[label] = observed
        if (
            observed["native"]["id"] != receipt["baseline_thread_id"]
            or observed["goal"] != expected["goal"]
        ):
            raise RuntimeError("pre-update stock conversation, goal or history changed")
        receipt[label + "_prefix"] = managed.preserve_prefix(
            expected["history"]["raw_rollout_text"].encode("utf-8"),
            observed["history"]["raw_rollout_text"].encode("utf-8"),
            receipt["baseline_thread_id"],
        )

    try:
        if modern_managed_update:
            config("v1", include_mcp=False)
            endpoint = managed.seed(rollback_cli)
            receipt["baseline_thread_id"] = request(
                "thread/start", dict(cwd=str(workspace), ephemeral=False)
            )["thread"]["id"]
            request(
                "thread/goal/set",
                dict(
                    threadId=receipt["baseline_thread_id"],
                    objective="Preserve this stock-created paused goal through package replacement",
                    status="paused",
                    tokenBudget=1000,
                    origin="automatic",
                ),
            )
            native = request(
                "thread/read",
                dict(threadId=receipt["baseline_thread_id"], includeTurns=True),
            )["thread"]
            until = time.monotonic() + 3
            while time.monotonic() < until:
                rows = [
                    json.loads(line)
                    for line in Path(native["path"]).read_text().splitlines()
                ]
                if any(
                    row["type"] == "event_msg"
                    and row.get("payload", {}).get("type") == "thread_goal_updated"
                    for row in rows
                ):
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError("stock goal update did not reach its actual rollout")
            receipt["baseline_reference"] = baseline_snapshot(endpoint)
            emit()
            config("v1")
            endpoint = managed.install_candidate(managed_cli)
            codex = managed.cli
            receipt.update(server_pid=managed.pid, endpoint=endpoint, codex=str(codex))
            verify_baseline(endpoint, "baseline_under_candidate")
            receipt["stock_to_candidate_preserved"] = True
            emit()
        elif managed:
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
        receipt["expected_toy_startup_versions"] = expected_toy_startup_versions(
            modern_managed_update
        )
        receipt["exact_toy_startups"] = (
            sorted(row["version"] for row in receipt["toy_processes"])
            == receipt["expected_toy_startup_versions"]
        )
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
                if modern_managed_update:
                    should_rollback = (
                        managed.candidate_attempted and not managed.effect_unknown
                    )
                else:
                    managed.stop("candidate")
                    should_rollback = receipt["state"] == "passed"
                if should_rollback:

                    def verify_rollback(rollback_endpoint):
                        if modern_managed_update:
                            verify_baseline(
                                rollback_endpoint, "baseline_after_rollback"
                            )
                        observed = {}
                        receipt["rollback_threads"] = observed
                        for thread in receipt.get("threads", []):
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
                            snapshots = receipt.get("after", receipt.get("before", {}))
                            if thread not in snapshots:
                                raise RuntimeError(
                                    "rollback has no qualified goal snapshot"
                                )
                            expected = snapshots[thread]["goal"]
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
                            notice = receipt.get("managed_notice")
                            row["history"] = managed.notice_history(
                                native,
                                notice["event_id"] if notice else "",
                                notice["selected"]["notice"]["text"] if notice else "",
                                bool(notice) and thread == receipt["threads"][0],
                            )
                        receipt["rollback_conversations_readable"] = True

                    managed.rollback(rollback_cli, verify_rollback)
                    if modern_managed_update:
                        receipt["modern_package_roundtrip_preserved"] = True
                elif modern_managed_update and managed.cli is not None:
                    if managed.effect_unknown:
                        receipt["modern_rollback_held"] = (
                            "unknown installation outcome; readback required"
                        )
                    managed.stop("modern_cleanup")
            except Exception as exc:
                receipt.update(
                    state="failed",
                    managed_cleanup_error=type(exc).__name__ + ": " + str(exc),
                )
            finally:
                if modern_managed_update and receipt["state"] != "passed":
                    managed.cleanup_failed_updaters()
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
    parser.add_argument("--modern-managed-update", action="store_true")
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
            args.modern_managed_update,
        )
    )
