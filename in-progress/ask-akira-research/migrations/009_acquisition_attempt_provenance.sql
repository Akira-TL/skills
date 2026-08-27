CREATE TABLE acquisition_attempts (
    id INTEGER PRIMARY KEY,
    candidate_id INTEGER REFERENCES candidates(id) ON DELETE CASCADE,
    paper_id TEXT REFERENCES papers(id) ON DELETE CASCADE,
    target_kind TEXT NOT NULL
        CHECK (target_kind IN ('main_text', 'supplement', 'code_data')),
    target_label TEXT,
    route_family TEXT NOT NULL
        CHECK (route_family IN ('publisher', 'open_index', 'repository', 'preprint', 'authenticated', 'other')),
    resource_kind TEXT NOT NULL
        CHECK (resource_kind IN ('article_page', 'full_text_html', 'pdf', 'xml', 'repository_record', 'supplement', 'other')),
    source_url TEXT NOT NULL,
    outcome TEXT NOT NULL
        CHECK (outcome IN (
            'acquired', 'not_found', 'access_denied', 'auth_required',
            'challenge', 'invalid_artifact', 'network_error', 'other_failure'
        )),
    detail TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    CHECK (candidate_id IS NOT NULL OR paper_id IS NOT NULL)
);
CREATE INDEX acquisition_attempts_candidate_idx
    ON acquisition_attempts(candidate_id, target_kind, attempted_at);
CREATE INDEX acquisition_attempts_paper_idx
    ON acquisition_attempts(paper_id, target_kind, attempted_at);
