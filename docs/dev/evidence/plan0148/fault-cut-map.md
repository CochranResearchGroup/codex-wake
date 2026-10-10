# Ticket0148 fault-cut evidence map

All52 exact installed test results bind to actual test source hashes in private
plan0148/f1-case-manifest.json. Current package82-file parity is ticket0147
identity.json; candidate0.12.0-d5896eb. Source unchanged since integration85d9f73.
No rerun or new fault effect; this records checked evidence, not extra acceptance.

| Named fault/control | Public test | Source locator |
| --- | --- | --- |
| sqlite busy refuses admission then original intent can retry | tests.test_a2a_mailbox_faults.MailboxFaultTests.test_sqlite_busy_refuses_admission_then_original_intent_can_retry | tests/test_a2a_mailbox_faults.py:43 |
| disk full before commit rolls back all admission effects | tests.test_a2a_mailbox_faults.MailboxFaultTests.test_disk_full_before_commit_rolls_back_all_admission_effects | tests/test_a2a_mailbox_faults.py:56 |
| corrupt store refused without recreating or resetting bytes | tests.test_a2a_mailbox_faults.MailboxFaultTests.test_corrupt_store_refused_without_recreating_or_resetting_bytes | tests/test_a2a_mailbox_faults.py:76 |
| revoked authenticated actor has no mailbox effects | tests.test_a2a_mailbox_faults.MailboxFaultTests.test_revoked_authenticated_actor_has_no_mailbox_effects | tests/test_a2a_mailbox_faults.py:87 |
| concurrent distinct sends have unique contiguous fifo slots | tests.test_a2a_mailbox_faults.MailboxFaultTests.test_concurrent_distinct_sends_have_unique_contiguous_fifo_slots | tests/test_a2a_mailbox_faults.py:108 |
| cancellation and first claim race have one serialized winner | tests.test_a2a_mailbox_faults.MailboxFaultTests.test_cancellation_and_first_claim_race_have_one_serialized_winner | tests/test_a2a_mailbox_faults.py:124 |
| simultaneous identical terminal ack has one durable receipt | tests.test_a2a_mailbox_faults.MailboxFaultTests.test_simultaneous_identical_terminal_ack_has_one_durable_receipt | tests/test_a2a_mailbox_faults.py:153 |
| publication before journal cut reconciles identical projection | tests.test_a2a_scheduler_faults.SchedulerFaultTests.test_publication_before_journal_cut_reconciles_identical_projection | tests/test_a2a_scheduler_faults.py:56 |
| stale published projection after cancel has no dispatch authority | tests.test_a2a_scheduler_faults.SchedulerFaultTests.test_stale_published_projection_after_cancel_has_no_dispatch_authority | tests/test_a2a_scheduler_faults.py:85 |
| hourly limit counts actual attempts and reopens after window | tests.test_a2a_scheduler_faults.SchedulerFaultTests.test_hourly_limit_counts_actual_attempts_and_reopens_after_window | tests/test_a2a_scheduler_faults.py:100 |
| other owner cannot use valid lease to claim or finish | tests.test_a2a_scheduler_faults.SchedulerFaultTests.test_other_owner_cannot_use_valid_lease_to_claim_or_finish | tests/test_a2a_scheduler_faults.py:120 |
| sender revocation after publication blocks dispatch | tests.test_a2a_scheduler_faults.SchedulerFaultTests.test_sender_revocation_after_publication_blocks_dispatch | tests/test_a2a_scheduler_faults.py:149 |
| recipient revocation after publication blocks dispatch | tests.test_a2a_scheduler_faults.SchedulerFaultTests.test_recipient_revocation_after_publication_blocks_dispatch | tests/test_a2a_scheduler_faults.py:152 |
| sql failure before claim commit rolls back attempt and receipts | tests.test_a2a_scheduler_faults.SchedulerFaultTests.test_sql_failure_before_claim_commit_rolls_back_attempt_and_receipts | tests/test_a2a_scheduler_faults.py:155 |
| scanning respects bound and fifo without consuming attempts | tests.test_a2a_scheduler_faults.SchedulerFaultTests.test_scanning_respects_bound_and_fifo_without_consuming_attempts | tests/test_a2a_scheduler_faults.py:183 |
| versioned snapshot preserves identity and verifies read only | tests.test_a2a_backup.BackupTests.test_versioned_snapshot_preserves_identity_and_verifies_read_only | tests/test_a2a_backup.py:24 |
| paused and independent operator authority required | tests.test_a2a_backup.BackupTests.test_paused_and_independent_operator_authority_required | tests/test_a2a_backup.py:35 |
| wal snapshot preserves message receipt and uncertain notification | tests.test_a2a_backup.BackupTests.test_wal_snapshot_preserves_message_receipt_and_uncertain_notification | tests/test_a2a_backup.py:48 |
| private paths symlinks and existing snapshot refused | tests.test_a2a_backup.BackupTests.test_private_paths_symlinks_and_existing_snapshot_refused | tests/test_a2a_backup.py:75 |
| incomplete copy preserves request and refuses verification | tests.test_a2a_backup.BackupTests.test_incomplete_copy_preserves_request_and_refuses_verification | tests/test_a2a_backup.py:95 |
| completion audit failure preserves verified backup | tests.test_a2a_backup.BackupTests.test_completion_audit_failure_preserves_verified_backup | tests/test_a2a_backup.py:107 |
| readonly verification does not change source or backup | tests.test_a2a_backup.BackupTests.test_readonly_verification_does_not_change_source_or_backup | tests/test_a2a_backup.py:120 |
| corruption unknown version and different bus refused | tests.test_a2a_backup.BackupTests.test_corruption_unknown_version_and_different_bus_refused | tests/test_a2a_backup.py:132 |
| copy deadline preserves partial evidence and request | tests.test_a2a_backup.BackupTests.test_copy_deadline_preserves_partial_evidence_and_request | tests/test_a2a_backup.py:158 |
| old actor authority is not activated by verification | tests.test_a2a_backup.BackupTests.test_old_actor_authority_is_not_activated_by_verification | tests/test_a2a_backup.py:167 |
| quiesced restore preserves same identity and later audit | tests.test_a2a_backup.BackupTests.test_quiesced_restore_preserves_same_identity_and_later_audit | tests/test_a2a_backup.py:183 |
| restore refuses new actor authority without reviving snapshot | tests.test_a2a_backup.BackupTests.test_restore_refuses_new_actor_authority_without_reviving_snapshot | tests/test_a2a_backup.py:196 |
| restore refuses concurrent participating connection | tests.test_a2a_backup.BackupTests.test_restore_refuses_concurrent_participating_connection | tests/test_a2a_backup.py:213 |
| new connections refuse during exclusive lifecycle window | tests.test_a2a_backup.BackupTests.test_new_connections_refuse_during_exclusive_lifecycle_window | tests/test_a2a_backup.py:222 |
| restore completion failure preserves request stage and pause | tests.test_a2a_backup.BackupTests.test_restore_completion_failure_preserves_request_stage_and_pause | tests/test_a2a_backup.py:230 |
| restore copy interruption preserves canonical and snapshot | tests.test_a2a_backup.BackupTests.test_restore_copy_interruption_preserves_canonical_and_snapshot | tests/test_a2a_backup.py:249 |
| restore refuses new recipient receipt and preserves outcome | tests.test_a2a_backup.BackupTests.test_restore_refuses_new_recipient_receipt_and_preserves_outcome | tests/test_a2a_backup.py:278 |
| damaged source is quarantined and recovers under fresh held authority | tests.test_a2a_recovery.RecoveryTests.test_damaged_source_is_quarantined_and_recovers_under_fresh_held_authority | tests/test_a2a_recovery.py:27 |
| wrong commitment operator and gap refuse without source effect | tests.test_a2a_recovery.RecoveryTests.test_wrong_commitment_operator_and_gap_refuse_without_source_effect | tests/test_a2a_recovery.py:45 |
| fresh authority hold and old actor history | tests.test_a2a_recovery.RecoveryTests.test_fresh_authority_hold_and_old_actor_history | tests/test_a2a_recovery.py:59 |
| reader fences recovery | tests.test_a2a_recovery.RecoveryTests.test_reader_fences_recovery | tests/test_a2a_recovery.py:103 |
| quarantine cut is reconciled | tests.test_a2a_recovery.RecoveryTests.test_quarantine_cut_is_reconciled | tests/test_a2a_recovery.py:139 |
| activation cut is reconciled | tests.test_a2a_recovery.RecoveryTests.test_activation_cut_is_reconciled | tests/test_a2a_recovery.py:142 |
| authority publication cut is reconciled | tests.test_a2a_recovery.RecoveryTests.test_authority_publication_cut_is_reconciled | tests/test_a2a_recovery.py:145 |
| completion receipt cut is reconciled | tests.test_a2a_recovery.RecoveryTests.test_completion_receipt_cut_is_reconciled | tests/test_a2a_recovery.py:148 |
| changed quarantined bytes refuse reconciliation | tests.test_a2a_recovery.RecoveryTests.test_changed_quarantined_bytes_refuse_reconciliation | tests/test_a2a_recovery.py:162 |
| malformed intent blocks readers and is not discarded | tests.test_a2a_recovery.RecoveryTests.test_malformed_intent_blocks_readers_and_is_not_discarded | tests/test_a2a_recovery.py:181 |
| corrupt snapshot refuses before source quarantine | tests.test_a2a_recovery.RecoveryTests.test_corrupt_snapshot_refuses_before_source_quarantine | tests/test_a2a_recovery.py:194 |
| deliberate unknown disposition releases only into paused fresh authority | tests.test_recovery_disposition.RecoveryDispositionTests.test_deliberate_unknown_disposition_releases_only_into_paused_fresh_authority | tests/test_recovery_disposition.py:70 |
| fresh authority cannot process or dispatch snapshot history | tests.test_recovery_disposition.RecoveryDispositionTests.test_fresh_authority_cannot_process_or_dispatch_snapshot_history | tests/test_recovery_disposition.py:94 |
| lost disposition response reconciles original key without second effect | tests.test_recovery_disposition.RecoveryDispositionTests.test_lost_disposition_response_reconciles_original_key_without_second_effect | tests/test_recovery_disposition.py:129 |
| release refuses a reintroduced legacy notification | tests.test_recovery_disposition.RecoveryDispositionTests.test_release_refuses_a_reintroduced_legacy_notification | tests/test_recovery_disposition.py:152 |
| release reconciliation returns the original release receipt | tests.test_recovery_disposition.RecoveryDispositionTests.test_release_reconciliation_returns_the_original_release_receipt | tests/test_recovery_disposition.py:165 |
| storage failure before disposition commit keeps the original hold | tests.test_recovery_disposition.RecoveryDispositionTests.test_storage_failure_before_disposition_commit_keeps_the_original_hold | tests/test_recovery_disposition.py:175 |
| corrupted legacy boundary cannot enable snapshot processing | tests.test_recovery_disposition.RecoveryDispositionTests.test_corrupted_legacy_boundary_cannot_enable_snapshot_processing | tests/test_recovery_disposition.py:193 |
| later recovery epoch has its own disposition and release | tests.test_recovery_disposition.RecoveryDispositionTests.test_later_recovery_epoch_has_its_own_disposition_and_release | tests/test_recovery_disposition.py:204 |
| unreceipted hold clear is not a release | tests.test_recovery_disposition.RecoveryDispositionTests.test_unreceipted_hold_clear_is_not_a_release | tests/test_recovery_disposition.py:231 |

Provider-free controls protect transactions, scheduler claims, immutable receipts,
backup/restore and held recovery. Fresh-process CLI workload evidence is separate
in progress.md. None proves actual subagent ancestry or final release. Original
hosted evidence remains historical; hosted-CI waiting is explicitly waived for
this execution, never fabricated as a new hosted result.
