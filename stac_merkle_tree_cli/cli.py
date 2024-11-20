# stac_merkle_cli/cli.py

import click
import json
from pathlib import Path
from .compute_merkle_info import process_catalog
from .verify_merkle_tree_json import verify_merkle_tree

@click.group()
def cli():
    """
    STAC Merkle Tree CLI Tool.

    Commands:
      compute    Compute Merkle hashes for a STAC catalog.
      verify     Verify the integrity of a Merkle tree JSON file.
    """
    pass

@cli.command()
@click.argument('catalog_path', type=click.Path(exists=True, file_okay=False), required=True)
@click.option('--merkle-tree-file', type=click.Path(), default='merkle_tree.json',
              help='Path to the output Merkle tree structure file.')
def compute(catalog_path: str, merkle_tree_file: str):
    """
    Compute Merkle hashes for STAC catalogs, handling nested catalogs and collections.

    CATALOG_PATH: Path to the root directory containing 'catalog.json'.
    """
    catalog_dir = Path(catalog_path)
    catalog_json_path = catalog_dir / 'catalog.json'
    
    if not catalog_json_path.exists():
        click.echo(f"Error: 'catalog.json' not found in {catalog_dir}", err=True)
        exit(1)
    
    # Define the root hash_method
    root_hash_method = {
        'function': 'sha256',
        'fields': ['*'],
        'ordering': 'ascending',
        'description': 'Computed by including the merkle:root of collections and the catalog\'s own merkle:object_hash.'
    }
    
    # Process the root catalog
    merkle_tree = process_catalog(catalog_json_path, root_hash_method)
    
    if not merkle_tree:
        click.echo("Error: Merkle tree is empty. Check your Catalog structure and hash methods.", err=True)
        exit(1)
    
    # Save the merkle_tree.json
    output_path = Path(catalog_path) / merkle_tree_file
    try:
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(merkle_tree, f, indent=2)
        click.echo(f"Merkle tree structure saved to {output_path}")
    except Exception as e:
        click.echo(f"Error writing to {output_path}: {e}", err=True)
        exit(1)

@cli.command()
@click.argument('merkle_tree_file', type=click.Path(exists=True, dir_okay=False), required=True)
def verify(merkle_tree_file: str):
    """
    Verify that the merkle:root in the Merkle tree JSON matches the recalculated root.

    MERKLE_TREE_FILE: Path to the Merkle tree JSON file.
    """
    merkle_tree_path = Path(merkle_tree_file)
    verification_result = verify_merkle_tree(merkle_tree_path)
    if verification_result:
        click.echo("Verification Successful: The merkle:root matches.")
        exit(0)
    else:
        click.echo("Verification Failed: The merkle:root does not match.", err=True)
        exit(1)

if __name__ == '__main__':
    cli()
