CREATE OR REPLACE FUNCTION truncate_prefix(input_string) AS
    SUBSTRING(input_string, STRPOS(input_string, ':') + 1);


CREATE VIEW acts_upstream AS SELECT * FROM gaf_association WHERE qualifiers like 'acts_%';
CREATE VIEW involved_in AS SELECT * FROM gaf_association WHERE qualifiers like 'involved_in';


SELECT
    u.gene,
    a.ontology_class_ref,
    a.*
FROM
    gaf_association a,
    UNNEST(a.with_or_from_list) AS u(gene),
    acts_upstream au
WHERE
    a.evidence_type = 'IBA'
    AND a.qualifiers = 'involved_in'
    AND u.gene LIKE 'MGI%'
    AND au.db_object_id = truncate_prefix(u.gene)
    AND au.ontology_class_ref = a.ontology_class_ref
    ;

SELECT
    u.gene,
    a.ontology_class_ref,
    a.*
FROM
    gaf_association a,
    UNNEST(a.with_or_from_list) AS u(gene),
    acts_upstream au
WHERE
    a.evidence_type = 'IBA'
    AND a.qualifiers = 'involved_in'
    AND u.gene LIKE 'MGI%'
    AND au.db_object_id = truncate_prefix(u.gene)
    AND au.ontology_class_ref = a.ontology_class_ref
    AND NOT EXISTS (
        SELECT 1
        FROM involved_in ii
        WHERE ii.db_object_id = truncate_prefix(u.gene)
        AND ii.ontology_class_ref = a.ontology_class_ref
        AND evidence_type != 'IBA'
    )
    ;


CREATE TABLE isa_partof_closure AS
SELECT
    e.subject,
    e.predicate,
    e.object
FROM
    entailed_edge e
WHERE
    e.predicate IN ('rdfs:subClassOf', 'BFO:0000050');
--- find unique contributions fromm a pub or GO_REF

CREATE OR REPLACE VIEW gaf_unique_reference_contrib AS
SELECT
    a.*
FROM
    gaf_association a
WHERE (
            NOT EXISTS(SELECT 1
                         FROM gaf_association a2
                                  INNER JOIN isa_partof_closure ipc ON a2.ontology_class_ref = ipc.subject
                         WHERE a2.supporting_references != a.supporting_references
                           AND ipc.object = a.ontology_class_ref
                           AND a2.db_object_id = a.db_object_id
                         )
              );

CREATE OR REPLACE VIEW gaf_unique_reference_contrib_summary AS
    SELECT
        evidence_type,supporting_references,count(*)
    FROM gaf_unique_reference_contrib
    GROUP BY evidence_type,supporting_references;