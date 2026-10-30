#!/usr/bin/env python3
"""Installed provider-free durable flow acceptance using the actual Mailbox owner."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

from controller_runtime_expanded_acceptance import prepare


def main():
    import codex_wake
    from codex_wake.a2a_mailbox import Mailbox
    from codex_wake.controller_runtime import ControllerRuntime
    from codex_wake.operation_commands import local_actor
    with tempfile.TemporaryDirectory(prefix='wake-flow406-') as directory:
        root = Path(directory) / 'wake'
        fixture = prepare(root)
        config = fixture['config']
        config['local_caller']['targets'].append(dict(host=socket.gethostname(),
            environment=os.environ.get('WSL_DISTRO_NAME') or os.name, flow_id='fixture'))
        sender = fixture['natives'][0].thread_id
        config['flow_callers'] = {sender: dict(config['local_caller'], grant_id='fixture-native-flow')}
        (root / 'controller-messaging.json').write_text(json.dumps(config))
        target = fixture['target']
        source = dict(id='fixture', version=1, entry='send', nodes=[
            dict(id='send', type='call', operation='operations.send', arguments=dict(
                sender_binding='native-sender', expected_target=target, body='flow question',
                delivery='inbox', queue=True, response_requested=False), next='wait'),
            dict(id='wait', type='wait', operation_id={'ref': 'steps.send.result.operation.operation_id'}, timeout=0, next='branch'),
            {'id': 'branch', 'type': 'branch', 'condition': {'op': 'eq',
                'left': {'ref': 'steps.wait.result.operation.answer.text'}, 'right': 'actual flow answer'},
                'then': 'answer', 'else': 'wrong'},
            dict(id='answer', type='end', value={'ref': 'steps.wait.result.operation.answer.text'}),
            dict(id='wrong', type='end', value='wrong branch')])
        def cli(verb, arguments):
            result = subprocess.run([sys.executable, '-m', 'codex_wake.cli', '--wake-root', str(root),
                'flows', verb, '--arguments', json.dumps(arguments)], text=True, capture_output=True)
            if result.returncode:
                raise AssertionError((result.stdout, result.stderr))
            return json.loads(result.stdout)['result']
        cli('publish', dict(definition=source))
        run = cli('start', dict(flow_id='fixture', version=1, inputs={}, intent='fixture-one', binding='original-caller'))
        run_id = run['run_id']
        waiting = cli('advance', dict(run_id=run_id))
        assert waiting['phase'] == 'waiting', waiting
        original = waiting['steps']['send']['result']['operation']
        mailbox = Mailbox(fixture['bus'])
        message_id = original['result']['message_id']
        mailbox.ack(fixture['actors'][1], message_id, outcome='accepted')
        mailbox.reply(fixture['actors'][1], message_id, body='actual flow answer',
            idempotency_key='fixture-answer', kind='result', delivery='inbox', outcome='completed')
        finished = cli('advance', dict(run_id=run_id))
        assert finished['phase'] == 'completed' and finished['result'] == 'actual flow answer', finished
        assert cli('advance', dict(run_id=run_id)) == finished
        runtime = ControllerRuntime(root)
        child = runtime.operation(local_actor(root), 'operations.result',
            {'operation_id': original['operation_id']}, authorize=lambda: local_actor(root))
        assert child['result']['operation']['result']['message_id'] == message_id
        import asyncio
        async def native():
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            parameters = StdioServerParameters(command=str(Path(sys.executable).parent / 'codex-wake-mcp'),
                args=['--wake-root', str(root)], env={key: value for key, value in os.environ.items() if key != 'PYTHONPATH'})
            metadata = dict(threadId=sender, sessionId=sender, callId='fixture-flow',
                **{'x-codex-turn-metadata': dict(thread_id=sender, session_id=sender, turn_id='fixture')})
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    async def call(verb, arguments):
                        response = await session.call_tool('wake_flows_' + verb,
                            dict(arguments, caller_thread_id=sender), meta=metadata)
                        assert not response.is_error, response
                        return json.loads(response.content[0].text)['result']
                    denied = await session.call_tool('wake_flows_definition',
                        dict(flow_id='fixture', version=1, caller_thread_id=sender))
                    assert denied.is_error
                    started = await call('start', dict(flow_id='fixture', version=1, inputs={}, intent='native-one', binding='native-original'))
                    waiting = await call('advance', dict(run_id=started['run_id']))
                    assert waiting['phase'] == 'waiting', waiting
                    original = waiting['steps']['send']['result']['operation']
                    message_id = original['result']['message_id']
                    mailbox.ack(fixture['actors'][1], message_id, outcome='accepted')
                    mailbox.reply(fixture['actors'][1], message_id, body='actual flow answer',
                        idempotency_key='native-flow-answer', kind='result', delivery='inbox', outcome='completed')
                    finished = await call('advance', dict(run_id=started['run_id']))
                    assert finished['phase'] == 'completed' and finished['result'] == 'actual flow answer', finished
        asyncio.run(native())
        print(json.dumps(dict(status='passed', package=codex_wake.__file__, checks=[
            'installed CLI immutable publish and idempotent start',
            'actual Mailbox submission and retained cursor after caller process exit',
            'late actual recipient result returned by restarted flow',
            'typed Boolean branch and completed result never redispatch',
            'actual installed stdio MCP native identity and correlated Mailbox answer']), sort_keys=True))


if __name__ == '__main__':
    main()
