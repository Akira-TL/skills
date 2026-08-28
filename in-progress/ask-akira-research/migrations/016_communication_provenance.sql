CREATE TABLE communication_products (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    purpose TEXT NOT NULL,
    audience TEXT NOT NULL,
    source_commit TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'completed', 'superseded')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE communication_artifacts (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES communication_products(id) ON DELETE CASCADE,
    role TEXT NOT NULL
        CHECK (role IN ('title_abstract', 'methods', 'results', 'discussion', 'figure', 'figure_legend', 'table', 'lay_summary', 'traceability', 'generator', 'other')),
    path TEXT NOT NULL,
    timing_role TEXT NOT NULL DEFAULT 'derived_output'
        CHECK (timing_role IN ('source_support', 'derived_output')),
    git_tracking TEXT NOT NULL DEFAULT 'required'
        CHECK (git_tracking IN ('required', 'not_required')),
    tracking_reason TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(product_id, path),
    CHECK (git_tracking = 'required' OR (tracking_reason IS NOT NULL AND trim(tracking_reason) <> ''))
);
CREATE INDEX communication_artifacts_product_idx ON communication_artifacts(product_id, role);
