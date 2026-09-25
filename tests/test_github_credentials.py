from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from codex_wake.github_credentials import resolve_github_credential
from codex_wake.cli import build_parser
from codex_wake.webhook_lifecycle import WebhookListenerConfig, required_secret_references
from tests.test_github_polling import config as polling_config
from dataclasses import replace


class GitHubCredentialTests(unittest.TestCase):
    def test_gh_backend_uses_fixed_command_and_never_exposes_failure_output(self) -> None:
        with patch("codex_wake.github_credentials.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "test-token\n"
            self.assertEqual(resolve_github_credential("GH_CLI"), "test-token")
            run.assert_called_once_with(
                ["gh", "auth", "token", "--hostname", "github.com"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            self.assertEqual(
                resolve_github_credential("GH_CLI", hostname="api.github.com"), "test-token",
            )
            run.return_value.returncode = 1
            run.return_value.stderr = "private-token"
            with self.assertRaisesRegex(ValueError, "authentication is unavailable") as raised:
                resolve_github_credential("GH_CLI")
            self.assertNotIn("private-token", str(raised.exception))

    def test_explicit_environment_reference_does_not_call_gh(self) -> None:
        with patch.dict(os.environ, {"EXPLICIT_GITHUB_TOKEN": "limited-token"}):
            with patch("codex_wake.github_credentials.subprocess.run") as run:
                self.assertEqual(resolve_github_credential("EXPLICIT_GITHUB_TOKEN"), "limited-token")
                run.assert_not_called()

    def test_user_service_uses_homebrew_gh_when_path_lacks_it(self) -> None:
        with patch("codex_wake.github_credentials.subprocess.run") as run:
            run.side_effect = [
                FileNotFoundError(),
                type("Result", (), {"returncode": 0, "stdout": "test-token\n"})(),
            ]
            with patch("codex_wake.github_credentials.Path.is_file", return_value=True):
                with patch("codex_wake.github_credentials.os.access", return_value=True):
                    self.assertEqual(resolve_github_credential("GH_CLI"), "test-token")
            self.assertEqual(run.call_args.args[0][0], "/home/linuxbrew/.linuxbrew/bin/gh")

    def test_gh_backend_rejects_other_hostname_and_invalid_token(self) -> None:
        with self.assertRaises(ValueError):
            resolve_github_credential("GH_CLI", hostname="example.com")
        with patch("codex_wake.github_credentials.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "bad\ntoken"
            with self.assertRaises(ValueError):
                resolve_github_credential("GH_CLI")

    def test_new_source_and_binding_default_to_gh(self) -> None:
        parser = build_parser()
        source = parser.parse_args([
            "github-ci", "source", "configure", "--source", "sample",
            "--repository", "Example/repo", "--repository-id", "1",
            "--workflow-id", "2", "--ref", "refs/heads/main",
            "--conclusion", "success", "--enabled",
        ])
        binding = parser.parse_args([
            "github-webhook", "binding", "configure", "--source", "sample",
            "--installation-id", "sample", "--repository", "Example/repo",
            "--repository-id", "1", "--callback-url", "https://example.com/github/webhook",
        ])
        self.assertEqual(source.credential_ref, "GH_CLI")
        self.assertEqual(binding.provider_credential_ref, "GH_CLI")

    def test_gh_source_requires_only_hmac_environment_reference(self) -> None:
        listener = WebhookListenerConfig(source_instance="sample", secret_ref="HMAC_SECRET")
        source = replace(polling_config(evidence_mode="positive_only"), credential_ref="GH_CLI")
        self.assertEqual(required_secret_references(listener, source), frozenset({"HMAC_SECRET"}))
