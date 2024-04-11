CREATE VIEW IF NOT EXISTS isa_partof_closure AS
    SELECT
        e.subject AS id,
        group_concat(e.object,  '|') AS isa_partof_closure,
        group_concat(l.label, '|') AS isa_partof_label_closure
    FROM
        entailed_edge AS e
        INNER JOIN term_label AS l ON e.object = l.id
    WHERE
        e.predicate IN ('rdfs:subClassOf', 'BFO:0000050')
     GROUP BY
        e.subject;


-- regulates_closure
CREATE VIEW IF NOT EXISTS regulates_closure AS
SELECT
    e.subject AS id,
    group_concat(e.object,  '|') AS regulates_closure,
    group_concat(l.label, '|') AS regulates_label_closure
FROM
    entailed_edge AS e
    INNER JOIN term_label AS l ON e.object = l.id
WHERE
    e.predicate IN ('RO:0002211', 'RO:0002212', 'RO:0002213', 'rdfs:subClassOf', 'BFO:0000050')
GROUP BY
    e.subject;

-- taxon_closure
CREATE VIEW IF NOT EXISTS taxon_closure AS
SELECT
    e.subject AS id,
    group_concat(e.object,  '|') AS taxon_closure,
    group_concat(l.label, '|') AS taxon_label_closure
FROM
    entailed_edge AS e
    INNER JOIN term_label AS l ON e.object = l.id
WHERE
    e.predicate = 'rdfs:subClassOf'
GROUP BY
    e.subject;

-- evidence_closure
CREATE VIEW IF NOT EXISTS evidence_closure AS
SELECT
    e.subject AS id,
    group_concat(e.object,  '|') AS evidence_closure,
    group_concat(l.label, '|') AS evidence_label_closure
FROM
    entailed_edge AS e
    INNER JOIN term_label AS l ON e.object = l.id
WHERE
    e.predicate = 'rdfs:subClassOf'
GROUP BY
    e.subject;

-- isa_partof_closure
CREATE VIEW IF NOT EXISTS isa_partof_closure AS
SELECT
    e.subject AS id,
    group_concat(e.object,  '|') AS isa_partof_closure,
    group_concat(l.label, '|') AS isa_partof_label_closure
FROM
    entailed_edge AS e
    INNER JOIN term_label AS l ON e.object = l.id
WHERE
    e.predicate IN ('rdfs:subClassOf', 'BFO:0000050')
GROUP BY
    e.subject;

-- regulates_closure
CREATE VIEW IF NOT EXISTS regulates_closure AS
SELECT
    e.subject AS id,
    group_concat(e.object,  '|') AS regulates_closure,
    group_concat(l.label, '|') AS regulates_label_closure
FROM
    entailed_edge AS e
    INNER JOIN term_label AS l ON e.object = l.id
WHERE
    e.predicate IN ('RO:0002211', 'RO:0002212', 'RO:0002213')
GROUP BY
    e.subject;

-- taxon_closure
CREATE VIEW IF NOT EXISTS taxon_closure AS
SELECT
    e.subject AS id,
    group_concat(e.object,  '|') AS taxon_closure,
    group_concat(l.label, '|') AS taxon_label_closure
FROM
    entailed_edge AS e
    INNER JOIN term_label AS l ON e.object = l.id
WHERE
    e.predicate = 'rdfs:subClassOf'
GROUP BY
    e.subject;

-- evidence_closure
CREATE VIEW IF NOT EXISTS evidence_closure AS
SELECT
    e.subject AS id,
    group_concat(e.object,  '|') AS evidence_closure,
    group_concat(l.label, '|') AS evidence_label_closure
FROM
    entailed_edge AS e
    INNER JOIN term_label AS l ON e.object = l.id
WHERE
    e.predicate = 'rdfs:subClassOf'
GROUP BY
    e.subject;

