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

**Message receipt**:
An attributable record of retrieval, acceptance or another message outcome.
Reading records retrieval; it does not accept the work.

**Work claim**:
The exact recipient's explicit acceptance of processing a message. Only a newly
accepted claim permits that worker to begin; it grants no additional task rights.
Successful or failed processing requires this claim before terminal acknowledgment.

**Receipt publication**:
Making an existing receipt available to observers. Publication is durable journal
work and does not itself require the recipient's tab to remain open.
