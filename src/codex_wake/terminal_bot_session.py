"""Repository-owned codex-bots integration; no external launcher is patched.

Launchers call ensure_bot_session through their configured public operation client.
The supplied command is used only when creating an empty dedicated destination.
Existing bot processes are never restarted or supplemented on reuse.
"""


def ensure_bot_session(execute, *, argv, name='bots', server=None, backend='tmux', cwd=None):
    """Call the portable ensure operation through an authorized host client."""
    defaults = {'argv': list(argv)}
    if cwd is not None: defaults['cwd'] = str(cwd)
    arguments = dict(name=name, backend=backend, defaults=defaults)
    if server is not None: arguments['server'] = server
    return execute('tabs.session.ensure', arguments)
