# Live GitHub successor trigger preflight

State: ARMED_NOT_EXECUTED
Issue: #109
Plan: `docs/dev/plans/0082-2026-09-16-live-github-adapter-successor.md`
Base: `main`
Merge method: `squash`

## Purpose

This docs-only change is the fresh, single `main` push candidate for a
successor live GitHub webhook qualification. Its pull request must be green and
its number, head SHA, base SHA, file scope, and squash method frozen before a
new exact lifecycle authorization gate. Opening and validating it authorizes no
runtime, secret, provider, merge, delivery, cleanup, or dispatch effect.

## Corrected canonical boundary

- Provider-free runner PR #130 merged as
  `858ccdb339c4acb45f3d4db7e2b33fd6f54a3a12`.
- Plan 0081 consumed one runtime establishment and cleanup attempt, stopped
  before provider effects, retired its secret, and retained its owner-only root
  and receipt. Trigger PR #131 closed unmerged.
- Corrective PR #132 merged as
  `27dedc00228c4ff99820dfa4b84e7895f62075a1` after 24 focused tests, 565
  comprehensive Python tests, 12 plugin tests, both planning audits, independent
  closed-world review, and hosted Python 3.11/3.12 release gates passed.
- The correction isolates wheel installation from caller Python paths, proves
  exact venv distribution/entry-point custody, and accepts only semantically
  valid systemd absent-unit tuples including the observed rc 4 form.

## Pre-effect boundary

- GitHub repository hook inventory must remain empty.
- The exact frozen source, service unit, listener port, wake, and journal must
  remain absent; the predecessor never created them.
- A fresh successor root, receipt, HMAC secret, wake, journal, and delivery are
  required. No predecessor counter or secret may be reset or reused.
- The retained predecessor root remains owner-only and both of its secret
  artifacts remain absent.
- The accepted Cooper/bastion route remains unchanged.

## Exact post-gate use

Only after a new explicit authorization, establish one fresh isolated
no-dispatch runtime, create one exact `workflow_run` repository hook, and
squash-merge this already-green docs-only pull request once. Bind acceptance
to the resulting `main` merge SHA and one post-anchor completed push run.
Redelivery and retries remain forbidden. Delete the exact returned hook, retire
the successor secret, and clean the successor runtime after observation.
Retain the predecessor failure receipt/root and the accepted ingress route.
