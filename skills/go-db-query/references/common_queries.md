# Common GO-DB Query Patterns

This document provides SQL query patterns for common GO-DB operations. All queries can be executed via `duckdb` on the command line.

## Pattern 1: Find Genes Annotated to a Term (Using Closure)

Find all genes annotated to a specific GO term OR any of its descendant terms.

### Example: All yeast genes that are kinases

```sql
SELECT DISTINCT
    a.db_object_symbol,
    a.db_object_id,
    a.db_object_name,
    a.ontology_class_ref,
    t.label AS term_label
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
INNER JOIN term_label t ON a.ontology_class_ref = t.id
WHERE ipc.object = 'GO:0016301'  -- kinase activity
  AND a.db_object_taxon LIKE '%559292%';  -- S. cerevisiae taxon ID
```

**How it works:**
- Join annotations table with `isa_partof_closure` on the annotated term
- Filter where the closure's `object` (ancestor) is the target term
- This finds both direct annotations AND annotations to descendant terms
- Add taxon filter to restrict to specific organism

### Example: Count all annotations to nucleus (including descendants)

```sql
SELECT COUNT(*)
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
WHERE ipc.object = 'GO:0005634';  -- nucleus
```

### Variation: Include term labels in results

```sql
SELECT DISTINCT
    a.db_object_symbol,
    a.ontology_class_ref,
    t.label AS annotated_term_label,
    parent.label AS parent_term_label
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
INNER JOIN term_label t ON a.ontology_class_ref = t.id
INNER JOIN term_label parent ON ipc.object = parent.id
WHERE ipc.object = 'GO:0016301'  -- kinase activity
  AND a.db_object_taxon LIKE '%9606%';  -- human
```

## Pattern 2: Count Annotations by Taxon/Evidence

Group and aggregate annotations by various dimensions.

### Example: Count annotations by evidence type

```sql
SELECT
    evidence_type,
    COUNT(*) AS annotation_count,
    COUNT(DISTINCT db_object_id) AS unique_genes
FROM gaf_association
GROUP BY evidence_type
ORDER BY annotation_count DESC;
```

### Example: Count annotations by taxon for a specific term

```sql
SELECT
    db_object_taxon,
    COUNT(*) AS annotation_count
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
WHERE ipc.object = 'GO:0016301'  -- kinase activity
GROUP BY db_object_taxon
ORDER BY annotation_count DESC
LIMIT 20;
```

### Example: Evidence breakdown by aspect (P/F/C)

```sql
SELECT
    aspect,
    evidence_type,
    COUNT(*) AS annotation_count
FROM gaf_association
GROUP BY aspect, evidence_type
ORDER BY aspect, annotation_count DESC;
```

### Example: Annotations per organism database

```sql
SELECT
    assigned_by,
    COUNT(*) AS total_annotations,
    COUNT(DISTINCT ontology_class_ref) AS unique_terms,
    COUNT(DISTINCT db_object_id) AS unique_genes
FROM gaf_association
GROUP BY assigned_by
ORDER BY total_annotations DESC;
```

## Pattern 3: Find Unique/Redundant Annotations

Identify annotations that are unique contributions or redundant with more specific annotations.

### Example: Find unique contributions from a specific reference

Find annotations that are NOT redundant with more specific (child term) annotations from other references.

```sql
SELECT DISTINCT
    a.db_object_symbol,
    a.ontology_class_ref,
    t.label AS term_label,
    a.supporting_references,
    a.evidence_type
FROM gaf_association a
INNER JOIN term_label t ON a.ontology_class_ref = t.id
WHERE a.supporting_references = 'GO_REF:0000108'  -- specific reference
  AND NOT EXISTS (
    SELECT 1
    FROM gaf_association a2
    INNER JOIN isa_partof_closure ipc ON a2.ontology_class_ref = ipc.subject
    WHERE a2.supporting_references != a.supporting_references  -- different reference
      AND ipc.object = a.ontology_class_ref  -- a2 is to a child term
      AND a2.db_object_id = a.db_object_id   -- same gene
  );
```

**How it works:**
- For each annotation (a), check if there's another annotation (a2)
- Where a2 is to a MORE SPECIFIC term (child in the hierarchy)
- And a2 comes from a DIFFERENT reference
- If no such a2 exists, then a is a "unique contribution"

### Example: Find redundant IEA annotations

