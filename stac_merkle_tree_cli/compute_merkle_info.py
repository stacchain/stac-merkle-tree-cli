#!/usr/bin/env python3

import click
import json
import hashlib
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# Define Merkle fields to exclude from hashing
MERKLE_FIELDS = {"merkle:object_hash", "merkle:hash_method", "merkle:root"}

def remove_merkle_fields(data: Any) -> Any:
    """
    Recursively removes Merkle fields and the Merkle extension URL from a nested dictionary or list.
    Also sorts lists like 'stac_extensions' for consistent ordering.

    Parameters:
    - data (Any): The data structure (dict, list, or other) to process.

    Returns:
    - Any: The data structure with Merkle fields and extension URL removed, and lists sorted.
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
    - stac_object (Dict[str, Any]): The STAC object JSON content.
    - hash_method (Dict[str, Any]): The hash method details from merkle:hash_method.

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

def compute_merkle_root_from_file(hashes_file_path: Path, hash_method: Dict[str, Any]) -> str:
    """
    Computes the merkle:root by building a Merkle tree from hashes stored in a file.

    Parameters:
    - hashes_file_path (Path): Path to the file containing hashes.
    - hash_method (Dict[str, Any]): The hash method to use.

    Returns:
    - str: The computed Merkle root as a hexadecimal string.
    """
    hash_function_name = hash_method.get('function', 'sha256').replace('-', '').lower()
    hash_func = getattr(hashlib, hash_function_name)
    ordering = hash_method.get('ordering', 'ascending')

    # Read hashes from file
    with hashes_file_path.open('r', encoding='utf-8') as f:
        hashes = [line.strip() for line in f if line.strip()]

    # Order hashes
    if ordering == 'ascending':
        hashes.sort()
    elif ordering == 'descending':
        hashes.sort(reverse=True)
    elif ordering == 'unsorted':
        pass  # Keep original order
    else:
        raise ValueError(f"Unsupported ordering method: {ordering}")

    # Build the Merkle tree
    while len(hashes) > 1:
        new_hashes = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]
            combined = bytes.fromhex(left) + bytes.fromhex(right)
            new_hash = hash_func(combined).hexdigest()
            new_hashes.append(new_hash)
        hashes = new_hashes

    return hashes[0]

def write_merkle_node(node_id: str, merkle_root: str, child_hashes_file: Path, merkle_tree_file: Path):
    """
    Writes a Merkle tree node to the Merkle tree structure file.

    Parameters:
    - node_id (str): The identifier of the node (e.g., collection or catalog ID).
    - merkle_root (str): The Merkle root hash of the node.
    - child_hashes_file (Path): Path to the file containing child hashes.
    - merkle_tree_file (Path): Path to the Merkle tree structure file.
    """
    node = {
        'node_id': node_id,
        'merkle_root': merkle_root,
        'child_hashes_file': str(child_hashes_file)
    }
    with merkle_tree_file.open('a', encoding='utf-8') as f:
        json.dump(node, f)
        f.write('\n')

def process_item(item_path: Path, hash_method: Dict[str, Any]) -> str:
    """
    Processes a STAC Item to compute and add Merkle info.

    Parameters:
    - item_path (Path): Path to the Item JSON file.
    - hash_method (Dict[str, Any]): The hash method to use.

    Returns:
    - str: The merkle:object_hash of the Item.
    """
    try:
        with item_path.open('r', encoding='utf-8') as f:
            item_json = json.load(f)

        if item_json.get('type') != 'Feature':
            return ''

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

def is_item_directory(directory: Path) -> bool:
    """
    Determines if a directory contains a single Item JSON file.

    Parameters:
    - directory (Path): Path to the directory.

    Returns:
    - bool: True if the directory contains exactly one JSON file of type 'Feature', False otherwise.
    """
    json_files = list(directory.glob('*.json'))
    if len(json_files) != 1:
        return False
    item_json = {}
    try:
        with json_files[0].open('r', encoding='utf-8') as f:
            item_json = json.load(f)
    except:
        return False
    return item_json.get('type') == 'Feature'

def process_collection(collection_path: Path, parent_hash_method: Dict[str, Any], merkle_tree_file: Path) -> str:
    """
    Processes a STAC Collection to compute its merkle:root and writes the Merkle node to a file.

    Parameters:
    - collection_path (Path): Path to the Collection JSON file.
    - parent_hash_method (Dict[str, Any]): The hash method inherited from the parent.
    - merkle_tree_file (Path): Path to the Merkle tree structure file.

    Returns:
    - str: The merkle:object_hash of the Collection.
    """
    try:
        with collection_path.open('r', encoding='utf-8') as f:
            collection_json = json.load(f)

        if collection_json.get('type') != 'Collection':
            return ''

        # Determine the hash_method to use
        hash_method = collection_json.get('merkle:hash_method', parent_hash_method)

        if not hash_method:
            raise ValueError(f"Hash method not specified for {collection_path}")

        # Use a temporary file for child hashes
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as temp_hashes_file:
            temp_hashes_file_path = Path(temp_hashes_file.name)

            collection_dir = collection_path.parent

            # Process items directly in the collection directory
            for item_file in collection_dir.glob('*.json'):
                if item_file == collection_path:
                    continue
                with item_file.open('r', encoding='utf-8') as f_item:
                    item_json = json.load(f_item)
                    if item_json.get('type') == 'Feature':
                        item_hash = process_item(item_file, hash_method)
                        if item_hash:
                            temp_hashes_file.write(item_hash + '\n')

            # Recursively process subdirectories
            for subdirectory in collection_dir.iterdir():
                if subdirectory.is_dir():
                    sub_collection_json = subdirectory / 'collection.json'
                    sub_catalog_json = subdirectory / 'catalog.json'

                    if sub_collection_json.exists():
                        # Process sub-collection
                        sub_collection_hash = process_collection(sub_collection_json, hash_method, merkle_tree_file)
                        if sub_collection_hash:
                            temp_hashes_file.write(sub_collection_hash + '\n')
                    elif sub_catalog_json.exists():
                        # Process sub-catalog
                        sub_catalog_hash = process_catalog(sub_catalog_json, hash_method, merkle_tree_file)
                        if sub_catalog_hash:
                            temp_hashes_file.write(sub_catalog_hash + '\n')
                    elif is_item_directory(subdirectory):
                        # Process item in its own directory
                        item_file = list(subdirectory.glob('*.json'))[0]
                        item_hash = process_item(item_file, hash_method)
                        if item_hash:
                            temp_hashes_file.write(item_hash + '\n')
                    else:
                        # Handle other cases or ignore
                        click.echo(f"Unrecognized structure in {subdirectory}", err=True)

        # Compute own merkle:object_hash
        own_hash = compute_merkle_object_hash(collection_json, hash_method)
        collection_json['merkle:object_hash'] = own_hash

        # Include own hash in the computation
        with temp_hashes_file_path.open('a', encoding='utf-8') as f:
            f.write(own_hash + '\n')

        # Compute merkle:root from hashes in the file
        merkle_root = compute_merkle_root_from_file(temp_hashes_file_path, hash_method)

        # Update collection JSON
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

        # Write the Merkle node to the Merkle tree structure file
        write_merkle_node(
            node_id=collection_json.get('id', str(collection_path)),
            merkle_root=merkle_root,
            child_hashes_file=temp_hashes_file_path,
            merkle_tree_file=merkle_tree_file
        )

        return own_hash

    except Exception as e:
        click.echo(f"Error processing Collection {collection_path}: {e}", err=True)
        return ''

def process_catalog(catalog_path: Path, hash_method: Dict[str, Any], merkle_tree_file: Path) -> str:
    """
    Processes the root STAC Catalog to compute its merkle:root and writes the Merkle node to a file.

    Parameters:
    - catalog_path (Path): Path to the Catalog JSON file.
    - hash_method (Dict[str, Any]): The hash method to use.
    - merkle_tree_file (Path): Path to the Merkle tree structure file.

    Returns:
    - str: The merkle:object_hash of the Catalog.
    """
    try:
        with catalog_path.open('r', encoding='utf-8') as f:
            catalog_json = json.load(f)

        if catalog_json.get('type') != 'Catalog':
            return ''

        # Use a temporary file for child hashes
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as temp_hashes_file:
            temp_hashes_file_path = Path(temp_hashes_file.name)

            catalog_dir = catalog_path.parent

            # Process collections in the 'collections' directory
            collections_dir = catalog_dir / 'collections'
            if not collections_dir.exists():
                click.echo(f"No 'collections' directory found in {catalog_dir}", err=True)
                return ''

            for collection_dir in collections_dir.iterdir():
                if collection_dir.is_dir():
                    collection_json_path = collection_dir / 'collection.json'
                    if collection_json_path.exists():
                        collection_hash = process_collection(collection_json_path, hash_method, merkle_tree_file)
                        if collection_hash:
                            temp_hashes_file.write(collection_hash + '\n')
                    else:
                        click.echo(f"'collection.json' not found in {collection_dir}", err=True)

        # Compute own merkle:object_hash
        own_hash = compute_merkle_object_hash(catalog_json, hash_method)
        catalog_json['merkle:object_hash'] = own_hash

        # Include own hash in the computation
        with temp_hashes_file_path.open('a', encoding='utf-8') as f:
            f.write(own_hash + '\n')

        # Compute merkle:root from hashes in the file
        merkle_root = compute_merkle_root_from_file(temp_hashes_file_path, hash_method)

        # Update catalog JSON
        catalog_json['merkle:root'] = merkle_root
        catalog_json['merkle:hash_method'] = hash_method

        # Ensure the Merkle extension is listed
        catalog_json.setdefault('stac_extensions', [])
        extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
        if extension_url not in catalog_json['stac_extensions']:
            catalog_json['stac_extensions'].append(extension_url)
        # Sort stac_extensions for consistent ordering
        catalog_json['stac_extensions'].sort()

        # Save the updated Catalog JSON
        with catalog_path.open('w', encoding='utf-8') as f:
            json.dump(catalog_json, f, indent=2)
            f.write('\n')

        click.echo(f"Processed Catalog: {catalog_path}")

        # Write the Merkle node to the Merkle tree structure file
        write_merkle_node(
            node_id=catalog_json.get('id', str(catalog_path)),
            merkle_root=merkle_root,
            child_hashes_file=temp_hashes_file_path,
            merkle_tree_file=merkle_tree_file
        )

        return own_hash

    except Exception as e:
        click.echo(f"Error processing Catalog {catalog_path}: {e}", err=True)
        return ''
