from __future__ import annotations

from dataclasses import replace
import json
import os
import unittest

from codex_wake.github_webhook_admin import GitHubWebhookAdmin, GitHubWebhookAdminError
from codex_wake.managed_webhooks import (
    InventoryClass,
    ManagedWebhookBinding,
    OperationKind,
    OperationReceipt,
    OperationState,
)


def binding(**changes: object) -> ManagedWebhookBinding:
    values: dict[str, object] = {
        "owner_id": "wake-owner-1",
        "installation_id": "wake-install-1",
        "canonical_root": "/var/lib/codex-wake",
        "owner_uid": os.getuid(),
        "provider_host": "api.github.com",
        "source_instance": "github-workflow",
        "repository": "octo/example",
        "repository_id": 42,
        "callback_url": "https://hooks.example.test/github/webhook",
        "events": ("workflow_run",),
        "service_id": "codex-wake-github-webhook-github-workflow.service",
        "executable_id": "codex-wake-github-webhook",
        "provider_credential_ref": "CODEX_WAKE_GITHUB_ADMIN_TOKEN",
        "secret_generation": 1,
    }
    values.update(changes)
    return ManagedWebhookBinding(**values)


def owned(item: ManagedWebhookBinding, hook_id: int = 9) -> ManagedWebhookBinding:
    receipt = OperationReceipt(
        operation_id="op_1_create", operation=OperationKind.CREATE, state=OperationState.SUCCEEDED,
        generation=1, inventory=InventoryClass.EXACT, hook_id=hook_id, code="READBACK_EXACT",
    )
    return replace(item, provider_hook_id=hook_id, receipts=(receipt,))


def hook(hook_id: int = 9, **changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": hook_id,
        "name": "web",
        "active": True,
        "events": ["workflow_run"],
        "config": {
            "url": "https://hooks.example.test/github/webhook",
            "content_type": "json",
            "insecure_ssl": "0",
        },
    }
    value.update(changes)
    return value


class Response:
    def __init__(self, body: object = b"", status: int = 200) -> None:
        self.status = status
        self.body = body if type(body) is bytes else json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.closed = False

    def read1(self, limit: int) -> bytes:
        chunk, self.body = self.body[:limit], self.body[limit:]
        return chunk

    def close(self) -> None:
        self.closed = True


class FakeHTTPS:
    def __init__(
        self,
        responses: list[Response | Exception],
        *,
        repository: object = None,
    ) -> None:
        self.responses = list(responses)
        self.repository = repository if repository is not None else {"id": 42, "full_name": "octo/example"}
        self.origins: list[tuple[str, float]] = []
        self.requests: list[tuple[str, str, bytes | None, dict[str, str]]] = []
        self.closes = 0

    def __call__(self, host: str, timeout: float) -> "FakeHTTPS":
        self.origins.append((host, timeout))
        return self

    def request(self, method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None) -> None:
        self.requests.append((method, path, body, dict(headers or {})))

    def getresponse(self) -> Response:
        if self.requests[-1][0:2] == ("GET", "/repos/octo/example"):
            return Response(self.repository)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def close(self) -> None:
        self.closes += 1


