CREATE SEQUENCE IF NOT EXISTS gaf_sequence;

CREATE TABLE IF NOT EXISTS gaf_association_flat (
        db TEXT NOT NULL,
        db_object_id TEXT NOT NULL,
        db_object_symbol TEXT NOT NULL,
        qualifiers VARCHAR,
        ontology_class_ref TEXT NOT NULL,
        supporting_references TEXT,
        evidence_type TEXT,
        with_or_from TEXT,
        aspect VARCHAR(1),
        db_object_name TEXT,
        db_object_synonyms TEXT,
        db_object_type VARCHAR,
        db_object_taxon TEXT,
        annotation_date_string TEXT,
        assigned_by TEXT,
        annotation_extensions TEXT,
        gene_product_form TEXT
);

--- TODO: have a direct negation column
CREATE VIEW gaf_association AS
SELECT
 nextval('gaf_sequence') AS internal_id,
        db,
        db_object_id,
        db_object_symbol,
        qualifiers,
        ontology_class_ref,
        supporting_references,
        evidence_type,
        with_or_from,
        aspect,
        db_object_name,
        db_object_synonyms,
        db_object_type,
        db_object_taxon,
        annotation_date_string,
        assigned_by,
        annotation_extensions,
        gene_product_form,
strptime(annotation_date_string, '%Y%m%d') AS annotation_date,
concat_ws(':', db, db_object_id) AS subject,
str_split(qualifiers, '|') AS qualifiers_list,
CASE WHEN qualifiers_list[1] = 'NOT' THEN true ELSE false END AS is_negation,
str_split(with_or_from, '|') AS with_or_from_list,
str_split(supporting_references, '|') AS supporting_references_list,
str_split(db_object_synonyms, '|') AS db_object_synonyms_list,
str_split(annotation_extensions, ',') AS annotation_extensions_list
FROM gaf_association_flat;

CREATE TABLE IF NOT EXISTS gpi_version_1_2_flat (
    db TEXT,
    db_object_id TEXT,
    db_object_symbol TEXT,
    db_object_name TEXT,
    db_object_synonyms TEXT,
    db_object_type TEXT,
    taxon TEXT,
    parent_object_id TEXT,
    db_xrefs TEXT,
    properties TEXT
);


--- TODO: make a union of 1.2 and 2.0 files
--- TODO make a column for OBO NCBITaxon ID for taxon
CREATE VIEW gpi AS
SELECT
  *,
  concat_ws(':', db, db_object_id) AS id,
    str_split(db_object_synonyms, '|') AS db_object_synonyms_list,
    str_split(db_xrefs, '|') AS db_xrefs_list,
    str_split(properties, '|') AS properties_list
FROM gpi_version_1_2_flat;

CREATE VIEW gpi_count_by_taxon AS
    SELECT taxon, count(*) AS count FROM gpi GROUP BY taxon;

CREATE VIEW gpi_db_xref AS
  SELECT id, unnest(db_xrefs_list) AS db_xref FROM gpi;

CREATE VIEW gpi_db_xref_with_db AS
  SELECT id, SPLIT_PART(db_xref, ':', 1) AS db, db_xref FROM gpi_db_xref;

CREATE VIEW gpi_db_xref_count_by_db AS
  SELECT db, count(*) AS count FROM gpi_db_xref_with_db GROUP BY db ORDER BY count DESC;

CREATE VIEW iba_term AS
  SELECT DISTINCT ontology_class_ref AS term FROM gaf_association
  WHERE evidence_type = 'IBA';

--- genes with no IBA annotations in each aspect
CREATE VIEW genes_with_no_iba_annotations AS
  SELECT db, db_object_id, db_object_symbol, db_object_taxon, db_object_type, aspect FROM gaf_association
  WHERE evidence_type != 'IBA'
  GROUP BY db, db_object_id, db_object_symbol, db_object_taxon, db_object_type, aspect
  HAVING count(*) = 1;

--- pivoted view with number of IBAs per gene in each of F, P, C
CREATE VIEW iba_count_by_gene AS
  SELECT db, db_object_id, db_object_symbol, db_object_taxon, db_object_type,
    count(*) FILTER (WHERE aspect = 'F') AS iba_count_F,
    count(*) FILTER (WHERE aspect = 'P') AS iba_count_P,
    count(*) FILTER (WHERE aspect = 'C') AS iba_count_C
  FROM gaf_association
  WHERE evidence_type = 'IBA'
  GROUP BY db, db_object_id, db_object_symbol, db_object_taxon, db_object_type;