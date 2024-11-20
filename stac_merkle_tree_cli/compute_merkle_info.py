# stac_merkle_cli/compute_merkle_info.py

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any


def remove_merkle_fields(data: Any) -> Any:
    """
    Recursively removes Merkle-specific fields from the data.
    """
    if isinstance(data, dict):
        return {k: remove_merkle_fields(v) for k, v in data.items() if k not in {"merkle:object_hash", "merkle:hash_method", "merkle:root"}}
    elif isinstance(data, list):
        return [remove_merkle_fields(item) for item in data]
    else:
        return data


def compute_merkle_object_hash(stac_object: Dict[str, Any], hash_method: Dict[str, Any]) -> str:
    """
    Computes the merkle:object_hash for a STAC object.

    Parameters:
    - stac_object (Dict[str, Any]): The STAC Catalog, Collection, or Item JSON object.
    - hash_method (Dict[str, Any]): The hash method details from merkle:hash_method.

    Returns:
    - str: The computed object hash as a hexadecimal string.
    """
    fields = hash_method.get('fields', ['*'])
    if fields == ['*'] or fields == ['all']:
        data_to_hash = remove_merkle_fields(stac_object)
    else:
        selected_data = {field: stac_object.get(field) for field in fields if field in stac_object}
        data_to_hash = remove_merkle_fields(selected_data)

    # Serialize the data to a compact JSON string with sorted keys
    json_str = json.dumps(data_to_hash, sort_keys=True, separators=(',', ':'))

    # Get the hash function
    hash_function_name = hash_method.get('function', 'sha256').replace('-', '').lower()
    hash_func = getattr(hashlib, hash_function_name, None)
    if not hash_func:
        raise ValueError(f"Unsupported hash function: {hash_function_name}")

    # Compute the hash
    return hash_func(json_str.encode('utf-8')).hexdigest()


def compute_merkle_root(hashes: List[str], hash_method: Dict[str, Any]) -> str:
    if not hashes:
        return ''
    
    # Enforce ordering
    ordering = hash_method.get('ordering', 'ascending')
    if ordering == 'ascending':
        hashes.sort()
    elif ordering == 'descending':
        hashes.sort(reverse=True)
    elif ordering != 'unsorted':
        raise ValueError(f"Unsupported ordering: {ordering}")
    
    # Get the hash function
    hash_function_name = hash_method.get('function', 'sha256').replace('-', '').lower()
    hash_func = getattr(hashlib, hash_function_name, None)
    if not hash_func:
        raise ValueError(f"Unsupported hash function: {hash_function_name}")
    
    current_level = hashes.copy()
    print(f"Initial hashes for merkle:root computation: {current_level}")

    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            combined = bytes.fromhex(left) + bytes.fromhex(right)
            new_hash = hash_func(combined).hexdigest()
            next_level.append(new_hash)
            print(f"Combined '{left}' + '{right}' => '{new_hash}'")
        current_level = next_level
        print(f"Next level hashes: {current_level}")

    print(f"Final merkle:root: {current_level[0]}")
    return current_level[0]



