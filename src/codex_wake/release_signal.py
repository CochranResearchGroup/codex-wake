"""Small bounded stdio MCP client for the installed Cargo Signal service."""
import json
import selectors
import shutil
import subprocess


class SignalClient:
    def __init__(self, executable='cargo-signal'):
        command = shutil.which(executable)
        if not command:
            raise ValueError('Cargo Signal MCP executable unavailable')
        self.process = subprocess.Popen([command, 'mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True)
        self.sequence = 0
        self.request('initialize', dict(protocolVersion='2025-03-26', capabilities={},
                                       clientInfo=dict(name='codex-wake-release', version='1')))
        self.process.stdin.write(json.dumps(dict(jsonrpc='2.0', method='notifications/initialized')) + '\n')
        self.process.stdin.flush()

    def request(self, method, params):
        self.sequence += 1
        self.process.stdin.write(json.dumps(dict(jsonrpc='2.0', id=self.sequence, method=method, params=params)) + '\n')
        self.process.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            if not selector.select(30):
                raise ValueError('Cargo Signal MCP response unresolved; reconcile recorded attempt')
        line = self.process.stdout.readline(1024 * 1024)
        response = json.loads(line)
        if response.get('id') != self.sequence or 'error' in response:
            raise ValueError('Cargo Signal MCP protocol failure')
        return response['result']

    def call(self, name, arguments):
        result = self.request('tools/call', dict(name=name, arguments=arguments))
        if not isinstance(result.get('structuredContent'), dict):
            raise ValueError('Cargo Signal MCP returned no structured receipt')
        return result['structuredContent']

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()