-- amigo_ann_config_view
CREATE VIEW amigo_ann_config_view AS
SELECT
    concat_ws('_', a.subject, ontology_class_ref, internal_id::VARCHAR) AS id,
    db AS source,
    a.subject AS bioentity,
    a.db_object_symbol AS bioentity_label,
    a.db_object_symbol AS bioentity_label_searchable,
    a.db_object_name AS bioentity_name,
    a.db_object_name AS bioentity_name_searchable,
    a.db_object_id AS bioentity_internal_id,
    a.qualifiers_list AS qualifier,
    a.ontology_class_ref AS annotation_class,
    cls_lbl.label AS annotation_class_label,
    cls_lbl.label AS annotation_class_label_searchable,
    a.db_object_type AS type,
    a.annotation_date_string AS date,
    a.assigned_by,
    NULL AS is_redundant_for,
    isa.isa_partof_closure,
    isa.isa_partof_label_closure AS isa_partof_closure_label,
    isa.isa_partof_label_closure AS isa_partof_closure_label_searchable,
    reg.regulates_closure,
    reg.regulates_label_closure AS regulates_closure_label,
    reg.regulates_label_closure AS regulates_closure_label_searchable,
    a.db_object_taxon AS taxon,
    taxon_lbl.label AS taxon_label,
    taxon_lbl.label AS taxon_label_searchable,
    taxon.taxon_closure,
    taxon.taxon_label_closure AS taxon_closure_label,
    taxon.taxon_label_closure AS taxon_closure_label_searchable,
    NULL AS taxon_subset_closure,
    NULL AS taxon_subset_closure_label,
    NULL AS taxon_subset_closure_label_searchable,
    NULL AS secondary_taxon,
    NULL AS secondary_taxon_label,
    NULL AS secondary_taxon_label_searchable,
    NULL AS secondary_taxon_closure,
    NULL AS secondary_taxon_closure_label,
    NULL AS secondary_taxon_closure_label_searchable,
    NULL AS has_participant_closure,
    NULL AS has_participant_closure_label,
    NULL AS has_participant_closure_label_searchable,
    a.db_object_synonyms_list AS synonym,
    a.db_object_synonyms_list AS synonym_searchable,
    a.aspect,
    NULL AS bioentity_isoform,
    a.evidence_type,
    ev.evidence_closure AS evidence_type_closure,
    a.with_or_from_list AS evidence_with,
    a.with_or_from_list AS evidence_with_searchable,
    NULL AS evidence,
    NULL AS evidence_label,
    NULL AS evidence_label_searchable,
    NULL AS evidence_closure,
    NULL AS evidence_closure_label,
    NULL AS evidence_closure_label_searchable,
    NULL AS evidence_subset_closure,
    NULL AS evidence_subset_closure_label,
    NULL AS evidence_subset_closure_label_searchable,
    a.supporting_references_list AS reference,
    a.supporting_references_list AS reference_searchable,
    a.annotation_extensions_list AS annotation_extension_class,
    a.annotation_extensions_list AS annotation_extension_class_label,
    a.annotation_extensions_list AS annotation_extension_class_label_searchable,
    a.annotation_extensions_list AS annotation_extension_class_closure,
    a.annotation_extensions_list AS annotation_extension_class_closure_label,
    a.annotation_extensions_list AS annotation_extension_class_closure_label_searchable,
    a.annotation_extensions AS annotation_extension_json,
    NULL AS panther_family,
    NULL AS panther_family_searchable,
    NULL AS panther_family_label,
    NULL AS panther_family_label_searchable,
    NULL AS geospatial_x,
    NULL AS geospatial_y,
    NULL AS geospatial_z
FROM
    gaf_association AS a
    LEFT JOIN term_label AS cls_lbl ON a.ontology_class_ref = cls_lbl.id
    LEFT JOIN term_label AS taxon_lbl ON a.db_object_taxon = taxon_lbl.id
    LEFT JOIN isa_partof_closure AS isa ON a.ontology_class_ref = isa.id
    LEFT JOIN regulates_closure AS reg ON a.ontology_class_ref = reg.id
    LEFT JOIN taxon_closure AS taxon ON a.db_object_taxon = taxon.id
    LEFT JOIN evidence_closure AS ev ON a.evidence_type = ev.id;

