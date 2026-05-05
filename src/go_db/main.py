"""Main python file."""

import logging
from pathlib import Path
from typing import Iterator, List, Optional, Union
from urllib.request import urlopen

import duckdb
from pydantic import BaseModel

from go_db.sql import ADHOC_VIEWS_PATH, GAF_DDL_PATH, GO_RULES_PATH

logger = logging.getLogger(__name__)


class LoaderConfiguration(BaseModel):
    """Configuration for loading GO database."""

    db: str
    """Path to duckdb database."""

    sources: Optional[List[str]] = None
    """Names of GAF sources"""

    gpi_sources: Optional[List[str]] = None
    """Names of GPI sources"""

    go_db_path: Optional[Union[str, List[str]]] = None
    """Path to GO sqlite database (from semsql), or list of paths for multiple databases."""

    additional_db_paths: Optional[List[str]] = None
    """Additional paths to SQLite databases to attach (not loaded)"""

    append: Optional[bool] = False
    """If true, subsequent load calls will append"""

    force: Optional[bool] = False
    """If true, force overwrite of database if present."""

    _connection: Optional[duckdb.DuckDBPyConnection] = None

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Get connection."""
        if self._connection is None:
            logger.info(f"Connecting to database: {self.db}")
            # Just use regular connection - DuckDB will handle read/write appropriately
            try:
                self._connection = duckdb.connect(self.db)
            except duckdb.SerializationException as e:
                logger.error(f"Failed to connect to database: {e}")
                logger.error("Database may be from a different DuckDB version or corrupted.")
                logger.error(f"Current DuckDB version: {duckdb.__version__}")
                logger.error("Try recreating the database with: go-db load -d new_db.db ...")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
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
    """
    Load SQL DDL (CREATE TABLE statements).

    Example:
    -------
    >>> config = LoaderConfiguration(db=":memory:")
    >>> from go_db import LoaderConfiguration, load_ddl
    >>> load_ddl(config)
    >>> connection = config.connection

    """
    connection = config.connection
    # load from GAF_DDL_PATH
    logger.info("Loading DDL data.")
    ddls_files = [GAF_DDL_PATH, GO_RULES_PATH, ADHOC_VIEWS_PATH]
    for ddl_file in ddls_files:
        with open(ddl_file) as f:
            ddl = f.read()
        logger.debug(f"DDL: {ddl}")
        connection.sql(ddl)


def load_gaf(config: LoaderConfiguration) -> None:
    """
    Load GAF data from a configuration

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
    """Load GPI data from configuration."""
    logger.info(f"Loading GPI data: {config.gpi_sources}")
    for source in config.gpi_sources:
        load_gpi_source(config, source)


def load_gaf_source(config: LoaderConfiguration, source: str) -> None:
    """Load GAF data from a source, supporting both regular and gzipped files."""
    logger.info(f"Loading GAF data from {source}.")

    # Check if the file is gzipped (ends with .gz)
    is_gzipped = source.endswith(".gz")

    # Adjust the SQL query based on whether the file is gzipped
    if is_gzipped:
        sql = f"INSERT INTO gaf_association_flat SELECT * FROM read_csv_auto('{source}', delim='\t', header=false, compression='gzip')"
    else:
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
    # config.connection.sql(DERIVED_GAF)
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
        sql = f"USE semsql; CREATE TABLE {config.name}.{table} AS SELECT * FROM semsql.{table}"
        print(f"Executing SQL: {sql}")
        con.execute(sql)
        print(f"Table '{table}' bulk loaded successfully.")

    # Verify the data loaded into DuckDB tables
    for table in tables:
        print(f"\n{table} table:")
        con.execute(f"SELECT * FROM {table} LIMIT 5").df()
    con.execute(f"USE {config.name}")
    con.execute("DETACH DATABASE semsql")


