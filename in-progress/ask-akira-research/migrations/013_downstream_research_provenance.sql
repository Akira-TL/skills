CREATE TABLE datasets (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    identity TEXT,
    source TEXT NOT NULL,
    source_url TEXT,
    version TEXT,
    received_at TEXT NOT NULL,
    unit_of_inference TEXT NOT NULL,
    provenance_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE dataset_artifacts (
    id INTEGER PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    role TEXT NOT NULL
        CHECK (role IN ('raw', 'curated', 'metadata', 'manifest', 'other')),
    location TEXT NOT NULL,
    storage_kind TEXT NOT NULL DEFAULT 'local'
        CHECK (storage_kind IN ('local', 'external')),
    git_tracking TEXT NOT NULL DEFAULT 'required'
        CHECK (git_tracking IN ('required', 'not_required')),
    tracking_reason TEXT,
    source_url TEXT,
    version TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(dataset_id, location),
    CHECK (git_tracking = 'required' OR (tracking_reason IS NOT NULL AND trim(tracking_reason) <> ''))
);
CREATE INDEX dataset_artifacts_dataset_idx ON dataset_artifacts(dataset_id, role);

CREATE TABLE analysis_runs (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    analysis_mode TEXT NOT NULL
        CHECK (analysis_mode IN ('confirmatory', 'exploratory')),
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'frozen', 'completed', 'abandoned')),
    target_uncertainty TEXT NOT NULL,
    estimand TEXT NOT NULL,
    unit_of_inference TEXT NOT NULL,
    primary_analysis TEXT NOT NULL,
    analysis_path TEXT NOT NULL,
    code_path TEXT NOT NULL,
    freeze_commit TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status <> 'completed' OR completed_at IS NOT NULL)
);

CREATE TABLE analysis_inputs (
    analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    role TEXT NOT NULL DEFAULT 'primary',
    PRIMARY KEY (analysis_id, dataset_id, role)
);
CREATE INDEX analysis_inputs_dataset_idx ON analysis_inputs(dataset_id, analysis_id);

CREATE TABLE analysis_artifacts (
    id INTEGER PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    role TEXT NOT NULL
        CHECK (role IN ('estimate', 'diagnostic', 'figure', 'table', 'log', 'other')),
    path TEXT NOT NULL,
    git_tracking TEXT NOT NULL DEFAULT 'required'
        CHECK (git_tracking IN ('required', 'not_required')),
    tracking_reason TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(analysis_id, path),
    CHECK (git_tracking = 'required' OR (tracking_reason IS NOT NULL AND trim(tracking_reason) <> ''))
);
CREATE INDEX analysis_artifacts_analysis_idx ON analysis_artifacts(analysis_id, role);

CREATE TABLE analysis_amendments (
    id INTEGER PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    timing TEXT NOT NULL CHECK (timing IN ('pre_result', 'post_result')),
    description TEXT NOT NULL,
    reason TEXT NOT NULL,
    commit_ref TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX analysis_amendments_analysis_idx ON analysis_amendments(analysis_id, timing);

CREATE TABLE project_observations (
    id INTEGER PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    effect TEXT,
    statistics_json TEXT,
    scope TEXT,
    source_artifact_id INTEGER REFERENCES analysis_artifacts(id) ON DELETE SET NULL,
    source_locator TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX project_observations_analysis_idx ON project_observations(analysis_id);
