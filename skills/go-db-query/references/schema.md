# GO-DB Schema Reference

This document describes the main tables and views available in GO-DB DuckDB databases (db/*.ddb).

## Core Tables

### gaf_association
Main denormalized view of Gene Ontology annotations.

**Key columns:**
- `subject` - Gene/product identifier (e.g., "UniProtKB:P12345")
- `db` - Database source (e.g., "UniProtKB")
- `db_object_id` - Object ID within database
- `db_object_symbol` - Gene symbol (e.g., "TP53")
- `db_object_name` - Full gene/product name
- `ontology_class_ref` - GO term ID (e.g., "GO:0016301")
- `evidence_type` - Evidence code (e.g., "IEA", "IDA", "IMP")
- `db_object_taxon` - NCBI Taxonomy ID (e.g., "taxon:9606" for human)
- `aspect` - GO aspect: "P" (biological process), "F" (molecular function), or "C" (cellular component)
- `supporting_references` - Reference IDs (e.g., "PMID:12345678")
- `assigned_by` - Annotation source (e.g., "SGD", "UniProt")
- `annotation_date` - Date of annotation
- `is_negation` - Boolean indicating NOT qualifier
- `qualifiers_list` - Array of qualifier strings
- `with_or_from_list` - Array of supporting evidence
- `supporting_references_list` - Array of references

### gpi_version_1_2
Gene product information.

**Key columns:**
- `db` - Database source
- `db_object_id` - Object ID
- `db_object_symbol` - Gene symbol
- `db_object_name` - Full name
- `db_object_type` - Type (e.g., "protein", "gene")
- `taxon` - NCBI Taxonomy ID
- `parent_object_id` - Parent object reference

## Ontology Tables

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
- `predicate` - Statement type (e.g., "rdfs:label", "IAO:0000115" for definitions)
- `value` - Statement value

### term_label
Convenience view mapping term IDs to human-readable labels.

**Columns:**
- `id` - Term ID (e.g., "GO:0016301")
- `label` - Human-readable label (e.g., "kinase activity")

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

### regulates_closure
Transitive closure of regulation relationships.

**Structure:** Similar to isa_partof_closure but for RO:0002211/0002212/0002213 predicates.

### taxon_closure
Transitive closure of taxonomic relationships.

**Structure:** Similar to isa_partof_closure but specifically for taxonomic hierarchies.

## Common Indices

Most tables have indices on:
- Subject/object columns in closure tables
- ontology_class_ref in annotation tables
- db_object_id for gene lookups
- taxon for organism filtering

## Database Statistics

Typical database sizes:
- Small organism DBs (e.g., SGD yeast): ~100k annotations
- Large organism DBs (e.g., goa_human): ~1M annotations
- GOA UniProt all: ~400M+ annotations

## Views and Materialized Tables

Many databases include additional views:
- `amigo_ann_config_view` - Denormalized view with all closures pre-joined
- `gaf_unique_reference_contrib` - Annotations that are unique contributions
- `GORULE_*_violations` - GO rules validation views
- Various evidence analysis views

Consult the source code in `src/go_db/sql/` for complete view definitions.
