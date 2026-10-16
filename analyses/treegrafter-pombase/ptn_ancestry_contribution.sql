-- PomBase contribution to TreeGrafter annotations, following PANTHER tree ancestry.
-- Run from the repository root with DuckDB against a GO-DB database (read-only is sufficient),
-- after generating tmp/treegrafter-pombase/ptn_edges.tsv (see Makefile target treegrafter-pombase).
--
-- A TreeGrafter annotation (GO_REF:0000118) records the PTN it was grafted onto.
-- Its GO term is inherited from an ancestor-or-self PTN carrying an IBD; IBA rows
-- record that IBD node in with_or_from, and PomBase: identifiers there show
-- PomBase experimental evidence behind it.
--
-- Rules, all evaluated over ancestor-or-self PTNs A of the graft PTN G:
--   resolvable    : some A has an IBA for the same GO term
--   pombase_term  : some A has an IBA for the same GO term citing PomBase
--   pombase_only  : pombase_term, and no IBA for that term at any A cites another source
--   pombase_any   : some A has any IBA (any GO term) citing PomBase (broad PTN-level rule)
SET threads = 8;
SET memory_limit = '24GB';

CREATE TEMP TABLE ptn_edge AS
SELECT * FROM read_csv('tmp/treegrafter-pombase/ptn_edges.tsv', delim = '\t', header = true);

CREATE TEMP TABLE iba_node_term AS
WITH iba AS (
    SELECT DISTINCT ontology_class_ref, with_or_from
    FROM gaf_association
    WHERE evidence_type = 'IBA'
)
SELECT
    regexp_extract(with_or_from, 'PANTHER:PTN[0-9]+') AS node,
    ontology_class_ref,
    BOOL_OR(regexp_matches(with_or_from, '(^|[|,])PomBase:')) AS has_pombase,
    BOOL_OR(LEN(LIST_FILTER(
        regexp_split_to_array(with_or_from, '[|,]'),
        r -> r <> '' AND r NOT LIKE 'PANTHER:%' AND r NOT LIKE 'PomBase:%'
    )) > 0) AS has_other_source
FROM iba
GROUP BY ALL;

CREATE TEMP TABLE iba_node AS
SELECT node, BOOL_OR(has_pombase) AS has_pombase
FROM iba_node_term
GROUP BY node;

CREATE TEMP TABLE treegrafter_node_term AS
SELECT with_or_from AS node, ontology_class_ref, COUNT(*) AS annotation_count
FROM gaf_association
WHERE supporting_references = 'GO_REF:0000118'
GROUP BY ALL;

-- ancestor-or-self closure from each TreeGrafter graft node, restricted to IBA nodes
CREATE TEMP TABLE graft_ancestor AS
WITH RECURSIVE up(graft, ancestor) AS (
    SELECT DISTINCT node, node FROM treegrafter_node_term
    UNION ALL
    SELECT up.graft, e.parent
    FROM up
    INNER JOIN ptn_edge e ON e.child = up.ancestor
)
SELECT up.*
FROM up
INNER JOIN iba_node n ON n.node = up.ancestor;

CREATE TEMP TABLE treegrafter_flags AS
SELECT
    t.node,
    t.ontology_class_ref,
    t.annotation_count,
    COALESCE(BOOL_OR(nt.node IS NOT NULL), FALSE) AS resolvable,
    COALESCE(BOOL_OR(nt.has_pombase), FALSE) AS pombase_term,
    COALESCE(BOOL_OR(nt.has_pombase) AND NOT BOOL_OR(nt.has_other_source), FALSE) AS pombase_only,
    COALESCE(BOOL_OR(n.has_pombase), FALSE) AS pombase_any,
    COALESCE(BOOL_OR(ga.ancestor = t.node), FALSE) AS graft_is_iba_node
FROM treegrafter_node_term t
LEFT JOIN graft_ancestor ga ON ga.graft = t.node
LEFT JOIN iba_node n ON n.node = ga.ancestor
LEFT JOIN iba_node_term nt ON nt.node = ga.ancestor AND nt.ontology_class_ref = t.ontology_class_ref
GROUP BY t.node, t.ontology_class_ref, t.annotation_count;

