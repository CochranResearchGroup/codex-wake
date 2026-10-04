import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from codex_wake.a2a_tmux_delivery import TmuxBinding, empty_composer
from codex_wake.process import boot_id_value, process_start_time_ticks


EMPTY = '› Ask Codex to do anything\n\n GPT-6 · /repo · session\n ← for agents · ? for shortcuts\n'


class TmuxDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.binding = TmuxBinding('fixture', 'recipient', str(self.root), '/tmp/tmux/socket',
            os.getpid(), process_start_time_ticks(os.getpid()), boot_id_value(), 'fixture-generation')
        self.claim = {'attempt_id': 'attempt_' + 'a' * 32}
        self.job = {'message_id': 'msg_' + 'b' * 32, 'expires_at': time.time() + 60}
        self.pane = {'pane_id': '%1'}

    def test_composer_refuses_drafts_modal_unknown_and_wrapped_input(self):
        self.assertTrue(empty_composer(EMPTY))
        for text in (EMPTY.replace('Ask Codex to do anything', 'my unfinished draft'),
                     EMPTY.replace('GPT-6', 'continuation of pasted draft\nGPT-6'),
                     'Approve this command?', '', 'shell $', EMPTY.replace('›', '>')):
            self.assertFalse(empty_composer(text))

    def test_busy_recipient_cannot_paste(self):
        with patch.object(TmuxBinding, 'locate', return_value=({'status': {'type': 'active'}}, self.pane)), \
             patch('codex_wake.a2a_tmux_delivery.SubprocessTmuxRunner') as runner:
            self.assertEqual(self.binding.probe()['reason'], 'busy')
            self.assertEqual(self.binding.deliver(self.claim, self.job, self.root)['status'], 'unsent')
            runner.return_value.paste_prompt.assert_not_called()

    def test_draft_appearing_after_probe_is_preserved(self):
        with patch.object(TmuxBinding, 'locate', return_value=({}, self.pane)), \
             patch.object(TmuxBinding, 'probe', return_value={'status': 'ready'}), \
             patch('codex_wake.a2a_tmux_delivery.SubprocessTmuxRunner') as runner:
            runner.return_value.capture_pane.return_value = EMPTY.replace('Ask Codex to do anything', 'human draft')
            self.assertEqual(self.binding.deliver(self.claim, self.job, self.root)['status'], 'unsent')
            runner.return_value.paste_prompt.assert_not_called()

    def test_visible_prompt_receipt_carries_pointer_only(self):
        with patch.object(TmuxBinding, 'locate', return_value=({}, self.pane)), \
             patch.object(TmuxBinding, 'probe', return_value={'status': 'ready'}), \
             patch('codex_wake.a2a_tmux_delivery.SubprocessTmuxRunner') as runner:
            runner.return_value.capture_pane.side_effect = [EMPTY, 'A2A_NOTIFICATION=' + self.job['message_id']]
            result = self.binding.deliver(self.claim, self.job, self.root)
            self.assertEqual(result['status'], 'submitted')
            self.assertEqual(result['receipt_id'], self.claim['attempt_id'])
            prompt = runner.return_value.paste_prompt.call_args.args[-1]
            self.assertIn(self.job['message_id'], prompt)
            self.assertNotIn('message body', prompt)

    def test_partial_paste_is_uncertain_and_expired_job_has_no_effect(self):
        with patch.object(TmuxBinding, 'locate', return_value=({}, self.pane)), \
             patch.object(TmuxBinding, 'probe', return_value={'status': 'ready'}), \
             patch('codex_wake.a2a_tmux_delivery.SubprocessTmuxRunner') as runner:
            runner.return_value.capture_pane.return_value = EMPTY
            runner.return_value.paste_prompt.side_effect = OSError('lost connection after paste')
            self.assertEqual(self.binding.deliver(self.claim, self.job, self.root)['status'], 'uncertain')
            runner.reset_mock()
            self.job['expires_at'] = time.time() - 1
            self.assertEqual(self.binding.deliver(self.claim, self.job, self.root)['status'], 'unsent')
            runner.return_value.paste_prompt.assert_not_called()

    def test_reused_process_generation_cannot_be_adopted(self):
        from dataclasses import replace
        binding = replace(self.binding, process_start_ticks=self.binding.process_start_ticks + 1)
        self.assertEqual(binding.deliver(self.claim, self.job, self.root)['status'], 'unsent')


if __name__ == '__main__':
    unittest.main()