def bulk_load_sqlite_to_duckdb_multi(config: LoaderConfiguration, sqlite_dbs: List[str], tables: List[str]):
    """
    Bulk load multiple SQLite databases to DuckDB.

    Creates tables from the first database and inserts from subsequent ones.

    :param config: Loader configuration
    :param sqlite_dbs: List of SQLite database paths
    :param tables: List of table names to load
    :return:
    """
    if not sqlite_dbs:
        raise ValueError("At least one SQLite database path is required.")

    con = config.connection

    # Install SQLite extension once
    con.execute("INSTALL sqlite")
    con.execute("LOAD sqlite")

    for idx, sqlite_db in enumerate(sqlite_dbs):
        print(f"Processing SQLite database {idx + 1}/{len(sqlite_dbs)}: {sqlite_db}")
        if not sqlite_db:
            logger.warning(f"Skipping empty SQLite database path at index {idx}")
            continue

        logger.info(f"Processing SQLite database {idx + 1}/{len(sqlite_dbs)}: {sqlite_db}")

        # Attach the SQLite database
        alias = f"semsql_{idx}"
        con.execute(f"ATTACH DATABASE '{sqlite_db}' AS {alias}")
        con.execute(f"USE {alias}")

        # Process each table
        for table in tables:
            if idx == 0:
                # First database: CREATE TABLE
                con.execute(f"USE {alias}; CREATE TABLE {config.name}.{table} AS SELECT * FROM {alias}.{table}")
                logger.info(f"Table '{table}' created and loaded from first database.")
            else:
                # Subsequent databases: INSERT INTO
                con.execute(f"USE {alias}; INSERT INTO {config.name}.{table} SELECT * FROM {alias}.{table}")
                logger.info(f"Table '{table}' appended from database {idx + 1}.")

        # Detach the database
        con.execute(f"USE {config.name}")
        con.execute(f"DETACH DATABASE {alias}")

    # Verify the data loaded into DuckDB tables
    for table in tables:
        count = con.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()[0]
        logger.info(f"Table '{table}' contains {count} rows after loading from {len(sqlite_dbs)} databases.")


def bulk_load_go_db(config: LoaderConfiguration):
    """
    Bulk load GO Sqlite ontology database(s).

    :param config:
    :return:
    """
    # Define the SQLite database and tables
    tables = ["edge", "entailed_edge", "statements", "rdfs_subclass_of_statement"]

    sqlite_dbs = [config.go_db_path]
    if config.additional_db_paths:
        sqlite_dbs.extend(config.additional_db_paths)
    bulk_load_sqlite_to_duckdb_multi(config, sqlite_dbs, tables)


SWISSPROT_URL = "https://rest.uniprot.org/uniprotkb/stream?query=reviewed:true&format=list"
SWISSPROT_CACHE_DIR = Path.home() / ".cache" / "go-db"
SWISSPROT_CACHE_FILE = SWISSPROT_CACHE_DIR / "swissprot_ids.txt"

# Mapping of GAF db prefix to UniProt xref field name and organism ID
# Format: db_prefix -> (uniprot_xref_field, organism_id, id_prefix_in_gaf)
UNIPROT_XREF_MAPPINGS = {
    "FB": ("xref_flybase", 7227, "FB"),  # Drosophila melanogaster
    "MGI": ("xref_mgi", 10090, "MGI"),  # Mus musculus
    "RGD": ("xref_rgd", 10116, "RGD"),  # Rattus norvegicus
    "ZFIN": ("xref_zfin", 7955, "ZFIN"),  # Danio rerio
    "WB": ("xref_wormbase", 6239, "WB"),  # Caenorhabditis elegans
    "SGD": ("xref_sgd", 559292, "SGD"),  # Saccharomyces cerevisiae S288C
    "PomBase": ("xref_pombase", 284812, "PomBase"),  # Schizosaccharomyces pombe
}


