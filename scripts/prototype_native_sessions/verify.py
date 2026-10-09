"""Replay saved prototype evidence; does not perform live delivery."""
import json
from pathlib import Path

root = Path(__file__).parent
for topology, token in [('background', 'TOKEN_native_20261008'),
                        ('independent', 'INDEPENDENT_20261008')]:
    def read(actor):
        result = json.loads((root / f'{topology}-{actor}.json').read_text())
        assert not result.get('isError'), result
        return json.loads(result['content'][0]['text'])
    a, b = read('A'), read('B')
    def final(turn):
        return [i['text'] for i in turn['items']
                if i['type'] == 'agentMessage' and i.get('phase') == 'final_answer']
    sent = next(t for t in a['turns'] if token + '_A_SENT' in final(t))
    received = next(t for t in a['turns'] if token + '_RECEIVED' in final(t))
    replied = next(t for t in b['turns'] if token + '_B_SENT' in final(t))
    assert sent['status'] == received['status'] == replied['status'] == 'completed'
    assert sent['completedAt'] < received['startedAt']
    for actor, turn, destination in [('A', sent, b['thread']['id']),
                                     ('B', replied, a['thread']['id'])]:
        assert any(i['type'] == 'mcpToolCall' and
                   i['tool'] == 'send_message_to_thread' and
                   i['arguments']['threadId'] == destination and
                   i['status'] == 'completed' for i in turn['items'])
    if topology == 'independent':
        assert token + '_RECEIVED' in (root / 'independent-A-pane.txt').read_text()
        assert token + '_B_SENT' in (root / 'independent-B-pane.txt').read_text()
    print(f'{topology}: PASS; A ended before native reply began; both sends completed')
