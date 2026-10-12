"""Tests for the PANTHER tree helpers in analyses/treegrafter-pombase."""

import gzip
import importlib.util
from pathlib import Path

import pytest
from click.testing import CliRunner

SCRIPT = Path(__file__).parent.parent / "analyses" / "treegrafter-pombase" / "panther_trees.py"


@pytest.fixture(scope="module")
def panther_trees():
    """Import the analysis script as a module."""
    spec = importlib.util.spec_from_file_location("panther_trees", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "newick,expected",
    [
        ("(AN1:0.1,AN2:0.2)AN0;", [("AN1", "AN0"), ("AN2", "AN0")]),
        (
            "((AN2:0.8,AN3:0.8)AN1:0.5,AN4:0.2)AN0;",
            [("AN2", "AN1"), ("AN3", "AN1"), ("AN1", "AN0"), ("AN4", "AN0")],
        ),
        # PANTHER wraps the root in an extra unlabelled group
        ("((AN1:0.1,AN2:0.2)AN0);", [("AN1", "AN0"), ("AN2", "AN0")]),
        # labels without branch lengths
        ("((AN2,AN3)AN1,AN4)AN0;", [("AN2", "AN1"), ("AN3", "AN1"), ("AN1", "AN0"), ("AN4", "AN0")]),
    ],
)
def test_parse_edges(panther_trees, newick, expected):
    """Every labelled child is linked to its labelled parent."""
    assert panther_trees.parse_edges(newick) == expected


def test_edges_cli(panther_trees, tmp_path):
    """The edges command writes PTN child-parent pairs for each family tree."""
    tree_dir = tmp_path / "Tree_MSF"
    tree_dir.mkdir()
    (tree_dir / "PTHR00001.newick").write_text("((AN2:0.8,AN3:0.8)AN1:0.5,AN4:0.2)AN0;\n")
    rows = {"AN0": "PTN000000010", "AN1": "PTN000000011", "AN2": "PTN000000012", "AN3": "PTN000000013"}
    rows["AN4"] = "PTN000000014"
    with gzip.open(tmp_path / "PAINT_TreeGrafter_Annotations_TOTAL.txt.gz", "wt") as f:
        for an, ptn in rows.items():
            f.write(f"PTHR00001:{an}\tPTHR00001:SF1  GO:0000001;  PC00001;\t{ptn}\n")
    output = tmp_path / "ptn_edges.tsv"

    result = CliRunner().invoke(panther_trees.cli, ["edges", str(tmp_path), str(output)])

    assert result.exit_code == 0, result.output
    assert output.read_text().splitlines() == [
        "child\tparent",
        "PANTHER:PTN000000012\tPANTHER:PTN000000011",
        "PANTHER:PTN000000013\tPANTHER:PTN000000011",
        "PANTHER:PTN000000011\tPANTHER:PTN000000010",
        "PANTHER:PTN000000014\tPANTHER:PTN000000010",
    ]
