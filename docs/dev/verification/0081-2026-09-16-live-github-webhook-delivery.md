# Live GitHub webhook delivery verification

Date: 2026-09-16
Issues: `CochranResearchGroup/codex-wake#109`, `CochranResearchGroup/codex-wake#103`
Plans: 0070, 0081, and 0082
Result: ACCEPTED

## Accepted boundary

One fresh isolated runtime from corrected canonical commit
`27dedc00228c4ff99820dfa4b84e7895f62075a1` armed one dispatch-disabled wake
after a fresh source anchor. GitHub hook `680422493` targeted only
`https://codex-wake.ecochran.dyndns.org/github/webhook` with event
`workflow_run`, JSON content, TLS verification enabled, and a fresh owner-only
HMAC secret reference. The secret bytes were never printed or tracked.

Green docs-only PR #133, frozen at head
`f5b40697ac0fd0bfece665c8199e15135f6b3408` on base `27dedc0`, was squash-
merged once as `5f21ed1a3bf80804a95b4e26b5bb154071411b42`.
GitHub Actions run `35138287516`, attempt 1, completed successfully for workflow
`279450573`, event `push`, repository ID `1242753508`, branch `main`, and that
exact merge SHA.

Provider delivery `80e50480-b201-11f1-9387-9a306ef1c969` was the one completed
`workflow_run` delivery and returned HTTP 200. Earlier `requested` and
`in_progress` deliveries were rejected with 400 and were not redelivered. The
listener performed the authoritative run-attempt read and durably committed
occurrence `github:repository:1242753508:run:35138287516:attempt:1` with
verification method `github-run-attempt-read`.

## Convergence and dispatch separation

- Journal receipts: `0 -> 1` after webhook, then `1` after polling.
- Wake state: `pending -> firing_local` during the explicit no-dispatch poll.
- Hook create attempts: 1.
- Trigger merge attempts: 1.
- Delivery observations: 1.
- Hook delete attempts: 1.
- Redelivery attempts: 0.
- Dispatch calls: 0.
- Global installation, release, and ingress mutations: 0.

The accepted 200 and verified journal receipt independently prove HMAC
authentication and commit-before-ack at the application boundary. Polling did
not create a second occurrence.

## Cleanup and retained evidence

The exact hook was deleted once and the repository hook inventory read back as
empty. Runtime cleanup uninstalled the exact user service, retired both
successor secret artifacts, verified the unrelated failed-unit boundary, and
passed the cleanup interlock. The successor root
`/home/ecochran76/.local/state/codex-wake/qualification/p53-c6-live-github-_et4xjiy`
was removed.

Fresh readback reports the unit inactive/not-found, MainPID `0`, no matching
listener process, and no listener on `127.0.0.1:8820`. The predecessor failure
root remains owner-only at
`/home/ecochran76/.local/state/codex-wake/qualification/p53-c6-live-github-1ndna5z1`;
both of its secret artifacts remain absent.

The sanitized external successor receipt is retained at
`/home/ecochran76/.local/state/codex-wake/qualification-receipts/p53-c7-live-github-successor.json`
with SHA-256
`06326bf8e561f445ca4ee7ded088b7a11a101e180c6ec75f60be89f155a7b385`.
It records lifecycle counters create/trigger/delete as `1/1/1`, redelivery and
dispatch as `0/0`, delivery and convergence identities, and `cleanup.safe=true`
with successor-root removal. Secret-related receipt fields are intentionally
redacted.

The sanitized GitHub coordination-ledger observation is issue comment
`5703125171`:
`https://github.com/CochranResearchGroup/codex-wake/issues/109#issuecomment-5703125171`.
It preserves the provider delivery status/action, authoritative verification
method, convergence counters, cleanup readback, and receipt hash without a raw
payload or secret.

## Correction and validation custody

The predecessor attempt stopped before provider effects and consumed no hook or
trigger counter. Corrective PR #132 passed both Python 3.11 and 3.12 hosted
release gates and merged as `27dedc0`. Its focused tests passed 24/24,
comprehensive Python passed 565/565, OpenClaw plugin tests passed 12/12, and
closed-world review accepted both reproduced adapter defects plus 15 negative
cleanup-census probes.

Before the successor effect, independent provider-free verification installed
the exact wheel with `--no-deps` in a fresh venv lacking `dbus-next` and launched
the exact `codex-wake` and `codex-waked` entry points. This established that the
bounded GitHub path does not eagerly require the lazily imported systemd-signal
dependency. PR #133 passed both hosted release gates before its controlled
merge. The final closeout PR must pass those gates before issues #109 and #103
close from canonical-main readback.
