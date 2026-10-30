"""Compatibility entrypoints for the Profiles implementation absorbed by Wake.

Explicit legacy --config and CODEX_PROFILES_CONFIG are migration inputs. They
select the same owner; no state or credential migration occurs automatically.
"""
import json
import os
from pathlib import Path
import socket
import sys


def default_config():
    return Path(os.environ.get('CODEX_WAKE_ACCOUNTS_CONFIG') or
                os.environ.get('CODEX_PROFILES_CONFIG') or
                str(Path(os.environ.get('CODEX_WAKE_ROOT', '.codex/wake')) / 'controller-accounts.toml'))


def main(argv=None):
    from codex_profiles.cli import build_parser, main as profiles_main, split_run_profile_and_args
    from codex_profiles.config import load_settings
    from .controller_accounts import ControllerAccounts
    from .managed_inventory import InventoryError
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not any(arg == '--config' or arg.startswith('--config=') for arg in arguments):
        arguments = ['--config', str(default_config()), *arguments]
    # Preserve all supported legacy commands. Only run needs configuration
    # materialization, and command-line overrides avoid changing shared files.
    parsed, _ = build_parser().parse_known_args(arguments)
    if not parsed.config.is_file() and parsed.command not in ('completion', 'shell-init'):
        print('account operation held: explicit account configuration is unavailable', file=sys.stderr)
        return 2
    if parsed.command == 'run':
        try:
            settings = load_settings(parsed.config, parsed.state_root, parsed.source_root)
            profile, native_args = split_run_profile_and_args(settings, parsed.profile, list(parsed.codex_args))
            owner = ControllerAccounts(parsed.config, host=socket.gethostname(),
                environment=os.environ.get('WSL_DISTRO_NAME') or os.name)
            view = owner.execute('configuration.explain', {'selector': profile})
            overrides = []
            for key, source in view['provenance'].items():
                if source.startswith('native:'):
                    continue
                value = view['effective'][key]
                if value == '[redacted]':
                    raise InventoryError('unsupported_target', 'secret configuration overrides require the native credential owner')
                # JSON scalar/array syntax is valid TOML for supported native
                # setting values. Quoted dotted segments preserve native keys.
                native_key = '.'.join(json.dumps(segment) for segment in key.split('.'))
                overrides += ['-c', native_key + '=' + json.dumps(value, separators=(',', ':'))]
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
    return main(['run', '--channel', 'stock', *sys.argv[1:]])


def modded_main():
    return main(['run', '--channel', 'modded', *sys.argv[1:]])
