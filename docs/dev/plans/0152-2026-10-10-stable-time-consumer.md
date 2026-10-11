# Plan 0152 | StableTime consumer rollout

State: CLOSED

## Current State

Installed into release 0.13.0-stable-time-01; eight workers active and a qualified service response retained in ../wsl-time/docs/dev/evidence/consumer-rollout-01. 29 focused tests pass. Operator recovery deferral preserved.

Operator authorizes live rollout to WSL timing consumers and defers recovery acceptance. Primary agent implements the existing network_time_decision seam, with authenticated StableTime selected by explicit client config. Focused native-network, network wake and inspection tests pass; installation remains.

## Scope

Preserve record schemas, source polling policy, old unconfigured provider and unrelated dirty work. Configured failures hold without fallback. Native Windows QPC bounds transport handoff; no guest clock projection. Private runtime selector ~/.config/codex-wake/stable-time-client.json opts this workstation into the service; CODEX_WAKE_STABLE_TIME_CONFIG overrides it. Scope includes installed release, command and existing supervisor callers. No clock setting, sleep, restart of Windows authority, mailbox migration, commits or remote push. Strict service availability remains disclosed. Stop at live installed service read and focused consumer verification. Standards and Spec review run serially in primary context. Recovery acceptance remains deferred.
