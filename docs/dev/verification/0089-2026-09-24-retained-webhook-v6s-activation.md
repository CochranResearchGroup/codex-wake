# Retained webhook v6-sentinel activation

Date: 2026-09-24
Issue: #141
Plan: `docs/dev/plans/0093-2026-09-24-recurring-poll-sentinel-rollout-successor.md`
Outcome: RETAINED_ACTIVE_CANONICAL_READBACK_REQUIRED

## Frozen candidate and qualification

- Canonical rollout candidate: `450834c92d8865d2e0b551182cc2b8e3bf4903de`.
- Product correction: `f2a4c3ceda4c86ce8befe1e392e79ab68c8be116`.
- Wheel SHA-256:
  `1324221594d2d1ab085452919baeb124fcde860412e0832b31b9a671c6ae5a0a`.
- Qualification passed 22 focused polling tests, 689 comprehensive Python
  tests, 12 provider-free plugin tests, isolated-wheel smoke, and hosted Python
  3.11 and 3.12 gates.
- A provider-free public-interface fixture proved two polling cycles with the
  success target firing, the failure sentinel pending, and zero dispatch.

## Rehearsal and retained occurrence

Receipt 0088 records accepted rehearsal hook `685365102`, signed completed
delivery, two distinct polling timestamps, sentinel continuity, and exact
cleanup. The rehearsal sentinel is cancelled; its hook is deleted; its units,
listener, and secret environment are absent.

Retained hook `685366419` is active at generation 2 with desired fingerprint
`62006d5e1a52dc297f5c139e972eaa378b734c5f8a4a940323a628f11816f2cf`.
PR #164 squash-merged as canonical
`579d2761391580ed7fc874a16154736004e29c6c`; main workflow run `36092196814`
passed both hosted gates. Signed completed delivery `3844658156756050000`
returned HTTP 200. Polling succeeded at `2026-09-25T03:54:40Z` and
`2026-09-25T03:57:57Z`. Success target
`wake_27c4255f5aea45c891914ac20e71d7f6` is firing, failure sentinel
`wake_51d55e2cf37c40c790ba5d37a8cbd0c9` remains pending, and dispatch is zero.

## Restart and ingress

The one authorized retained listener restart occurred at
`2026-09-25T03:59:35Z`. Its main PID changed from `80441` to `751`; the exact
unit remained active, running, and enabled, and the listener remained bound
only to `127.0.0.1:8820`. The dispatch-disabled poller remained active and
enabled.

Correctly shaped requests with an invalid signature returned HTTP 401 through
raw loopback, `codex-wake.localhost`, the Cooper Host route, bastion HTTPS, and
public certificate-verifying HTTPS. No ingress mutation occurred.

## Final gate

The final closeout PR supplies a normal `main` GitHub Actions delivery without
a manual workflow trigger or redelivery. Its merge commit and resulting run
cannot be named truthfully in pre-merge content. Issue closure is therefore
withheld until the owner-only activation manifest and issue readback record
that exact signed delivery, three fresh recurring health samples at the current
generation, and one retained-sentinel cancellation. The hook, listener,
dispatch-disabled poller, success occurrence, and durable repository-scoped
read credential remain retained.

The final bounded counters at canonical-readback entry are two provider
creates, one rehearsal disable, one rehearsal delete, zero provider updates,
zero redeliveries, one explicit workflow rerun, one rehearsal service
install/start and stop/uninstall, one retained service install/start, one
retained listener restart, one of two sentinel cancellations, and zero
dispatch. The closeout merge and second sentinel cancellation consume their
remaining ceilings only after their exact postconditions are observable.
