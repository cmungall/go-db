"""
Build the PomBase-via-TreeGrafter page from exported data.

Run after ptn_ancestry_contribution.sql and viz/export_viz_data.sql have written
viz/out/*.json (see Makefile target treegrafter-pombase)::

    python analyses/treegrafter-pombase/build_page.py

Reads the example family trees from tmp/treegrafter-pombase/Tree_MSF and writes
viz/pombase-treegrafter.html.
"""

import json
import re
from pathlib import Path

from panther_trees import parse_edges

HERE = Path(__file__).resolve().parent
VIZ = HERE / "viz"
OUT = VIZ / "out"
TREES = HERE.parent.parent / "tmp/treegrafter-pombase/Tree_MSF"
FAMILIES = ["PTHR43114", "PTHR28283"]
LEAF = re.compile(r"(AN\d+):([A-Za-z0-9]+)\|([^|]+)\|UniProtKB=(\w+);")


def load(name: str) -> list[dict]:
    """Load one exported JSON array."""
    return json.loads((OUT / name).read_text())


def parse_leaves(tree_text: str) -> dict[str, dict]:
    """
    Map leaf AN labels to species code, gene id and UniProtKB accession.

    >>> parse_leaves("AN3:SCHPO|PomBase=SPCC285.09c|UniProtKB=P36599;")
    {'AN3': {'sp': 'SCHPO', 'gene': 'SPCC285.09c', 'up': 'P36599'}}
    """
    leaves = {}
    for line in tree_text.splitlines():
        m = LEAF.match(line.strip())
        if m:
            an, sp, gene, up = m.groups()
            leaves[an] = {"sp": sp, "gene": gene.split("=", 1)[1], "up": up}
    return leaves


def family_data(fam: str, ptn: dict, terms: list[dict], iba: list[dict]) -> dict:
    """Assemble tree layout order, parents, grafts and IBA evidence for one family."""
    newick = (TREES / f"{fam}.newick").read_text().strip()
    leaves = parse_leaves((TREES / f"{fam}.tree").read_text())
    order = re.findall(r"AN\d+", newick)
    parent = {child: par for child, par in parse_edges(newick)}
    nodes = {
        an: {"an": an, "ptn": ptn[(fam, an)], "leaf": leaves.get(an), "grafts": [], "iba": [], "parent": parent.get(an)}
        for an in order
    }
    by_ptn = {node["ptn"]: node for node in nodes.values()}
    for t in terms:
        if t["fam"] == fam:
            nodes[t["an"]]["grafts"].append(
                {
                    "term": t["term"],
                    "label": t["label"],
                    "src": t["src_an"],
                    "depth": t["depth"],
                    "n": t["n"],
                    "pombase": t["src_pombase"],
                }
            )
    for i in iba:
        node = by_ptn.get(i["node"].replace("PANTHER:", ""))
        if node:
            node["iba"].append({"term": i["ontology_class_ref"], "with": i["with_or_from"].split("|")})
    return {"order": order, "nodes": nodes}


def main() -> None:
    """Write viz/pombase-treegrafter.html."""
    ptn = {(r["fam"], r["an"]): r["ptn"].replace("PANTHER:", "") for r in load("fam_ptn.json")}
    terms = load("fam_terms.json")
    iba = load("fam_iba.json")
    data = {
        "fams": {fam: family_data(fam, ptn, terms, iba) for fam in FAMILIES},
        "depth": load("depth.json"),
        "top": load("top.json"),
        "clades": load("clades.json"),
        "summary": load("summary.json")[0],
    }
    page = (VIZ / "page_template.html").read_text()
    page = page.replace("/*DATA*/", json.dumps(data, separators=(",", ":")))
    (VIZ / "pombase-treegrafter.html").write_text(page)
    print(f"wrote {VIZ / 'pombase-treegrafter.html'} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
