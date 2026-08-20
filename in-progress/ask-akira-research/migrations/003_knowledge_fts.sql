CREATE VIRTUAL TABLE knowledge_fts USING fts5(
    entity_type UNINDEXED,
    entity_id UNINDEXED,
    paper_id UNINDEXED,
    title,
    body,
    tokenize = 'unicode61'
);

INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
SELECT 'paper', id, id, title,
       trim(coalesce(doi, '') || ' ' || coalesce(pmid, '') || ' ' || coalesce(pmcid, '') || ' ' || coalesce(journal, ''))
FROM papers;
INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
SELECT 'method', CAST(id AS TEXT), paper_id, name,
       trim(coalesce(purpose, '') || ' ' || coalesce(description, '') || ' ' || coalesce(reusable_notes, ''))
FROM methods;
INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
SELECT 'experiment', CAST(id AS TEXT), paper_id, coalesce(question, ''),
       trim(coalesce(design, '') || ' ' || coalesce(samples, '') || ' ' || coalesce(controls, '') || ' ' || coalesce(analysis, '') || ' ' || coalesce(result_summary, ''))
FROM experiments;
INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
SELECT 'observation', CAST(id AS TEXT), paper_id, statement,
       trim(coalesce(effect, '') || ' ' || coalesce(statistics_json, '') || ' ' || coalesce(scope, '') || ' ' || coalesce(certainty, ''))
FROM observations;
INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
SELECT 'claim', CAST(id AS TEXT), paper_id, statement,
       trim(coalesce(claim_type, '') || ' ' || coalesce(author_strength, '') || ' ' || coalesce(scope, ''))
FROM claims;
INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
SELECT 'issue', CAST(id AS TEXT), paper_id, assessment,
       trim(coalesce(category, '') || ' ' || coalesce(nature, '') || ' ' || coalesce(basis, '') || ' ' || coalesce(severity, '') || ' ' || coalesce(why_it_matters, '') || ' ' || coalesce(alternative_explanations, '') || ' ' || coalesce(possible_resolution, ''))
FROM issues;
INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
SELECT 'lead', CAST(id AS TEXT), paper_id, coalesce(title, coalesce(identifier, '')),
       trim(coalesce(type, '') || ' ' || coalesce(identifier, '') || ' ' || coalesce(purpose, '') || ' ' || coalesce(priority, '') || ' ' || coalesce(status, ''))
FROM leads;

CREATE TRIGGER papers_fts_ai AFTER INSERT ON papers BEGIN
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('paper', new.id, new.id, new.title,
            trim(coalesce(new.doi, '') || ' ' || coalesce(new.pmid, '') || ' ' || coalesce(new.pmcid, '') || ' ' || coalesce(new.journal, '')));
END;
CREATE TRIGGER papers_fts_ad AFTER DELETE ON papers BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'paper' AND entity_id = old.id;
END;
CREATE TRIGGER papers_fts_au AFTER UPDATE ON papers BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'paper' AND entity_id = old.id;
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('paper', new.id, new.id, new.title,
            trim(coalesce(new.doi, '') || ' ' || coalesce(new.pmid, '') || ' ' || coalesce(new.pmcid, '') || ' ' || coalesce(new.journal, '')));
END;

CREATE TRIGGER methods_fts_ai AFTER INSERT ON methods BEGIN
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('method', CAST(new.id AS TEXT), new.paper_id, new.name,
            trim(coalesce(new.purpose, '') || ' ' || coalesce(new.description, '') || ' ' || coalesce(new.reusable_notes, '')));
END;
CREATE TRIGGER methods_fts_ad AFTER DELETE ON methods BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'method' AND entity_id = CAST(old.id AS TEXT);
END;
CREATE TRIGGER methods_fts_au AFTER UPDATE ON methods BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'method' AND entity_id = CAST(old.id AS TEXT);
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('method', CAST(new.id AS TEXT), new.paper_id, new.name,
            trim(coalesce(new.purpose, '') || ' ' || coalesce(new.description, '') || ' ' || coalesce(new.reusable_notes, '')));
END;

CREATE TRIGGER experiments_fts_ai AFTER INSERT ON experiments BEGIN
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('experiment', CAST(new.id AS TEXT), new.paper_id, coalesce(new.question, ''),
            trim(coalesce(new.design, '') || ' ' || coalesce(new.samples, '') || ' ' || coalesce(new.controls, '') || ' ' || coalesce(new.analysis, '') || ' ' || coalesce(new.result_summary, '')));
