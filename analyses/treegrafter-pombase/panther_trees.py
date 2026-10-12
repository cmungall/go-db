"""
Fetch PANTHER family trees and turn them into PTN child-parent edges.

PANTHER family trees (``PTHRnnnnn.newick``) label nodes with family-local AN
identifiers. PANTHER's PAINT annotation file maps each ``PTHRnnnnn:ANn`` to its
persistent PTN identifier, which is what GO annotations cite in with/from.

Usage::

    python panther_trees.py download tmp/treegrafter-pombase
    python panther_trees.py edges tmp/treegrafter-pombase tmp/treegrafter-pombase/ptn_edges.tsv
"""

import gzip
import re
import shutil
import tarfile
import urllib.request
from pathlib import Path

import click

TREES_URL = "https://data.pantherdb.org/ftp/downloads/TreeGrafter/PANTHER19.0_data_trees_hmms_only.tar.gz"
PAINT_URL = "https://data.pantherdb.org/ftp/downloads/paint/current/PAINT_TreeGrafter_Annotations_TOTAL.txt.gz"
PAINT_FILE = "PAINT_TreeGrafter_Annotations_TOTAL.txt.gz"
TREE_DIR = "Tree_MSF"
# family trees with internal node labels, and leaf tables; skips *.bifurcate.newick, HMMs and alignments
TREE_MEMBER = re.compile(r"Tree_MSF/(PTHR\d+\.(newick|tree))$")
LABEL = re.compile(r"[^(),:;]+")


def parse_edges(newick: str) -> list[tuple[str, str]]:
    """
    Return (child, parent) label pairs from a newick string with internal node labels.

    >>> parse_edges("((AN2:0.8,AN3:0.8)AN1:0.5,AN4:0.2)AN0;")
    [('AN2', 'AN1'), ('AN3', 'AN1'), ('AN1', 'AN0'), ('AN4', 'AN0')]

    Polytomies give one edge per child:

    >>> parse_edges("(AN1:0.1,AN2:0.2,AN3:0.3)AN0;")
    [('AN1', 'AN0'), ('AN2', 'AN0'), ('AN3', 'AN0')]
    """
    edges = []
    # each open group collects the labels of its direct children
    stack: list[list[str]] = []
    pending_children: list[str] = []
    i = 0
    while i < len(newick):
        c = newick[i]
        if c == "(":
            stack.append([])
            i += 1
        elif c == ")":
            pending_children = stack.pop()
            i += 1
        elif c == ":":
            # skip branch length
            i += 1
            while i < len(newick) and newick[i] not in ",();":
                i += 1
        elif c in ",;":
            i += 1
        else:
            m = LABEL.match(newick, i)
            label = m.group(0)
            i = m.end()
            edges.extend((child, label) for child in pending_children)
            pending_children = []
            if stack:
                stack[-1].append(label)
    return edges


def parse_an_to_ptn(lines) -> dict[str, str]:
    r"""
    Map ``PTHRnnnnn:ANn`` to ``PANTHER:PTNnnnnnnnnn`` from PAINT annotation file lines.

    >>> parse_an_to_ptn(["PTHR10000:AN1\tPTHR10000:SF8  GO:0000287;  PC00195;\tPTN004118867\n"])
    {'PTHR10000:AN1': 'PANTHER:PTN004118867'}
    """
    mapping = {}
    for line in lines:
        fields = line.rstrip("\n").split("\t")
        mapping[fields[0]] = f"PANTHER:{fields[-1]}"
    return mapping


@click.group()
def cli() -> None:
    """Fetch PANTHER trees and derive PTN edges."""


@cli.command()
@click.argument("out_dir", type=click.Path(file_okay=False, path_type=Path))
def download(out_dir: Path) -> None:
    """Download PANTHER 19 family trees and the current AN-to-PTN mapping into OUT_DIR."""
    tree_dir = out_dir / TREE_DIR
    tree_dir.mkdir(parents=True, exist_ok=True)
    # stream the 2.9 GB archive, keeping only the small tree files
    n = 0
    with urllib.request.urlopen(TREES_URL) as response, tarfile.open(fileobj=response, mode="r|gz") as tar:  # noqa: S310
        for member in tar:
            m = TREE_MEMBER.search(member.name)
            if m and member.isfile():
                (tree_dir / m.group(1)).write_bytes(tar.extractfile(member).read())
                n += 1
    click.echo(f"wrote {n} tree files to {tree_dir}")
    # written last, so its presence marks a complete download
    with urllib.request.urlopen(PAINT_URL) as response, (out_dir / PAINT_FILE).open("wb") as out:  # noqa: S310
        shutil.copyfileobj(response, out)


@cli.command()
@click.argument("data_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("output", type=click.Path(dir_okay=False, path_type=Path))
def edges(data_dir: Path, output: Path) -> None:
    """Write PTN child-parent edges (TSV) for every family tree in DATA_DIR."""
    with gzip.open(data_dir / PAINT_FILE, "rt") as f:
        an_to_ptn = parse_an_to_ptn(f)
    written = 0
    with output.open("w") as out:
        out.write("child\tparent\n")
        for tree_file in sorted((data_dir / TREE_DIR).glob("PTHR*.newick")):
            family = tree_file.name.split(".")[0]
            for child, parent in parse_edges(tree_file.read_text().strip()):
                out.write(f"{an_to_ptn[f'{family}:{child}']}\t{an_to_ptn[f'{family}:{parent}']}\n")
                written += 1
    click.echo(f"wrote {written} edges to {output}")


if __name__ == "__main__":
    cli()
