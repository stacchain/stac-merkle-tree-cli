#!/usr/bin/env python3

import click
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any

# Define Merkle fields to exclude from hashing
MERKLE_FIELDS = {"merkle:object_hash", "merkle:hash_method", "merkle:root"}

def remove_merkle_fields(data):
    """
    Recursively removes Merkle fields and the Merkle extension URL from a nested dictionary.
    Also sorts lists like 'stac_extensions' for consistent ordering.

    Parameters:
    - data: The data structure (dict or list) to process.

    Returns:
    - The data structure with Merkle fields and extension URL removed, and lists sorted.
    """
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            if k not in MERKLE_FIELDS:
                if k == 'stac_extensions' and isinstance(v, list):
                    # Remove Merkle extension URL from stac_extensions
                    extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
                    v = [ext for ext in v if ext != extension_url]
                    # Sort the stac_extensions list for consistent ordering
                    v.sort()
                new_data[k] = remove_merkle_fields(v)
        return new_data
    elif isinstance(data, list):
        return [remove_merkle_fields(v) for v in data]
    else:
        return data

def compute_merkle_object_hash(
    stac_object: Dict[str, Any],
    hash_method: Dict[str, Any]
) -> str:
    """
    Computes the merkle:object_hash for a STAC object (Catalog, Collection, or Item).

    Parameters:
    - stac_object (dict): The STAC object JSON content.
    - hash_method (dict): The hash method details from merkle:hash_method.

    Returns:
    - str: The computed Merkle object hash as a hexadecimal string.
    """
    fields = hash_method.get('fields', ['*'])
    if fields == ['*'] or fields == ['all']:
        # Exclude Merkle fields from all levels
        data_to_hash = remove_merkle_fields(stac_object)
    else:
        # Include only specified fields, then remove Merkle fields
        selected_data = {field: stac_object.get(field) for field in fields if field in stac_object}
        data_to_hash = remove_merkle_fields(selected_data)
    # Serialize the data to a canonical JSON string
    json_str = json.dumps(data_to_hash, sort_keys=True, separators=(',', ':'))
    # Get the hash function
    hash_function_name = hash_method.get('function', 'sha256').replace('-', '').lower()
    hash_func = getattr(hashlib, hash_function_name, None)
    if not hash_func:
        raise ValueError(f"Unsupported hash function: {hash_function_name}")
    # Compute the hash
    merkle_object_hash = hash_func(json_str.encode('utf-8')).hexdigest()
    return merkle_object_hash

def compute_merkle_root(hashes: List[str], ordering: str, hash_function: str) -> str:
    """
    Computes the merkle:root by building a Merkle tree from the provided hashes.

    Parameters:
    - hashes (List[str]): List of merkle:object_hash values of child objects.
    - ordering (str): Ordering method specified in merkle:hash_method.ordering.
    - hash_function (str): The hash function to use (e.g., 'sha256').

    Returns:
    - str: The computed Merkle root as a hexadecimal string.
    """
    # Order the hashes
    if ordering == 'ascending':
        hashes.sort()
    elif ordering == 'descending':
        hashes.sort(reverse=True)
    elif ordering == 'unsorted':
        pass  # Keep the original order
    else:
        raise ValueError(f"Unsupported ordering method: {ordering}")

    # Convert hash_function to actual function
    hash_func = getattr(hashlib, hash_function.replace('-', '').lower(), None)
    if not hash_func:
        raise ValueError(f"Unsupported hash function: {hash_function}")

    # Build the Merkle tree
    def merkle_tree_level(nodes: List[str]) -> List[str]:
        if len(nodes) == 1:
            return nodes
        new_level = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            if i + 1 < len(nodes):
                right = nodes[i + 1]
            else:
                right = left  # Duplicate the last node if odd number of nodes
            combined = bytes.fromhex(left) + bytes.fromhex(right)
            new_hash = hash_func(combined).hexdigest()
            new_level.append(new_hash)
        return merkle_tree_level(new_level)

    root_hash = merkle_tree_level(hashes)[0]
    return root_hash

def process_item(item_path: Path, hash_method: Dict[str, Any]) -> str:
    """
    Processes a STAC Item to compute and add Merkle info.

    Parameters:
    - item_path (Path): Path to the Item JSON file.
    - hash_method (dict): The hash method to use.

    Returns:
    - str: The merkle:object_hash of the Item.
    """
    try:
        with item_path.open('r', encoding='utf-8') as f:
            item_json = json.load(f)

        # Compute merkle:object_hash
        own_hash = compute_merkle_object_hash(item_json, hash_method)

        # Add merkle:object_hash to 'properties'
        properties = item_json.setdefault('properties', {})
        properties['merkle:object_hash'] = own_hash

        # Ensure the Merkle extension is listed
        item_json.setdefault('stac_extensions', [])
        extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
        if extension_url not in item_json['stac_extensions']:
            item_json['stac_extensions'].append(extension_url)
            item_json['stac_extensions'].sort()  # Sort for consistent ordering

        # Save the updated Item JSON
        with item_path.open('w', encoding='utf-8') as f:
            json.dump(item_json, f, indent=2)
            f.write('\n')

        click.echo(f"Processed Item: {item_path}")

        return own_hash

    except Exception as e:
        click.echo(f"Error processing Item {item_path}: {e}", err=True)
        return ''


