CREATE TABLE hypothesis_sets (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    target_uncertainty TEXT NOT NULL,
    artifact_path TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'frozen', 'superseded', 'closed')),
    freeze_commit TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status <> 'frozen' OR (freeze_commit IS NOT NULL AND trim(freeze_commit) <> ''))
);

CREATE TABLE research_designs (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    hypothesis_set_id INTEGER NOT NULL REFERENCES hypothesis_sets(id) ON DELETE RESTRICT,
    target_estimand TEXT NOT NULL,
    primary_outcome TEXT NOT NULL,
    experimental_unit TEXT NOT NULL,
    artifact_path TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'frozen', 'execution_ready', 'superseded')),
    feasibility_status TEXT NOT NULL DEFAULT 'unresolved'
        CHECK (feasibility_status IN ('unresolved', 'ready')),
    feasibility_summary TEXT,
    freeze_commit TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status NOT IN ('frozen', 'execution_ready') OR (freeze_commit IS NOT NULL AND trim(freeze_commit) <> '')),
    CHECK (feasibility_status <> 'unresolved' OR (feasibility_summary IS NOT NULL AND trim(feasibility_summary) <> '')),
    CHECK (status <> 'execution_ready' OR feasibility_status = 'ready')
);

CREATE INDEX research_designs_hypothesis_idx
    ON research_designs(hypothesis_set_id, status);
