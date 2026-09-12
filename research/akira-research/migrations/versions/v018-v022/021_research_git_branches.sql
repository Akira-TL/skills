ALTER TABLE research_nodes
    ADD COLUMN closure_reason TEXT;

CREATE TABLE research_git_branches (
    id INTEGER PRIMARY KEY,
    node_id INTEGER NOT NULL UNIQUE REFERENCES research_nodes(id) ON DELETE CASCADE,
    branch_name TEXT NOT NULL UNIQUE,
    base_commit TEXT NOT NULL,
    tip_commit TEXT NOT NULL,
    disposition TEXT NOT NULL DEFAULT 'active'
        CHECK (disposition IN ('active', 'merged', 'archived')),
    final_ref TEXT,
    closure_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (disposition = 'active' OR (final_ref IS NOT NULL AND trim(final_ref) <> '')),
    CHECK (disposition = 'active' OR (closure_reason IS NOT NULL AND trim(closure_reason) <> ''))
);
CREATE INDEX research_git_branches_disposition_idx
    ON research_git_branches(disposition, node_id);

INSERT INTO meta(key, value)
VALUES('research_git_workflow_started_at', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
ON CONFLICT(key) DO NOTHING;
