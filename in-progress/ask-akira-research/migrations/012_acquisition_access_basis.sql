ALTER TABLE acquisition_attempts ADD COLUMN access_basis TEXT NOT NULL DEFAULT 'not_applicable'
    CHECK (access_basis IN (
        'not_applicable',
        'publisher_open',
        'public_repository',
        'institutional_repository',
        'author_manuscript',
        'preprint',
        'authenticated_user',
        'user_provided',
        'unverified'
    ));

ALTER TABLE acquisition_attempts ADD COLUMN access_basis_detail TEXT;

-- Preserve useful provenance when upgrading older projects, but do not silently
-- bless arbitrary internet mirrors. Only mechanically unambiguous legacy routes
-- are classified here; everything else remains unverified and must be repaired
-- before completion.
UPDATE acquisition_attempts
SET access_basis = CASE
        WHEN outcome <> 'acquired' THEN 'not_applicable'
        WHEN route_family = 'publisher' THEN 'publisher_open'
        WHEN route_family = 'repository' THEN 'public_repository'
        WHEN route_family = 'preprint' THEN 'preprint'
        WHEN route_family = 'authenticated' THEN 'authenticated_user'
        WHEN route_family = 'open_index'
             AND (
                 lower(source_url) LIKE '%pmc.ncbi.nlm.nih.gov/%'
                 OR lower(source_url) LIKE '%europepmc.org/%'
                 OR lower(source_url) LIKE '%ncbi.nlm.nih.gov/pmc/%'
             ) THEN 'public_repository'
        ELSE 'unverified'
    END,
    access_basis_detail = CASE
        WHEN outcome <> 'acquired' THEN NULL
        WHEN route_family = 'publisher' THEN 'Legacy migration: acquired directly from publisher route.'
        WHEN route_family = 'repository' THEN 'Legacy migration: acquired from repository route.'
        WHEN route_family = 'preprint' THEN 'Legacy migration: acquired from preprint route.'
        WHEN route_family = 'authenticated' THEN 'Legacy migration: acquired through authenticated user route.'
        WHEN route_family = 'open_index'
             AND (
                 lower(source_url) LIKE '%pmc.ncbi.nlm.nih.gov/%'
                 OR lower(source_url) LIKE '%europepmc.org/%'
                 OR lower(source_url) LIKE '%ncbi.nlm.nih.gov/pmc/%'
             ) THEN 'Legacy migration: acquired from recognized public full-text repository.'
        ELSE 'Legacy acquisition requires explicit access-basis verification.'
    END;
