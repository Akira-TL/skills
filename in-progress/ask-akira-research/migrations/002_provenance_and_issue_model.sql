CREATE TABLE artifacts_v2 (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    content_type TEXT,
    version TEXT,
    source TEXT,
    source_url TEXT,
    retrieved_at TEXT,
    created_at TEXT NOT NULL
);

INSERT INTO artifacts_v2(
    id, paper_id, kind, path, content_type, version,
    source, source_url, retrieved_at, created_at
)
SELECT
    id, paper_id, kind, path, content_type, version,
    source, source_url, retrieved_at, created_at
FROM artifacts;

DROP TABLE artifacts;
ALTER TABLE artifacts_v2 RENAME TO artifacts;
CREATE INDEX artifacts_paper_idx ON artifacts(paper_id);

CREATE TABLE issues_v2 (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    nature TEXT NOT NULL
        CHECK (nature IN ('flaw', 'scope_limitation', 'reporting_gap', 'concern')),
    target_type TEXT,
    target_id TEXT,
    assessment TEXT NOT NULL,
    basis TEXT NOT NULL
        CHECK (basis IN ('demonstrated', 'potential', 'not_reported')),
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

INSERT INTO issues_v2(
    id, paper_id, category, nature, target_type, target_id,
    assessment, basis, severity, confidence, why_it_matters,
    alternative_explanations, possible_resolution, artifact_id,
    source_locator, created_at
)
SELECT
    id,
    paper_id,
    category,
    CASE basis
        WHEN 'demonstrated_flaw' THEN 'flaw'
        WHEN 'not_reported' THEN 'reporting_gap'
        ELSE 'concern'
    END,
    target_type,
    target_id,
    assessment,
    CASE basis
        WHEN 'demonstrated_flaw' THEN 'demonstrated'
        WHEN 'potential_concern' THEN 'potential'
        ELSE 'not_reported'
    END,
    severity,
    confidence,
    why_it_matters,
    alternative_explanations,
    possible_resolution,
    artifact_id,
    source_locator,
    created_at
FROM issues;

DROP TABLE issues;
ALTER TABLE issues_v2 RENAME TO issues;
CREATE INDEX issues_paper_idx ON issues(paper_id);
CREATE INDEX issues_severity_idx ON issues(severity);
