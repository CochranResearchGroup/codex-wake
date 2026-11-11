# Ticket544 encoded publication repair

Source base:66145ef2. Owner worktree:/tmp/wake544. Product write surface:
`src/codex_wake/tab_monitor.py`, `tests/test_tab_monitor_publication.py`.

Public seam: `TabMonitor.publish_observation` and `tabs.monitor.status` prove
complete persisted rows, metadata-only caller preservation, lazy legacy callers,
strict metadata and total-document capacity safety. Installed-runtime acceptance
and performance thresholds remain the primary lane's separate qualification.

Trusted internal serializer supplies a strict stdlib JSON resource array from
the retained observer; no portable command accepts this callback. The publisher
encodes metadata strictly and shares the existing atomic byte writer. It does
not parse or re-encode the resource array. Formatting and routing still lazily
materialize rows through the existing loader.

Red command (Python3.11, `PYTHONPATH=src`):
`/tmp/wake216-py311/bin/python -m unittest tests.test_tab_monitor_publication.MonitorPublicationTests.test_encoded_publication_preserves_full_rows_without_materializing_frame`
Initially failed with `TypeError: TabMonitor.publish_observation() got an unexpected keyword argument 'resources_serializer'`.
First green attempt failed its status equality assertion: status adds
`monitor_freshness=stale` for an unavailable row. Corrected the independent
expected public result and added exact persisted-row equality. This was a test
expectation correction; no product freshness change.

Focused green selection, each with `PYTHONPATH=src`, both Python3.11 and3.12:
```
/tmp/wake216-py311/bin/python -m unittest tests.test_tab_monitor_publication.MonitorPublicationTests.test_encoded_publication_preserves_full_rows_without_materializing_frame tests.test_tab_monitor_publication.MonitorPublicationTests.test_encoded_publication_failure_preserves_previous_snapshot tests.test_tab_monitor_publication.MonitorPublicationTests.test_metadata_frames_are_materialized_only_for_actual_publication tests.test_tab_monitor_publication.MonitorPublicationTests.test_publisher_writes_changed_evidence_immediately_before_heartbeat
/tmp/wake216-py312/bin/python -m unittest tests.test_tab_monitor_publication.MonitorPublicationTests.test_encoded_publication_preserves_full_rows_without_materializing_frame tests.test_tab_monitor_publication.MonitorPublicationTests.test_encoded_publication_failure_preserves_previous_snapshot tests.test_tab_monitor_publication.MonitorPublicationTests.test_metadata_frames_are_materialized_only_for_actual_publication tests.test_tab_monitor_publication.MonitorPublicationTests.test_publisher_writes_changed_evidence_immediately_before_heartbeat
```
Both passed4 tests; logs alongside this receipt. The capacity test confirms rows
fit alone but total metadata plus rows exceeds1MiB, previous snapshot survives,
no temporary file remains, strict NaN metadata fails, and publication can then
succeed. This preservation invariant already passed after the first implementation;
no artificial red was manufactured for unchanged atomic-write behavior.

No hosted CI, deployment, production service changes, acceptance threshold
changes, broad code review or post-review TDD pass. Parent owns producer
`serialize_resources` integration and final daemon/routing check.

Memory disposition: not_durable — bounded worker implementation evidence is
retained here and reconciled into the parent issue/plan rather than independent
memory capture.

## Integrated producer qualification

The producer was integrated at2e41e942 and publication at0c457db4;7cf0e16a
handles minimal metadata correctly. The combined public monitor/observer/read
channel selection passes20tests onbothPython3.11/3.12 (13.010/12.986s).
The complete affected tab selection passes225tests perinterpreter (74.037/
70.656s). This includes the actual daemon full-row and enabled-routing cases.
Logs and selection boundaries: ../plan0216/validation-encoded-publication.
These checks resolve the initial agent checkpoint's producer dependency;
installed CPU and live-read-only acceptance remain separate pending gates.
