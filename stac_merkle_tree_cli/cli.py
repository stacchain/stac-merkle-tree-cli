# stac_merkle_cli/cli.py

import json
import logging
from pathlib import Path

import click

from .compute_merkle_info import MerkleTreeProcessor
from .verify_merkle_tree_json import MerkleTreeVerifier

# Configure the root logger
logger = logging.getLogger("stac_merkle_cli")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose (debug) logging.")
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Enable quiet mode. Only warnings and errors will be shown.",
)
@click.pass_context
def cli(ctx, verbose, quiet):
    """
    STAC Merkle Tree CLI Tool.

    Commands:
      compute    Compute Merkle hashes for a STAC catalog.
      verify     Verify the integrity of a Merkle tree JSON file.
    """
    # Adjust logging level based on options
    if verbose and quiet:
        click.echo("Error: --verbose and --quiet cannot be used together.", err=True)
        ctx.exit(1)
    elif verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")
    elif quiet:
        logger.setLevel(logging.WARNING)
        for handler in logger.handlers:
            handler.setLevel(logging.WARNING)
        logger.debug("Quiet mode enabled.")


@cli.command()
@click.argument(
    "catalog_path", type=click.Path(exists=True, file_okay=False), required=True
)
@click.option(
    "--merkle-tree-file",
    type=click.Path(),
    default="merkle_tree.json",
    help="Path to the output Merkle tree structure file.",
)
@click.pass_context
def compute(ctx, catalog_path: str, merkle_tree_file: str):
    """
    Compute Merkle hashes for STAC catalogs, handling nested catalogs and collections.

    CATALOG_PATH: Path to the root directory containing 'catalog.json'.
    """
    catalog_dir = Path(catalog_path)
    catalog_json_path = catalog_dir / "catalog.json"

    if not catalog_json_path.exists():
        logger.error(f"'catalog.json' not found in {catalog_dir}")
        click.echo(f"Error: 'catalog.json' not found in {catalog_dir}", err=True)
        ctx.exit(1)

    # Define the root hash_method
    root_hash_method = {
        "function": "sha256",
        "fields": ["*"],
        "ordering": "ascending",
        "description": "Computed by including the merkle:root of collections and the catalog's own merkle:object_hash.",
    }

    # Initialize the MerkleTreeProcessor
    processor = MerkleTreeProcessor(logger=logger)

    # Process the root catalog
    merkle_tree = processor.process_catalog(catalog_json_path, root_hash_method)

    if not merkle_tree:
        logger.error(
            "Merkle tree is empty. Check your Catalog structure and hash methods."
        )
        click.echo(
            "Error: Merkle tree is empty. Check your Catalog structure and hash methods.",
            err=True,
        )
        ctx.exit(1)

    # Save the merkle_tree.json
    output_path = Path(catalog_path) / merkle_tree_file
    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(merkle_tree, f, indent=2)
        logger.info(f"Merkle tree structure saved to {output_path}")
        click.echo(f"Merkle tree structure saved to {output_path}")
    except Exception as e:
        logger.exception(f"Error writing to {output_path}: {e}")
        click.echo(f"Error writing to {output_path}: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument(
    "merkle_tree_file", type=click.Path(exists=True, dir_okay=False), required=True
)
@click.pass_context
def verify(ctx, merkle_tree_file: str):
    """
    Verify that the merkle:root in the Merkle tree JSON matches the recalculated root.

    MERKLE_TREE_FILE: Path to the Merkle tree JSON file.
    """
    merkle_tree_path = Path(merkle_tree_file)
    logger.info(f"Verifying Merkle tree at {merkle_tree_path}")

    verifier = MerkleTreeVerifier(logger=logger)
    verification_result = verifier.verify_merkle_tree(merkle_tree_path)

    if verification_result:
        logger.info("Verification Successful: The merkle:root matches.")
        click.echo("Verification Successful: The merkle:root matches.")
        ctx.exit(0)
    else:
        logger.error("Verification Failed: The merkle:root does not match.")
        click.echo("Verification Failed: The merkle:root does not match.", err=True)
        ctx.exit(1)


if __name__ == "__main__":
    cli()