Find IEA (electronic) annotations that are redundant with experimental evidence on parent terms.

```sql
SELECT
    a.db_object_symbol,
    a.ontology_class_ref AS iea_term,
    t.label AS iea_term_label,
    a.evidence_type
FROM gaf_association a
INNER JOIN term_label t ON a.ontology_class_ref = t.id
WHERE a.evidence_type = 'IEA'
  AND EXISTS (
    SELECT 1
    FROM gaf_association a2
    INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
    WHERE a2.evidence_type IN ('IDA', 'IMP', 'IGI', 'IPI')  -- experimental evidence
      AND ipc.object = a2.ontology_class_ref  -- a2 is to a parent term
      AND a2.db_object_id = a.db_object_id    -- same gene
  )
LIMIT 100;
```

## Pattern 4: Term Lookup and Hierarchy

Explore the ontology structure itself.

### Example: Find all direct children of a term

```sql
SELECT DISTINCT
    e.subject AS child_id,
    t.label AS child_label
FROM edge e
INNER JOIN term_label t ON e.subject = t.id
WHERE e.object = 'GO:0016301'  -- kinase activity
  AND e.predicate = 'rdfs:subClassOf'
ORDER BY child_label;
```

### Example: Find all ancestors of a term

```sql
SELECT DISTINCT
    ipc.object AS ancestor_id,
    t.label AS ancestor_label,
    ipc.predicate
FROM isa_partof_closure ipc
INNER JOIN term_label t ON ipc.object = t.id
WHERE ipc.subject = 'GO:0004672'  -- protein kinase activity
ORDER BY ancestor_label;
```

### Example: Count descendants of a term

```sql
SELECT COUNT(DISTINCT subject) AS descendant_count
FROM isa_partof_closure
WHERE object = 'GO:0016301';  -- kinase activity
```

### Example: Search for terms by label

```sql
SELECT id, label
FROM term_label
WHERE label LIKE '%kinase%'
ORDER BY label;
```

### Example: Get term definition

```sql
SELECT value AS definition
FROM statements
WHERE subject = 'GO:0016301'
  AND predicate = 'IAO:0000115';  -- definition predicate
```

## Pattern 5: Genes Annotated to Both T1 and T2 (Using Closure)

Find genes with annotations to multiple terms, using closure to include descendant terms.

### Example: Genes that are both kinases AND membrane proteins

```sql
SELECT DISTINCT
    a1.db_object_symbol,
    a1.db_object_id,
    a1.db_object_name
FROM gaf_association a1
INNER JOIN isa_partof_closure ipc1 ON a1.ontology_class_ref = ipc1.subject
INNER JOIN gaf_association a2 ON a1.db_object_id = a2.db_object_id
INNER JOIN isa_partof_closure ipc2 ON a2.ontology_class_ref = ipc2.subject
WHERE ipc1.object = 'GO:0016301'  -- kinase activity
  AND ipc2.object = 'GO:0016020'  -- membrane
  AND a1.db_object_taxon LIKE '%9606%';  -- human
```

**How it works:**
- Join gaf_association twice (a1 and a2) on the same gene (db_object_id)
- Join each with closure tables (ipc1 and ipc2)
- Filter where ipc1 ancestors include term T1
- Filter where ipc2 ancestors include term T2
- Result: genes annotated to (T1 OR descendants) AND (T2 OR descendants)

### Variation: Genes in process P with function F

```sql
SELECT DISTINCT
    a1.db_object_symbol,
    a1.db_object_id,
    t1.label AS function_term,
    t2.label AS process_term
FROM gaf_association a1
INNER JOIN isa_partof_closure ipc1 ON a1.ontology_class_ref = ipc1.subject
INNER JOIN term_label t1 ON a1.ontology_class_ref = t1.id
INNER JOIN gaf_association a2 ON a1.db_object_id = a2.db_object_id
INNER JOIN isa_partof_closure ipc2 ON a2.ontology_class_ref = ipc2.subject
INNER JOIN term_label t2 ON a2.ontology_class_ref = t2.id
WHERE ipc1.object = 'GO:0016301'  -- kinase activity (F)
  AND ipc2.object = 'GO:0007165'  -- signal transduction (P)
  AND a1.aspect = 'F'
  AND a2.aspect = 'P'
  AND a1.db_object_taxon LIKE '%559292%';  -- yeast
```

