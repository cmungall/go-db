"""Command line interface for go-db."""

import logging
from typing import Optional

import click

from go_db.main import (
    LoaderConfiguration,
    bulk_load_sqlite_to_duckdb,
    load_all,
    materialize_view,
    validate_db,
    validate_db_iter,
)
from go_db.queries.evidence import EvidenceRedundancyAnalyzer

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
    "--go-db-path",
    "-g",
    multiple=True,
    help="Path to semsql/sqlite version of GO ontology. Can be specified multiple times.",
)
@click.option(
    "--sqlite-db",
    "-s",
    multiple=True,
    help="Additional SQLite database to load. Format: path:table1,table2,... Can be specified multiple times.",
)
@click.option("--validate/--no-validate", default=True, show_default=True)
@click.argument("sources", nargs=-1)
def load(sources, validate, go_db_path, sqlite_db, **kwargs):
    """
    Load sources into a database based on a config file.

    Examples
    --------
        # Load with single GO database
        go-db load -g db/go.db data/mgi.gaf

        # Load with multiple GO databases
        go-db load -g db/go1.db -g db/go2.db data/mgi.gaf

        # Load additional SQLite databases with specific tables
        go-db load -s other.db:table1,table2 -g db/go.db data/mgi.gaf

        # Load multiple SQLite databases
        go-db load -s db1.sqlite:edges,nodes -s db2.sqlite data/mgi.gaf

    """
    gaf_sources = [s for s in sources if ".gaf" in s]
    gpi_sources = [s for s in sources if ".gpi" in s]
    unrecognized = [s for s in sources if s not in gaf_sources + gpi_sources]
    if unrecognized:
        raise ValueError(f"Unknown source file type: {unrecognized}")

    # Handle go_db_path - convert tuple to list or single string
    if go_db_path:
        if len(go_db_path) == 1:
            go_db_path_value = go_db_path[0]
        else:
            go_db_path_value = list(go_db_path)
    else:
        # Use default if not specified
        go_db_path_value = "db/go.db"

    if sqlite_db:
        additional_db_paths = sqlite_db
    else:
        additional_db_paths = []

    config = LoaderConfiguration(
        **kwargs,
        sources=gaf_sources,
        gpi_sources=gpi_sources,
        go_db_path=go_db_path_value,
        additional_db_paths=additional_db_paths,
    )

    # Process additional SQLite databases if provided
    if False and sqlite_db:
        for db_spec in sqlite_db:
            if ":" not in db_spec:
                raise ValueError(f"SQLite database spec must be in format 'path:table1,table2,...'. Got: {db_spec}")

            db_path, tables_str = db_spec.split(":", 1)
            tables = [t.strip() for t in tables_str.split(",")]

            logger.info(f"Loading SQLite database: {db_path} with tables: {tables}")

            # Check if we have multiple databases for the same set of tables
            # For simplicity, load each SQLite database separately
            bulk_load_sqlite_to_duckdb(config, db_path, tables)

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
    "--go-db-path",
    "-g",
    multiple=True,
    help="Path to semsql/sqlite version of GO ontology. Can be specified multiple times.",
)
@click.argument("view_name")
def materialize(view_name, go_db_path, **kwargs):
    """Materialize a view."""
    # Handle go_db_path - convert tuple to list or single string
    if go_db_path:
        if len(go_db_path) == 1:
            go_db_path_value = go_db_path[0]
        else:
            go_db_path_value = list(go_db_path)
    else:
        # Use default if not specified
        go_db_path_value = "db/go.db"

    config = LoaderConfiguration(**kwargs, go_db_path=go_db_path_value)
    materialize_view(config, view_name)


