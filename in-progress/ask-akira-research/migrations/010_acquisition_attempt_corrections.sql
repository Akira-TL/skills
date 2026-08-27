ALTER TABLE acquisition_attempts
    ADD COLUMN validity_status TEXT NOT NULL DEFAULT 'active'
        CHECK (validity_status IN ('active', 'superseded'));

ALTER TABLE acquisition_attempts
    ADD COLUMN superseded_by_attempt_id INTEGER
        REFERENCES acquisition_attempts(id) ON DELETE SET NULL;

ALTER TABLE acquisition_attempts
    ADD COLUMN supersession_reason TEXT;

CREATE INDEX acquisition_attempts_validity_idx
    ON acquisition_attempts(candidate_id, paper_id, target_kind, validity_status, attempted_at);
