"""Resolve default governor controls against the configured local MCP owner."""
import os
from pathlib import Path
from types import SimpleNamespace
import tomllib


def configured(root):
    """Explicit isolated roots stay exact; ordinary UI and MCP share host settings."""
    from .local_control_lifecycle import root_for
    root = Path(root).expanduser().absolute()
    if root != root_for(SimpleNamespace(wake_root=None)):
        return root, None
    homes = [Path(os.environ['CODEX_HOME'])] if os.environ.get('CODEX_HOME') else []
    homes.append(Path.home() / '.codex')
    for home in dict.fromkeys(homes):
        path = home / 'config.toml'
        if not path.exists():
            continue
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_size > 2 * 1024 * 1024 or not path.is_file():
            raise ValueError('governor host configuration must be a bounded locally owned file')
        data = tomllib.loads(path.read_text())
        server = data.get('mcp_servers', {}).get('codex-wake')
        if not isinstance(server, dict) or server.get('enabled') is False:
            continue
        # Remote connector configuration does not identify a local root.
        if server.get('url'):
            return root, None
        args = server.get('args', [])
        if not isinstance(args, list) or len(args) > 128 or any(not isinstance(arg, str) for arg in args):
            raise ValueError('configured Wake MCP arguments must be a bounded string array')
        selected = {}
        names = ('--goal-limits-root', '--goal-limits-policy', '--wake-root')
        for index, arg in enumerate(args):
            key, separator, value = arg.partition('=')
            if key not in names:
                continue
            if not separator:
                if index + 1 >= len(args):
                    raise ValueError('configured governor root or policy is missing its value')
                value = args[index + 1]
            path_value = Path(value).expanduser()
            if not path_value.is_absolute():
                raise ValueError('configured governor root and policy must use absolute paths')
            if key in selected and selected[key] != path_value:
                raise ValueError('configured governor owner is ambiguous; inspect Wake MCP configuration')
            selected[key] = path_value
        policy = selected.get('--goal-limits-policy')
        destination = selected.get('--goal-limits-root')
        if destination is None and policy is not None:
            destination = selected.get('--wake-root')
        return destination or root, policy
    return root, None
