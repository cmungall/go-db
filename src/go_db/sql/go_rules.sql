CREATE VIEW IF NOT EXISTS entailed_is_a AS
  SELECT DISTINCT subject, object
    FROM entailed_edge
    WHERE predicate = 'rdfs:subClassOf';

CREATE VIEW IF NOT EXISTS obsolete_term AS
  SELECT DISTINCT subject AS id
    FROM statements
    WHERE predicate = 'owl:deprecated' AND value = 'true';

CREATE TABLE IF NOT EXISTS term_label AS
    SELECT DISTINCT subject AS id, value AS label
        FROM statements
        WHERE predicate = 'rdfs:label';

CREATE TABLE IF NOT EXISTS term_xref AS
    SELECT DISTINCT subject AS id, value AS xref
        FROM statements
        WHERE predicate = 'oio:hasDbXref';

CREATE VIEW IF NOT EXISTS term_ec AS
  WITH split_xref AS (
    SELECT
        id,
        xref,
        STRING_SPLIT(xref[4:], '.') AS parts
    FROM
        term_xref
    WHERE xref LIKE 'EC:%'
  )
  SELECT
    id,
    xref,
    parts[1] AS l1,
    parts[2] AS l2,
    parts[3] AS l3,
    parts[4] AS l4,
    ARRAY_LENGTH(FILTER(parts, x -> x != '-')) AS level
  FROM
    split_xref;

--- associations where the same gene is annotated two different l4 ECs
CREATE VIEW IF NOT EXISTS EC_rule_violation AS
SELECT DISTINCT a.internal_id, 'EC_rule' AS rule, a.db, a.db_object_id, a.ontology_class_ref AS t1, b.ontology_class_ref AS t2, e.xref AS ec1, e2.xref AS ec2, a.db_object_symbol, a.db_object_taxon
FROM gaf_association AS a,
    gaf_association AS b,
    term_ec AS e,
    term_ec AS e2
WHERE e.level = 4
 AND e2.level = 4
 AND a.db_object_id = b.db_object_id
    AND a.ontology_class_ref != b.ontology_class_ref
    AND a.db = b.db
    AND b.ontology_class_ref = e2.id
    AND a.ontology_class_ref = e.id
    AND a.ontology_class_ref IN (SELECT id FROM term_ec WHERE level = 4)
    AND b.ontology_class_ref IN (SELECT id FROM term_ec WHERE level = 4);

CREATE VIEW EC_rule_violation_by_taxon_summary AS
SELECT t1, t2, ec1, ec2, COUNT(distinct db_object_taxon) AS taxon_count
FROM EC_rule_violation GROUP BY t1, t2, ec1, ec2;

CREATE VIEW IF NOT EXISTS GORULE_0000002_violations AS
SELECT internal_id, 'GORULE:0000002' AS rule
FROM gaf_association
WHERE (ontology_class_ref = 'GO:0005488' OR ontology_class_ref = 'GO:0005515')
  AND qualifiers LIKE '%NOT%';

CREATE VIEW IF NOT EXISTS GORULE_0000004_violations  AS
SELECT DISTINCT a.internal_id, 'GORULE:0000004' AS rule
FROM gaf_association a
JOIN gaf_association b ON a.with_or_from = b.db_object_id AND a.db = b.db
WHERE a.ontology_class_ref = 'GO:0005515'
  AND NOT EXISTS (
    SELECT 1
    FROM gaf_association r
    WHERE r.db = b.db
      AND r.db_object_id = b.db_object_id
      AND r.with_or_from = a.db_object_id
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

CREATE OR REPLACE VIEW GORULE_0000008_violations AS
SELECT internal_id, 'GORULE:0000008' AS rule
FROM gaf_association
WHERE ontology_class_ref IN (
    SELECT subject FROM statements
                   WHERE predicate = 'oio:inSubset'
                     AND object = 'obo:go#gocheck_do_not_annotate'

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


CREATE VIEW IF NOT EXISTS GORULE_0000018_violations AS
SELECT internal_id, 'GORULE:0000018' AS rule
FROM gaf_association
WHERE evidence_type = 'IPI'
  AND with_or_from IS NULL;


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



CREATE VIEW IF NOT EXISTS gorule_view AS select * from duckdb_views() where view_name like 'GORULE%';

CREATE VIEW IF NOT EXISTS gorule_violations AS
SELECT *
FROM GORULE_0000002_violations
UNION
SELECT *
FROM GORULE_0000004_violations
UNION
SELECT *
FROM GORULE_0000005_violations
UNION
SELECT *
FROM GORULE_0000006_violations
UNION
SELECT *
FROM GORULE_0000007_violations
UNION
SELECT *
FROM GORULE_0000008_violations
UNION
SELECT *
FROM GORULE_0000013_violations
UNION
SELECT *
FROM GORULE_0000014_violations
UNION
SELECT *
FROM GORULE_0000016_violations
UNION
SELECT *
FROM GORULE_0000017_violations
UNION
SELECT *
FROM GORULE_0000022_violations
UNION
SELECT *
FROM GORULE_0000029_violations
UNION
SELECT *
FROM GORULE_0000015_violations
UNION
SELECT *
FROM GORULE_0000018_violations;

--- each violation turned into a list
CREATE VIEW IF NOT EXISTS gaf_association_plus_violations AS
SELECT a.*, string_agg(v.rule, ',') AS violations
FROM gaf_association a
LEFT JOIN gorule_violations v ON a.internal_id = v.internal_id
GROUP BY a.*;