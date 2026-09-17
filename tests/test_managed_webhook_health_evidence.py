from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from codex_wake.managed_webhook_health_evidence import ManagedWebhookHealthEvidenceStore
from codex_wake.managed_webhooks import ManagedWebhookBinding


def binding(root: Path) -> ManagedWebhookBinding:
    return ManagedWebhookBinding(
        owner_id="health-owner", installation_id="health-install",
        canonical_root=str(root.resolve()), owner_uid=os.getuid(),
        provider_host="api.github.com", source_instance="github-ci",
        repository="example/project", repository_id=42,
        callback_url="https://hooks.example.test/github/webhook", events=("workflow_run",),
        service_id="codex-wake-github-webhook-github-ci.service",
        executable_id="codex-wake-github-webhook",
        provider_credential_ref="GITHUB_ADMIN_TOKEN", secret_generation=1,
    )


class ManagedWebhookHealthEvidenceStoreTests(unittest.TestCase):
    def test_recording_rejects_a_symlinked_lock_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookHealthEvidenceStore(root)
            store.lock_path.parent.mkdir(parents=True)
            target = Path(temporary) / "outside-lock"
            target.touch()
            store.lock_path.symlink_to(target)

            with self.assertRaisesRegex(ValueError, "health evidence"):
                store.record_polling(binding(root), observed_at=1)


if __name__ == "__main__":
    unittest.main()
