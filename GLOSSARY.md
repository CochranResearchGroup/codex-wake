# Codex Wake

Codex Wake records wake requests and agent messages whose deadlines must remain meaningful across outages and restarts.

## Language

**Wake deadline**:
The point in time when a registered wake becomes due, including time spent asleep.

**Message expiration**:
The deadline after which a message is no longer eligible for delivery, including time spent asleep.

**Trusted time**:
A bounded estimate of current time accepted under the configured source-selection rules.

**Time uncertainty**:
The condition in which available evidence cannot establish whether a deadline has passed.
