INSERT INTO meta(key, value)
VALUES('hypothesis_provenance_started_at', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
ON CONFLICT(key) DO NOTHING;

CREATE TABLE hypothesis_proposals (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    origin TEXT NOT NULL CHECK (origin IN ('user', 'agent')),
    original_statement TEXT NOT NULL,
    operationalized_statement TEXT,
    operationalized_by TEXT CHECK (operationalized_by IN ('user', 'agent')),
    rationale TEXT,
    source_context TEXT,
    created_at TEXT NOT NULL,
    CHECK (
        (operationalized_statement IS NULL AND operationalized_by IS NULL)
        OR (
            operationalized_statement IS NOT NULL
            AND trim(operationalized_statement) <> ''
            AND operationalized_by IS NOT NULL
        )
    )
);

CREATE TABLE hypothesis_set_proposals (
    hypothesis_set_id INTEGER NOT NULL REFERENCES hypothesis_sets(id) ON DELETE CASCADE,
    proposal_id INTEGER NOT NULL REFERENCES hypothesis_proposals(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (hypothesis_set_id, proposal_id)
);
CREATE INDEX hypothesis_set_proposals_proposal_idx
    ON hypothesis_set_proposals(proposal_id, hypothesis_set_id);

CREATE TABLE user_hypothesis_decisions (
    id INTEGER PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES hypothesis_proposals(id) ON DELETE RESTRICT,
    decision TEXT NOT NULL
        CHECK (decision IN ('accepted_for_exploration', 'prioritized', 'deferred', 'rejected', 'modified')),
    source_statement TEXT NOT NULL,
    rationale TEXT,
    resulting_proposal_id INTEGER REFERENCES hypothesis_proposals(id) ON DELETE RESTRICT,
    decided_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK (resulting_proposal_id IS NULL OR resulting_proposal_id <> proposal_id),
    CHECK (
        (decision = 'modified' AND resulting_proposal_id IS NOT NULL)
        OR (decision <> 'modified' AND resulting_proposal_id IS NULL)
    )
);
CREATE INDEX user_hypothesis_decisions_proposal_idx
    ON user_hypothesis_decisions(proposal_id, decided_at, id);

CREATE TABLE research_judgments (
    id INTEGER PRIMARY KEY,
    actor TEXT NOT NULL CHECK (actor IN ('user', 'agent')),
    judgment_type TEXT NOT NULL
        CHECK (judgment_type IN (
            'scientific_assessment',
            'research_priority',
            'strategic_preference',
            'resource_constraint',
            'recommendation'
        )),
    statement TEXT NOT NULL,
    basis TEXT,
    source_statement TEXT,
    proposal_id INTEGER REFERENCES hypothesis_proposals(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    CHECK (actor <> 'agent' OR (basis IS NOT NULL AND trim(basis) <> '')),
    CHECK (actor <> 'user' OR (source_statement IS NOT NULL AND trim(source_statement) <> ''))
);
CREATE INDEX research_judgments_actor_idx
    ON research_judgments(actor, created_at, id);
CREATE INDEX research_judgments_proposal_idx
    ON research_judgments(proposal_id, created_at, id);
