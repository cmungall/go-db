CREATE SEQUENCE IF NOT EXISTS gaf_sequence;

CREATE TABLE IF NOT EXISTS gaf_association_flat (
        db TEXT NOT NULL,
        local_id TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS gaf_association (
        internal_id INTEGER PRIMARY KEY DEFAULT nextval('gaf_sequence'),
        db TEXT NOT NULL,
        local_id TEXT NOT NULL,
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
        gene_product_form TEXT,

        annotation_date DATE,
        subject TEXT NOT NULL,
        with_or_from_list TEXT[],
        supporting_references_list TEXT[],
        db_object_synonyms_list TEXT[],
        annotation_extensions_list TEXT[]
);