class GitHubWebhookAdminTests(unittest.TestCase):
    def make_admin(self, http: FakeHTTPS, item: ManagedWebhookBinding | None = None, **changes: object) -> GitHubWebhookAdmin:
        return GitHubWebhookAdmin(
            item or binding(), credential_resolver=lambda ref: "provider-token",
            secret_generation_resolver=lambda generation: "resolved-hook-secret",
            connection_factory=http, monotonic=lambda: 100.0, **changes,
        )

    def assert_common_headers(self, headers: dict[str, str], *, body: bool = False) -> None:
        self.assertEqual(headers["Authorization"], "Bearer provider-token")
        self.assertEqual(headers["Accept"], "application/vnd.github+json")
        self.assertEqual(headers["X-GitHub-Api-Version"], "2026-03-10")
        self.assertEqual(headers["User-Agent"], "codex-wake-github-webhook-admin")
        self.assertEqual(headers.get("Content-Type"), "application/json" if body else None)

    def test_list_get_create_and_update_use_exact_repository_contract(self) -> None:
        item = binding()
        http = FakeHTTPS([Response([hook(1)]), Response(hook(1)), Response(hook(17), status=201), Response(hook(9))])
        admin = self.make_admin(http, item)

        self.assertEqual(admin.list_hooks(repository_id=42)[0].hook_id, 1)
        self.assertEqual(admin.get_hook(repository_id=42, hook_id=1).hook_id, 1)
        self.assertEqual(admin.create_hook(item).hook_id, 17)
        self.assertEqual(admin.update_hook(hook_id=9, binding=owned(item)).hook_id, 9)

        self.assertEqual(
            [(method, path) for method, path, _, _ in http.requests],
            [
                ("GET", "/repos/octo/example"),
                ("GET", "/repos/octo/example/hooks?per_page=100&page=1"),
                ("GET", "/repos/octo/example"),
                ("GET", "/repos/octo/example/hooks/1"),
                ("GET", "/repos/octo/example"),
                ("POST", "/repos/octo/example/hooks"),
                ("GET", "/repos/octo/example"),
                ("PATCH", "/repos/octo/example/hooks/9"),
            ],
        )
        for method, _, body, headers in http.requests:
            self.assert_common_headers(headers, body=method in {"POST", "PATCH"})
        expected = {
            "name": "web", "active": True, "events": ["workflow_run"],
            "config": {
                "url": "https://hooks.example.test/github/webhook", "content_type": "json",
                "insecure_ssl": "0", "secret": "resolved-hook-secret",
            },
        }
        writes = [body for method, _, body, _ in http.requests if method in {"POST", "PATCH"}]
        self.assertEqual(json.loads(writes[0]), expected)
        self.assertEqual(json.loads(writes[1]), expected)
        self.assertEqual(http.origins, [("api.github.com", 10.0)] * 8)
        self.assertEqual(http.closes, 8)

    def test_get_404_is_none_and_does_not_follow_or_retry(self) -> None:
        http = FakeHTTPS([Response({}, status=404)])
        self.assertIsNone(self.make_admin(http).get_hook(repository_id=42, hook_id=9))
        self.assertEqual(
            [(method, path) for method, path, _, _ in http.requests],
            [("GET", "/repos/octo/example"), ("GET", "/repos/octo/example/hooks/9")],
        )

        mismatched = FakeHTTPS([Response(hook(10))])
        with self.assertRaises(GitHubWebhookAdminError):
            self.make_admin(mismatched).get_hook(repository_id=42, hook_id=9)

    def test_rate_limit_or_redirect_fails_closed_without_a_retry(self) -> None:
        for status in (403, 429, 302):
            with self.subTest(status=status):
                http = FakeHTTPS([Response({"message": "token=provider-token"}, status=status)])
                with self.assertRaisesRegex(GitHubWebhookAdminError, "administration is unavailable") as raised:
                    self.make_admin(http).list_hooks(repository_id=42)
                self.assertNotIn("provider-token", str(raised.exception))
                self.assertEqual(len(http.requests), 2)

    def test_write_is_one_request_and_failure_never_retries_or_leaks_secrets(self) -> None:
        http = FakeHTTPS([Response({"message": "secret=resolved-hook-secret token=provider-token"}, status=500)])
        admin = self.make_admin(http)
        with self.assertRaises(GitHubWebhookAdminError) as raised:
            admin.create_hook(binding())
        self.assertEqual(len(http.requests), 2)
        self.assertNotIn("provider-token", str(raised.exception))
        self.assertNotIn("resolved-hook-secret", str(raised.exception))
        self.assertNotIn("provider-token", repr(admin))
        self.assertNotIn("resolved-hook-secret", repr(admin))
        self.assertNotIn("CODEX_WAKE_GITHUB_ADMIN_TOKEN", repr(admin))

    def test_provider_event_order_is_normalized_before_comparison(self) -> None:
        item = binding(events=("push", "workflow_run"))
        http = FakeHTTPS([Response([hook(events=["workflow_run", "push"])])])
        observed = self.make_admin(http, item).list_hooks(repository_id=42)
        self.assertEqual(observed[0].events, ("push", "workflow_run"))

    def test_binding_and_repository_mismatch_fail_before_credentials_or_network(self) -> None:
        http = FakeHTTPS([])
        admin = self.make_admin(http)
        with self.assertRaisesRegex(ValueError, "repository is invalid"):
            admin.list_hooks(repository_id=43)
        with self.assertRaisesRegex(ValueError, "binding is invalid"):
            admin.create_hook(binding(repository="elsewhere/example"))
        with self.assertRaisesRegex(ValueError, "configuration is invalid"):
            self.make_admin(http, binding(provider_host="attacker.example"))
        self.assertEqual(http.requests, [])

        unattested = FakeHTTPS([], repository={"id": 43, "full_name": "octo/example"})
        with self.assertRaises(GitHubWebhookAdminError):
            self.make_admin(unattested).create_hook(binding())
        self.assertEqual(
            [(method, path) for method, path, _, _ in unattested.requests],
            [("GET", "/repos/octo/example")],
        )

    def test_nonconforming_foreign_hook_remains_bounded_inventory(self) -> None:
        foreign = hook(
            77,
            events=["*"],
            config={
                "url": "http://foreign.example.test/hook",
                "content_type": "form",
                "insecure_ssl": "1",
            },
        )
        observed = self.make_admin(FakeHTTPS([Response([foreign])])).list_hooks(repository_id=42)
        self.assertEqual(observed[0].events, ("*",))
        self.assertEqual(observed[0].content_type, "form")
        self.assertTrue(observed[0].insecure_ssl)

        many_events = [f"event_{index}" for index in range(32)]
        observed = self.make_admin(FakeHTTPS([Response([hook(78, events=many_events)])])).list_hooks(repository_id=42)
        self.assertEqual(len(observed[0].events), 32)

    def test_paginated_inventory_is_bounded_and_duplicate_ids_fail_closed(self) -> None:
        first = [hook(index) for index in range(1, 101)]
        http = FakeHTTPS([Response(first), Response([hook(101)])])
        hooks = self.make_admin(http).list_hooks(repository_id=42)
        self.assertEqual((len(hooks), hooks[-1].hook_id), (101, 101))
        self.assertEqual(len(http.requests), 3)

        duplicate = FakeHTTPS([Response([hook(1), hook(1)])])
        with self.assertRaises(GitHubWebhookAdminError):
            self.make_admin(duplicate).list_hooks(repository_id=42)
        self.assertEqual(len(duplicate.requests), 2)

    def test_page_and_request_budgets_fail_before_an_extra_request(self) -> None:
        full = [hook(index) for index in range(1, 101)]
        http = FakeHTTPS([Response(full), Response(full)])
        with self.assertRaises(GitHubWebhookAdminError):
            self.make_admin(http, max_pages=1).list_hooks(repository_id=42)
        self.assertEqual(len(http.requests), 2)

        requests = FakeHTTPS([Response(full), Response([hook(101)])])
        with self.assertRaises(GitHubWebhookAdminError):
            self.make_admin(requests, max_requests=1).list_hooks(repository_id=42)
        self.assertEqual(len(requests.requests), 1)

    def test_malformed_duplicate_key_and_oversized_response_are_rejected_without_raw_body(self) -> None:
        malformed = FakeHTTPS([Response(b'[{"id":1,"id":2}]')])
        with self.assertRaises(GitHubWebhookAdminError) as raised:
            self.make_admin(malformed).list_hooks(repository_id=42)
        self.assertNotIn("id", str(raised.exception))

        oversized = FakeHTTPS([Response(b"x" * 65)])
        with self.assertRaises(GitHubWebhookAdminError):
            self.make_admin(oversized, max_response_bytes=64).list_hooks(repository_id=42)
        self.assertEqual(len(oversized.requests), 2)

    def test_deadline_fails_before_network_and_future_lifecycle_methods_are_exact(self) -> None:
        ticks = iter((0.0, 31.0))
        expired = FakeHTTPS([])
        admin = GitHubWebhookAdmin(
            binding(), credential_resolver=lambda ref: "provider-token",
            secret_generation_resolver=lambda generation: "resolved-hook-secret",
            connection_factory=expired, monotonic=lambda: next(ticks), deadline_seconds=30,
        )
        with self.assertRaises(GitHubWebhookAdminError):
            admin.list_hooks(repository_id=42)
        self.assertEqual(expired.requests, [])

        http = FakeHTTPS([Response(hook(9, active=False)), Response(b"", status=204), Response([
            {"id": 101, "event": "workflow_run", "status": "OK"},
        ])])
        admin = self.make_admin(http)
        self.assertFalse(admin.disable_hook(repository_id=42, hook_id=9).active)
        self.assertIsNone(admin.delete_hook(repository_id=42, hook_id=9))
        self.assertEqual(admin.list_deliveries(repository_id=42, hook_id=9)[0].delivery_id, 101)
        self.assertEqual(
            [(method, path) for method, path, _, _ in http.requests],
            [
                ("GET", "/repos/octo/example"),
                ("PATCH", "/repos/octo/example/hooks/9"),
                ("GET", "/repos/octo/example"),
                ("DELETE", "/repos/octo/example/hooks/9"),
                ("GET", "/repos/octo/example"),
                ("GET", "/repos/octo/example/hooks/9/deliveries?per_page=100&page=1"),
            ],
        )
        self.assertEqual(
            json.loads(next(body for method, _, body, _ in http.requests if method == "PATCH")),
            {"active": False},
        )
