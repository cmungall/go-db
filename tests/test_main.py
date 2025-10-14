from typing import List

import pytest
from go_db import LoaderConfiguration, load_ddl, load_gaf
from go_db.main import bulk_load_go_db, load_derived_tables

from tests import INPUT_DIR

TEST_ONTOLOGY_DB = str(INPUT_DIR / "go-nucleus.db")


@pytest.fixture
def sources() -> List[str]:
    return [str(INPUT_DIR / "test-uniprot-cytosol.gaf")]


def test_load_ddl():
    config = LoaderConfiguration(db=":memory:", go_db_path=TEST_ONTOLOGY_DB)
    bulk_load_go_db(config)
    load_ddl(config)
    # Add verification logic here. For now, we're ensuring the function executes without error.


def test_load_gaf(sources):
    config = LoaderConfiguration(db=":memory:", sources=sources, go_db_path=TEST_ONTOLOGY_DB)
    bulk_load_go_db(config)
    load_ddl(config)
    load_gaf(config)
    # Assuming there's a mechanism to verify the loaded data.
    # Here, you might query `gaf_association_flat` and assert on the expected results.


def test_load_derived_tables(sources):
    config = LoaderConfiguration(db=":memory:", sources=sources, go_db_path=TEST_ONTOLOGY_DB)
    # Assuming load_gaf or similar setup is required before loading derived tables
    bulk_load_go_db(config)
    load_ddl(config)
    load_gaf(config)
    load_derived_tables(config)
    # Verification logic to confirm `gaf_association` contains the expected data