-- Sanity: how many TreeGrafter graft nodes are in the PANTHER 19 trees
SELECT
    COUNT(*) AS treegrafter_nodes,
    COUNT(*) FILTER (WHERE node IN (SELECT child FROM ptn_edge UNION SELECT parent FROM ptn_edge))
        AS nodes_in_trees
FROM (SELECT DISTINCT node FROM treegrafter_node_term);

-- Overall
SELECT
    SUM(annotation_count) AS treegrafter_total,
    SUM(annotation_count) FILTER (WHERE resolvable) AS resolvable,
    SUM(annotation_count) FILTER (WHERE pombase_term) AS pombase_term,
    SUM(annotation_count) FILTER (WHERE pombase_only) AS pombase_only,
    SUM(annotation_count) FILTER (WHERE pombase_any) AS pombase_any_term,
    SUM(annotation_count) FILTER (WHERE graft_is_iba_node AND pombase_any) AS pombase_any_direct_graft_only
FROM treegrafter_flags;

-- By clade, using the NCBITaxon closure in isa_partof_closure.
-- Each taxon is assigned to the first matching clade in priority order.
CREATE TEMP TABLE clade (clade_id VARCHAR, clade_label VARCHAR, priority INTEGER);
INSERT INTO clade VALUES
    ('NCBITaxon:2', 'Bacteria', 1),
    ('NCBITaxon:2157', 'Archaea', 2),
    ('NCBITaxon:4751', 'Fungi', 3),
    ('NCBITaxon:33208', 'Metazoa', 4),
    ('NCBITaxon:33090', 'Viridiplantae', 5),
    ('NCBITaxon:2759', 'Other Eukaryota', 6),
    ('NCBITaxon:10239', 'Viruses', 7);

CREATE TEMP TABLE treegrafter_by_taxon AS
SELECT
    replace(split_part(a.db_object_taxon, '|', 1), 'taxon:', 'NCBITaxon:') AS taxon,
    COUNT(*) AS treegrafter_total,
    COUNT(*) FILTER (WHERE f.resolvable) AS resolvable,
    COUNT(*) FILTER (WHERE f.pombase_term) AS pombase_term,
    COUNT(*) FILTER (WHERE f.pombase_only) AS pombase_only,
    COUNT(*) FILTER (WHERE f.pombase_any) AS pombase_any_term
FROM gaf_association a
INNER JOIN treegrafter_flags f
    ON f.node = a.with_or_from AND f.ontology_class_ref = a.ontology_class_ref
WHERE a.supporting_references = 'GO_REF:0000118'
GROUP BY ALL;

CREATE TEMP TABLE taxon_clade AS
SELECT taxon, ARG_MIN(c.clade_label, c.priority) AS clade_label
FROM treegrafter_by_taxon t
INNER JOIN isa_partof_closure ipc ON ipc.subject = t.taxon
INNER JOIN clade c ON ipc.object = c.clade_id
GROUP BY taxon;

CREATE TEMP TABLE clade_summary AS
SELECT
    CASE WHEN GROUPING(tc.clade_label) = 1 THEN 'ALL' ELSE COALESCE(tc.clade_label, 'Unmapped') END AS clade,
    SUM(treegrafter_total) AS treegrafter_total,
    SUM(resolvable) AS resolvable,
    SUM(pombase_term) AS pombase_term,
    SUM(pombase_only) AS pombase_only,
    SUM(pombase_any_term) AS pombase_any_term,
    ROUND(100 * SUM(resolvable) / SUM(treegrafter_total), 1) AS pct_resolvable,
    ROUND(100 * SUM(pombase_term) / SUM(treegrafter_total), 1) AS pct_pombase_term,
    ROUND(100 * SUM(pombase_term) / SUM(resolvable), 1) AS pct_pombase_term_of_resolvable,
    ROUND(100 * SUM(pombase_only) / SUM(resolvable), 1) AS pct_pombase_only_of_resolvable,
    COUNT(*) FILTER (WHERE pombase_term > 0) AS taxa_reached
FROM treegrafter_by_taxon t
LEFT JOIN taxon_clade tc USING (taxon)
GROUP BY ROLLUP (tc.clade_label)
ORDER BY treegrafter_total DESC;

SELECT * FROM clade_summary;
COPY clade_summary TO 'analyses/treegrafter-pombase/viz/out/clades.json' (FORMAT JSON, ARRAY true);
