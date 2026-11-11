# Ticket541 cached inventory

Fixed base fa2363c24bf921ecf0bd8390739e96041e620e8f; integration feat/efficient-tab-observer.

Public regression red: Python3.12 unittest test_tab_observation reported missing
ObservationCache (two errors), then green after implementation. Added native
metadata enrichment coverage using the existing process/metadata system boundary.

One pane investigation feeds process recognition, exact metadata attachment and
trait projection. Existing layout observer uses the same cache. Tmux inventory
now retains title/path/tty rather than performing another inventory for metadata
matching. Cache is host-owned, memory-only, bounded512entries/default2seconds;
process birth and presentation generations fence reuse. Descendant births are
validated and expiry detects new descendants below a stable shell. Invalidation
is explicit for source loss/epoch replacement. Cached screen-derived values are
already redacted traits, never raw capture. Build digest cache remains stat-keyed.

Focused checks: Python3.11 and3.12 observation3 tests PASS, existing controller9
PASS, traits6 PASS, organization tests PASS (see execution ledger for final count).
Undefined-name lint PASS; diff whitespace PASS. Python environments rebuilt after
reboot at /tmp/wake216-py311 and py312; no hosted CI or runtime activation.

Remaining integration belongs to #544 (persistent owner/feed wiring), #545
(independent slow checks), #546 (projection) and #547 (installed resource proof).
