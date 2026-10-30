"""Wake-owned immutable build operations over the absorbed pinned-build owner.

Manifest and recipe mappings are trusted host configuration, never caller paths.
Launch retains the existing private-home lock and descriptor pinning boundary.
"""
from pathlib import Path
import io

from codex_profiles.build_channels import BuildError, load_build, run_build
from codex_profiles import upgrades
from .managed_inventory import InventoryError


class ControllerBuilds:
    def __init__(self, manifest, accounts, *, recipes=None):
        self.manifest = Path(manifest)
        self.accounts = accounts
        self.recipes = dict(recipes or {})

    def execute(self, operation, arguments):
        allowed = {
            'builds.list': {'account'},
            'builds.launch': {'account', 'channel', 'expected_target', 'args'},
            'builds.stage': {'recipe'},
            'builds.rollback': {'account', 'channel', 'expected_target'},
        }
        if operation not in allowed:
            raise InventoryError('unsupported_operation', 'unsupported build operation')
        if not isinstance(arguments, dict) or set(arguments) - allowed[operation]:
            raise InventoryError('invalid_argument', 'unsupported build arguments')
        try:
            if operation == 'builds.stage':
                recipe = arguments.get('recipe')
                if not isinstance(recipe, str) or recipe not in self.recipes:
                    raise InventoryError('unauthorized_target', 'recipe is not host authorized')
                return upgrades.stage(self.manifest.parent, Path(self.recipes[recipe]))
            account = self.accounts.execute('accounts.resolve', {'selector': arguments.get('account')})['account']
            home = Path(account['home'])
            channels = ('stock', 'modded') if operation == 'builds.list' else (arguments.get('channel'),)
            rows = []
            for channel in channels:
                try:
                    build = load_build(self.manifest, channel, home)
                except BuildError:
                    if operation == 'builds.list':
                        continue
                    raise
                target = dict(account['target'], build_channel=channel, build_sha256=build.sha256,
                              build_revision=build.revision, executable=str(build.executable))
                rows.append(dict(name=channel, target=target, source=build.source,
                                 upstream_version=build.upstream_version, account_identity='unverified'))
            if operation == 'builds.list':
                return {'owner': 'codex-wake', 'builds': rows}
            if arguments.get('expected_target') != target:
                raise InventoryError('stale_target', 'expected account and immutable build identity required')
            if operation == 'builds.rollback':
                return upgrades.select(self.manifest.parent, home, channel=channel, rollback=True)
            args = arguments.get('args', ['--version'])
            if not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
                raise InventoryError('invalid_argument', 'build arguments must be strings')
            output = io.StringIO()
            code = run_build(build, home, account['id'], args, output=output)
            return {'target': target, 'exit_code': code, 'identity': output.getvalue(),
                    'status': 'exited', 'account_identity': 'unverified'}
        except InventoryError:
            raise
        except (BuildError, upgrades.UpgradeError, OSError, ValueError) as error:
            raise InventoryError('build_held', str(error)) from error
