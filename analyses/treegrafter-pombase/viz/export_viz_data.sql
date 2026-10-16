-- Export the data behind the PomBase-via-TreeGrafter page.
-- Run from the repository root against goa_uniprot_all.ddb (read-only):
--   duckdb -readonly <db> < analyses/treegrafter-pombase/viz/export_viz_data.sql
-- Needs ptn_edges.tsv and the PAINT AN->PTN file in tmp/treegrafter-pombase/
-- (see Makefile target treegrafter-pombase). Writes small JSON files to analyses/treegrafter-pombase/viz/out/.
SET threads = 8;
SET memory_limit = '24GB';

CREATE TEMP TABLE ptn_edge AS
SELECT * FROM read_csv('tmp/treegrafter-pombase/ptn_edges.tsv', delim = '\t', header = true);

CREATE TEMP TABLE an AS
SELECT split_part(column0, ':', 1) AS fam, split_part(column0, ':', 2) AS an, 'PANTHER:' || column2 AS ptn
FROM read_csv('tmp/treegrafter-pombase/PAINT_TreeGrafter_Annotations_TOTAL.txt.gz',
    delim = '\t', header = false, columns = {'column0': 'VARCHAR', 'column1': 'VARCHAR', 'column2': 'VARCHAR'});

CREATE TEMP TABLE iba_node_term AS
WITH iba AS (
    SELECT DISTINCT ontology_class_ref, with_or_from
    FROM gaf_association
    WHERE evidence_type = 'IBA'
)
SELECT
    regexp_extract(with_or_from, 'PANTHER:PTN[0-9]+') AS node,
    ontology_class_ref,
    BOOL_OR(regexp_matches(with_or_from, '(^|[|,])PomBase:')) AS has_pombase
FROM iba
GROUP BY ALL;

CREATE TEMP TABLE tnt AS
SELECT with_or_from AS node, ontology_class_ref, COUNT(*) AS n
FROM gaf_association
WHERE supporting_references = 'GO_REF:0000118'
GROUP BY ALL;

CREATE TEMP TABLE up AS
WITH RECURSIVE up(graft, ancestor, depth) AS (
    SELECT DISTINCT node, node, 0 FROM tnt
    UNION ALL
    SELECT up.graft, e.parent, depth + 1 FROM up INNER JOIN ptn_edge e ON e.child = up.ancestor
)
SELECT * FROM up WHERE ancestor IN (SELECT node FROM iba_node_term);

-- nearest same-term IBA ancestor-or-self for each graft node and GO term
CREATE TEMP TABLE nearest AS
SELECT
    t.node AS graft, t.ontology_class_ref, t.n,
    ARG_MIN(up.ancestor, up.depth) AS src,
    MIN(up.depth) AS depth,
    ARG_MIN(nt.has_pombase, up.depth) AS src_pombase,
    BOOL_OR(nt.has_pombase) AS any_pombase
FROM tnt t
INNER JOIN up ON up.graft = t.node
INNER JOIN iba_node_term nt ON nt.node = up.ancestor AND nt.ontology_class_ref = t.ontology_class_ref
GROUP BY ALL;

COPY (
    SELECT SUM(n) AS resolved, SUM(n) FILTER (WHERE src_pombase) AS nearest_pombase,
        SUM(n) FILTER (WHERE any_pombase) AS any_pombase,
        COUNT(DISTINCT src) FILTER (WHERE src_pombase) AS pombase_sources
    FROM nearest
) TO 'analyses/treegrafter-pombase/viz/out/summary.json' (FORMAT JSON, ARRAY true);

COPY (
    SELECT LEAST(depth, 15) AS d, SUM(n) FILTER (WHERE src_pombase) AS pombase, SUM(n) AS total
    FROM nearest GROUP BY 1 ORDER BY 1
) TO 'analyses/treegrafter-pombase/viz/out/depth.json' (FORMAT JSON, ARRAY true);

COPY (
    SELECT n.src, s.fam, s.an, SUM(n.n) AS ann, COUNT(DISTINCT n.graft) AS grafts, MAX(n.depth) AS maxdepth,
        STRING_AGG(DISTINCT tl.label, '; ') AS terms
    FROM nearest n
    INNER JOIN an s ON s.ptn = n.src
    INNER JOIN term_label tl ON tl.id = n.ontology_class_ref
    WHERE n.src_pombase
    GROUP BY ALL ORDER BY ann DESC LIMIT 10
) TO 'analyses/treegrafter-pombase/viz/out/top.json' (FORMAT JSON, ARRAY true);

-- worked-example families
CREATE TEMP TABLE example_fam (fam VARCHAR);
INSERT INTO example_fam VALUES ('PTHR43114'), ('PTHR28283');

COPY (
    SELECT a.fam, a.an, a.ptn FROM an a WHERE a.fam IN (SELECT fam FROM example_fam)
) TO 'analyses/treegrafter-pombase/viz/out/fam_ptn.json' (FORMAT JSON, ARRAY true);

COPY (
    SELECT a.fam, a.an, n.ontology_class_ref AS term, tl.label, s.an AS src_an, n.depth, n.n, n.src_pombase
    FROM nearest n
    INNER JOIN an a ON a.ptn = n.graft
    INNER JOIN an s ON s.ptn = n.src
    INNER JOIN term_label tl ON tl.id = n.ontology_class_ref
    WHERE a.fam IN (SELECT fam FROM example_fam)
    ORDER BY a.fam, a.an, term
) TO 'analyses/treegrafter-pombase/viz/out/fam_terms.json' (FORMAT JSON, ARRAY true);

COPY (
    SELECT DISTINCT regexp_extract(g.with_or_from, 'PANTHER:PTN[0-9]+') AS node, g.ontology_class_ref, g.with_or_from
    FROM gaf_association g
    INNER JOIN an a ON a.ptn = regexp_extract(g.with_or_from, 'PANTHER:PTN[0-9]+')
    WHERE g.evidence_type = 'IBA' AND a.fam IN (SELECT fam FROM example_fam)
) TO 'analyses/treegrafter-pombase/viz/out/fam_iba.json' (FORMAT JSON, ARRAY true);
