-- Frozen schema from main 94e17a68e655d9e54ead6001704dc0ef453eb933
CREATE TABLE mail_envelopes (global_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE NOT NULL, sender_key TEXT NOT NULL, recipient_key TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, created REAL NOT NULL,
                    expires REAL NOT NULL, envelope TEXT NOT NULL, in_reply_to TEXT REFERENCES mail_envelopes(message_id), UNIQUE(sender_key,idempotency_key));
CREATE TABLE mail_bodies (message_id TEXT PRIMARY KEY REFERENCES mail_envelopes(message_id), body TEXT NOT NULL);
CREATE TABLE mail_state (message_id TEXT PRIMARY KEY REFERENCES mail_envelopes(message_id),
                    recipient_seq INTEGER NOT NULL, admission TEXT NOT NULL, notification TEXT NOT NULL,
                    recipient TEXT NOT NULL, read_receipt TEXT, claim_receipt TEXT, claim_generation INTEGER,
                    terminal_receipt TEXT, terminal_at REAL);
CREATE TABLE mail_sequences (recipient_key TEXT PRIMARY KEY, next_sequence INTEGER NOT NULL);
CREATE TABLE mail_receipts (receipt_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id TEXT UNIQUE NOT NULL REFERENCES events(receipt_id),
                    message_id TEXT NOT NULL REFERENCES mail_envelopes(message_id), kind TEXT NOT NULL,
                    actor_key TEXT NOT NULL, created REAL NOT NULL, details TEXT NOT NULL);
CREATE TABLE mail_outbox (outbox_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    message_id TEXT NOT NULL REFERENCES mail_envelopes(message_id), receipt_id TEXT,
                    recipient_key TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
                    generation INTEGER NOT NULL DEFAULT 0, owner TEXT, lease_until REAL,
                    attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0);
CREATE TABLE mail_leases (name TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    generation INTEGER NOT NULL, lease_until REAL NOT NULL);
CREATE TABLE mail_attempts (attempt_id TEXT PRIMARY KEY, recipient_key TEXT NOT NULL,
                    message_ids TEXT NOT NULL, owner TEXT NOT NULL, generation INTEGER NOT NULL,
                    created REAL NOT NULL, state TEXT NOT NULL, evidence TEXT NOT NULL);
CREATE INDEX mail_recipient ON mail_envelopes(recipient_key,global_seq);
CREATE INDEX mail_sender ON mail_envelopes(sender_key,global_seq);
CREATE INDEX mail_replies ON mail_envelopes(in_reply_to,global_seq);
CREATE INDEX mail_pending ON mail_outbox(kind,status,next_attempt);
CREATE TRIGGER mail_envelope_immutable BEFORE UPDATE ON mail_envelopes BEGIN SELECT RAISE(ABORT,'immutable envelope'); END;
CREATE TRIGGER mail_body_immutable BEFORE UPDATE ON mail_bodies BEGIN SELECT RAISE(ABORT,'immutable body'); END;
CREATE TRIGGER mail_receipt_immutable BEFORE UPDATE ON mail_receipts BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
INSERT INTO meta VALUES ('mailbox_schema','1');
