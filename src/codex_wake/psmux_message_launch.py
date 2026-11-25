"""Private Windows psmux child for an already selected exact Codex account."""
import ctypes
import os
from pathlib import Path
import re
import subprocess
import sys


def main(binding, nonce):
    # psmux filter commands can run with a different inherited PYTHONPATH.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from codex_wake.psmux_message_recovery import Presentation, Runtime, _ENV, _load, _write
    from codex_wake.tab_psmux_bridge import process_birth

    if os.name != 'nt' or ctypes.windll.shell32.IsUserAnAdmin() or not re.fullmatch(r'[a-f0-9]{32}', nonce):
        return 2
    binding = Path(binding)
    value = _load(binding)
    runtime = Runtime(value['spec'])
    spec = runtime.spec
    if runtime.identify_process() != value['runtime']['server_birth']:
        return 2
    process = subprocess.Popen(
        [spec['codex'], '--remote', runtime.endpoint, '--remote-auth-token-env', _ENV,
         'resume', spec['thread'], '--no-alt-screen'], cwd=spec['cwd'], env=runtime.environment())
    try:
        _write(Presentation(binding, value)._marker(nonce),
               dict(nonce=nonce, thread=spec['thread'], pid=process.pid, birth=process_birth(process.pid)))
        return process.wait()
    finally:
        if process.poll() is None:
            process.terminate()


if __name__ == '__main__':
    raise SystemExit(main(*sys.argv[1:]))