def load_swissprot_ids(
    config: LoaderConfiguration,
    url: Optional[str] = None,
    cache_file: Optional[Union[str, Path]] = None,
    refresh: bool = False,
) -> int:
    """
    Load SwissProt mapping table keyed by GAF subject.

    Creates a unified `swissprot` table that maps GAF subjects to SwissProt accessions.
    Works for both:
    - UniProtKB entries: directly matched by accession
    - MOD entries (FB, MGI, etc.): matched via UniProt cross-references

    Table columns:
    - subject: GAF subject as it appears (e.g., "UniProtKB:O14733" or "FB:FBgn0027570")
    - uniprot_accession: The SwissProt accession

    This allows simple joins in queries:
        SELECT g.*, s.subject IS NOT NULL as is_swissprot
        FROM gaf_association g
        LEFT JOIN swissprot s ON g.subject = s.subject

    :param config: Loader configuration with database connection
    :param url: Optional URL to fetch IDs from (defaults to UniProt REST API)
    :param cache_file: Path to cache file. If exists, uses cached data. Defaults to ~/.cache/go-db/
    :param refresh: If True, re-fetch from URL even if cache exists
    :return: Number of entries in swissprot table

    """
    if url is None:
        url = SWISSPROT_URL

    if cache_file is None:
        cache_file = SWISSPROT_CACHE_FILE
    else:
        cache_file = Path(cache_file)

    # Check if we can use cached data
    if cache_file.exists() and not refresh:
        logger.info(f"Using cached SwissProt IDs from {cache_file}")
        tmp_path = str(cache_file)
    else:
        logger.info(f"Fetching SwissProt IDs from {url}")

        # Fetch the ID list from UniProt
        with urlopen(url) as response:
            content = response.read().decode("utf-8")

        # Ensure cache directory exists
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to cache file
        cache_file.write_text(content)
        logger.info(f"Cached SwissProt IDs to {cache_file}")
        tmp_path = str(cache_file)

    conn = config.connection

    # Drop tables if exist (for idempotency)
    conn.sql("DROP TABLE IF EXISTS swissprot")
    conn.sql("DROP TABLE IF EXISTS _swissprot_all")

    # Load all SwissProt accessions into temp table
    conn.sql(f"""
    CREATE TABLE _swissprot_all AS
    SELECT column0 AS accession
    FROM read_csv('{tmp_path}', header=false, columns={{'column0': 'VARCHAR'}})
    """)

    total_count = conn.sql("SELECT COUNT(*) FROM _swissprot_all").fetchone()[0]
    logger.info(f"Loaded {total_count} SwissProt accessions from cache")

    # Create swissprot table keyed by GAF subject
    # Start with direct UniProtKB matches
    conn.sql("""
    CREATE TABLE swissprot AS
    SELECT DISTINCT
        g.subject,
        s.accession as uniprot_accession
    FROM gaf_association g
    JOIN _swissprot_all s ON g.subject = 'UniProtKB:' || s.accession
    """)

    direct_count = conn.sql("SELECT COUNT(*) FROM swissprot").fetchone()[0]
    logger.info(f"Found {direct_count} direct UniProtKB SwissProt matches")

    # Clean up temp table
    conn.sql("DROP TABLE _swissprot_all")

    # Now auto-detect and load xref mappings for non-UniProtKB databases
    xref_count = load_uniprot_xrefs(config, refresh=refresh)
    if xref_count > 0:
        # Add MOD entries via xref mappings
        conn.sql("""
        INSERT INTO swissprot (subject, uniprot_accession)
        SELECT DISTINCT x.xref_id, x.uniprot_accession
        FROM uniprot_xref x
        WHERE EXISTS (
            SELECT 1 FROM gaf_association g WHERE g.subject = x.xref_id
        )
        AND NOT EXISTS (
            SELECT 1 FROM swissprot s WHERE s.subject = x.xref_id
        )
        """)
        xref_added = conn.sql("SELECT COUNT(*) FROM swissprot").fetchone()[0] - direct_count
        logger.info(f"Added {xref_added} entries via xref mappings")

    # Create index for efficient joins
    conn.sql("CREATE INDEX swissprot_subject_idx ON swissprot(subject)")
    conn.sql("CREATE INDEX swissprot_accession_idx ON swissprot(uniprot_accession)")

    # Get final count
    count = conn.sql("SELECT COUNT(*) FROM swissprot").fetchone()[0]
    logger.info(f"Total swissprot entries: {count}")

    return count


