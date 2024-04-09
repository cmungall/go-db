"""Main python file."""
import logging
from pathlib import Path
from typing import List, Optional, Iterator

import duckdb
from pydantic import BaseModel

from go_db.sql import GAF_DDL_PATH, GO_RULES_PATH

logger = logging.getLogger(__name__)


DERIVED = """
INSERT INTO gaf_association
SELECT
 nextval('gaf_sequence') AS internal_id,
        db,
        local_id,
        db_object_symbol,
        qualifiers,
        ontology_class_ref,
        supporting_references,
        evidence_type,
        with_or_from,
        aspect,
        db_object_name,
        db_object_synonyms,
        db_object_type,
        db_object_taxon,
        annotation_date_string,
        assigned_by,
        annotation_extensions,
        gene_product_form,
strptime(annotation_date_string, '%Y%m%d') AS annotation_date,
concat_ws(':', db, local_id) AS subject,
str_split(with_or_from, '|') AS with_or_from_list,
str_split(supporting_references, '|') AS supporting_references_list,
str_split(db_object_synonyms, '|') AS db_object_synonyms_list,
str_split(annotation_extensions, ',') AS annotation_extensions_list
FROM gaf_association_flat;
"""


class LoaderConfiguration(BaseModel):
    """Configuration model."""
    db: str
    """Path to duckdb database."""

    sources: Optional[List[str]] = None
    """Names of GAF sources"""

    go_db_path: Optional[str] = None
    """Path to GO sqlite database (from semsql)."""

    append: Optional[bool] = False

    force: Optional[bool] = False

    _connection: Optional[duckdb.DuckDBPyConnection] = None

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Get connection."""
        if self._connection is None:
            self._connection = duckdb.connect(self.db)
        return self._connection

    @property
    def name(self) -> str:
        """Get name."""
        db = self.db
        if db == ":memory:":
            return "memory"
        # take the basename minus the suffix
        return db.split("/")[-1].split(".")[0]

    @property
    def is_memory(self) -> bool:
        """Check if database is in memory."""
        return self.db == ":memory:"

    def check(self) -> None:
        """Check configuration."""
        if self.is_memory:
            return
        path = Path(self.db)
        if path.exists():
            if self.append:
                raise NotImplementedError("Append not implemented.")
            if self.force:
                path.unlink()
                return
            else:
                raise ValueError(f"Database exists: {self.db}. Use --force to overwrite.")



def load_ddl(config: LoaderConfiguration) -> None:
    """Load DDL data.

    >>> config = LoaderConfiguration(db=":memory:")
    >>> from go_db import LoaderConfiguration, load_ddl
    >>> load_ddl(config)
    >>> connection = config.connection
    """
    connection = config.connection
    # load from GAF_DDL_PATH
    logger.info("Loading DDL data.")
    ddls_files = [GAF_DDL_PATH, GO_RULES_PATH]
    for ddl_file in ddls_files:
        with open(ddl_file) as f:
            ddl = f.read()
        logger.debug(f"DDL: {ddl}")
        connection.sql(ddl)


def load_gaf(config: LoaderConfiguration) -> None:
    """Load GAF data.
    
    >>> config = LoaderConfiguration(db=":memory:", sources=["tests/input/test-uniprot.gaf"])
    >>> from go_db import LoaderConfiguration, load_ddl
    >>> load_ddl(config)
    >>> load_gaf(config)
    >>> con = config.connection
    >>> df = con.sql("SELECT * FROM gaf_association_flat LIMIT 5").fetchdf()
    >>> for _, row in df.iterrows():  # doctest: +NORMALIZE_WHITESPACE
    ...    row = row.to_dict()
    ...    print(row["db_object_symbol"])
    <BLANKLINE>
    ...
    MAP2K7
    ...
    """
    for source in config.sources:
        load_gaf_source(config, source)


def load_gaf_source(config: LoaderConfiguration, source: str) -> None:
    """Load GAF data from a source."""
    logger.info(f"Loading GAF data from {source}.")
    sql = f"INSERT INTO gaf_association_flat SELECT * FROM read_csv('{source}', delim='\t', header=false)"
    logger.debug(f"SQL: {sql}")
    config.connection.sql(sql)


def load_derived_tables(config: LoaderConfiguration) -> None:
    """
    Load derived tables.

    TODO: drop and reload - this can lead to doubling up at the moment...

    >>> config = LoaderConfiguration(db=":memory:", sources=["tests/input/test-uniprot.gaf"])
    >>> from go_db import LoaderConfiguration, load_ddl
    >>> load_ddl(config)
    >>> load_gaf(config)
    >>> load_derived_tables(config)
    >>> con = config.connection
    >>> df = con.sql("SELECT * FROM gaf_association LIMIT 5").fetchdf()
    >>> for _, row in df.iterrows():  # doctest: +NORMALIZE_WHITESPACE
    ...    row = row.to_dict()
    ...    print(row["subject"], row["with_or_from_list"])
    xxx
    """
    logger.info("Loading derived tables.")
    config.connection.sql(DERIVED)


def load_all(config: LoaderConfiguration) -> None:
    """
    Load all steps
    """
    config.check()
    bulk_load_go_db(config)
    load_ddl(config)
    load_gaf(config)
    load_derived_tables(config)
    logger.info("All steps completed.")


def validate_db_iter(config: LoaderConfiguration) -> Iterator[str]:
    """
    Validate the database.
    """
    print("Validating the database.")
    logger.info("Validating the database.")
    conn = config.connection
    # introspect database for all views
    df = conn.sql("SELECT view_name FROM gorule_view").fetchdf()
    print(df)
    views = []
    for _, row in df.iterrows():
        print(f"Row: {row}")
        row = row.to_dict()
        views.append(row["view_name"])
    for view in views:
        print(f"Validating view {view}")
        df = conn.sql(f"SELECT * FROM {view} LIMIT 5").fetchdf()
        for _, row in df.iterrows():
            row = row.to_dict()
            yield f"{view}: {row}"

def validate_db(config: LoaderConfiguration) -> None:
    """
    Validate the database.
    """
    for x in validate_db_iter(config):
        print(x)


def bulk_load_sqlite_to_duckdb(config: LoaderConfiguration, sqlite_db: str, tables: List[str]):
    # Create a DuckDB connection
    con = config.connection

    if not sqlite_db:
        raise ValueError("SQLite database path is required.")
    # Attach the SQLite database
    con.execute("INSTALL sqlite")
    con.execute("LOAD sqlite")
    print(f"ATTACH DATABASE '{sqlite_db}' AS semsql")
    con.execute(f"ATTACH DATABASE '{sqlite_db}' AS semsql")
    con.execute("USE semsql")

    # Bulk load the data from SQLite tables to DuckDB tables
    for table in tables:
        con.execute(f"USE semsql; CREATE TABLE {config.name}.{table} AS SELECT * FROM semsql.{table}")
        print(f"Table '{table}' bulk loaded successfully.")

    # Verify the data loaded into DuckDB tables
    for table in tables:
        print(f"\n{table} table:")
        con.execute(f"SELECT * FROM {table} LIMIT 5").df()
    con.execute(f"USE {config.name}")
    con.execute("DETACH DATABASE semsql")


def bulk_load_go_db(config: LoaderConfiguration):
    # Define the SQLite database and tables
    tables = ["edge", "entailed_edge", "statements", "rdfs_subclass_of_statement"]

    # Bulk load SQLite database to DuckDB
    bulk_load_sqlite_to_duckdb(config, config.go_db_path, tables)