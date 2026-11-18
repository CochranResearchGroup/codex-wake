"""Qualified input admission at the SSH frame boundary; private pipes only."""
import os
import unittest
from unittest.mock import patch

from codex_wake import measurements
from codex_wake.host_commands import bounded_stdin
from codex_wake.managed_inventory import InventoryError
from test_measurements import observation


class HostInputTests(unittest.TestCase):
    def test_qualified_frame_is_read_without_a_guest_clock(self):
        reader, writer = os.pipe()
        os.write(writer, b'{"operation":"hosts.list"}')
        os.close(writer)
        with os.fdopen(reader, 'r') as stream, patch('sys.stdin', stream), patch(
                'codex_wake.measurements.snapshot', return_value=observation(1000)), patch(
                'time.monotonic', side_effect=AssertionError('guest clock')):
            self.assertEqual(bounded_stdin(), {'operation': 'hosts.list'})

    def test_frame_cannot_be_accepted_after_its_original_deadline_or_clock_loss(self):
        for clock_lost in (False, True):
            with self.subTest(clock_lost=clock_lost):
                reader, writer = os.pipe()
                os.write(writer, b'{"operation":"hosts.list"}')
                os.close(writer)
                finished = False
                read = os.read
                def observe():
                    if finished and clock_lost:
                        raise measurements.TimeUnavailable('lost after EOF')
                    return observation(7000 if finished else 1000)
                def receive(fd, count):
                    nonlocal finished
                    chunk = read(fd, count)
                    if not chunk:
                        finished = True
                    return chunk
                with os.fdopen(reader, 'r') as stream, patch('sys.stdin', stream), patch(
                        'codex_wake.measurements.snapshot', side_effect=observe), patch('os.read', side_effect=receive):
                    with self.assertRaises(measurements.TimeUnavailable if clock_lost else InventoryError):
                        bounded_stdin()

    def test_unqualified_clock_refuses_an_already_available_frame(self):
        reader, writer = os.pipe()
        os.write(writer, b'{"operation":"hosts.list"}')
        os.close(writer)
        with os.fdopen(reader, 'r') as stream, patch('sys.stdin', stream), patch(
                'codex_wake.measurements.snapshot', side_effect=measurements.TimeUnavailable('unavailable')):
            with self.assertRaises(measurements.TimeUnavailable):
                bounded_stdin()

