---
name: go-db-query
description: Skills for querying Gene Ontology annotation databases in DuckDB format. Use this for queries about GO annotations, genes, terms, evidence codes, or taxonomic relationships in GO-DB databases (db/*.ddb files). Particularly useful for hierarchical queries using closure tables to find genes annotated to terms and their descendants.
---

# GO-DB Query Skill

## Overview

This skill provides expertise for querying GO-DB DuckDB databases containing Gene Ontology (GO) annotations. GO-DB databases store annotations linking genes/proteins to GO terms, along with the full GO ontology structure. The key feature is the use of **closure tables** that enable efficient hierarchical queries across the ontology graph.

Use this skill when working with queries involving:
- Finding genes annotated to specific GO terms (including descendants)
- Analyzing evidence codes and annotation sources
- Exploring ontology hierarchies and term relationships
- Computing annotation statistics by taxon, evidence, or other dimensions
- Identifying unique or redundant annotations using ontological reasoning

## Database Locations

All databases are in `~/repos/go-db/db/*.ddb`:

```bash
# List available databases
ls -lh ~/repos/go-db/db/*.ddb
```

### Common Databases

| Database | Description | Approx Size |
|----------|-------------|-------------|
| `goa_human.ddb` | Human GOA annotations | ~400MB |
| `mgi.ddb` | Mouse Genome Informatics | ~400MB |
| `sgd.ddb` | Saccharomyces Genome Database (yeast) | ~300MB |
| `pombase.ddb` | Fission yeast annotations | ~280MB |
| `fb.ddb` | FlyBase (Drosophila) | ~300MB |
| `zfin.ddb` | Zebrafish Information Network | ~300MB |
| `rgd.ddb` | Rat Genome Database | ~300MB |
| `wb.ddb` | WormBase (C. elegans) | ~300MB |
| `tair.ddb` | Arabidopsis annotations | ~300MB |
| `goa_uniprot_gcrp.ddb` | GOA GCRP (Gene-Centric Reference Proteome) | ~35GB |
| `goa_uniprot_all.ddb` | All UniProt GO annotations | ~90GB |
| `fungi.ddb` | All fungal annotations | ~10GB |
| `bacteria.ddb` | All bacterial annotations | ~23GB |
| `virus.ddb` | Viral annotations | varies |
| `archaea.ddb` | Archaeal annotations | ~700MB |

## Building New Databases

To build or rebuild databases, use the Makefile in `~/repos/go-db`:

```bash
cd ~/repos/go-db

# Build a specific organism database from GO annotation files
make db/sgd.ddb
make db/goa_human.ddb
make db/pombase.ddb

# Build taxonomic group databases
make db/fungi.ddb
make db/bacteria.ddb
make db/virus.ddb

# Convenience targets
make human     # builds db/goa_human.ddb
make fungi     # builds db/fungi.ddb
make bacteria  # builds db/bacteria.ddb

# Build for any taxon by ID
make db/taxon_9606.ddb  # human by taxon ID
```

### Loading Custom GAF Files

```bash
cd ~/repos/go-db
uv run go-db load -d db/mydb.ddb -g db/go.db path/to/annotations.gaf
```

## Executing Queries

### Command Line Usage

```bash
# Query a specific database
duckdb ~/repos/go-db/db/sgd.ddb "SELECT COUNT(*) FROM gaf_association"

# Interactive mode
duckdb ~/repos/go-db/db/sgd.ddb
D SELECT * FROM term_label WHERE label LIKE '%kinase%' LIMIT 10;
D .quit

# Export results to CSV
duckdb ~/repos/go-db/db/goa_human.ddb "COPY (SELECT ...) TO 'results.csv' (HEADER, DELIMITER ',')"

# Read-only mode (recommended for large databases)
duckdb -readonly ~/repos/go-db/db/goa_uniprot_gcrp.ddb
```

## Core Concepts

### Closure Tables

Closure tables are the heart of GO-DB querying. They contain the **transitive closure** of ontological relationships:

- **isa_partof_closure**: Contains all is-a and part-of relationships, both direct and inferred
  - Example: If "protein kinase" is-a "kinase" and "kinase" is-a "catalytic activity", the table includes all three relationships plus the transitive "protein kinase" -> "catalytic activity"

**How to use**: Join annotations with closure tables to find all genes annotated to a term OR its descendants

```sql
-- Find all yeast kinases (including specific types like protein kinase)
SELECT DISTINCT a.db_object_symbol, a.db_object_id
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
WHERE ipc.object = 'GO:0016301'  -- kinase activity
  AND a.db_object_taxon LIKE '%559292%';  -- yeast
```

## Key Query Patterns

### 1. Finding Genes by GO Term (with Closure)

The most common pattern: find all genes annotated to a term or its descendants.

```sql
SELECT DISTINCT
    a.db_object_symbol,
    a.ontology_class_ref,
    t.label AS term_label
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
INNER JOIN term_label t ON a.ontology_class_ref = t.id
WHERE ipc.object = '<GO_TERM_ID>'
  AND a.db_object_taxon LIKE '%<TAXON_ID>%';
```

### 2. Counting and Grouping Annotations

```sql
SELECT
    evidence_type,
    COUNT(*) AS annotation_count,
    COUNT(DISTINCT db_object_id) AS unique_genes
FROM gaf_association
WHERE <filters>
GROUP BY evidence_type
ORDER BY annotation_count DESC;
```

### 3. Finding Unique Contributions

Identify annotations that are not redundant with more specific annotations from other sources.

```sql
SELECT a.*
FROM gaf_association a
WHERE NOT EXISTS (
    SELECT 1
    FROM gaf_association a2
    INNER JOIN isa_partof_closure ipc ON a2.ontology_class_ref = ipc.subject
    WHERE a2.supporting_references != a.supporting_references
      AND ipc.object = a.ontology_class_ref  -- a2 is to a child term
      AND a2.db_object_id = a.db_object_id
);
```

### 4. Exploring Term Hierarchies

**Find direct children:**
```sql
SELECT DISTINCT e.subject, t.label
FROM edge e
INNER JOIN term_label t ON e.subject = t.id
WHERE e.object = '<GO_TERM_ID>'
  AND e.predicate = 'rdfs:subClassOf';
```

**Find all ancestors:**
```sql
SELECT DISTINCT ipc.object, t.label
FROM isa_partof_closure ipc
INNER JOIN term_label t ON ipc.object = t.id
WHERE ipc.subject = '<GO_TERM_ID>';
```

### 5. Genes Annotated to Multiple Terms

Find genes with annotations to both T1 and T2 (or their descendants).

```sql
SELECT DISTINCT a1.db_object_symbol, a1.db_object_id
FROM gaf_association a1
INNER JOIN isa_partof_closure ipc1 ON a1.ontology_class_ref = ipc1.subject
INNER JOIN gaf_association a2 ON a1.db_object_id = a2.db_object_id
INNER JOIN isa_partof_closure ipc2 ON a2.ontology_class_ref = ipc2.subject
WHERE ipc1.object = '<GO_TERM_1>'
  AND ipc2.object = '<GO_TERM_2>';
```

## Key Tables Reference

### gaf_association
Main annotation table with columns:
- `db_object_symbol`, `db_object_id`: Gene identifier and symbol
- `subject`: Full subject ID (e.g., "UniProtKB:P12345")
- `ontology_class_ref`: GO term ID (e.g., "GO:0016301")
- `evidence_type`: Evidence code (e.g., "IEA", "IDA")
- `db_object_taxon`: NCBI taxon ID (e.g., "taxon:9606")
- `aspect`: GO aspect - "P" (process), "F" (function), "C" (component)
- `supporting_references`: Reference IDs
- `assigned_by`: Annotation source

### isa_partof_closure
Transitive closure table with columns:
- `subject`: Descendant term ID
- `predicate`: Relationship type
- `object`: Ancestor term ID

### term_label
Term ID to label mapping:
- `id`: GO term ID
- `label`: Human-readable label

### entailed_edge
All ontology relationships (including inferred):
- `subject`, `predicate`, `object`

For complete schema documentation, refer to `references/schema.md`.

## Common Taxon IDs

- 9606: Human
- 10090: Mouse
- 559292: S. cerevisiae (yeast)
- 7227: D. melanogaster (fly)
- 284812: S. pombe (fission yeast)
- 6239: C. elegans (worm)
- 7955: D. rerio (zebrafish)
- 10116: Rat

## Common Evidence Codes

**Experimental**: IDA, IMP, IGI, IPI, IEP
**Computational**: IEA, ISS, ISO, ISA, ISM, IBA
**Curator/Author**: TAS, NAS, IC, ND

## Common GO_REFs for IEA Annotations

- `GO_REF:0000002`: InterPro2GO
- `GO_REF:0000003`: EC2GO
- `GO_REF:0000041`: UniProtKB-SubCell
- `GO_REF:0000043`: UniProtKB-KW
- `GO_REF:0000044`: UniProtKB-Seq
- `GO_REF:0000104`: PAINT
- `GO_REF:0000107`: Reactome
- `GO_REF:0000108`: GOC IBA

## Resources

- `references/schema.md` - Complete schema documentation
- `references/common_queries.md` - Comprehensive SQL examples

## Tips

- **Start simple**: Begin with basic queries and add complexity incrementally
- **Use EXPLAIN**: Check query plans for complex queries
- **LIMIT during development**: Add LIMIT to test queries on large databases
- **Check indices**: Closure tables have indices on subject/object pairs
- **Validate term IDs**: Verify GO term IDs exist in term_label before running
- **Use -readonly**: When querying large databases to avoid lock issues