def fetch_uniprot_xrefs(
    db_prefix: str,
    xref_field: str,
    organism_id: int,
    cache_dir: Path = SWISSPROT_CACHE_DIR,
    refresh: bool = False,
) -> Path:
    """
    Fetch UniProt cross-references for a specific database and cache locally.

    :param db_prefix: Database prefix (e.g., "FB", "MGI")
    :param xref_field: UniProt xref field name (e.g., "xref_flybase")
    :param organism_id: NCBI taxonomy ID
    :param cache_dir: Directory for caching
    :param refresh: Force re-fetch even if cached
    :return: Path to cached TSV file
    """
    cache_file = cache_dir / f"uniprot_xref_{db_prefix.lower()}.tsv"

    if cache_file.exists() and not refresh:
        logger.info(f"Using cached UniProt xrefs for {db_prefix} from {cache_file}")
        return cache_file

    url = (
        f"https://rest.uniprot.org/uniprotkb/stream?"
        f"query=reviewed:true+AND+organism_id:{organism_id}&format=tsv&fields=accession,{xref_field}"
    )
    logger.info(f"Fetching UniProt xrefs for {db_prefix} from {url}")

    with urlopen(url) as response:
        content = response.read().decode("utf-8")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(content)
    logger.info(f"Cached UniProt xrefs for {db_prefix} to {cache_file}")

    return cache_file


def load_uniprot_xrefs(
    config: LoaderConfiguration,
    refresh: bool = False,
) -> int:
    """
    Auto-detect database prefixes in GAF and load UniProt cross-reference mappings.

    Creates table `uniprot_xref` with columns:
    - uniprot_accession: UniProt accession (e.g., "A0A0B4K692")
    - db_prefix: Source database (e.g., "FB")
    - xref_id: Cross-reference ID as it appears in GAF subject (e.g., "FB:FBgn0027570")

    :param config: Loader configuration
    :param refresh: Force re-fetch from UniProt
    :return: Total number of xref mappings loaded
    """
    conn = config.connection

    # Detect which db prefixes are present in the GAF
    result = conn.sql("SELECT DISTINCT db FROM gaf_association_flat").fetchall()
    db_prefixes = {row[0] for row in result}

    # Find which prefixes have UniProt xref mappings
    mappings_to_load = []
    for prefix in db_prefixes:
        if prefix in UNIPROT_XREF_MAPPINGS:
            mappings_to_load.append((prefix, *UNIPROT_XREF_MAPPINGS[prefix]))

    if not mappings_to_load:
        logger.info("No UniProt xref mappings needed for this database")
        return 0

    logger.info(f"Loading UniProt xrefs for: {[m[0] for m in mappings_to_load]}")

    # Create or replace xref table
    conn.sql("DROP TABLE IF EXISTS uniprot_xref")
    conn.sql("""
    CREATE TABLE uniprot_xref (
        uniprot_accession VARCHAR,
        db_prefix VARCHAR,
        xref_id VARCHAR
    )
    """)

    total_count = 0
    for db_prefix, xref_field, organism_id, gaf_prefix in mappings_to_load:
        cache_file = fetch_uniprot_xrefs(db_prefix, xref_field, organism_id, refresh=refresh)

        # Load TSV and expand semicolon-separated xrefs
        # UniProt format: accession<TAB>xref1;xref2;...
        conn.sql(f"""
        INSERT INTO uniprot_xref
        SELECT
            column0 as uniprot_accession,
            '{db_prefix}' as db_prefix,
            '{gaf_prefix}:' || trim(unnest(string_split(column1, ';'))) as xref_id
        FROM read_csv('{cache_file}', delim='\t', header=true, columns={{'column0': 'VARCHAR', 'column1': 'VARCHAR'}})
        WHERE column1 IS NOT NULL AND column1 != ''
        """)

        count = conn.sql(f"SELECT COUNT(*) FROM uniprot_xref WHERE db_prefix = '{db_prefix}'").fetchone()[0]
        logger.info(f"Loaded {count} UniProt xrefs for {db_prefix}")
        total_count += count

    # Prune to only xrefs that appear in gaf_association
    before_count = conn.sql("SELECT COUNT(*) FROM uniprot_xref").fetchone()[0]
    conn.sql("""
    DELETE FROM uniprot_xref
    WHERE NOT EXISTS (
        SELECT 1 FROM gaf_association g
        WHERE g.subject = uniprot_xref.xref_id
    )
    """)
    after_count = conn.sql("SELECT COUNT(*) FROM uniprot_xref").fetchone()[0]
    logger.info(f"Pruned uniprot_xref from {before_count} to {after_count} (keeping only IDs in GAF)")

    # Create index
    conn.sql("CREATE INDEX uniprot_xref_xref_id_idx ON uniprot_xref(xref_id)")
    conn.sql("CREATE INDEX uniprot_xref_accession_idx ON uniprot_xref(uniprot_accession)")

    return after_count
