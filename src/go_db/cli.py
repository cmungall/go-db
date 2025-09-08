"""Command line interface for go-db."""

import logging
from typing import Optional

import click

from go_db.main import LoaderConfiguration, load_all, materialize_view, validate_db, validate_db_iter

__all__ = [
    "main",
]

logger = logging.getLogger(__name__)


@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
def main(verbose: int, quiet: bool):
    """
    CLI for go-db.

    :param verbose: Verbosity while running.
    :param quiet: Boolean to be quiet or verbose.
    """
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)
    logger.info(f"Starting go-db CLI, logging level: {logger.level}")


@main.command()
@click.option("--db", "-d", show_default=True, default=":memory:", help="Database connection string.")
@click.option("--append/--no-append", default=False, show_default=True)
@click.option("--force/--no-force", "-f", default=False, show_default=True, help="")
@click.option(
    "--go-db-path", "-g", default="db/go.db", show_default=True, help="Path to semsql/sqlite version of GO ontology."
)
@click.option("--validate/--no-validate", default=True, show_default=True)
@click.argument("sources", nargs=-1)
def load(sources, validate, **kwargs):
    """
    Load sources into a database based on a config file.

    Example:
    -------
        go-db load --g db/mgi.db data/mgi.gaf

    """
    gaf_sources = [s for s in sources if ".gaf" in s]
    gpi_sources = [s for s in sources if ".gpi" in s]
    unrecognized = [s for s in sources if s not in gaf_sources + gpi_sources]
    if unrecognized:
        raise ValueError(f"Unknown source file type: {unrecognized}")
    config = LoaderConfiguration(**kwargs, sources=gaf_sources, gpi_sources=gpi_sources)
    load_all(config)
    if validate:
        validate_db(config)


@main.command()
@click.option("--db", "-d", default=":memory:", help="Database connection string.")
def validate(**kwargs):
    """Run the go-db's demo command."""
    print(kwargs)
    logger.info("Validating the database.")
    config = LoaderConfiguration(**kwargs, sources=[])
    print(f"Validating the database; conf={config}.")
    for x in validate_db_iter(config):
        print(x)


@main.command()
@click.option("--db", "-d", show_default=True, default=":memory:", help="Database connection string.")
@click.option("--append/--no-append", default=False, show_default=True)
@click.option("--force/--no-force", "-f", default=False, show_default=True)
@click.option(
    "--go-db-path", "-g", default="db/go.db", show_default=True, help="Path to semsql/sqlite version of GO ontology."
)
@click.argument("view_name")
def materialize(view_name, **kwargs):
    """Materialize a view."""
    config = LoaderConfiguration(**kwargs)
    materialize_view(config, view_name)


@main.command()
@click.option("--db", "-d", required=True, help="Database connection string.")
@click.option(
    "--format", "-f", default="gaf", type=click.Choice(["gaf"]), help="Output format (currently only GAF supported)."
)
@click.option("--output", "-o", type=click.File("w"), default="-", help="Output file (default: stdout).")
@click.option("--query", "-q", help="Custom SQL query to filter results.")
@click.option("--db-object-taxon", help="Filter by taxon (e.g., 'taxon:9606').")
@click.option("--assigned-by", help="Filter by assigned_by field.")
@click.option("--aspect", help="Filter by aspect (F, P, or C).")
@click.option("--evidence-type", help="Filter by evidence type.")
@click.option("--ontology-class-ref", help="Filter by ontology class reference.")
@click.option("--limit", type=int, help="Limit number of results.")
def export(
    db: str,
    format: str,
    output,
    query: Optional[str],
    db_object_taxon: Optional[str],
    assigned_by: Optional[str],
    aspect: Optional[str],
    evidence_type: Optional[str],
    ontology_class_ref: Optional[str],
    limit: Optional[int],
):
    """
    Export GAF data from the database.

    Examples
    --------
        # Export all data to stdout
        go-db export -d mydb.db

        # Export human annotations to a file
        go-db export -d mydb.db --db-object-taxon='taxon:9606' -o human.gaf

        # Export with custom SQL
        go-db export -d mydb.db --query="WHERE aspect='P' AND evidence_type='EXP'"

        # Combine filters
        go-db export -d mydb.db --aspect=F --assigned-by=UniProt

    """
    import datetime

    config = LoaderConfiguration(db=db)
    conn = config.connection

    # Build the WHERE clause
    where_clauses = []

    if query:
        # Use custom query as-is (user provides WHERE clause)
        where_clauses.append(query.replace("WHERE", "").strip())

    # Add field-specific filters
    if db_object_taxon:
        where_clauses.append(f"db_object_taxon = '{db_object_taxon}'")
    if assigned_by:
        where_clauses.append(f"assigned_by = '{assigned_by}'")
    if aspect:
        where_clauses.append(f"aspect = '{aspect}'")
    if evidence_type:
        where_clauses.append(f"evidence_type = '{evidence_type}'")
    if ontology_class_ref:
        where_clauses.append(f"ontology_class_ref = '{ontology_class_ref}'")

    # Build the final query
    base_query = "SELECT * FROM gaf_association_flat"
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    if limit:
        base_query += f" LIMIT {limit}"

    logger.info(f"Executing query: {base_query}")

    # Write GAF header
    output.write("!gaf-version: 2.2\n")
    output.write("!generated-by: go-db\n")
    output.write(f"!date-generated: {datetime.datetime.now().strftime('%Y-%m-%d')}\n")
    output.write("!\n")

    # Execute query and write results
    try:
        result = conn.sql(base_query)
        df = result.fetchdf()

        # Write data rows
        for _, row in df.iterrows():
            # GAF format has tab-separated columns
            fields = [
                str(row["db"] if row["db"] is not None else ""),
                str(row["db_object_id"] if row["db_object_id"] is not None else ""),
                str(row["db_object_symbol"] if row["db_object_symbol"] is not None else ""),
                str(row["qualifiers"] if row["qualifiers"] is not None else ""),
                str(row["ontology_class_ref"] if row["ontology_class_ref"] is not None else ""),
                str(row["supporting_references"] if row["supporting_references"] is not None else ""),
                str(row["evidence_type"] if row["evidence_type"] is not None else ""),
                str(row["with_or_from"] if row["with_or_from"] is not None else ""),
                str(row["aspect"] if row["aspect"] is not None else ""),
                str(row["db_object_name"] if row["db_object_name"] is not None else ""),
                str(row["db_object_synonyms"] if row["db_object_synonyms"] is not None else ""),
                str(row["db_object_type"] if row["db_object_type"] is not None else ""),
                str(row["db_object_taxon"] if row["db_object_taxon"] is not None else ""),
                str(row["annotation_date_string"] if row["annotation_date_string"] is not None else ""),
                str(row["assigned_by"] if row["assigned_by"] is not None else ""),
                str(row["annotation_extensions"] if row["annotation_extensions"] is not None else ""),
                str(row["gene_product_form"] if row["gene_product_form"] is not None else ""),
            ]
            output.write("\t".join(fields) + "\n")

        logger.info(f"Exported {len(df)} records")

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise click.ClickException(f"Query failed: {e}") from e


if __name__ == "__main__":
    main()