def process_collection(collection_path: Path, parent_hash_method: Dict[str, Any]) -> str:
    """
    Processes a STAC Collection to compute and add Merkle info.

    Parameters:
    - collection_path (Path): Path to the Collection JSON file.
    - parent_hash_method (dict): The hash method inherited from the parent.

    Returns:
    - str: The merkle:object_hash of the Collection.
    """
    try:
        with collection_path.open('r', encoding='utf-8') as f:
            collection_json = json.load(f)

        # Determine the hash_method to use
        hash_method = collection_json.get('merkle:hash_method', parent_hash_method)

        if not hash_method:
            raise ValueError(f"Hash method not specified for {collection_path}")

        # Process items in the collection folder, including nested subdirectories
        collection_folder = collection_path.parent
        item_paths = list(collection_folder.rglob('*.json'))
        # Exclude the collection file itself
        item_paths = [p for p in item_paths if p.resolve() == p.resolve() and p.resolve() != collection_path.resolve()]

        # Load items and their IDs
        items = []
        for item_file in item_paths:
            with item_file.open('r', encoding='utf-8') as f:
                item_json = json.load(f)
                if item_json.get('type') != 'Feature':
                    continue  # Skip non-item JSON files
                item_id = item_json.get('id', '')
                items.append((item_id, item_file))

        # Sort items based on their IDs
        items.sort(key=lambda x: x[0])

        item_hashes = []
        for item_id, item_file in items:
            item_hash = process_item(item_file, hash_method)
            if item_hash:
                item_hashes.append(item_hash)

        # Compute merkle:object_hash
        own_hash = compute_merkle_object_hash(collection_json, hash_method)
        collection_json['merkle:object_hash'] = own_hash
        item_hashes.append(own_hash)  # Add own hash before computing Merkle root

        # Compute merkle:root
        hash_function_name = hash_method.get('function', 'sha256')
        merkle_root = compute_merkle_root(item_hashes, 'unsorted', hash_function_name)
        collection_json['merkle:root'] = merkle_root
        collection_json['merkle:hash_method'] = hash_method

        # Ensure the Merkle extension is listed
        collection_json.setdefault('stac_extensions', [])
        extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
        if extension_url not in collection_json['stac_extensions']:
            collection_json['stac_extensions'].append(extension_url)
        # Sort stac_extensions for consistent ordering
        collection_json['stac_extensions'].sort()

        # Save the updated Collection JSON
        with collection_path.open('w', encoding='utf-8') as f:
            json.dump(collection_json, f, indent=2)
            f.write('\n')

        click.echo(f"Processed Collection: {collection_path}")

        return own_hash

    except Exception as e:
        click.echo(f"Error processing Collection {collection_path}: {e}", err=True)
        return ''

def process_catalog(catalog_path: Path) -> str:
    """
    Processes the root STAC Catalog to compute and add Merkle info.

    Parameters:
    - catalog_path (Path): Path to the Catalog JSON file.

    Returns:
    - str: The merkle:object_hash of the Catalog.
    """
    try:
        with catalog_path.open('r', encoding='utf-8') as f:
            catalog_json = json.load(f)

        # Root hash method
        hash_method = {
            'function': 'sha256',
            'fields': ['*'],
            'ordering': 'ascending',
            'description': 'Computed by including the merkle:root of collections and the catalogs own merkle:object_hash.'
        }

        # Process collections in the collections folder
        catalog_folder = catalog_path.parent
        collections_folder = catalog_folder / 'collections'
        collection_hashes = []

        if not collections_folder.exists():
            click.echo(f"Collections folder not found: {collections_folder}", err=True)
            return ''

        for collection_dir in collections_folder.iterdir():
            if collection_dir.is_dir():
                collection_json_path = collection_dir / 'collection.json'
                if collection_json_path.exists():
                    collection_hash = process_collection(collection_json_path, hash_method)
                    if collection_hash:
                        # Load the updated collection.json to get its merkle:root
                        with collection_json_path.open('r', encoding='utf-8') as f:
                            collection_json = json.load(f)
                        collection_root = collection_json.get('merkle:root')
                        if collection_root:
                            collection_hashes.append(collection_root)
                        else:
                            click.echo(f"Collection merkle:root not found for {collection_json_path}", err=True)
                    else:
                        click.echo(f"Failed to process collection {collection_json_path}", err=True)
                else:
                    click.echo(f"collection.json not found in {collection_dir}", err=True)

        # Compute merkle:object_hash of the catalog
        own_hash = compute_merkle_object_hash(catalog_json, hash_method)
        catalog_json['merkle:object_hash'] = own_hash
        collection_hashes.append(own_hash)

        # Compute merkle:root of the catalog
        ordering = hash_method.get('ordering', 'ascending')
        hash_function_name = hash_method.get('function', 'sha256')
        merkle_root = compute_merkle_root(collection_hashes, ordering, hash_function_name)
        catalog_json['merkle:root'] = merkle_root
        catalog_json['merkle:hash_method'] = hash_method

        # Ensure the Merkle extension is listed
        catalog_json.setdefault('stac_extensions', [])
        extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
        if extension_url not in catalog_json['stac_extensions']:
            catalog_json['stac_extensions'].append(extension_url)
        catalog_json['stac_extensions'].sort()

        # Save the updated Catalog JSON
        with catalog_path.open('w', encoding='utf-8') as f:
            json.dump(catalog_json, f, indent=2)
            f.write('\n')

        click.echo(f"Processed Catalog: {catalog_path}")

        return own_hash

    except Exception as e:
        click.echo(f"Error processing Catalog {catalog_path}: {e}", err=True)
        return ''