### Example: Genes NOT annotated to a specific term

Find genes annotated to T1 but NOT to T2 (or its descendants).

```sql
SELECT DISTINCT
    a.db_object_symbol,
    a.db_object_id
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
WHERE ipc.object = 'GO:0016301'  -- kinase activity
  AND a.db_object_taxon LIKE '%559292%'  -- yeast
  AND NOT EXISTS (
    SELECT 1
    FROM gaf_association a2
    INNER JOIN isa_partof_closure ipc2 ON a2.ontology_class_ref = ipc2.subject
    WHERE a2.db_object_id = a.db_object_id
      AND ipc2.object = 'GO:0005634'  -- nucleus
  );
```

## Pattern 6: Evidence Analysis

Analyze evidence codes and their relationships.

### Example: Compare evidence types for a term

```sql
SELECT
    evidence_type,
    COUNT(*) AS annotation_count,
    COUNT(DISTINCT db_object_id) AS unique_genes
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
WHERE ipc.object = 'GO:0016301'  -- kinase activity
GROUP BY evidence_type
ORDER BY annotation_count DESC;
```

### Example: Find genes with conflicting annotations (with/without NOT)

```sql
SELECT DISTINCT
    a1.db_object_symbol,
    a1.db_object_id,
    a1.ontology_class_ref,
    t.label
FROM gaf_association a1
INNER JOIN gaf_association a2 ON a1.db_object_id = a2.db_object_id
    AND a1.ontology_class_ref = a2.ontology_class_ref
INNER JOIN term_label t ON a1.ontology_class_ref = t.id
WHERE a1.is_negation = false
  AND a2.is_negation = true;
```

## Pattern 7: Reference and Citation Analysis

Analyze publications and their contributions.

### Example: Most cited papers for a term

```sql
SELECT
    a.supporting_references,
    COUNT(*) AS citation_count,
    COUNT(DISTINCT db_object_id) AS unique_genes
FROM gaf_association a
INNER JOIN isa_partof_closure ipc ON a.ontology_class_ref = ipc.subject
WHERE ipc.object = 'GO:0016301'  -- kinase activity
  AND a.supporting_references LIKE 'PMID:%'
GROUP BY a.supporting_references
ORDER BY citation_count DESC
LIMIT 20;
```

### Example: Annotations added in a specific date range

```sql
SELECT
    COUNT(*) AS new_annotations,
    COUNT(DISTINCT db_object_id) AS unique_genes,
    COUNT(DISTINCT ontology_class_ref) AS unique_terms
FROM gaf_association
WHERE annotation_date >= '2024-01-01'
  AND annotation_date < '2024-02-01';
```

## Tips for Effective Queries

1. **Always use closure tables for hierarchical queries** - Don't just match ontology_class_ref directly
2. **Add DISTINCT when needed** - Closure joins can create duplicates
3. **Filter early** - Apply taxon and evidence filters before joins when possible
4. **Use term_label for readability** - Join with term_label to show human-readable names
5. **Check for indices** - Most databases have indices on subject/object in closures
6. **Limit large results** - Use LIMIT for exploratory queries on large databases
7. **Use EXPLAIN** - Run `EXPLAIN` before complex queries to understand query plans

## Common Taxon IDs

- 9606: Homo sapiens (human)
- 10090: Mus musculus (mouse)
- 559292: Saccharomyces cerevisiae S288C (yeast)
- 7227: Drosophila melanogaster (fruit fly)
- 6239: Caenorhabditis elegans (worm)
- 3702: Arabidopsis thaliana (plant)
- 284812: Schizosaccharomyces pombe (fission yeast)

## Common Evidence Codes

**Experimental:**
- IDA: Inferred from Direct Assay
- IMP: Inferred from Mutant Phenotype
- IGI: Inferred from Genetic Interaction
- IPI: Inferred from Physical Interaction
- IEP: Inferred from Expression Pattern

**Computational:**
- IEA: Inferred from Electronic Annotation
- ISS: Inferred from Sequence or Structural Similarity
- ISO: Inferred from Sequence Orthology
- ISA: Inferred from Sequence Alignment
- ISM: Inferred from Sequence Model
- IBA: Inferred from Biological aspect of Ancestor

**Author/Curator:**
- TAS: Traceable Author Statement
- NAS: Non-traceable Author Statement
- IC: Inferred by Curator
- ND: No biological Data available
