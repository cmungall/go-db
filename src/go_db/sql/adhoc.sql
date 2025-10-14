-- pre-populate GO_REF table from 2 column CSV data/go_ref.csv

CREATE TABLE go_ref AS SELECT * FROM read_csv('data/go_refs.csv', header=true);
CREATE INDEX go_ref_id_idx_i ON go_ref(id);

CREATE OR REPLACE FUNCTION truncate_prefix(input_string) AS
    SUBSTRING(input_string, STRPOS(input_string, ':') + 1);


CREATE VIEW acts_upstream AS SELECT * FROM gaf_association WHERE qualifiers like 'acts_%';
CREATE VIEW involved_in AS SELECT * FROM gaf_association WHERE qualifiers like 'involved_in';

CREATE OR REPLACE VIEW do_not_annotate_subset AS
    SELECT subject AS id
    FROM statements
    WHERE predicate = 'oio:inSubset'
        AND object = 'obo:go#gocheck_do_not_annotate';




CREATE TABLE isa_partof_closure AS
SELECT
    e.subject,
    e.predicate,
    e.object
FROM
    entailed_edge e
WHERE
    e.predicate IN ('rdfs:subClassOf', 'BFO:0000050');

CREATE INDEX isa_partof_closure_subject_idx_so ON isa_partof_closure(subject, object);

CREATE OR REPLACE VIEW go_ref_summary AS
SELECT
    evidence_type,
    r.id,
    r.title,
    COUNT(*) AS count
FROM
    gaf_association_flat a
    INNER JOIN go_ref r ON (a.supporting_references = r.id)
WHERE evidence_type IN ('IEA', 'IBA')
GROUP BY
    evidence_type,
    r.id,
    r.title;

CREATE INDEX gaf_association_flat_meth ON
  gaf_association_flat(db_object_id, ontology_class_ref, evidence_type, supporting_references);

--- find unique contributions fromm a pub or GO_REF
CREATE OR REPLACE VIEW gaf_unique_reference_contrib AS
SELECT
    a.*
FROM
    gaf_association_flat a
WHERE (
            NOT EXISTS(SELECT 1
                         FROM gaf_association_flat a2
                                  INNER JOIN isa_partof_closure ipc ON a2.ontology_class_ref = ipc.subject
                         WHERE a2.supporting_references != a.supporting_references
                           AND ipc.object = a.ontology_class_ref
                           AND a2.db_object_id = a.db_object_id
                         )
              );

CREATE OR REPLACE VIEW gaf_unique_reference_contrib_term AS
    SELECT
        ontology_class_ref,evidence_type,supporting_references,count(*) AS association_count
    FROM gaf_unique_reference_contrib
    GROUP BY ontology_class_ref,evidence_type,supporting_references;

CREATE OR REPLACE VIEW gaf_unique_reference_contrib_term_l AS
    SELECT
        l.id,
        l.label,
        a.*
    FROM
        gaf_unique_reference_contrib_term as a INNER JOIN
        term_label as l ON (a.ontology_class_ref = l.id);

CREATE OR REPLACE VIEW gaf_unique_reference_contrib_summary AS
    SELECT
        evidence_type,supporting_references,count(*) AS association_count
    FROM gaf_unique_reference_contrib
    GROUP BY evidence_type,supporting_references;

--- find unique contributions fromm a pub or GO_REF
CREATE OR REPLACE VIEW pairwise_gaf_unique_reference_contrib AS
SELECT
    evidence_type,
    unique_ref.id AS unique_ref_id,
    unique_ref.title AS unique_ref_title,
    comparator_ref.id AS comparator_ref_id,
    comparator_ref.title AS comparator_ref_title,
    a.*
FROM
    gaf_association_flat a,
    go_ref unique_ref,
    go_ref comparator_ref
WHERE
    a.supporting_references = unique_ref.id
    AND EXISTS (SELECT 1 FROM gaf_association_flat a2 WHERE a2.supporting_references = comparator_ref.id)
    AND
       (
            NOT EXISTS(SELECT 1
                         FROM gaf_association_flat a2
                                  INNER JOIN isa_partof_closure ipc ON a2.ontology_class_ref = ipc.subject
                         WHERE a2.supporting_references = comparator_ref.id
                           AND ipc.object = a.ontology_class_ref
                           AND a2.db_object_id = a.db_object_id
                         )
              );

CREATE OR REPLACE VIEW pairwise_gaf_unique_reference_contrib_summary AS
      SELECT
            evidence_type,
            unique_ref_id,
            unique_ref_title,
            comparator_ref_id,
            comparator_ref_title,
            count(*) AS association_count
        FROM pairwise_gaf_unique_reference_contrib
        GROUP BY
            evidence_type,
            unique_ref_id,
            unique_ref_title,
            comparator_ref_id,
            comparator_ref_title;