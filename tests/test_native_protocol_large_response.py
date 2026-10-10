"""Native reconciliation must tolerate long-thread responses with a finite cap."""
import json
from pathlib import Path
import tempfile
import threading
import unittest

from websockets.sync.server import unix_serve
from codex_wake.native_delivery import native_evidence


class NativeLargeResponseTests(unittest.TestCase):
    def test_reconciliation_reads_user_message_beyond_default_websocket_cap(self):
        prompt = 'wake regression marker'
        thread_id = '01a10922-e791-7dd0-8bb2-ae9f110a688b'
        def handler(ws):
            for raw in ws:
                request = json.loads(raw)
                if 'id' not in request:
                    continue
                method = request['method']
                if method == 'initialize':
                    result = {}
                elif method == 'thread/queue/list':
                    result = {'data': [], 'nextCursor': None}
                else:
                    result = {'thread': {'id': thread_id, 'turns': [
                        {'id': 'turn', 'status': 'completed', 'items': [
                            {'id': 'large-context', 'type': 'assistantMessage', 'text': 'x' * (2 * 1024 * 1024)},
                            {'id': 'message', 'clientId': 'submission', 'type': 'userMessage',
                             'content': [{'type': 'text', 'text': prompt}]},
                        ]},
                    ]}}
                ws.send(json.dumps({'id': request['id'], 'result': result}))
        with tempfile.TemporaryDirectory() as directory:
            endpoint = Path(directory) / 'server.sock'
            with unix_serve(handler, str(endpoint)) as server:
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    evidence, reason = native_evidence({'endpoint': 'unix://' + str(endpoint),
                        'codex_cmd': 'unused', 'thread_id': thread_id}, prompt)
                    self.assertEqual(evidence['client_message_id'], 'submission')
                    self.assertEqual(evidence['source'], 'native_turn')
                finally:
                    server.shutdown()
                    worker.join(timeout=2)
