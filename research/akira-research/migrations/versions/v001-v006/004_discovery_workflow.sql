ALTER TABLE candidates ADD COLUMN source_url TEXT;
ALTER TABLE candidates ADD COLUMN acquisition_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (acquisition_status IN ('pending', 'queued', 'acquired', 'unavailable'));
ALTER TABLE candidates ADD COLUMN reading_priority TEXT NOT NULL DEFAULT 'normal'
    CHECK (reading_priority IN ('core', 'high', 'normal', 'low'));
ALTER TABLE candidates ADD COLUMN exclusion_reason TEXT;

CREATE TABLE search_run_candidates (
    search_run_id INTEGER NOT NULL REFERENCES search_runs(id) ON DELETE CASCADE,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    result_rank INTEGER,
    source_result_id TEXT,
    source_url TEXT,
    discovered_at TEXT NOT NULL,
    PRIMARY KEY(search_run_id, candidate_id)
);
CREATE INDEX search_run_candidates_candidate_idx
    ON search_run_candidates(candidate_id, search_run_id);