def process_item(item_path: Path, hash_method: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a STAC Item to compute and return its object hash.

    Parameters:
    - item_path (Path): Path to the Item JSON file.
    - hash_method (Dict[str, Any]): The hash method to use.

    Returns:
    - Dict[str, Any]: A dictionary containing 'node_id' and 'merkle:object_hash'.
    """
    try:
        with item_path.open('r', encoding='utf-8') as f:
            item_json = json.load(f)

        if item_json.get('type') != 'Feature':
            print(f"Skipping non-Item JSON: {item_path}")
            return {}

        # Compute merkle:object_hash
        object_hash = compute_merkle_object_hash(item_json, hash_method)

        # Add merkle:object_hash to 'properties'
        properties = item_json.setdefault('properties', {})
        properties['merkle:object_hash'] = object_hash

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

        print(f"Processed Item: {item_path}")

        # Return the structured Item node
        return {
            'node_id': item_json.get('id', item_path.stem),
            'type': 'Item',
            'merkle:object_hash': object_hash
        }

    except Exception as e:
        print(f"Error processing Item {item_path}: {e}")
        return {}


def process_collection(collection_path: Path, parent_hash_method: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a STAC Collection to compute its merkle:root and builds a hierarchical Merkle node.

    Parameters:
    - collection_path (Path): Path to the Collection JSON file.
    - parent_hash_method (Dict[str, Any]): The hash method inherited from the parent.

    Returns:
    - Dict[str, Any]: The structured Merkle tree node for the collection.
    """
    try:
        with collection_path.open('r', encoding='utf-8') as f:
            collection_json = json.load(f)

        if collection_json.get('type') != 'Collection':
            print(f"Skipping non-Collection JSON: {collection_path}")
            return {}

        # Determine the hash_method to use
        hash_method = collection_json.get('merkle:hash_method', parent_hash_method)

        if not hash_method:
            raise ValueError(f"Hash method not specified for {collection_path}")

        children = []

        collection_dir = collection_path.parent

        # Process items directly in the collection directory
        for item_file in collection_dir.glob('*.json'):
            if item_file == collection_path:
                continue
            item_node = process_item(item_file, hash_method)
            if item_node:
                children.append(item_node)

        # Recursively process subdirectories
        for subdirectory in collection_dir.iterdir():
            if subdirectory.is_dir():
                sub_collection_json = subdirectory / 'collection.json'
                sub_catalog_json = subdirectory / 'catalog.json'

                if sub_collection_json.exists():
                    # Process sub-collection
                    sub_collection_node = process_collection(sub_collection_json, hash_method)
                    if sub_collection_node:
                        children.append(sub_collection_node)
                elif sub_catalog_json.exists():
                    # Process sub-catalog
                    sub_catalog_node = process_catalog(sub_catalog_json, hash_method)
                    if sub_catalog_node:
                        children.append(sub_catalog_node)
                elif is_item_directory(subdirectory):
                    # Process item in its own directory
                    item_files = list(subdirectory.glob('*.json'))
                    if item_files:
                        item_file = item_files[0]
                        item_node = process_item(item_file, hash_method)
                        if item_node:
                            children.append(item_node)
                else:
                    # Handle other cases or ignore
                    print(f"Unrecognized structure in {subdirectory}")

        # Compute own merkle:object_hash
        own_object_hash = compute_merkle_object_hash(collection_json, hash_method)
        collection_json['merkle:object_hash'] = own_object_hash

        # Collect all hashes: own_object_hash + child hashes
        child_hashes = []
        for child in children:
            if child['type'] in {'Collection', 'Catalog'}:
                child_hashes.append(child.get('merkle:root'))
            else:
                child_hashes.append(child.get('merkle:object_hash'))

        # Exclude None values
        child_hashes = [h for h in child_hashes if h]

        # Include own_object_hash
        all_hashes = child_hashes + [own_object_hash]

        # Compute merkle:root
        merkle_root = compute_merkle_root(all_hashes, hash_method)

        collection_json['merkle:root'] = merkle_root
        collection_json['merkle:hash_method'] = hash_method

        # Ensure the Merkle extension is listed and sorted
        extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
        collection_json.setdefault('stac_extensions', [])
        if extension_url not in collection_json['stac_extensions']:
            collection_json['stac_extensions'].append(extension_url)
        collection_json['stac_extensions'].sort()

        # Save the updated Collection JSON
        with collection_path.open('w', encoding='utf-8') as f:
            json.dump(collection_json, f, indent=2)
            f.write('\n')

        print(f"Processed Collection: {collection_path}")

        # Build the hierarchical Merkle node
        collection_node = {
            'node_id': collection_json.get('id', str(collection_path)),
            'type': 'Collection',
            'merkle:object_hash': own_object_hash,
            'merkle:root': merkle_root,
            'children': children
        }

        return collection_node

    except Exception as e:
        print(f"Error processing Collection {collection_path}: {e}")
        return {}


def process_catalog(catalog_path: Path, parent_hash_method: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Processes the root STAC Catalog to compute its merkle:root and builds a hierarchical Merkle node.

    Parameters:
    - catalog_path (Path): Path to the Catalog JSON file.
    - parent_hash_method (Dict[str, Any], optional): The hash method inherited from the parent.

    Returns:
    - Dict[str, Any]: The structured Merkle tree node for the catalog.
    """
    try:
        with catalog_path.open('r', encoding='utf-8') as f:
            catalog_json = json.load(f)

        if catalog_json.get('type') != 'Catalog':
            print(f"Skipping non-Catalog JSON: {catalog_path}")
            return {}

        # Determine the hash_method to use
        hash_method = catalog_json.get('merkle:hash_method', parent_hash_method)

        if not hash_method:
            raise ValueError(f"Hash method not specified for {catalog_path}")

        children = []

        catalog_dir = catalog_path.parent

        # Process collections in the 'collections' directory
        collections_dir = catalog_dir / 'collections'
        if not collections_dir.exists():
            print(f"No 'collections' directory found in {catalog_dir}")
            # It's possible for a catalog to have no collections
        else:
            for collection_dir in collections_dir.iterdir():
                if collection_dir.is_dir():
                    collection_json_path = collection_dir / 'collection.json'
                    if collection_json_path.exists():
                        collection_node = process_collection(collection_json_path, hash_method)
                        if collection_node:
                            children.append(collection_node)
                    else:
                        print(f"'collection.json' not found in {collection_dir}")

        # Compute own merkle:object_hash
        own_object_hash = compute_merkle_object_hash(catalog_json, hash_method)
        catalog_json['merkle:object_hash'] = own_object_hash

        # Collect all hashes: own_object_hash + child hashes
        child_hashes = []
        for child in children:
            if child['type'] in {'Collection', 'Catalog'}:
                child_hashes.append(child.get('merkle:root'))
            else:
                child_hashes.append(child.get('merkle:object_hash'))

        # Exclude None values
        child_hashes = [h for h in child_hashes if h]

        # Include own_object_hash
        all_hashes = child_hashes + [own_object_hash]

        # Compute merkle:root
        merkle_root = compute_merkle_root(all_hashes, hash_method)

        catalog_json['merkle:root'] = merkle_root
        catalog_json['merkle:hash_method'] = hash_method

        # Ensure the Merkle extension is listed and sorted
        extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
        catalog_json.setdefault('stac_extensions', [])
        if extension_url not in catalog_json['stac_extensions']:
            catalog_json['stac_extensions'].append(extension_url)
        catalog_json['stac_extensions'].sort()

        # Save the updated Catalog JSON
        with catalog_path.open('w', encoding='utf-8') as f:
            json.dump(catalog_json, f, indent=2)
            f.write('\n')

        print(f"Processed Catalog: {catalog_path}")

        # Build the hierarchical Merkle node
        catalog_node = {
            'node_id': catalog_json.get('id', str(catalog_path)),
            'type': 'Catalog',
            'merkle:object_hash': own_object_hash,
            'merkle:root': merkle_root,
            'children': children
        }

        return catalog_node

    except Exception as e:
        print(f"Error processing Catalog {catalog_path}: {e}")
        return {}


def is_item_directory(directory: Path) -> bool:
    """
    Determines if a given directory contains a single Item JSON file.

    Parameters:
    - directory (Path): The directory to check.

    Returns:
    - bool: True if the directory contains exactly one Item JSON file, False otherwise.
    """
    item_files = list(directory.glob('*.json'))
    if len(item_files) == 1:
        try:
            with item_files[0].open('r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('type') == 'Feature'
        except:
            return False
    return False
