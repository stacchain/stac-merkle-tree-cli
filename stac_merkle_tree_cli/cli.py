# stac_merkle_cli/cli.py

import click
from pathlib import Path
from .compute_merkle_info import process_catalog

@click.command()
@click.argument('catalog_path', type=click.Path(exists=True), required=True)
@click.option('--merkle-tree-file', type=click.Path(), default='merkle_tree.json',
              help='Path to the output Merkle tree structure file.')
def main(catalog_path: str, merkle_tree_file: str):
    """
    CLI tool to compute Merkle hashes for STAC catalogs, handling nested catalogs and collections.

    Parameters:
    - CATALOG_PATH: Path to the root 'catalog.json' file.

    Options:
    --merkle-tree-file TEXT  Path to the output Merkle tree structure file. Defaults to 'merkle_tree.json'.
    """
    catalog_path = Path(catalog_path)
    merkle_tree_file = Path(merkle_tree_file)

    # Ensure the Merkle tree file is empty or create it
    if merkle_tree_file.exists():
        merkle_tree_file.unlink()
    merkle_tree_file.touch()

    # Define the root hash_method
    root_hash_method = {
        'function': 'sha256',
        'fields': ['*'],
        'ordering': 'ascending',
        'description': 'Computed by including the merkle:root of collections and the catalog\'s own merkle:object_hash.'
    }

    # Process the root catalog
    process_catalog(catalog_path, root_hash_method, merkle_tree_file)

    click.echo(f"Merkle tree structure saved to {merkle_tree_file}")

if __name__ == '__main__':
    main()
