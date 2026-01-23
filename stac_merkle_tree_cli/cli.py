import json
from pathlib import Path

import click

from .compute_merkle_info import process_catalog
from .proofs import generate_item_proofs
from .verify import verify_tree
from .verify_proof import verify_item


@click.group()
def main():
    """
    STAC Merkle Tree CLI

    Tools for ensuring metadata integrity and provenance in STAC Catalogs.
    """
    pass


@main.command()
@click.argument(
    "catalog_path", type=click.Path(exists=True, file_okay=False), required=True
)
@click.option(
    "--merkle-tree-file",
    type=click.Path(),
    default="merkle_tree.json",
    help="Path to the output Merkle tree structure file.",
)
@click.option(
    "--ignore-links/--include-links",
    default=True,
    help='Exclude the "links" field from hashing to prevent circular dependencies (Default: True).',
)
def compute(catalog_path: str, merkle_tree_file: str, ignore_links: bool):
    """
    Computes Merkle hashes for a STAC Catalog.

    Walks the catalog hierarchy, computes 'merkle:object_hash' for every Item,
    and aggregates them into 'merkle:root' values for Collections and Catalogs.
    """
    catalog_dir = Path(catalog_path)
    catalog_json_path = catalog_dir / "catalog.json"

    if not catalog_json_path.exists():
        click.echo(f"Error: 'catalog.json' not found in {catalog_dir}", err=True)
        exit(1)

    # Define the root hash_method
    root_hash_method = {
        "function": "sha256",
        "fields": ["*"],  # This will be filtered by ignore_links logic internally
        "ordering": "ascending",
        "description": "Computed by including the merkle:root of collections and the catalog's own merkle:object_hash.",
    }

    click.echo("Starting compute process...")
    click.echo(f" - Ignore Links: {'Yes' if ignore_links else 'No'}")

    # Process the root catalog
    merkle_tree = process_catalog(
        catalog_json_path,
        root_hash_method,
        ignore_links=ignore_links,
    )

    if not merkle_tree:
        click.echo(
            "Error: Merkle tree is empty. Check your Catalog structure and hash methods.",
            err=True,
        )
        exit(1)

    # Save the merkle_tree.json
    output_path = Path(f"{catalog_path}/{merkle_tree_file}")
    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(merkle_tree, f, indent=2)
        click.echo(f"Success! Merkle tree structure saved to {output_path}")
    except Exception as e:
        click.echo(f"Error writing to {output_path}: {e}", err=True)
        exit(1)


@main.command()
@click.argument(
    "catalog_path", type=click.Path(exists=True, file_okay=False), required=True
)
@click.option(
    "--base-url", required=True, help="The base URL where proof files will be hosted."
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="proofs",
    help="Directory to save proof files (default: ./proofs)",
)
def proofs(catalog_path: str, base_url: str, output_dir: str):
    """
    Generates Merkle Inclusion Proofs for all Items.
    """
    catalog_dir = Path(catalog_path)
    merkle_tree_path = catalog_dir / "merkle_tree.json"

    if not merkle_tree_path.exists():
        click.echo(
            "Error: 'merkle_tree.json' not found. Run 'compute' first.", err=True
        )
        exit(1)

    click.echo(f"Generating proofs for {catalog_path}...")

    try:
        generate_item_proofs(merkle_tree_path, output_dir, base_url)
        click.echo(f"Success! Proofs generated in '{output_dir}' and items updated.")
    except Exception as e:
        click.echo(f"Error generating proofs: {e}", err=True)
        exit(1)


@main.command()
@click.argument(
    "catalog_path", type=click.Path(exists=True, file_okay=False), required=True
)
def verify(catalog_path: str):
    """
    Verifies the integrity of the Merkle Tree.

    Re-calculates hashes from the tree structure and compares them
    against the stored 'merkle:root' values.
    """
    success = verify_tree(catalog_path)

    if not success:
        exit(1)


@main.command()
@click.argument(
    "item_path", type=click.Path(exists=True, file_okay=True), required=True
)
@click.argument(
    "proof_path", type=click.Path(exists=True, file_okay=True), required=True
)
def verify_proof(item_path: str, proof_path: str):
    """
    Verify a single Item against a Merkle Proof file.

    This allows users to verify an Item without needing the entire catalog.
    """
    try:
        with open(item_path, "r") as f:
            item = json.load(f)

        with open(proof_path, "r") as f:
            proof = json.load(f)

        if verify_item(item, proof):
            click.secho("✅ Verification SUCCESS", fg="green")
        else:
            click.secho("❌ Verification FAILED", fg="red")
            exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in file: {e}", err=True)
        exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        exit(1)


if __name__ == "__main__":
    main()
