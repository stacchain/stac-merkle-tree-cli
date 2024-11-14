# stac_merkle_cli/cli.py

import click
from pathlib import Path
from .compute_merkle_info import process_catalog

@click.command()
@click.argument('catalog_path', type=click.Path(exists=True, file_okay=True, dir_okay=False))
def main(catalog_path):
    """
    Computes and adds Merkle info to each STAC object in the catalog.

    CATALOG_PATH is the path to your root catalog.json file.
    """
    catalog_path = Path(catalog_path).resolve()

    if not catalog_path.exists():
        click.echo(f"Catalog file does not exist: {catalog_path}", err=True)
        return

    # Process the root catalog
    process_catalog(catalog_path)

    click.echo("Merkle info computation and addition completed.")
