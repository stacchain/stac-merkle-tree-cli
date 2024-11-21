#!/usr/bin/env python3

import hashlib
import json
import sys
from typing import List

import click


def load_collection(collection_file: str) -> dict:
    """
    Loads the STAC Collection JSON file.

    Parameters:
    - collection_file (str): Path to the STAC Collection JSON file.

    Returns:
    - dict: Parsed JSON content of the collection.
    """
    try:
        with open(collection_file, "r", encoding="utf-8") as f:
            collection = json.load(f)
        return collection
    except Exception as e:
        click.echo(f"Error loading collection file: {e}", err=True)
        sys.exit(1)


def get_merkle_fields(collection: dict) -> dict:
    """
    Extracts the Merkle-related fields from the collection.

    Parameters:
    - collection (dict): The collection data.

    Returns:
    - dict: A dictionary containing merkle:object_hash, merkle:proof, and merkle:hash_method.
    """
    try:
        merkle_object_hash = (
            collection.get("merkle:object_hash")
            or collection["properties"]["merkle:object_hash"]
        )
        merkle_proof = (
            collection.get("merkle:proof") or collection["properties"]["merkle:proof"]
        )
        merkle_hash_method = (
            collection.get("merkle:hash_method")
            or collection["properties"]["merkle:hash_method"]
        )
        return {
            "object_hash": merkle_object_hash,
            "proof": merkle_proof,
            "hash_method": merkle_hash_method,
        }
    except KeyError as e:
        click.echo(f"Missing required Merkle field in collection: {e}", err=True)
        sys.exit(1)


def verify_merkle_proof(
    collection_hash: str,
    proof_hashes: List[str],
    proof_positions: List[str],
    merkle_root: str,
    hash_function: str = "sha256",
) -> bool:
    """
    Verifies that a given collection hash is part of the Merkle tree with the specified Merkle root.

    Parameters:
    - collection_hash (str): The merkle:object_hash of the collection (hex string).
    - proof_hashes (List[str]): List of sibling hashes in the Merkle proof (hex strings).
    - proof_positions (List[str]): List of positions corresponding to each sibling hash ("left" or "right").
    - merkle_root (str): The Merkle root of the catalog (hex string).
    - hash_function (str): The hash function to use (default: "sha256").

    Returns:
    - bool: True if verification is successful, False otherwise.
    """
    if len(proof_hashes) != len(proof_positions):
        click.echo(
            "The number of proof hashes must match the number of proof positions.",
            err=True,
        )
        sys.exit(1)

    # Initialize current hash with the collection's hash
    try:
        current_hash = bytes.fromhex(collection_hash)
    except ValueError:
        click.echo("Invalid hex string for collection_hash.", err=True)
        sys.exit(1)

    # Iterate through each proof step
    for idx, (sibling_hash_hex, position) in enumerate(
        zip(proof_hashes, proof_positions)
    ):
        try:
            sibling_hash = bytes.fromhex(sibling_hash_hex)
        except ValueError:
            click.echo(
                f"Invalid hex string in proof_hashes at index {idx}: {sibling_hash_hex}",
                err=True,
            )
            sys.exit(1)

        if position.lower() == "left":
            combined = sibling_hash + current_hash
        elif position.lower() == "right":
            combined = current_hash + sibling_hash
        else:
            click.echo(
                f"Invalid position value at index {idx}: {position}. Must be 'left' or 'right'.",
                err=True,
            )
            sys.exit(1)

        # Compute the new hash using the specified hash function
        hash_func = getattr(hashlib, hash_function.replace("-", ""), None)
        if not hash_func:
            click.echo(f"Unsupported hash function: {hash_function}", err=True)
            sys.exit(1)

        current_hash = hash_func(combined).digest()

    # Compare the computed root with the provided Merkle root
    computed_merkle_root = current_hash.hex()
    print("computed_merkle_root: ", computed_merkle_root)
    return computed_merkle_root.lower() == merkle_root.lower()


@click.command()
@click.argument("collection_file", type=click.Path(exists=True))
@click.option(
    "--merkle-root", required=False, help="Merkle root of the catalog (hex string)."
)
def main(collection_file, merkle_root):
    """
    Verify if a STAC collection is part of a catalog using Merkle proofs.

    COLLECTION_FILE is the path to the STAC Collection JSON file.
    """
    # Load the collection
    collection = load_collection(collection_file)

    # Extract Merkle fields
    merkle_fields = get_merkle_fields(collection)
    collection_hash = merkle_fields["object_hash"]
    proof = merkle_fields["proof"]
    hash_method = merkle_fields["hash_method"]

    merkle_root = proof.get("catalog_root") or merkle_root
    if not merkle_root:
        click.echo("Merkle root not provided in proof or as an argument.", err=True)
        sys.exit(1)

    print("merkle_root: ", merkle_root)

    # Get hash function
    hash_function = hash_method.get("function", "sha256")

    # Get proof hashes and positions
    proof_hashes = proof.get("hashes", [])
    proof_positions = proof.get("positions", [])

    # Verify Merkle proof
    is_valid = verify_merkle_proof(
        collection_hash=collection_hash,
        proof_hashes=proof_hashes,
        proof_positions=proof_positions,
        merkle_root=merkle_root,
        hash_function=hash_function,
    )

    if is_valid:
        click.secho(
            "Verification successful: The collection is part of the catalog.",
            fg="green",
        )
    else:
        click.secho(
            "Verification failed: The collection is NOT part of the catalog.", fg="red"
        )


if __name__ == "__main__":
    main()
