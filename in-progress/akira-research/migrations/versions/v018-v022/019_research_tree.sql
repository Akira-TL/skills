-- migration-requires-foreign-keys-off

CREATE TABLE research_nodes (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL
        CHECK (kind IN (
            'objective', 'question', 'hypothesis', 'design', 'study',
            'analysis', 'observation', 'claim'
        )),
    label TEXT NOT NULL,
    scientific_scope TEXT,
    workflow_status TEXT NOT NULL DEFAULT 'open'
        CHECK (workflow_status IN ('open', 'active', 'blocked', 'resolved', 'closed')),
    branch_priority TEXT NOT NULL DEFAULT 'secondary'
        CHECK (branch_priority IN ('primary', 'secondary', 'parked')),
    parent_node_id INTEGER REFERENCES research_nodes(id) ON DELETE RESTRICT,
    canonical_entity_type TEXT,
    canonical_entity_id TEXT,
    artifact_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT,
    CHECK (parent_node_id IS NULL OR parent_node_id <> id),
    CHECK (
        (canonical_entity_type IS NULL AND canonical_entity_id IS NULL)
        OR (
            canonical_entity_type IS NOT NULL AND trim(canonical_entity_type) <> ''
            AND canonical_entity_id IS NOT NULL AND trim(canonical_entity_id) <> ''
        )
    ),
    CHECK (workflow_status <> 'closed' OR closed_at IS NOT NULL)
);
CREATE INDEX research_nodes_parent_idx
    ON research_nodes(parent_node_id, workflow_status, branch_priority);
CREATE UNIQUE INDEX research_nodes_canonical_entity_unique
    ON research_nodes(canonical_entity_type, canonical_entity_id)
    WHERE canonical_entity_type IS NOT NULL AND canonical_entity_id IS NOT NULL;

CREATE TABLE research_edges (
    id INTEGER PRIMARY KEY,
    source_node_id INTEGER NOT NULL REFERENCES research_nodes(id) ON DELETE RESTRICT,
    relation TEXT NOT NULL
        CHECK (relation IN (
            'spawned_from', 'addresses', 'tests', 'supports', 'weakens',
            'contradicts', 'qualifies', 'alternative_to', 'depends_on',
            'uses', 'produces'
        )),
    target_node_id INTEGER NOT NULL REFERENCES research_nodes(id) ON DELETE RESTRICT,
    basis_type TEXT,
    basis_ref TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    CHECK (source_node_id <> target_node_id),
    CHECK (
        relation NOT IN ('supports', 'weakens', 'contradicts', 'qualifies')
        OR (basis_ref IS NOT NULL AND trim(basis_ref) <> '')
    )
);
CREATE INDEX research_edges_source_idx ON research_edges(source_node_id, relation);
CREATE INDEX research_edges_target_idx ON research_edges(target_node_id, relation);

CREATE TABLE research_tree_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    root_node_id INTEGER NOT NULL REFERENCES research_nodes(id) ON DELETE RESTRICT,
    active_node_id INTEGER NOT NULL REFERENCES research_nodes(id) ON DELETE RESTRICT,
    updated_at TEXT NOT NULL
);

CREATE TABLE research_designs_v19 (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    hypothesis_set_id INTEGER REFERENCES hypothesis_sets(id) ON DELETE RESTRICT,
    question_node_id INTEGER REFERENCES research_nodes(id) ON DELETE RESTRICT,
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
    CHECK (hypothesis_set_id IS NOT NULL OR question_node_id IS NOT NULL),
    CHECK (status NOT IN ('frozen', 'execution_ready') OR (freeze_commit IS NOT NULL AND trim(freeze_commit) <> '')),
    CHECK (feasibility_status <> 'unresolved' OR (feasibility_summary IS NOT NULL AND trim(feasibility_summary) <> '')),
    CHECK (status <> 'execution_ready' OR feasibility_status = 'ready')
);

INSERT INTO research_designs_v19(
    id, slug, title, hypothesis_set_id, question_node_id, target_estimand,
    primary_outcome, experimental_unit, artifact_path, status,
    feasibility_status, feasibility_summary, freeze_commit, created_at, updated_at
)
SELECT
    id, slug, title, hypothesis_set_id, NULL, target_estimand,
    primary_outcome, experimental_unit, artifact_path, status,
    feasibility_status, feasibility_summary, freeze_commit, created_at, updated_at
FROM research_designs;

DROP TABLE research_designs;
ALTER TABLE research_designs_v19 RENAME TO research_designs;

CREATE INDEX research_designs_hypothesis_idx
    ON research_designs(hypothesis_set_id, status);
CREATE INDEX research_designs_question_idx
    ON research_designs(question_node_id, status);
