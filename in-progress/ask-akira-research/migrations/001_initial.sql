CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    doi TEXT,
    pmid TEXT,
    pmcid TEXT,
    authors TEXT,
    journal TEXT,
    year INTEGER,
    paper_type TEXT,
    canonical_identity TEXT,
    status TEXT NOT NULL DEFAULT 'discovered'
        CHECK (status IN ('discovered', 'acquired', 'active', 'archived')),
    read_depth TEXT NOT NULL DEFAULT 'none'
        CHECK (read_depth IN ('none', 'full_scan', 'deep_extraction')),
    reading_status TEXT NOT NULL DEFAULT 'unread'
        CHECK (reading_status IN ('unread', 'reconstructed', 'extracted')),
    critical_status TEXT NOT NULL DEFAULT 'not_reviewed'
        CHECK (critical_status IN ('not_reviewed', 'critically_reviewed')),
    sidecar_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX papers_doi_unique
    ON papers(lower(doi))
    WHERE doi IS NOT NULL AND trim(doi) <> '';
CREATE UNIQUE INDEX papers_pmid_unique
    ON papers(pmid)
    WHERE pmid IS NOT NULL AND trim(pmid) <> '';
CREATE UNIQUE INDEX papers_canonical_identity_unique
    ON papers(canonical_identity)
    WHERE canonical_identity IS NOT NULL AND trim(canonical_identity) <> '';

CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    content_type TEXT,
    version TEXT,
    source TEXT,
    source_url TEXT,
    retrieved_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX artifacts_paper_idx ON artifacts(paper_id);

CREATE TABLE search_runs (
    id INTEGER PRIMARY KEY,
    purpose TEXT NOT NULL,
    mode TEXT NOT NULL,
    source TEXT NOT NULL,
    query TEXT NOT NULL,
    filters TEXT,
    parent_run_id INTEGER REFERENCES search_runs(id),
    reason TEXT,
    executed_at TEXT NOT NULL,
    result_count INTEGER,
    what_we_learned TEXT,
    next_decision TEXT
);

CREATE TABLE candidates (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    doi TEXT,
    pmid TEXT,
    authors TEXT,
    year INTEGER,
    discovery_source TEXT,
    identity_status TEXT,
    relevance_status TEXT,
    relevance_reason TEXT,
    paper_id TEXT REFERENCES papers(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX candidates_paper_idx ON candidates(paper_id);
CREATE INDEX candidates_doi_idx ON candidates(doi);
CREATE INDEX candidates_pmid_idx ON candidates(pmid);

CREATE TABLE reading_runs (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    pass TEXT NOT NULL CHECK (pass IN ('reconstruction', 'critical_audit')),
    depth TEXT NOT NULL CHECK (depth IN ('full_scan', 'deep_extraction')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    artifacts_checked TEXT,
    sections_checked TEXT,
    notes TEXT
);
CREATE INDEX reading_runs_paper_idx ON reading_runs(paper_id);

CREATE TABLE methods (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    purpose TEXT,
    description TEXT,
    parameters TEXT,
    materials TEXT,
    software TEXT,
    reusable_notes TEXT,
    artifact_id INTEGER REFERENCES artifacts(id),
    source_locator TEXT
);
CREATE INDEX methods_paper_idx ON methods(paper_id);

CREATE TABLE experiments (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    question TEXT,
    design TEXT,
    samples TEXT,
    groups_json TEXT,
    controls TEXT,
    variables_json TEXT,
    analysis TEXT,
    result_summary TEXT,
    artifact_id INTEGER REFERENCES artifacts(id),
    source_locator TEXT
);
CREATE INDEX experiments_paper_idx ON experiments(paper_id);

CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    experiment_id INTEGER REFERENCES experiments(id),
    statement TEXT NOT NULL,
    effect TEXT,
    statistics_json TEXT,
    scope TEXT,
    certainty TEXT,
    artifact_id INTEGER REFERENCES artifacts(id),
    source_locator TEXT
);
CREATE INDEX observations_paper_idx ON observations(paper_id);
CREATE INDEX observations_experiment_idx ON observations(experiment_id);

CREATE TABLE claims (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    claim_type TEXT NOT NULL
        CHECK (claim_type IN ('descriptive', 'association', 'causal', 'mechanistic', 'speculative')),
    author_strength TEXT,
    scope TEXT,
    artifact_id INTEGER REFERENCES artifacts(id),
    source_locator TEXT
);
CREATE INDEX claims_paper_idx ON claims(paper_id);

CREATE TABLE issues (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    assessment TEXT NOT NULL,
    basis TEXT NOT NULL
        CHECK (basis IN ('demonstrated_flaw', 'potential_concern', 'not_reported')),
    severity TEXT NOT NULL
        CHECK (severity IN ('critical', 'major', 'moderate', 'minor')),
    confidence TEXT NOT NULL
        CHECK (confidence IN ('high', 'medium', 'low')),
    why_it_matters TEXT,
    alternative_explanations TEXT,
    possible_resolution TEXT,
    artifact_id INTEGER REFERENCES artifacts(id),
    source_locator TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX issues_paper_idx ON issues(paper_id);
CREATE INDEX issues_severity_idx ON issues(severity);

CREATE TABLE leads (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT,
    identifier TEXT,
    url TEXT,
    purpose TEXT,
    priority TEXT,
    status TEXT,
    artifact_id INTEGER REFERENCES artifacts(id),
    source_locator TEXT
);
CREATE INDEX leads_paper_idx ON leads(paper_id);

CREATE TABLE relations (
    id INTEGER PRIMARY KEY,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    confidence TEXT,
    note TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX relations_subject_idx ON relations(subject_type, subject_id);
CREATE INDEX relations_object_idx ON relations(object_type, object_id);
CREATE INDEX relations_predicate_idx ON relations(predicate);

CREATE TABLE change_log (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    paper_id TEXT REFERENCES papers(id),
    reason TEXT,
    run_id INTEGER,
    summary TEXT NOT NULL
);
CREATE INDEX change_log_paper_idx ON change_log(paper_id);
CREATE INDEX change_log_entity_idx ON change_log(entity_type, entity_id);
