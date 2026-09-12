CREATE TABLE user_reading_events (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('confirmed', 'revoked', 'invalidated')),
    sidecar_path TEXT NOT NULL,
    content_oid TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX user_reading_events_paper_idx
    ON user_reading_events(paper_id, id);
