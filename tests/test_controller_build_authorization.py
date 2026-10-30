import unittest
from types import SimpleNamespace
from codex_wake.controller_build_authorization import BuildAuthorization
from codex_wake.controller_auth import AuthError
from codex_wake.managed_inventory import InventoryError


class BuildAuthorizationTests(unittest.TestCase):
    def service(self, scopes, targets):
        actor = SimpleNamespace(scopes=scopes, targets=targets)
        authority = SimpleNamespace(authenticate=lambda token: actor)
        builds = SimpleNamespace(execute=lambda *args: self.fail('effect dispatched without runtime'))
        return BuildAuthorization(authority, builds)

    def test_observe_and_unscoped_deny_before_effect(self):
        for scopes in (set(), {'observe'}, {'account.observe'}):
            with self.assertRaises(AuthError):
                self.service(scopes, [{}]).execute('token', 'builds.launch', {})

    def test_exact_control_target_requires_durable_runtime(self):
        target = {key: 'fixture' for key in BuildAuthorization.ACCOUNT_FIELDS}
        with self.assertRaises(InventoryError) as caught:
            self.service({'control'}, [target]).execute('token', 'builds.launch', {'expected_target': target})
        self.assertEqual(caught.exception.code, 'operation_runtime_required')

    def test_broad_control_does_not_authorize_account(self):
        target = {key: 'fixture' for key in BuildAuthorization.ACCOUNT_FIELDS}
        with self.assertRaises(AuthError):
            self.service({'control'}, [{}]).execute('token', 'builds.launch', {'expected_target': target})

    def test_stage_requires_admin_and_host_pinned_recipe(self):
        with self.assertRaises(AuthError):
            self.service({'admin'}, [{}]).execute('token', 'builds.stage', {'recipe': '/tmp/untrusted'})

    def test_recipe_replacement_after_admission_is_refused_before_dispatch(self):
        import hashlib
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            recipe = Path(directory) / 'approved.json'
            recipe.write_text('{"version":1}')
            target = {'host': 'host', 'environment': 'test', 'recipe': 'approved',
                      'recipe_sha256': hashlib.sha256(recipe.read_bytes()).hexdigest()}
            actor = SimpleNamespace(scopes={'admin'}, targets=[target])
            authority = SimpleNamespace(authenticate=lambda token: actor)
            builds = SimpleNamespace(recipes={'approved': str(recipe)},
                execute=lambda *args: self.fail('changed recipe was dispatched'))
            class Runtime:
                def execute(unused, caller, operation, arguments, *, authorize, dispatch):
                    recipe.write_text('{"version":2}')
                    authorize()
                    return {'unexpected': 'changed recipe admitted'}
            service = BuildAuthorization(authority, builds,
                recipe_targets={'approved': target}, runtime=Runtime())
            with self.assertRaises(InventoryError) as caught:
                service.execute('token', 'builds.stage', {'recipe': 'approved'})
            self.assertEqual(caught.exception.code, 'stale_target')
