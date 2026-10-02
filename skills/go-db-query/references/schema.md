# GO-DB Schema Reference

This document describes the main tables and views available in GO-DB DuckDB databases (`~/repos/go-db/db/*.ddb`).

## Core Tables

### gaf_association_flat
Raw GAF (Gene Association File) data as loaded from source files.

**Columns:**
- `db` - Database source (e.g., "UniProtKB", "SGD", "FB")
- `db_object_id` - Object ID within database
- `db_object_symbol` - Gene symbol (e.g., "TP53")
- `qualifiers` - Pipe-separated qualifiers (e.g., "NOT|contributes_to")
- `ontology_class_ref` - GO term ID (e.g., "GO:0016301")
- `supporting_references` - Pipe-separated references (e.g., "PMID:12345|GO_REF:0000002")
- `evidence_type` - Evidence code (e.g., "IEA", "IDA", "IMP")
- `with_or_from` - Pipe-separated supporting identifiers
- `aspect` - GO aspect: "P" (biological process), "F" (molecular function), "C" (cellular component)
- `db_object_name` - Full gene/product name
- `db_object_synonyms` - Pipe-separated synonyms
- `db_object_type` - Type (e.g., "protein", "gene")
- `db_object_taxon` - NCBI Taxonomy ID (e.g., "taxon:9606")
- `annotation_date_string` - Date as YYYYMMDD string
- `assigned_by` - Annotation source (e.g., "SGD", "UniProt")
- `annotation_extensions` - Comma-separated extensions
- `gene_product_form` - Specific isoform if applicable

### gaf_association
Main denormalized view of Gene Ontology annotations with computed columns.

**Key columns (inherited from gaf_association_flat plus):**
- `internal_id` - Auto-generated sequence ID
- `annotation_date` - Parsed date object
- `subject` - Full subject ID (e.g., "UniProtKB:P12345", "SGD:S000001234")
- `qualifiers_list` - Array of qualifier strings
- `is_negation` - Boolean indicating NOT qualifier
- `with_or_from_list` - Array of supporting evidence
- `supporting_references_list` - Array of references
- `db_object_synonyms_list` - Array of synonyms
- `annotation_extensions_list` - Array of extensions

### gpi / gpi_version_1_2_flat
Gene product information from GPI files.

**Columns:**
- `db` - Database source
- `db_object_id` - Object ID
- `db_object_symbol` - Gene symbol
- `db_object_name` - Full name
- `db_object_synonyms` - Pipe-separated synonyms
- `db_object_type` - Type (e.g., "protein", "gene")
- `taxon` - NCBI Taxonomy ID
- `parent_object_id` - Parent object reference
- `db_xrefs` - Cross-references
- `properties` - Additional properties

### swissprot
Mapping of GAF subjects to SwissProt (reviewed UniProt) accessions.

**Columns:**
- `subject` - GAF subject as it appears (e.g., "UniProtKB:O14733" or "FB:FBgn0027570")
- `uniprot_accession` - The SwissProt accession

**Usage:** Join to identify reviewed/curated protein entries
```sql
SELECT g.*, s.subject IS NOT NULL as is_swissprot
FROM gaf_association g
LEFT JOIN swissprot s ON g.subject = s.subject
```

## Ontology Tables (from semsql)

### entailed_edge
Complete set of ontology relationships including transitive inferences.

**Columns:**
- `subject` - Source term ID (e.g., "GO:0016301")
- `predicate` - Relationship type (see predicates below)
- `object` - Target term ID (e.g., "GO:0016740")

**Common predicates:**
- `rdfs:subClassOf` - is-a relationship
- `BFO:0000050` - part-of relationship
- `RO:0002211` - regulates
- `RO:0002212` - negatively regulates
- `RO:0002213` - positively regulates

### edge
Asserted (direct) ontology relationships only. Same structure as `entailed_edge`.

### statements
Raw ontology statements including labels and metadata.

**Columns:**
- `subject` - Term ID
- `predicate` - Statement type
- `value` / `object` - Statement value

**Common predicates:**
- `rdfs:label` - Human-readable label
- `IAO:0000115` - Definition
- `oio:hasExactSynonym` - Exact synonym
- `oio:inSubset` - Subset membership

### rdfs_subclass_of_statement
Filtered view of just subClassOf statements from ontology.

## Closure Tables

Closure tables contain the **transitive closure** of relationships. These are critical for hierarchical queries.

### isa_partof_closure
Transitive closure of is-a and part-of relationships. This is the most commonly used closure table.

**Columns:**
- `subject` - Descendant term ID
- `predicate` - Relationship type ('rdfs:subClassOf' or 'BFO:0000050')
- `object` - Ancestor term ID

**Example:** If protein kinase is-a kinase, and kinase is-a catalytic activity, this table contains:
- (protein kinase, rdfs:subClassOf, kinase) - direct
- (kinase, rdfs:subClassOf, catalytic activity) - direct
- (protein kinase, rdfs:subClassOf, catalytic activity) - transitive/inferred

**Typical usage:** Find all annotations to a term OR any of its descendants.

```sql
SELECT a.*
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
WHERE ipc.object = 'GO:0016301';  -- finds all kinase annotations
```

### entailed_is_a (derived from entailed_edge)
Can be constructed as:
```sql
SELECT * FROM entailed_edge WHERE predicate = 'rdfs:subClassOf'
```

## Convenience Views

### term_label
Convenience view mapping term IDs to human-readable labels.

**Columns:**
- `id` - Term ID (e.g., "GO:0016301")
- `label` - Human-readable label (e.g., "kinase activity")

**Note:** Derived from statements table where predicate = 'rdfs:label'

### go_ref
GO Reference table with metadata about references.

**Columns:**
- `id` - GO_REF ID (e.g., "GO_REF:0000002")
- `title` - Reference title/description

### do_not_annotate_subset
Terms in the "do not annotate" subset.

**Columns:**
- `id` - Term ID that should not be used for direct annotation

## Analysis Views

### go_ref_summary
Summary of annotations by evidence type and GO_REF.

### gaf_unique_reference_contrib
Annotations that represent unique contributions (not redundant with more specific annotations).

### gaf_unique_reference_contrib_summary
Aggregated summary of unique contributions by evidence type and reference.

### pairwise_gaf_unique_reference_contrib_summary
Pairwise comparison of unique contributions between references.

### GORULE_*_violations
GO Rules validation views showing annotations that violate specific rules.

## Indices

Most databases have indices on:

### gaf_association_flat
- `(db_object_id, ontology_class_ref, evidence_type, supporting_references)` - Multi-column index for filtering

### isa_partof_closure
- `(subject, object)` - For join operations

### swissprot
- `(subject)` - For join lookups
- `(uniprot_accession)` - For reverse lookups

## Database Statistics

Typical database sizes:

| Database | Annotations | Size |
|----------|-------------|------|
| Small organism (SGD, PomBase) | ~100k-300k | ~300MB |
| Medium organism (goa_human, MGI) | ~1M | ~400MB |
| GOA GCRP | ~100M+ | ~35GB |
| GOA UniProt all | ~400M+ | ~90GB |

## Inspecting Schema

To see all tables/views in a database:

```bash
duckdb -readonly ~/repos/go-db/db/sgd.ddb \
  "SELECT table_name, table_type FROM information_schema.tables ORDER BY table_type, table_name"
```

To see columns in a table:

```bash
duckdb -readonly ~/repos/go-db/db/sgd.ddb "DESCRIBE gaf_association"
```

To see first few rows:

```bash
duckdb -readonly ~/repos/go-db/db/sgd.ddb "SELECT * FROM gaf_association LIMIT 5"
```
