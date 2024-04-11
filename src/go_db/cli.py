"""Command line interface for go-db."""
import click
import logging

from go_db.main import load_all, LoaderConfiguration, validate_db_iter, validate_db, materialize_view

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
@click.option("--db",
                "-d",
              show_default=True,
              default=":memory:", help="Database connection string.")
@click.option("--append/--no-append", default=False, show_default=True)
@click.option("--force/--no-force",
              "-f",
              default=False,
              show_default=True,
              help="")
@click.option("--go-db-path",
                "-g",
              default="db/go.db",
              show_default=True,
              help="Path to semsql/sqlite version of GO ontology.")
@click.option("--validate/--no-validate", default=True, show_default=True)
@click.argument("sources", nargs=-1)
def load(sources, validate, **kwargs):
    """
    Load sources into a database based on a config file.

    Example
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
@click.option("--db",
                "-d",
              default=":memory:", help="Database connection string.")
def validate(**kwargs):
    """Run the go-db's demo command."""
    print(kwargs)
    logger.info("Validating the database.")
    config = LoaderConfiguration(**kwargs, sources=[])
    print(f"Validating the database; conf={config}.")
    for x in validate_db_iter(config):
        print(x)


@main.command()
@click.option("--db",
                "-d",
              show_default=True,
              default=":memory:", help="Database connection string.")
@click.option("--append/--no-append", default=False, show_default=True)
@click.option("--force/--no-force",
              "-f",
              default=False,
              show_default=True)
@click.option("--go-db-path",
                "-g",
              default="db/go.db",
              show_default=True,
              help="Path to semsql/sqlite version of GO ontology.")
@click.argument("view_name")
def materialize(view_name, **kwargs):
    """
    Materialize a view.
    """
    config = LoaderConfiguration(**kwargs)
    materialize_view(config, view_name)

if __name__ == "__main__":
    main()
