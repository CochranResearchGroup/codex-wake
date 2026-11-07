"""Compatibility entrypoints for the Profiles implementation absorbed by Wake.

Explicit --config remains authoritative. CODEX_PROFILES_CONFIG is a legacy
fallback when no Wake default is selected; no credentials migrate automatically.
"""
import os
from pathlib import Path
import socket
import sys


def default_config():
    explicit = os.environ.get('CODEX_WAKE_ACCOUNTS_CONFIG')
    if explicit:
        return Path(explicit)
    if os.environ.get('CODEX_WAKE_ROOT'):
        return Path(os.environ['CODEX_WAKE_ROOT']) / 'controller-accounts.toml'
    from .shortcut_store import default_root, preference_path, user_root
    legacy = os.environ.get('CODEX_PROFILES_CONFIG')
    if legacy and not preference_path().exists() and not (user_root() / 'controller-accounts.toml').is_file():
        return Path(legacy)
    return default_root() / 'controller-accounts.toml'


def main(argv=None):
    from codex_profiles.cli import build_parser, main as profiles_main, split_run_profile_and_args
    from codex_profiles.config import load_settings
    from .controller_accounts import ControllerAccounts, launch_overrides
    from .managed_inventory import InventoryError
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not any(arg == '--config' or arg.startswith('--config=') for arg in arguments):
        try:
            selected = default_config()
        except (ValueError, OSError) as error:
            print('account operation held: ' + str(error), file=sys.stderr)
            return 2
        arguments = ['--config', str(selected), *arguments]
    # Preserve all supported legacy commands. Only run needs configuration
    # materialization, and command-line overrides avoid changing shared files.
    parsed, _ = build_parser().parse_known_args(arguments)
    if not parsed.config.is_file() and parsed.command not in ('completion', 'shell-init'):
        print('account operation held: explicit account configuration is unavailable', file=sys.stderr)
        return 2
    from .controller_registry import resolve_registry
    effective = resolve_registry(parsed.config)
    if effective != parsed.config:
        for index, argument in enumerate(arguments):
            if argument == '--config':
                arguments[index + 1] = str(effective)
            elif argument.startswith('--config='):
                arguments[index] = '--config=' + str(effective)
        parsed.config = effective
    if parsed.command == 'run':
        try:
            settings = load_settings(parsed.config, parsed.state_root, parsed.source_root)
            profile, native_args = split_run_profile_and_args(settings, parsed.profile, list(parsed.codex_args))
            if native_args in (['--version'], ['-V']):
                return profiles_main(arguments)
            owner = ControllerAccounts(parsed.config, host=socket.gethostname(),
                environment=os.environ.get('WSL_DISTRO_NAME') or os.name)
            view = owner.execute('configuration.explain', {'selector': profile})
            overrides = launch_overrides(view)
            # Native parser has already separated profile/build options. Keep
            # their exact arguments and prepend the configuration flags after
            # the profile, before the caller's explicit native overrides.
            if overrides:
                prefix = arguments[:arguments.index('run') + 1]
                if parsed.channel:
                    prefix += ['--channel', parsed.channel]
                if parsed.build_manifest:
                    prefix += ['--build-manifest', str(parsed.build_manifest)]
                if parsed.sudo:
                    prefix += ['--sudo']
                if parsed.sudo_user:
                    prefix += ['--sudo-user', parsed.sudo_user]
                arguments = [*prefix, profile, '--', *overrides, *native_args]
        except (InventoryError, OSError, ValueError) as error:
            print('account launch held: ' + str(error), file=sys.stderr)
            return 2
    return profiles_main(arguments)


def profile_main():
    arguments = list(sys.argv[1:])
    if arguments and arguments[0].startswith('-') and arguments[0] not in ('--channel', '--build-manifest', '--sudo', '--sudo-user', '--'):
        arguments.insert(0, '--')
    return main(['run', *arguments])


def stock_main():
    return main(['run', '--channel', 'stock', '--', *sys.argv[1:]])


def modded_main():
    return main(['run', '--channel', 'modded', '--', *sys.argv[1:]])
