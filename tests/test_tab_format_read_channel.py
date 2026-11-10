"""Native readonly formatting adapter framing, custody, bounds and owner cleanup."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import unittest
from unittest.mock import patch

import test_tab_formatting as fixture
from codex_wake.managed_inventory import InventoryError
from codex_wake.tab_format_read_channel import FormattingReadChannel
from codex_wake.tab_observer import TabObserver


@unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
class FormattingReadChannelTests(unittest.TestCase):
    setUp=fixture.FormattingTests.setUp
    tmux=fixture.FormattingTests.tmux
    call=fixture.FormattingTests.call

    def retained_owner(self):
        self.tabs.workspaces['work'].update(socket_path=self.socket,session_id='$0')
        owner=TabObserver(self.root,owner=self.tabs,settings=dict(health=False,errors=False))
        self.addCleanup(owner.close)
        return owner

    def test_native_adapter_preserves_hostile_payloads_and_only_forks_for_writes(self):
        stamp=int(time.time())
        literal='first\r\nline\nUnicodeé中文😀; quote" apostrophe\' slash\\ dollar$HOME\n'
        literal+='\n'.join(f'%begin {stamp} {i} 1\n%end {stamp} {i} 1' for i in range(260,300))
        self.tmux('set-option','-w','-t','@0','window-status-format',literal)
        expected=self.transport.formatting('read',dict(window='@0'),time.monotonic()+2)
        before=self.tmux('list-panes','-a','-F','#{session_id} #{window_id} #{pane_id} #{pane_pid} #{window_active} #{window_layout}')
        observer=self.retained_owner()
        self.assertEqual(observer.status()['formatting_reads'][0]['state'],'idle')
        actual=self.transport.formatting('read',dict(window='@0'),time.monotonic()+2)
        self.assertEqual(actual,expected)
        owned=observer.status()['formatting_reads'][0]['owned_pid']
        clients=self.tmux('list-clients','-F','#{client_pid} #{client_flags}')
        self.assertIn(str(owned),clients)
        self.assertIn('read-only',clients);self.assertIn('ignore-size',clients);self.assertIn('no-output',clients)
        self.assertEqual(self.tmux('list-panes','-a','-F','#{session_id} #{window_id} #{pane_id} #{pane_pid} #{window_active} #{window_layout}'),before)
        calls=[];run=subprocess.run
        def counted(*args,**kwargs):calls.append(args[0]);return run(*args,**kwargs)
        with patch('subprocess.run',side_effect=counted):
            again=self.transport.formatting('read',dict(window='@0'),time.monotonic()+2)
            self.assertEqual(again,expected)
        self.assertEqual(calls,[])
        with patch('subprocess.run',side_effect=counted):
            self.transport.formatting('write',dict(window='@0',values={'window-status-format':'writer stays finite'}),time.monotonic()+2)
            self.transport.capture('%0',1,time.monotonic()+2)
        self.assertTrue(any('set-option' in call for call in calls))
        self.assertTrue(any('capture-pane' in call for call in calls))
        observer.close()
        self.assertFalse(Path('/proc',str(owned)).exists())
        self.assertNotIn(str(owned),self.tmux('list-clients','-F','#{client_pid}'))

    def test_readonly_attach_preserves_session_environment(self):
        key='WAKE_FORMAT_READ_FIXTURE'
        self.tmux('set-option','-t','$0','update-environment',key)
        self.tmux('set-environment','-t','$0',key,'session-value')
        self.retained_owner()
        with patch.dict(os.environ,{key:'monitor-value'}):
            self.transport.formatting('read',dict(window='@0'),time.monotonic()+2)
        self.assertEqual(self.tmux('show-environment','-t','$0',key).strip(),key+'=session-value')

    def test_read_seam_rejects_nonmanaged_commands_before_creating_a_client(self):
        channel=FormattingReadChannel(self.transport);self.addCleanup(channel.close)
        invalid=[ [('set-option','-w','-t','@0','window-status-format','bad')],
                  [('send-keys','-t','%0','bad')],
                  [('show-options','-q','-v','-t','$1','status-interval')],
                  [('show-options','-w','-v','-t','@0','pane-border-style')],
                  [('display-message','-p','#{shell_command}')],
                  [('show-options','-w','-v','-t','@'+'1'*129,'window-status-format')],
                  [('show-options','-q','-v','-t','$0','status-interval')]*129 ]
        for commands in invalid:
            with self.subTest(command=commands[0]):
                with self.assertRaises(InventoryError) as error:channel.read(commands,time.monotonic()+2)
                self.assertEqual(error.exception.code,'invalid_argument')
        self.assertEqual(channel.status()['requests'],0)
        self.assertIsNone(channel.status()['owned_pid'])

    def test_socket_generation_replacement_closes_only_owned_reader(self):
        channel=FormattingReadChannel(self.transport);self.addCleanup(channel.close)
        command=[('show-options','-q','-v','-t','$0','status-interval')]
        channel.read(command,time.monotonic()+2);owned=channel.status()['owned_pid']
        previous=str(self.root/'old.sock');Path(self.socket).rename(previous)
        self.addCleanup(lambda:subprocess.run(['tmux','-S',previous,'kill-server'],capture_output=True))
        self.tmux('new-session','-d','-s','replacement','exec sleep 60')
        with self.assertRaises(InventoryError) as error:channel.read(command,time.monotonic()+2)
        self.assertEqual(error.exception.code,'workspace_changed')
        self.assertFalse(Path('/proc',str(owned)).exists())
        self.assertEqual(self.tmux('display-message','-p','#{session_name}').strip(),'replacement')

    def test_past_deadline_does_not_create_client_and_aggregate_output_is_bounded(self):
        channel=FormattingReadChannel(self.transport);self.addCleanup(channel.close)
        command=('show-options','-w','-v','-t','@0','window-status-format')
        with self.assertRaises(InventoryError) as error:channel.read([command],time.monotonic()-.1)
        self.assertEqual(error.exception.code,'formatting_read_timeout')
        self.assertIsNone(channel.status()['owned_pid'])
        channel.close()
        channel=FormattingReadChannel(self.transport);self.addCleanup(channel.close)
        self.tmux('set-option','-w','-t','@0','window-status-format','x'*8192)
        with self.assertRaises(InventoryError) as error:channel.read([command]*128,time.monotonic()+2)
        self.assertEqual(error.exception.code,'formatting_read_limit')
        self.assertIsNone(channel.status()['owned_pid'])
        self.assertEqual(channel.status()['failures'],1)

    def test_stalled_owned_peer_cannot_block_a_large_request_past_deadline(self):
        import signal
        channel=FormattingReadChannel(self.transport);self.addCleanup(channel.close)
        command=('show-options','-w','-v','-t','@0','window-status-format')
        channel.read([command],time.monotonic()+2)
        owned=channel.status()['owned_pid']
        # Control stdio is served by the tmux server; stopping the client PID
        # alone does not stall reads. This server belongs to our private fixture.
        server=int(self.tmux('display-message','-p','#{pid}').strip())
        os.kill(server,signal.SIGSTOP)
        try:
            until=time.monotonic()+1
            while 'State:\tT' not in Path('/proc',str(server),'status').read_text():
                self.assertLess(time.monotonic(),until,'Owned fixture peer did not stop.')
            started=time.monotonic()
            with self.assertRaises(InventoryError) as error:channel.read([command]*128,started+.05)
            self.assertEqual(error.exception.code,'formatting_read_timeout')
            self.assertLess(time.monotonic()-started,.8)
            self.assertFalse(Path('/proc',str(owned)).exists())
        finally:os.kill(server,signal.SIGCONT)

    def test_backoff_does_not_extend_when_monitor_ticks_faster_than_reconnect(self):
        from types import SimpleNamespace
        channel=FormattingReadChannel(self.transport);self.addCleanup(channel.close)
        command=[('show-options','-q','-v','-t','$0','status-interval')]
        base=time.monotonic()
        with self.assertRaises(InventoryError):channel.read(command,base-.1)
        with patch('codex_wake.tab_format_read_channel.time',SimpleNamespace(monotonic=lambda:base+.5)):
            with self.assertRaises(InventoryError):channel.read(command,base+3)
        with patch('codex_wake.tab_format_read_channel.time',SimpleNamespace(monotonic=lambda:base+1.1)):
            result=channel.read(command,base+3)
        self.assertEqual(result,[''])
        self.assertEqual(channel.status()['state'],'connected')

    def test_real_monitor_creates_reader_only_when_enabled_and_reaps_on_refresh_and_stop(self):
        from codex_wake.tab_monitor import TabMonitor
        path=self.root/'controller-tabs.json'
        config=dict(schema_version=1,workspaces={'work':dict(kind='tmux',socket_path=self.socket,session_id='$0')})
        path.write_text(json.dumps(config));path.chmod(0o600)
        self.call('configure',policy=dict(enabled=False))
        monitor=TabMonitor(self.root)
        self.addCleanup(lambda:monitor.execute('tabs.monitor.stop',{}))
        monitor.execute('tabs.monitor.start',dict(interval=.2,health=False,errors=False,cycle_timeout=2,probe_timeout=.5,stale_after=20))
        def reader_until(predicate):
            until=time.monotonic()+6
            while True:
                report=monitor.execute('tabs.monitor.status',{})
                readers=(report['monitor'].get('observer') or {}).get('formatting_reads',[])
                if readers and predicate(readers[0]):return readers[0]
                self.assertLess(time.monotonic(),until,report['monitor'].get('last_error'))
                time.sleep(.03)
        idle=reader_until(lambda value:value['state']=='idle')
        self.assertIsNone(idle['owned_pid'])
        self.call('configure',policy=dict(enabled=True))
        self.assertEqual(self.call('enable')['status'],'applied')
        first=reader_until(lambda value:value['owned_pid'] is not None)
        path.write_text(json.dumps(config)+'\n')
        second=reader_until(lambda value:value['owned_pid'] is not None and value['owned_pid']!=first['owned_pid'])
        self.assertFalse(Path('/proc',str(first['owned_pid'])).exists())
        self.assertEqual(monitor.execute('tabs.monitor.stop',{})['monitor']['status'],'stopped')
        self.assertFalse(Path('/proc',str(second['owned_pid'])).exists())
        self.assertEqual(self.tmux('list-clients','-F','#{client_pid}').strip(),'')
        self.assertTrue(self.tmux('list-panes','-F','#{pane_pid}').strip().isdigit())
