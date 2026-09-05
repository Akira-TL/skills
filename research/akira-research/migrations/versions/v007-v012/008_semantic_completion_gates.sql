ALTER TABLE issues ADD COLUMN basis_rationale TEXT;

ALTER TABLE search_runs ADD COLUMN discovery_method TEXT NOT NULL DEFAULT 'unspecified'
    CHECK (discovery_method IN (
        'unspecified',
        'seed_search',
        'query_expansion',
        'backward_citation',
        'forward_citation',
        'related_work',
        'method_search',
        'update_search',
        'exact_work',
        'other'
    ));
