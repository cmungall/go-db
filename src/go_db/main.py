"""Main python file."""
import logging
from pathlib import Path
from typing import List, Optional, Iterator

import duckdb
from pydantic import BaseModel

from go_db.sql import GAF_DDL_PATH, GO_RULES_PATH

logger = logging.getLogger(__name__)

class LoaderConfiguration(BaseModel):
    """Configuration for loading GO database."""

    db: str
    """Path to duckdb database."""

    sources: Optional[List[str]] = None
    """Names of GAF sources"""

    gpi_sources: Optional[List[str]] = None
    """Names of GPI sources"""

    go_db_path: Optional[str] = None
    """Path to GO sqlite database (from semsql)."""

    append: Optional[bool] = False
    """If true, subsequent load calls will append"""

    force: Optional[bool] = False
    """If true, force overwrite of database if present."""

    _connection: Optional[duckdb.DuckDBPyConnection] = None

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Get connection."""
        if self._connection is None:
            self._connection = duckdb.connect(self.db)
        return self._connection

    @property
    def name(self) -> str:
        """Get name/handle."""
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
        """
        Check/validate configuration.

        Ensures that the database is not present if force is not set.
        """
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


def materialize_view(config: LoaderConfiguration, view_name: str) -> None:
    """Converts a view into a table."""
    logger.info(f"Materializing view {view_name}.")
    v_tmp = f"{view_name}__tmp"
    config.connection.sql(f"CREATE TABLE {v_tmp} AS SELECT * FROM {view_name}")
    config.connection.sql(f"DROP VIEW {view_name}")
    config.connection.sql(f"ALTER TABLE {v_tmp} RENAME TO {view_name}")


def load_ddl(config: LoaderConfiguration) -> None:
    """Load SQL DDL (CREATE TABLE statements).

    Example:

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
    """Load GAF data from a configuration
    
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
    logger.info(f"Loading GAF data: {config.sources}")
    for source in config.sources:
        load_gaf_source(config, source)


def load_gpi(config: LoaderConfiguration) -> None:
    """Load GPI data from configuration.
    """
    logger.info(f"Loading GPI data: {config.gpi_sources}")
    for source in config.gpi_sources:
        load_gpi_source(config, source)


def load_gaf_source(config: LoaderConfiguration, source: str) -> None:
    """Load GAF data from a source."""
    logger.info(f"Loading GAF data from {source}.")
    sql = f"INSERT INTO gaf_association_flat SELECT * FROM read_csv('{source}', delim='\t', header=false)"
    logger.debug(f"SQL: {sql}")
    config.connection.sql(sql)


def load_gpi_source(config: LoaderConfiguration, source: str) -> None:
    """Load GPI data from a source."""
    logger.info(f"Loading GPI data from {source}.")
    sql = f"INSERT INTO gpi_version_1_2_flat SELECT * FROM read_csv('{source}', delim='\t', header=false)"
    logger.debug(f"SQL: {sql}")
    config.connection.sql(sql)

def load_derived_tables(config: LoaderConfiguration) -> None:
    """
    Load derived tables.
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
    #config.connection.sql(DERIVED_GAF)
    materialize_view(config, "gaf_association")
    materialize_view(config, "gpi")


def load_all(config: LoaderConfiguration) -> None:
    """
    Execute all steps to load the GO database.
    """
    config.check()
    bulk_load_go_db(config)
    load_ddl(config)
    load_gaf(config)
    load_gpi(config)
    load_derived_tables(config)
    logger.info("All steps completed.")


def validate_db_iter(config: LoaderConfiguration) -> Iterator[str]:
    """
    Validate the database.

    :return: Iterator of validation messages
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
    """
    Bulk load SQLite database to DuckDB.

    :param config:
    :param sqlite_db:
    :param tables:
    :return:
    """
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
    """
    Bulk load GO Sqlite ontology database.

    :param config:
    :return:
    """
    # Define the SQLite database and tables
    tables = ["edge", "entailed_edge", "statements", "rdfs_subclass_of_statement"]

    # Bulk load SQLite database to DuckDB
    bulk_load_sqlite_to_duckdb(config, config.go_db_path, tables)