END;
CREATE TRIGGER experiments_fts_ad AFTER DELETE ON experiments BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'experiment' AND entity_id = CAST(old.id AS TEXT);
END;
CREATE TRIGGER experiments_fts_au AFTER UPDATE ON experiments BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'experiment' AND entity_id = CAST(old.id AS TEXT);
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('experiment', CAST(new.id AS TEXT), new.paper_id, coalesce(new.question, ''),
            trim(coalesce(new.design, '') || ' ' || coalesce(new.samples, '') || ' ' || coalesce(new.controls, '') || ' ' || coalesce(new.analysis, '') || ' ' || coalesce(new.result_summary, '')));
END;

CREATE TRIGGER observations_fts_ai AFTER INSERT ON observations BEGIN
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('observation', CAST(new.id AS TEXT), new.paper_id, new.statement,
            trim(coalesce(new.effect, '') || ' ' || coalesce(new.statistics_json, '') || ' ' || coalesce(new.scope, '') || ' ' || coalesce(new.certainty, '')));
END;
CREATE TRIGGER observations_fts_ad AFTER DELETE ON observations BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'observation' AND entity_id = CAST(old.id AS TEXT);
END;
CREATE TRIGGER observations_fts_au AFTER UPDATE ON observations BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'observation' AND entity_id = CAST(old.id AS TEXT);
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('observation', CAST(new.id AS TEXT), new.paper_id, new.statement,
            trim(coalesce(new.effect, '') || ' ' || coalesce(new.statistics_json, '') || ' ' || coalesce(new.scope, '') || ' ' || coalesce(new.certainty, '')));
END;

CREATE TRIGGER claims_fts_ai AFTER INSERT ON claims BEGIN
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('claim', CAST(new.id AS TEXT), new.paper_id, new.statement,
            trim(coalesce(new.claim_type, '') || ' ' || coalesce(new.author_strength, '') || ' ' || coalesce(new.scope, '')));
END;
CREATE TRIGGER claims_fts_ad AFTER DELETE ON claims BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'claim' AND entity_id = CAST(old.id AS TEXT);
END;
CREATE TRIGGER claims_fts_au AFTER UPDATE ON claims BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'claim' AND entity_id = CAST(old.id AS TEXT);
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('claim', CAST(new.id AS TEXT), new.paper_id, new.statement,
            trim(coalesce(new.claim_type, '') || ' ' || coalesce(new.author_strength, '') || ' ' || coalesce(new.scope, '')));
END;

CREATE TRIGGER issues_fts_ai AFTER INSERT ON issues BEGIN
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('issue', CAST(new.id AS TEXT), new.paper_id, new.assessment,
            trim(coalesce(new.category, '') || ' ' || coalesce(new.nature, '') || ' ' || coalesce(new.basis, '') || ' ' || coalesce(new.severity, '') || ' ' || coalesce(new.why_it_matters, '') || ' ' || coalesce(new.alternative_explanations, '') || ' ' || coalesce(new.possible_resolution, '')));
END;
CREATE TRIGGER issues_fts_ad AFTER DELETE ON issues BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'issue' AND entity_id = CAST(old.id AS TEXT);
END;
CREATE TRIGGER issues_fts_au AFTER UPDATE ON issues BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'issue' AND entity_id = CAST(old.id AS TEXT);
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('issue', CAST(new.id AS TEXT), new.paper_id, new.assessment,
            trim(coalesce(new.category, '') || ' ' || coalesce(new.nature, '') || ' ' || coalesce(new.basis, '') || ' ' || coalesce(new.severity, '') || ' ' || coalesce(new.why_it_matters, '') || ' ' || coalesce(new.alternative_explanations, '') || ' ' || coalesce(new.possible_resolution, '')));
END;

CREATE TRIGGER leads_fts_ai AFTER INSERT ON leads BEGIN
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('lead', CAST(new.id AS TEXT), new.paper_id, coalesce(new.title, coalesce(new.identifier, '')),
            trim(coalesce(new.type, '') || ' ' || coalesce(new.identifier, '') || ' ' || coalesce(new.purpose, '') || ' ' || coalesce(new.priority, '') || ' ' || coalesce(new.status, '')));
END;
CREATE TRIGGER leads_fts_ad AFTER DELETE ON leads BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'lead' AND entity_id = CAST(old.id AS TEXT);
END;
CREATE TRIGGER leads_fts_au AFTER UPDATE ON leads BEGIN
    DELETE FROM knowledge_fts WHERE entity_type = 'lead' AND entity_id = CAST(old.id AS TEXT);
    INSERT INTO knowledge_fts(entity_type, entity_id, paper_id, title, body)
    VALUES ('lead', CAST(new.id AS TEXT), new.paper_id, coalesce(new.title, coalesce(new.identifier, '')),
            trim(coalesce(new.type, '') || ' ' || coalesce(new.identifier, '') || ' ' || coalesce(new.purpose, '') || ' ' || coalesce(new.priority, '') || ' ' || coalesce(new.status, '')));
END;
