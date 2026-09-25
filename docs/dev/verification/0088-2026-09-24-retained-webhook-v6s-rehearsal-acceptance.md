# Retained webhook v6-sentinel rehearsal acceptance

Date: 2026-09-24
Issue: #141
Plan: `docs/dev/plans/0093-2026-09-24-recurring-poll-sentinel-rollout-successor.md`
Outcome: REHEARSAL_ACCEPTED_RETAINED_ACTIVE_AWAITING_NATURAL_OCCURRENCE

## Frozen candidate

- Canonical candidate: `450834c92d8865d2e0b551182cc2b8e3bf4903de`.
- Product correction: `f2a4c3ceda4c86ce8befe1e392e79ab68c8be116`.
- Wheel SHA-256:
  `1324221594d2d1ab085452919baeb124fcde860412e0832b31b9a671c6ae5a0a`.
- Canonical qualification retained 689 Python and 12 provider-free plugin
  passes plus both hosted Python gates.
- A provider-free public-interface sentinel fixture performed two successful
  source polls, left the success target firing and failure sentinel pending,
  and recorded zero dispatch/submission.

## Rehearsal acceptance

Fresh source `p54-c4-rehearsal-v6s` configured conclusions `success` and
`failure` atomically. Hook `685365102` was created before either service and
read back exact at active generation 2. The dispatch-disabled poller started,
then success target `wake_26095b7fe6184af4ad26093946eea6ec` and failure
sentinel `wake_b6ec8ded04a1471c81aeaaaefe50eb03` were armed before the
current-generation listener started. All five shaped unsigned ingress checks
returned HTTP 401.

The sole rerun of main workflow run `36091606672` became attempt 2 and passed
both hosted Python gates. Completed signed delivery `3844657377290756000`
returned HTTP 200. Successful polling evidence was recorded at
`2026-09-25T03:48:22Z` and `2026-09-25T03:50:17Z`; after the second timestamp,
the target was firing, the sentinel remained pending, provider delivery was
observed, polling fallback was ready, and dispatch/redelivery were zero.

The sentinel was explicitly cancelled. Exact cleanup then produced
`DISABLED_PROVEN` and `DELETED_PROVEN`, removed the listener and poller units,
freed port 8820, and retired only the rehearsal environment. Independent
readback showed zero hooks and zero v6-sentinel units.

## Retained pre-merge state

Fresh retained source `p54-c4-retained-v6s` also atomically permits success and
failure. Hook `685366419` was created with services absent and reads back exact
at active generation 2. Its dispatch-disabled poller, success target
`wake_27c4255f5aea45c891914ac20e71d7f6`, failure sentinel
`wake_51d55e2cf37c40c790ba5d37a8cbd0c9`, and current-generation listener are
active. This receipt's merge is the one planned natural main occurrence; no
manual retained workflow trigger or webhook redelivery is authorized.

The persistent repository-scoped read credential remains owner-only mode 0600
under the user configuration root. Administrative webhook authority is absent
from long-lived environments. Dispatch is zero.