@main.command()
@click.option("--db", "-d", required=True, help="Database connection string or path to .db/.ddb file.")
@click.option(
    "--format", "-f", default="gaf", type=click.Choice(["gaf"]), help="Output format (currently only GAF supported)."
)
@click.option("--output", "-o", type=click.File("w"), default="-", help="Output file (default: stdout).")
@click.option("--query", "-q", help="Custom SQL query to filter results.")
@click.option("--db-object-taxon", help="Filter by taxon (e.g., 'taxon:9606').")
@click.option("--taxon-closure", help="Filter by taxon and all descendants (e.g., 'NCBITaxon:10239' for all viruses).")
@click.option("--exclude-taxon", multiple=True, help="Exclude specific taxon (can be used multiple times).")
@click.option(
    "--exclude-taxon-closure", multiple=True, help="Exclude taxon and all descendants (can be used multiple times)."
)
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
    taxon_closure: Optional[str],
    exclude_taxon: tuple,
    exclude_taxon_closure: tuple,
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

        # Export all virus annotations using taxon closure
        go-db export -d mydb.db --taxon-closure='NCBITaxon:10239' -o viruses.gaf

        # Export fungi excluding yeast (S. cerevisiae and S. pombe)
        go-db export -d mydb.db --taxon-closure='NCBITaxon:4751' \\
            --exclude-taxon='taxon:4932' --exclude-taxon='taxon:4896' -o non_yeast_fungi.gaf

        # Export all bacteria except E. coli and descendants
        go-db export -d mydb.db --taxon-closure='NCBITaxon:2' \\
            --exclude-taxon-closure='NCBITaxon:562' -o non_ecoli_bacteria.gaf

        # Export with custom SQL
        go-db export -d mydb.db --query="WHERE aspect='P' AND evidence_type='EXP'"

        # Combine filters
        go-db export -d mydb.db --aspect=F --assigned-by=UniProt

    """
    import datetime
    from pathlib import Path

    import duckdb

    # Check if database file exists and provide helpful error message
    db_path = Path(db)
    if not db_path.exists() and db != ":memory:":
        raise click.ClickException(f"Database file not found: {db}")

    try:
        config = LoaderConfiguration(db=db)
        conn = config.connection
    except duckdb.SerializationException as e:
        raise click.ClickException(
            f"Failed to open database '{db}'.\n"
            f"This database may have been created with a different DuckDB version.\n"
            f"Current DuckDB version: {duckdb.__version__}\n"
            f"Try one of these solutions:\n"
            f"1. Update DuckDB: pip install --upgrade duckdb\n"
            f"2. Recreate the database with current version: go-db load -d new.db <your-gaf-files>\n"
            f"3. Use a database created with DuckDB {duckdb.__version__}"
        ) from e
    except Exception as e:
        raise click.ClickException(f"Failed to connect to database: {e}") from e

    # Build the WHERE clause
    where_clauses = []

    if query:
        # Use custom query as-is (user provides WHERE clause)
        where_clauses.append(query.replace("WHERE", "").strip())

    # Handle taxon closure (hierarchical taxon filtering)
    if taxon_closure:
        # Normalize the taxon ID format
        # Input could be 'taxon:9606', 'NCBITaxon:9606', or just '9606'
        if ":" in taxon_closure:
            prefix, taxon_id = taxon_closure.split(":", 1)
            if prefix.lower() == "taxon":
                ncbi_taxon = f"NCBITaxon:{taxon_id}"
            else:
                ncbi_taxon = taxon_closure
        else:
            ncbi_taxon = f"NCBITaxon:{taxon_closure}"

        # Build subquery to get all descendant taxa
        taxon_subquery = f"""
        db_object_taxon IN (
            SELECT DISTINCT 'taxon:' || REPLACE(subject, 'NCBITaxon:', '') 
            FROM entailed_is_a
            WHERE object = '{ncbi_taxon}'
            UNION
            SELECT 'taxon:' || REPLACE('{ncbi_taxon}', 'NCBITaxon:', '')
        )
        """
        where_clauses.append(taxon_subquery.strip())
        print(f"Using taxon closure for {ncbi_taxon}: {where_clauses}")

    # Add field-specific filters
    if db_object_taxon and not taxon_closure:  # Don't use both taxon filters
        where_clauses.append(f"db_object_taxon = '{db_object_taxon}'")
    if assigned_by:
        where_clauses.append(f"assigned_by = '{assigned_by}'")
    if aspect:
        where_clauses.append(f"aspect = '{aspect}'")
    if evidence_type:
        where_clauses.append(f"evidence_type = '{evidence_type}'")
    if ontology_class_ref:
        where_clauses.append(f"ontology_class_ref = '{ontology_class_ref}'")

    # Handle taxon exclusions
    if exclude_taxon:
        # Exclude specific taxa
        exclude_list = []
        for taxon in exclude_taxon:
            # Normalize format to 'taxon:XXXX' for GAF
            if ":" in taxon:
                prefix, taxon_id = taxon.split(":", 1)
                if prefix.lower() == "ncbitaxon":
                    exclude_list.append(f"'taxon:{taxon_id}'")
                else:
                    exclude_list.append(f"'{taxon}'")
            else:
                exclude_list.append(f"'taxon:{taxon}'")

        if exclude_list:
            where_clauses.append(f"db_object_taxon NOT IN ({', '.join(exclude_list)})")
            logger.info(f"Excluding taxa: {', '.join(exclude_list)}")

    # Handle taxon closure exclusions (exclude taxon and all descendants)
    if exclude_taxon_closure:
        for taxon in exclude_taxon_closure:
            # Normalize the taxon ID format
            if ":" in taxon:
                prefix, taxon_id = taxon.split(":", 1)
                if prefix.lower() == "taxon":
                    ncbi_taxon = f"NCBITaxon:{taxon_id}"
                else:
                    ncbi_taxon = taxon
            else:
                ncbi_taxon = f"NCBITaxon:{taxon}"

            # Build subquery to exclude taxon and all descendants
            exclude_subquery = f"""
            db_object_taxon NOT IN (
                SELECT DISTINCT 'taxon:' || REPLACE(subject, 'NCBITaxon:', '') 
                FROM entailed_edge 
                WHERE predicate = 'rdfs:subClassOf' 
                AND object = '{ncbi_taxon}'
                UNION
                SELECT 'taxon:' || REPLACE('{ncbi_taxon}', 'NCBITaxon:', '')
            )
            """
            where_clauses.append(exclude_subquery.strip())
            logger.info(f"Excluding taxon closure for {ncbi_taxon}")

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

    # Execute query and stream results directly
    try:
        result = conn.sql(base_query)

        # GAF column order (must match gaf_association_flat table)
        gaf_columns = [
            "db",
            "db_object_id",
            "db_object_symbol",
            "qualifiers",
            "ontology_class_ref",
            "supporting_references",
            "evidence_type",
            "with_or_from",
            "aspect",
            "db_object_name",
            "db_object_synonyms",
            "db_object_type",
            "db_object_taxon",
            "annotation_date_string",
            "assigned_by",
            "annotation_extensions",
            "gene_product_form",
        ]

        # Stream results row by row without loading into memory
        record_count = 0
        while True:
            row = result.fetchone()
            if row is None:
                break

            # Convert row tuple to tab-separated string, replacing None with empty string
            fields = [str(val) if val is not None else "" for val in row]
            output.write("\t".join(fields) + "\n")
            record_count += 1

        logger.info(f"Exported {record_count} records")

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise click.ClickException(f"Query failed: {e}") from e


@main.group()
def evidence():
    """Analyze evidence redundancy in GO annotations."""
    pass


@evidence.command(name="unique-contributions")
@click.option("--db", "-d", required=True, help="Database connection string or path to .db/.ddb file.")
@click.option(
    "--method", "-m", default="supporting_references", help="Method to analyze (default: supporting_references)."
)
@click.option("--evidence-type", "-e", help="Filter by evidence type (e.g., IEA, IBA, etc.).")
@click.option(
    "--comparator", "-c", multiple=True, help="Specific methods/references to compare against (can be repeated)."
)
@click.option("--summary/--no-summary", default=False, help="Show summary instead of full results.")
@click.option(
    "--group-by",
    "-g",
    multiple=True,
    help="Fields to group by in summary (e.g., evidence_type, supporting_references).",
)
@click.option("--output", "-o", type=click.File("w"), default="-", help="Output file (default: stdout).")
@click.option("--format", "-f", type=click.Choice(["json", "tsv", "csv"]), default="tsv", help="Output format.")
def unique_contributions(db, method, evidence_type, comparator, summary, group_by, output, format):
    """
    Find unique contributions of evidence methods.

    Examples
    --------
        # Find all unique IEA contributions
        go-db evidence unique-contributions -d mydb.ddb -e IEA

        # Find IEA contributions unique compared to specific references
        go-db evidence unique-contributions -d mydb.ddb -e IEA -c GO_REF:0000002 -c GO_REF:0000043

        # Get summary of unique contributions
        go-db evidence unique-contributions -d mydb.ddb -e IEA --summary

        # Custom grouping in summary
        go-db evidence unique-contributions -d mydb.ddb --summary -g evidence_type -g assigned_by

    """
    import json
    from pathlib import Path

    import duckdb

    # Check if database exists
    db_path = Path(db)
    if not db_path.exists() and db != ":memory:":
        raise click.ClickException(f"Database file not found: {db}")

    try:
        conn = duckdb.connect(db, read_only=True)
    except Exception as e:
        raise click.ClickException(f"Failed to connect to database: {e}") from e

    analyzer = EvidenceRedundancyAnalyzer(conn)

    if summary:
        # Get summary of unique contributions
        result = analyzer.get_unique_contributions_summary(
            method=method,
            evidence_type=evidence_type,
            comparator_methods=list(comparator) if comparator else None,
            group_by=list(group_by) if group_by else None,
        )

        if format == "json":
            output.write(json.dumps(result.dict(), indent=2))
        else:
            # Write header
            if format == "tsv":
                sep = "\t"
            else:
                sep = ","

            headers = result.group_by_fields + ["contribution_count"]
            output.write(sep.join(headers) + "\n")

            # Write data
            for summary in result.summaries:
                row = []
                for field in result.group_by_fields:
                    row.append(str(getattr(summary, field, "")))
                row.append(str(summary.contribution_count))
                output.write(sep.join(row) + "\n")

        click.echo(f"Total unique contributions: {result.total_unique}", err=True)

    else:
        # Get full unique contributions
        result = analyzer.get_unique_contributions(
            method=method,
            evidence_type=evidence_type,
            comparator_methods=list(comparator) if comparator else None,
        )

        if format == "json":
            output.write(json.dumps(result.dict(), indent=2))
        else:
            # For TSV/CSV, write the annotations
            if result.annotations:
                import pandas as pd

                df = pd.DataFrame(result.annotations)

                if format == "tsv":
                    df.to_csv(output, sep="\t", index=False)
                else:
                    df.to_csv(output, index=False)

        click.echo(f"Found {result.count} unique contributions", err=True)

    conn.close()


@evidence.command(name="compare-references")
@click.option("--db", "-d", required=True, help="Database connection string or path to .db/.ddb file.")
@click.option("--set1", "-s1", multiple=True, required=True, help="References in first set (can be repeated).")
@click.option("--set2", "-s2", multiple=True, required=True, help="References in second set (can be repeated).")
@click.option("--evidence-type", "-e", help="Filter by evidence type (e.g., IEA).")
@click.option("--output", "-o", type=click.File("w"), default="-", help="Output file (default: stdout).")
def compare_references(db, set1, set2, evidence_type, output):
    """
    Compare two sets of references to find unique and overlapping contributions.

    Examples
    --------
        # Compare two individual references
        go-db evidence compare-references -d mydb.ddb -s1 GO_REF:0000002 -s2 GO_REF:0000043

        # Compare groups of references
        go-db evidence compare-references -d mydb.ddb \\
            -s1 GO_REF:0000002 -s1 GO_REF:0000003 \\
            -s2 GO_REF:0000043 -s2 GO_REF:0000044

        # Filter by evidence type
        go-db evidence compare-references -d mydb.ddb \\
            -s1 GO_REF:0000002 -s2 GO_REF:0000043 -e IEA

    """
    from pathlib import Path

    import duckdb

    # Check if database exists
    db_path = Path(db)
    if not db_path.exists() and db != ":memory:":
        raise click.ClickException(f"Database file not found: {db}")

    try:
        conn = duckdb.connect(db, read_only=True)
    except Exception as e:
        raise click.ClickException(f"Failed to connect to database: {e}") from e

    analyzer = EvidenceRedundancyAnalyzer(conn)

    result = analyzer.compare_reference_sets(
        reference_set1=list(set1),
        reference_set2=list(set2),
        evidence_type=evidence_type,
    )

    # Format output
    output.write(f"Reference Set 1: {', '.join(result.reference_set1)}\n")
    output.write(f"Reference Set 2: {', '.join(result.reference_set2)}\n")
    if result.evidence_type:
        output.write(f"Evidence Type: {result.evidence_type}\n")
    output.write("\n")
    output.write(f"Unique to Set 1: {result.unique_to_set1}\n")
    output.write(f"Unique to Set 2: {result.unique_to_set2}\n")
    output.write(f"Overlap: {result.overlap}\n")
    output.write(f"Total in Set 1: {result.total_set1}\n")
    output.write(f"Total in Set 2: {result.total_set2}\n")

    conn.close()


@evidence.command(name="find-redundant")
@click.option("--db", "-d", required=True, help="Database connection string or path to .db/.ddb file.")
@click.option("--reference", "-r", required=True, help="Reference to check for redundancy.")
@click.option("--evidence-type", "-e", default="IEA", help="Evidence type (default: IEA).")
@click.option("--output", "-o", type=click.File("w"), default="-", help="Output file (default: stdout).")
@click.option("--format", "-f", type=click.Choice(["json", "tsv", "csv"]), default="tsv", help="Output format.")
def find_redundant(db, reference, evidence_type, output, format):
    """
    Find annotations where a specific reference is redundant.

    Examples
    --------
        # Find redundant IEA annotations for a reference
        go-db evidence find-redundant -d mydb.ddb -r GO_REF:0000002

        # Output as JSON
        go-db evidence find-redundant -d mydb.ddb -r GO_REF:0000002 -f json

        # Save to file
        go-db evidence find-redundant -d mydb.ddb -r GO_REF:0000043 -o redundant.tsv

    """
    import json
    from pathlib import Path

    import duckdb

    # Check if database exists
    db_path = Path(db)
    if not db_path.exists() and db != ":memory:":
        raise click.ClickException(f"Database file not found: {db}")

    try:
        conn = duckdb.connect(db, read_only=True)
    except Exception as e:
        raise click.ClickException(f"Failed to connect to database: {e}") from e

    analyzer = EvidenceRedundancyAnalyzer(conn)

    result = analyzer.find_redundant_references(
        reference=reference,
        evidence_type=evidence_type,
    )

    if format == "json":
        output.write(json.dumps(result.dict(), indent=2))
    else:
        # For TSV/CSV, write the annotations
        if result.annotations:
            import pandas as pd

            df = pd.DataFrame(result.annotations)

            if format == "tsv":
                df.to_csv(output, sep="\t", index=False)
            else:
                df.to_csv(output, index=False)

    click.echo(f"Found {result.count} redundant annotations for {reference}", err=True)

    conn.close()


if __name__ == "__main__":
    main()
