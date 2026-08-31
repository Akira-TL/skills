CREATE TABLE analysis_dataset_artifact_timing (
    analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    dataset_artifact_id INTEGER NOT NULL REFERENCES dataset_artifacts(id) ON DELETE RESTRICT,
    timing_role TEXT NOT NULL
        CHECK (timing_role IN ('pre_result_input', 'post_result_context')),
    reason TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (analysis_id, dataset_artifact_id),
    CHECK (
        timing_role = 'pre_result_input'
        OR (reason IS NOT NULL AND trim(reason) <> '')
    )
);

CREATE INDEX analysis_dataset_artifact_timing_artifact_idx
    ON analysis_dataset_artifact_timing(dataset_artifact_id, analysis_id);
