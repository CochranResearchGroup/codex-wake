from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest

from codex_wake.cli import build_parser, github_webhook_command
from codex_wake.github_source_config import GitHubSourceStore
from codex_wake.managed_webhook_rotation import ManagedWebhookRotationStore, RotationRecord
from codex_wake.managed_webhook_rotation_preview import ManagedWebhookRotationPreviewer
from codex_wake.managed_webhooks import ManagedWebhookBinding, ManagedWebhookStore, ProviderHook
from codex_wake.records import WakeError
from codex_wake.webhook_lifecycle import WebhookListenerConfig, WebhookListenerStore
from tests.test_github_polling import config as github_config


class FakeProvider:
    def __init__(self, hooks: tuple[ProviderHook, ...] = ()) -> None:
        self.hooks = list(hooks)
        self.calls: list[tuple[str, int | None]] = []

    def list_hooks(self, *, repository_id: int) -> tuple[ProviderHook, ...]:
        self.calls.append(("list", repository_id))
        return tuple(self.hooks)

    def create_hook(self, binding: ManagedWebhookBinding) -> ProviderHook:
        self.calls.append(("create", None))
        created = matching_hook(binding, 101)
        self.hooks.append(created)
        return created

    def update_hook(self, *, hook_id: int, binding: ManagedWebhookBinding) -> ProviderHook:
        self.calls.append(("update", hook_id))
        updated = matching_hook(binding, hook_id)
        self.hooks = [updated if item.hook_id == hook_id else item for item in self.hooks]
        return updated

    def get_hook(self, *, repository_id: int, hook_id: int) -> ProviderHook | None:
        self.calls.append(("get", hook_id))
        return next((item for item in self.hooks if item.hook_id == hook_id), None)


def matching_hook(binding: ManagedWebhookBinding, hook_id: int) -> ProviderHook:
    return ProviderHook(
        hook_id=hook_id,
        callback_url=binding.callback_url,
        events=binding.events,
        active=True,
        content_type="json",
        insecure_ssl=False,
    )


class ProviderFactory:
    def __init__(self, provider: FakeProvider) -> None:
        self.provider = provider
        self.calls = 0

    def __call__(self, binding, *, credential_resolver, secret_generation_resolver):
        self.calls += 1
        self.binding = binding
        self.credential_resolver = credential_resolver
        self.secret_generation_resolver = secret_generation_resolver
        return self.provider


class ManagedWebhookCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "wake"
        WebhookListenerStore(self.root).configure(
            WebhookListenerConfig(
                source_instance="github-workflow",
                secret_ref="WEBHOOK_SECRET_VALUE",
                enabled=True,
            )
        )
        GitHubSourceStore(self.root).configure(github_config(
            source_instance="github-workflow", repository="octo/example", repository_id=42,
            evidence_mode="positive_only",
        ))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def args(self, *values: str):
        return build_parser().parse_args(["github-webhook", "binding", *values])

    def rotation_args(self, *values: str):
        return build_parser().parse_args(["github-webhook", "rotation", *values])

    def configure(self, *, as_json: bool = True) -> tuple[int, str]:
        values = [
            "configure",
            "--source", "github-workflow",
            "--installation-id", "install-1",
            "--repository", "octo/example",
            "--repository-id", "42",
            "--callback-url", "https://hooks.example.test/github/webhook",
            "--credential-ref", "GITHUB_ADMIN_TOKEN_VALUE",
        ]
        if as_json:
            values.append("--json")
        output = StringIO()
        with redirect_stdout(output):
            code = github_webhook_command(self.args(*values), self.root)
        return code, output.getvalue()

    def invoke(self, *values: str, provider: FakeProvider | None = None) -> tuple[int, str, ProviderFactory]:
        selected = provider or FakeProvider()
        factory = ProviderFactory(selected)
        output = StringIO()
        with redirect_stdout(output):
            code = github_webhook_command(
                self.args(*values), self.root, provider_factory=factory
            )
        return code, output.getvalue(), factory

    def test_configure_is_idempotent_secret_free_and_requires_listener(self) -> None:
        code, rendered = self.configure()
        self.assertEqual(code, 0)
        result = json.loads(rendered)
        self.assertEqual(result["lifecycle"], "UNMANAGED")
        self.assertTrue(result["provider_credential_reference_configured"])
        self.assertNotIn("GITHUB_ADMIN_TOKEN_VALUE", rendered)
        self.assertNotIn("WEBHOOK_SECRET_VALUE", rendered)
        path = ManagedWebhookStore(self.root).path
        original = path.read_bytes()

        code, second = self.configure()
        self.assertEqual(code, 0)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(json.loads(second)["generation"], 0)

        other = Path(self.temporary.name) / "other"
        with self.assertRaisesRegex(WakeError, "listener is not configured"):
            github_webhook_command(self.args(
                "configure", "--source", "github-workflow", "--installation-id", "install-1",
                "--repository", "octo/example", "--repository-id", "42",
                "--callback-url", "https://hooks.example.test/github/webhook",
                "--credential-ref", "GITHUB_ADMIN_TOKEN_VALUE",
            ), other)

    def test_show_is_local_and_redacts_reference_names(self) -> None:
        self.configure()
        code, rendered, factory = self.invoke("show", "github-workflow", "--json")
        self.assertEqual((code, factory.calls), (0, 0))
        self.assertNotIn("GITHUB_ADMIN_TOKEN_VALUE", rendered)
        self.assertNotIn("WEBHOOK_SECRET_VALUE", rendered)
        self.assertEqual(json.loads(rendered)["repository_id"], 42)

        WebhookListenerStore(self.root).path.unlink()
        code, rendered, factory = self.invoke("show", "github-workflow", "--json")
        self.assertEqual((code, factory.calls), (0, 0))
        self.assertFalse(json.loads(rendered)["listener_secret_reference_configured"])

    def test_dry_run_lists_once_and_never_writes(self) -> None:
        self.configure()
        provider = FakeProvider()
        code, rendered, factory = self.invoke(
            "reconcile", "github-workflow", "--json", provider=provider
        )
        result = json.loads(rendered)
        self.assertEqual(code, 0)
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["plan"]["action"], "WRITE")
        self.assertEqual(provider.calls, [("list", 42)])
        self.assertEqual(factory.calls, 1)
        self.assertEqual(ManagedWebhookStore(self.root).load("github-workflow").generation, 0)

    def test_apply_writes_once_reads_back_and_converges(self) -> None:
        self.configure()
        provider = FakeProvider()
        code, rendered, _ = self.invoke(
            "reconcile", "github-workflow", "--apply", "--json", provider=provider
        )
        result = json.loads(rendered)
        self.assertEqual(code, 0)
        self.assertEqual(result["receipt"]["state"], "SUCCEEDED")
        self.assertEqual(result["binding"]["lifecycle"], "ACTIVE")
        self.assertEqual(provider.calls, [("list", 42), ("list", 42), ("create", None), ("get", 101)])

    def test_status_and_collision_are_nonready_without_provider_write(self) -> None:
        self.configure()
        provider = FakeProvider()
        code, rendered, _ = self.invoke(
            "status", "github-workflow", "--json", provider=provider
        )
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(rendered)["plan"]["inventory"], "ABSENT")

        binding = ManagedWebhookStore(self.root).load("github-workflow")
        collision = FakeProvider((matching_hook(binding, 88),))
        code, rendered, _ = self.invoke(
            "reconcile", "github-workflow", "--apply", "--json", provider=collision
        )
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(rendered)["receipt"]["state"], "UNKNOWN")
        self.assertEqual(collision.calls, [("list", 42)])

        code, rendered, _ = self.invoke(
            "reconcile", "github-workflow", "--apply", "--json", provider=collision
        )
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(rendered)["binding"]["lifecycle"], "UNKNOWN")
        self.assertEqual(collision.calls, [("list", 42), ("list", 42)])

    def test_repository_identity_cannot_be_rebound(self) -> None:
        self.configure()
        args = self.args(
            "configure", "--source", "github-workflow", "--installation-id", "install-1",
            "--repository", "octo/other", "--repository-id", "43",
            "--callback-url", "https://hooks.example.test/github/webhook",
            "--credential-ref", "GITHUB_ADMIN_TOKEN_VALUE",
        )
        with self.assertRaisesRegex(WakeError, "ownership is immutable"):
            github_webhook_command(args, self.root)

        installation = self.args(
            "configure", "--source", "github-workflow", "--installation-id", "install-2",
            "--repository", "octo/example", "--repository-id", "42",
            "--callback-url", "https://hooks.example.test/github/webhook",
            "--credential-ref", "GITHUB_ADMIN_TOKEN_VALUE",
        )
        with self.assertRaisesRegex(WakeError, "ownership is immutable"):
            github_webhook_command(installation, self.root)

    def test_rotation_preview_is_local_redacted_and_fences_generic_apply(self) -> None:
        self.configure()
        setup_provider = FakeProvider()
        setup_code, _, _ = self.invoke(
            "reconcile", "github-workflow", "--apply", "--json", provider=setup_provider,
        )
        self.assertEqual(setup_code, 0)
        provider = FakeProvider()
        factory = ProviderFactory(provider)
        output = StringIO()
        with redirect_stdout(output):
            code = github_webhook_command(self.rotation_args(
                "preview", "--source", "github-workflow",
                "--target-generation", "2", "--overlap-seconds", "900", "--json",
            ), self.root, provider_factory=factory)
        result = json.loads(output.getvalue())
        self.assertEqual((code, factory.calls, provider.calls), (0, 0, []))
        self.assertEqual(result["next_action"], "PREPARE_ROTATION")
        self.assertEqual((result["previous_generation"], result["target_generation"]), (1, 2))
        self.assertFalse(result["apply_supported"])
        rendered = output.getvalue()
        for forbidden in (
            "WEBHOOK_SECRET_VALUE", "GITHUB_ADMIN_TOKEN_VALUE", "journal", "attestation",
        ):
            self.assertNotIn(forbidden, rendered)

        listener_store = WebhookListenerStore(self.root)
        listener_store.path.unlink()
        listener_store.configure(WebhookListenerConfig(
            source_instance="github-workflow", secret_ref="UNTRACKED_TARGET",
            previous_secret_ref="WEBHOOK_SECRET_VALUE", enabled=True,
        ))
        with self.assertRaisesRegex(WakeError, "rotation authority is invalid"):
            github_webhook_command(self.rotation_args(
                "status", "--source", "github-workflow", "--json",
            ), self.root, provider_factory=factory)
        listener_store.path.unlink()
        listener_store.configure(WebhookListenerConfig(
            source_instance="github-workflow", secret_ref="WEBHOOK_SECRET_VALUE", enabled=True,
        ))

        binding = ManagedWebhookStore(self.root).load("github-workflow")
        ManagedWebhookRotationStore(self.root).save(RotationRecord(
            owner_id=binding.owner_id, canonical_root=str(self.root.resolve()), owner_uid=os.getuid(),
            source_instance=binding.source_instance, service_id=binding.service_id,
            binding_revision=binding.generation, previous_generation=1, target_generation=2,
            overlap_deadline=2_000_000_000,
        ))
        output = StringIO()
        with redirect_stdout(output):
            code = github_webhook_command(self.rotation_args(
                "status", "--source", "github-workflow", "--json",
            ), self.root, provider_factory=factory)
        status = json.loads(output.getvalue())
        self.assertEqual((code, factory.calls, provider.calls), (0, 0, []))
        self.assertEqual((status["phase"], status["next_action"]), ("PREPARED", "INTEND_DUAL_RESTART"))

        previewer = ManagedWebhookRotationPreviewer(self.root)
        with self.assertRaisesRegex(ValueError, "clock moved backwards"):
            # Replace the fixture only in memory: persisted state remains the
            # authoritative input used by the previewer.
            current = ManagedWebhookRotationStore(self.root).load("github-workflow")
            ManagedWebhookRotationStore(self.root).save(
                replace(current, last_observed_at=10),
                expected_revision=current.revision,
            )
            previewer.preview("github-workflow", now=9)
        expired = previewer.preview("github-workflow", now=2_000_000_001)
        self.assertEqual((expired.deadline_state, expired.next_action), ("expired", "ROLLBACK_REQUIRED"))

        reconcile = self.args("reconcile", "github-workflow", "--apply", "--json")
        with self.assertRaisesRegex(WakeError, "blocked while rotation authority exists"):
            github_webhook_command(reconcile, self.root, provider_factory=factory)
        self.assertEqual((factory.calls, provider.calls), (0, []))


if __name__ == "__main__":
    unittest.main()
