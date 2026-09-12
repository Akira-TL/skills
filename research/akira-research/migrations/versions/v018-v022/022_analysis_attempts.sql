CREATE TABLE analysis_attempts (
    id INTEGER PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    attempt_key TEXT NOT NULL,
    parent_attempt_id INTEGER REFERENCES analysis_attempts(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'completed', 'selected', 'abandoned', 'invalid')),
    git_commit TEXT,
    config_path TEXT,
    output_path TEXT,
    reason TEXT NOT NULL,
    decision_reason TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(analysis_id, attempt_key),
    CHECK (parent_attempt_id IS NULL OR parent_attempt_id <> id),
    CHECK (status = 'planned' OR (git_commit IS NOT NULL AND trim(git_commit) <> '')),
    CHECK (status NOT IN ('completed', 'selected', 'abandoned', 'invalid') OR completed_at IS NOT NULL),
    CHECK (status <> 'selected' OR (decision_reason IS NOT NULL AND trim(decision_reason) <> ''))
);
CREATE INDEX analysis_attempts_analysis_idx ON analysis_attempts(analysis_id, status, id);
CREATE UNIQUE INDEX analysis_attempts_selected_unique
    ON analysis_attempts(analysis_id)
    WHERE status = 'selected';

INSERT INTO meta(key, value)
VALUES('analysis_attempt_workflow_started_at', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
ON CONFLICT(key) DO NOTHING;
