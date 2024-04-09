CREATE VIEW IF NOT EXISTS entailed_is_a AS
  SELECT DISTINCT subject, object
    FROM entailed_edge
    WHERE predicate = 'rdfs:subClassOf';

CREATE VIEW IF NOT EXISTS obsolete_term AS
  SELECT DISTINCT subject AS id
    FROM statements
    WHERE predicate = 'owl:deprecated' AND value = 'true';

CREATE VIEW IF NOT EXISTS GORULE_0000002_violations AS
SELECT internal_id, 'GORULE:0000002' AS rule
FROM gaf_association
WHERE (ontology_class_ref = 'GO:0005488' OR ontology_class_ref = 'GO:0005515')
  AND qualifiers LIKE '%NOT%';

CREATE VIEW IF NOT EXISTS GORULE_0000004_violations  AS
SELECT DISTINCT a.internal_id, 'GORULE:0000004' AS rule
FROM gaf_association a
JOIN gaf_association b ON a.with_or_from = b.local_id AND a.db = b.db
WHERE a.ontology_class_ref = 'GO:0005515'
  AND NOT EXISTS (
    SELECT 1
    FROM gaf_association r
    WHERE r.db = b.db
      AND r.local_id = b.local_id
      AND r.with_or_from = a.local_id
      AND r.ontology_class_ref IN (
        'GO:0005515',
        'GO:0042803',
        'GO:0051260',
        'GO:0043621'
      )
  );


CREATE VIEW IF NOT EXISTS GORULE_0000005_violations AS
SELECT internal_id, 'GORULE:0000005' AS rule
FROM gaf_association
WHERE ontology_class_ref IN ('GO:0005515', 'GO:0005488')
  AND evidence_type IN ('IEA', 'ISS', 'ISO', 'ISM', 'ISA', 'IBA', 'RCA');

CREATE VIEW IF NOT EXISTS GORULE_0000006_violations AS
SELECT internal_id, 'GORULE:0000006' AS rule
FROM gaf_association
WHERE evidence_type IN ('IEP', 'HEP')
  AND assigned_by != 'GOC'
  AND aspect != 'P';


CREATE VIEW IF NOT EXISTS GORULE_0000007_violations AS
SELECT internal_id, 'GORULE:0000007' AS rule
FROM gaf_association
WHERE evidence_type = 'IPI'
  AND ontology_class_ref IN (
    SELECT subject FROM entailed_is_a WHERE object = 'GO:0003824'
  );

CREATE VIEW IF NOT EXISTS GORULE_0000013_violations AS
SELECT internal_id, 'GORULE:0000013' AS rule
FROM gaf_association
WHERE ontology_class_ref NOT IN (SELECT subject FROM entailed_is_a)
  AND qualifiers NOT LIKE '%NOT%'
  AND evidence_type IN ('IBA', 'IKR', 'IRD', 'IC', 'ISA', 'ISM', 'ISO', 'ISS', 'NAS', 'RCA', 'TAS', 'IEA');

CREATE VIEW IF NOT EXISTS GORULE_0000014_violations AS
SELECT internal_id, 'GORULE:0000014' AS rule
FROM gaf_association
WHERE ontology_class_ref IN (SELECT id FROM obsolete_term);

CREATE VIEW IF NOT EXISTS GORULE_0000016_violations AS
SELECT internal_id, 'GORULE:0000016' AS rule
FROM gaf_association
WHERE evidence_type = 'IC'
  AND with_or_from IS NULL;

CREATE VIEW IF NOT EXISTS GORULE_0000017_violations AS
SELECT internal_id, 'GORULE:0000017' AS rule
FROM gaf_association
WHERE evidence_type = 'IDA'
  AND with_or_from IS NOT NULL;


--- TODO
CREATE TABLE retracted_publication (
  id TEXT PRIMARY KEY
);
CREATE VIEW IF NOT EXISTS GORULE_0000022_violations AS
SELECT internal_id, 'GORULE:0000022' AS rule
FROM gaf_association
WHERE supporting_references IN (SELECT id FROM retracted_publication);

CREATE VIEW IF NOT EXISTS GORULE_0000029_violations AS
SELECT internal_id, 'GORULE:0000029' AS rule
FROM gaf_association
WHERE evidence_type = 'IEA'
  AND annotation_date < (NOW() - INTERVAL '1 year')::DATE;


CREATE VIEW IF NOT EXISTS GORULE_0000015_violations AS
SELECT internal_id, 'GORULE:0000015' AS rule
FROM gaf_association
WHERE (ontology_class_ref IN ('GO:0044419', 'GO:0043903', 'GO:0018995')
       OR ontology_class_ref LIKE 'GO:0044419%'
       OR ontology_class_ref LIKE 'GO:0043903%'
       OR ontology_class_ref LIKE 'GO:0018995%')
  AND db_object_taxon IS NOT NULL
  AND array_length(regexp_split_to_array(db_object_taxon, '\|'), 1) > 1
  AND array_length(array_distinct(regexp_split_to_array(db_object_taxon, '\|')), 1) < array_length(regexp_split_to_array(db_object_taxon, '\|'), 1);

CREATE VIEW IF NOT EXISTS GORULE_0000018_violations AS
SELECT internal_id, 'GORULE:0000018' AS rule
FROM gaf_association
WHERE evidence_type = 'IPI'
  AND with_or_from IS NULL;


CREATE VIEW IF NOT EXISTS gorule_view AS select * from duckdb_views() where view_name like 'GORULE%';

