"""Modern no-model notice history must remain replayable by the stock TUI."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

_SPEC = importlib.util.spec_from_file_location(
    "modern_display_qualification",
    Path(__file__).parents[1] / "scripts/scoped_refresh_native_qualification.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class ModernDisplayHistoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = object.__new__(_MODULE.ModernManagedFixture)
        self.fixture.root = Path(temporary.name)
        self.fixture.home = self.fixture.root / "home"
        self.fixture.endpoint = "unix://owned"
        self.path = self.fixture.home / "sessions/owned.jsonl"
        self.path.parent.mkdir(parents=True)
        self.native = dict(
            id="thread", historyMode="paginated", turns=[], path=str(self.path)
        )
        self.turn = dict(
            id="event",
            rootTurnId="event",
            status="completed",
            items=[],
            itemsView="notLoaded",
            error=None,
            startedAt=None,
            completedAt=None,
            durationMs=None,
        )
        self.turns = dict(data=[self.turn], nextCursor=None)
        self.items = dict(
            data=[
                dict(
                    turnId="event",
                    startedAtMs=None,
                    completedAtMs=123,
                    item=dict(type="agentMessage", id="event", text="notice"),
                )
            ],
            nextCursor=None,
        )
        self.rows = [
            dict(type="session_meta", payload=dict(id="thread")),
            dict(
                type="response_item",
                payload=dict(
                    type="message",
                    id="event",
                    role="user",
                    content=[
                        dict(
                            type="input_text",
                            text='<codex_internal_context source="external_supervision">\nnotice\n</codex_internal_context>',
                        )
                    ],
                ),
            ),
            dict(
                type="event_msg",
                payload=dict(
                    type="item_completed",
                    thread_id="thread",
                    turn_id="event",
                    item=dict(
                        type="AgentMessage",
                        id="event",
                        content=[dict(type="Text", text="notice")],
                    ),
                    completed_at_ms=123,
                ),
            ),
            dict(
                type="event_msg",
                payload=dict(
                    type="task_complete",
                    root_turn_id="event",
                    turn_id="event",
                    last_agent_message=None,
                ),
            ),
        ]
        self.fixture.request = self.request

    def request(self, endpoint, method, params):
        self.assertEqual(endpoint, "unix://owned")
        self.assertEqual(params["threadId"], "thread")
        if method == "thread/turns/list":
            self.assertEqual(params["itemsView"], "notLoaded")
            return self.turns
        self.assertEqual(method, "thread/items/list")
        return self.items

    def read(self):
        self.path.write_text("".join(json.dumps(row) + "\n" for row in self.rows))
        return self.fixture.notice_history(self.native, "event", "notice", True)

    def test_completed_display_turn_is_not_executed_model_work(self):
        self.native["turns"] = [copy.deepcopy(self.turn)]
        result = self.read()
        self.assertEqual(result["model_turn_starts"], 0)
        self.assertEqual(result["completed_display_containers"], 1)
        self.assertEqual(result["canonical_paginated_notice_items"], 1)

    def test_rejects_orphan_item_and_foreign_public_turn(self):
        self.turns["data"] = []
        with self.assertRaises(RuntimeError):
            self.read()
        self.turns["data"] = [dict(self.turn, id="foreign")]
        with self.assertRaises(RuntimeError):
            self.read()

    def test_rejects_model_lifecycle_usage_and_unowned_completion(self):
        original = copy.deepcopy(self.rows)
        for payload in [
            dict(type="task_started", turn_id="event"),
            dict(type="token_count"),
            dict(
                type="task_complete",
                root_turn_id="foreign",
                turn_id="foreign",
                last_agent_message=None,
            ),
            dict(self.rows[-1]["payload"], started_at=123),
            dict(self.rows[-1]["payload"], last_agent_message="generated"),
        ]:
            with self.subTest(payload=payload):
                self.rows = copy.deepcopy(original) + [
                    dict(type="event_msg", payload=payload)
                ]
                with self.assertRaises(RuntimeError):
                    self.read()

    def test_rejects_missing_completion_and_incomplete_pages(self):
        self.rows.pop()
        with self.assertRaises(RuntimeError):
            self.read()
        self.turns["nextCursor"] = "more"
        with self.assertRaises(RuntimeError):
            self.read()

    def test_peer_baseline_have_no_items_or_turns(self):
        self.turns["data"] = []
        self.items["data"] = []
        self.rows = self.rows[:1]
        self.path.write_text(json.dumps(self.rows[0]) + "\n")
        result = self.fixture.notice_history(self.native, "", "", False)
        self.assertEqual(result["completed_display_containers"], 0)
