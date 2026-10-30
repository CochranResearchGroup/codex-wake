import hashlib
import json

from codex_wake.controller_builds import ControllerBuilds


def test_named_pinned_build_launch_preserves_identity(tmp_path):
    executable = tmp_path / 'native'
    executable.write_text('#!/bin/sh\nprintf "%s" "$CODEX_BUILD_CHANNEL" > "$CODEX_HOME/result"\n')
    executable.chmod(0o700)
    home = tmp_path / 'private'
    home.mkdir()
    manifest = tmp_path / 'builds.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'builds': {'modded': {
        'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'upstream_version': '1', 'revision': 'fixture', 'source': 'local fixture'}}}))
    class Accounts:
        def execute(self, operation, arguments):
            return {'account': {'id': 'fixture', 'home': str(home), 'target': {'provider': 'codex'}}}
    owner = ControllerBuilds(manifest, Accounts())
    listed = owner.execute('builds.list', {'account': 'fixture'})
    target = listed['builds'][0]['target']
    result = owner.execute('builds.launch', {'account': 'fixture', 'channel': 'modded', 'expected_target': target, 'args': ['--version']})
    assert result['exit_code'] == 0
    assert result['target'] == target
    assert (home / 'result').read_text() == 'modded'


def test_unregistered_recipe_is_unauthorized(tmp_path):
    from codex_wake.managed_inventory import InventoryError
    owner = ControllerBuilds(tmp_path / 'builds.json', None)
    try:
        owner.execute('builds.stage', {'recipe': '/tmp/untrusted'})
    except InventoryError as error:
        assert error.code == 'unauthorized_target'
    else:
        raise AssertionError('untrusted recipe accepted')
