# PomBase contribution to TreeGrafter annotations

How many TreeGrafter annotations (GO_REF:0000118) rest on PomBase experimental evidence?

TreeGrafter places a protein onto a PANTHER family tree and copies GO terms from annotated
ancestral nodes (IBDs). A TreeGrafter row records the graft node (a PTN) in its with/from column,
not the IBD node the term came from. IBA rows record the IBD node plus the leaf genes whose
experimental annotations support it, so a `PomBase:` identifier there shows PomBase evidence.

GO-DB has no PANTHER tree, so this analysis builds one (child-parent PTN edges from the PANTHER 19
family trees) and walks each graft node up to its ancestors.

## Rules

For a TreeGrafter annotation with graft node G and GO term T, over G and its ancestors:

| Rule | Definition |
|---|---|
| resolvable | some node has an IBA for T |
| PomBase-supported | some node has an IBA for T whose with/from cites `PomBase:` |
| PomBase-only | PomBase-supported, and no IBA for T on the path cites another non-PANTHER source |
| PomBase, any term | some node has an IBA for any term citing `PomBase:` (broad; not recommended) |

Matching is on the exact GO term. Using only the nearest same-term ancestor instead of any
ancestor changes the PomBase-supported total by less than 0.1%.

## Running

```bash
make treegrafter-pombase TG_DB=/path/to/goa_uniprot_all.ddb
```

1. `panther_trees.py download` streams the PANTHER 19 tree archive (2.9 GB) and keeps only the
   family trees, plus the current AN-to-PTN mapping, in `tmp/treegrafter-pombase/`.
2. `panther_trees.py edges` writes `tmp/treegrafter-pombase/ptn_edges.tsv` (about 3.5M edges).
3. `ptn_ancestry_contribution.sql` prints totals and a breakdown by clade, and writes
   `viz/out/clades.json`.
4. `viz/export_viz_data.sql` writes the remaining page data to `viz/out/`.
5. `build_page.py` fills `viz/page_template.html` and writes `viz/pombase-treegrafter.html`.

Each SQL step takes under a minute on the full database. The prose and worked examples in
`viz/page_template.html` are written by hand; check them after a rerun on a new snapshot.

## Results (goa_uniprot_all rebuilt 2026-10-11, TreeGrafter run 2026-07-27)

| Clade | TreeGrafter | PomBase-supported | Share | PomBase-only |
|---|---:|---:|---:|---:|
| All | 166,795,534 | 21,391,336 | 12.8% | 992,787 |
| Fungi | 21,205,140 | 6,119,593 | 28.9% | 479,348 |
| Other eukaryotes | 3,092,083 | 725,671 | 23.5% | 25,540 |
| Plants | 13,497,933 | 2,436,015 | 18.0% | 83,522 |
| Archaea | 977,806 | 141,362 | 14.5% | 6,557 |
| Animals | 67,232,552 | 6,866,908 | 10.2% | 234,896 |
| Bacteria | 60,787,857 | 5,101,587 | 8.4% | 162,923 |

90.1% of TreeGrafter annotations trace to a same-term IBA. Only 452,058 PomBase-supported
annotations are found without the tree, where the graft node is itself the IBD node.

## Caveats

- Contribution is not dependency: most PomBase-supported IBDs also cite other groups.
- NOT annotations on intermediate nodes, which would block inheritance, are not modelled.
- Pombe genes cited by UniProtKB accession rather than PomBase ID are not counted.
- TreeGrafter can lag PAINT. When an IBD term is refined (for example GO:1902660 to its child
  GO:0110034 in PTHR28283), TreeGrafter rows with the old term no longer match and are counted
  as unresolved. About 3.0M unresolved annotations have an IBA to a more specific term on their
  path; 452k of those cite PomBase.
