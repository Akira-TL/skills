CREATE TABLE studies (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    design_id INTEGER NOT NULL REFERENCES research_designs(id) ON DELETE RESTRICT,
    study_type TEXT,
    status TEXT NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('in_progress', 'completed', 'aborted')),
    provenance_path TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status <> 'completed' OR completed_at IS NOT NULL)
);
CREATE INDEX studies_design_idx ON studies(design_id, status);

CREATE TABLE study_samples (
    id INTEGER PRIMARY KEY,
    study_id INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    sample_key TEXT NOT NULL,
    source_identity TEXT,
    experimental_unit_identity TEXT,
    parent_sample_id INTEGER REFERENCES study_samples(id) ON DELETE RESTRICT,
    sample_type TEXT,
    status TEXT NOT NULL DEFAULT 'collected'
        CHECK (status IN ('collected', 'failed', 'missing', 'archived')),
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(study_id, sample_key),
    CHECK (parent_sample_id IS NULL OR parent_sample_id <> id)
);
CREATE INDEX study_samples_study_idx ON study_samples(study_id, status);
CREATE INDEX study_samples_unit_idx ON study_samples(study_id, experimental_unit_identity);

CREATE TABLE study_assays (
    id INTEGER PRIMARY KEY,
    study_id INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    slug TEXT NOT NULL,
    assay_type TEXT NOT NULL,
    measurement_target TEXT,
    protocol_ref TEXT,
    batch TEXT,
    run TEXT,
    instrument TEXT,
    operator TEXT,
    status TEXT NOT NULL DEFAULT 'completed'
        CHECK (status IN ('started', 'completed', 'failed')),
    started_at TEXT,
    completed_at TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(study_id, slug),
    CHECK (status <> 'completed' OR completed_at IS NOT NULL)
);
CREATE INDEX study_assays_study_idx ON study_assays(study_id, status);

CREATE TABLE study_assay_samples (
    assay_id INTEGER NOT NULL REFERENCES study_assays(id) ON DELETE CASCADE,
    sample_id INTEGER NOT NULL REFERENCES study_samples(id) ON DELETE RESTRICT,
    PRIMARY KEY (assay_id, sample_id)
);
CREATE INDEX study_assay_samples_sample_idx ON study_assay_samples(sample_id, assay_id);

CREATE TABLE study_deviations (
    id INTEGER PRIMARY KEY,
    study_id INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    deviation_key TEXT NOT NULL,
    description TEXT NOT NULL,
    reason TEXT,
    affected_units TEXT,
    scientific_impact TEXT NOT NULL,
    occurred_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(study_id, deviation_key)
);
CREATE INDEX study_deviations_study_idx ON study_deviations(study_id, id);

CREATE TABLE study_artifacts (
    id INTEGER PRIMARY KEY,
    study_id INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    role TEXT NOT NULL
        CHECK (role IN ('protocol', 'sample_manifest', 'assay_metadata', 'deviation_log', 'execution_log', 'other')),
    location TEXT NOT NULL,
    storage_kind TEXT NOT NULL DEFAULT 'local'
        CHECK (storage_kind IN ('local', 'external')),
    git_tracking TEXT NOT NULL DEFAULT 'required'
        CHECK (git_tracking IN ('required', 'not_required')),
    tracking_reason TEXT,
    version TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(study_id, location),
    CHECK (git_tracking = 'required' OR (tracking_reason IS NOT NULL AND trim(tracking_reason) <> ''))
);
CREATE INDEX study_artifacts_study_idx ON study_artifacts(study_id, role);

ALTER TABLE datasets
    ADD COLUMN study_id INTEGER REFERENCES studies(id) ON DELETE RESTRICT;
CREATE INDEX datasets_study_idx ON datasets(study_id, status);
