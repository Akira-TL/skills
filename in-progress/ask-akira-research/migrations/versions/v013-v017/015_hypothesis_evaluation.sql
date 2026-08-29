ALTER TABLE analysis_runs
    ADD COLUMN design_id INTEGER REFERENCES research_designs(id) ON DELETE RESTRICT;

ALTER TABLE analysis_artifacts
    ADD COLUMN timing_role TEXT NOT NULL DEFAULT 'result'
        CHECK (timing_role IN ('pre_result_support', 'result'));

CREATE INDEX analysis_runs_design_idx
    ON analysis_runs(design_id, analysis_mode, status);

CREATE TABLE hypothesis_evaluations (
    id INTEGER PRIMARY KEY,
    hypothesis_set_id INTEGER NOT NULL REFERENCES hypothesis_sets(id) ON DELETE RESTRICT,
    analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE RESTRICT,
    source_artifact_id INTEGER NOT NULL REFERENCES analysis_artifacts(id) ON DELETE RESTRICT,
    resolution_status TEXT NOT NULL
        CHECK (resolution_status IN ('unresolved', 'partially_resolved', 'resolved', 'not_interpretable')),
    decision TEXT NOT NULL,
    summary TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(hypothesis_set_id, analysis_id)
);

CREATE INDEX hypothesis_evaluations_hypothesis_idx
    ON hypothesis_evaluations(hypothesis_set_id, evaluated_at, id);
CREATE INDEX hypothesis_evaluations_analysis_idx
    ON hypothesis_evaluations(analysis_id, id);
