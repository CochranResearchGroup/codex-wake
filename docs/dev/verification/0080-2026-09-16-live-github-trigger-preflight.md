# Live GitHub trigger preflight

State: ARMED_NOT_EXECUTED
Issue: #109
Plan: `docs/dev/plans/0081-2026-09-16-live-github-webhook-delivery.md`
Base: `main`
Merge method: `squash`

## Purpose

This docs-only change is the single bounded `main` push candidate for the
P53-C6 live GitHub webhook qualification. Its pull request must be green and
its number, head SHA, base, file scope, and squash method must be frozen before
the exact lifecycle authorization gate. Merging it is a separate live trigger
effect and is not authorized by opening or validating the pull request.

## Canonical runner boundary

- Provider-free runner PR #130 squash-merged as
  `858ccdb339c4acb45f3d4db7e2b33fd6f54a3a12`.
- Closed-world review accepted lifecycle-ledger preservation, partial-secret
  retirement, systemd-query failure handling, and exact commit/tree wheel
  custody at checkpoint `e24afe3f88ddde501297f05b83f8300a93f2d8eb`.
- Local validation passed 22 focused tests, 563 comprehensive Python tests,
  12 OpenClaw plugin tests, compilation, diff hygiene, and active/goal planning
  audits. Hosted Python 3.11 and 3.12 release gates passed on PR #130.

## Pre-effect state

- No #109 GitHub repository webhook has been created.
- No #109 isolated runtime or user service has been established.
- No #109 HMAC secret has been provisioned.
- No trigger merge, webhook redelivery, live delivery observation, global
  install, release, ingress mutation, or live dispatch has occurred.
- The accepted exact Cooper/bastion route remains retained and unchanged.

## Exact post-gate use

Only after explicit authorization, establish the isolated no-dispatch runtime,
create one exact `workflow_run` repository hook, and then squash-merge this
already-green docs-only pull request once. Bind acceptance to the resulting
`main` merge SHA and one post-anchor completed push run. Redelivery and retry
remain forbidden. Delete the exact returned hook, retire secret material, and
clean the isolated runtime after observation; retain only the accepted ingress
route.
