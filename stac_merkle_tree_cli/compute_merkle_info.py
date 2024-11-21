# stac_merkle_cli/compute_merkle_info.py

import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union


class MerkleTreeProcessor:
    """
    A class to compute Merkle hashes for STAC Catalogs, Collections, and Items.
    It provides functionalities to process items and collections, compute object hashes,
    and construct the Merkle root for the entire catalog structure.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initializes the MerkleTreeProcessor with an optional logger.

        Parameters:
        - logger (logging.Logger, optional): A logger instance for logging messages.
                                              If not provided, a default logger is configured.
        """
        if logger is None:
            # Configure default logger
            self.logger = logging.getLogger(self.__class__.__name__)
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            if not self.logger.handlers:
                self.logger.addHandler(handler)
        else:
            self.logger = logger

    def remove_merkle_fields(self, data: Any) -> Any:
        """
        Recursively removes Merkle-specific fields from the data.

        Parameters:
        - data (Any): The JSON data (dict or list) from which to remove Merkle fields.

        Returns:
        - Any: The data with Merkle fields excluded.
        """
        if isinstance(data, dict):
            return {
                k: self.remove_merkle_fields(v)
                for k, v in data.items()
                if k not in {"merkle:object_hash", "merkle:hash_method", "merkle:root"}
            }
        elif isinstance(data, list):
            return [self.remove_merkle_fields(item) for item in data]
        else:
            return data

    def compute_merkle_object_hash(self, stac_object: Dict[str, Any], hash_method: Dict[str, Any]) -> str:
        """
        Computes the merkle:object_hash for a STAC object.

        Parameters:
        - stac_object (Dict[str, Any]): The STAC Catalog, Collection, or Item JSON object.
        - hash_method (Dict[str, Any]): The hash method details from merkle:hash_method.

        Returns:
        - str: The computed object hash as a hexadecimal string.
        """
        self.logger.debug("Computing merkle:object_hash for STAC object.")
        fields = hash_method.get('fields', ['*'])
        self.logger.debug(f"Hash fields: {fields}")

        if fields == ['*'] or fields == ['all']:
            data_to_hash = self.remove_merkle_fields(stac_object)
            self.logger.debug("Using all fields for hashing after removing Merkle fields.")
        else:
            selected_data = {
                field: stac_object.get(field)
                for field in fields
                if field in stac_object
            }
            data_to_hash = self.remove_merkle_fields(selected_data)
            self.logger.debug(f"Using specific fields for hashing: {list(selected_data.keys())}")

        # Serialize the data to a compact JSON string with sorted keys
        json_str = json.dumps(data_to_hash, sort_keys=True, separators=(',', ':'))
        self.logger.debug(f"Serialized JSON for hashing: {json_str}")

        # Get the hash function
        hash_function_name = hash_method.get('function', 'sha256').replace('-', '').lower()
        self.logger.debug(f"Selected hash function: {hash_function_name}")
        hash_func = getattr(hashlib, hash_function_name, None)
        if not hash_func:
            self.logger.error(f"Unsupported hash function: {hash_function_name}")
            raise ValueError(f"Unsupported hash function: {hash_function_name}")

        # Compute the hash
        object_hash = hash_func(json_str.encode('utf-8')).hexdigest()
        self.logger.debug(f"Computed merkle:object_hash: {object_hash}")

        return object_hash

    def compute_merkle_root(self, hashes: List[str], hash_method: Dict[str, Any]) -> str:
        """
        Computes the Merkle root from a list of hashes based on the provided hash method.

        Parameters:
        - hashes (List[str]): A list of hexadecimal hash strings.
        - hash_method (Dict[str, Any]): The hash method details (function, ordering).

        Returns:
        - str: The computed Merkle root as a hexadecimal string.
        """
        self.logger.debug(f"Computing Merkle root from {len(hashes)} hashes.")
        if not hashes:
            self.logger.warning("Empty hash list provided. Returning empty string.")
            return ''

        # Enforce ordering
        ordering = hash_method.get('ordering', 'ascending')
        self.logger.debug(f"Hash ordering method: {ordering}")
        if ordering == 'ascending':
            hashes.sort()
            self.logger.debug("Hashes sorted in ascending order.")
        elif ordering == 'descending':
            hashes.sort(reverse=True)
            self.logger.debug("Hashes sorted in descending order.")
        elif ordering == 'unsorted':
            self.logger.debug("Hashes remain unsorted.")
            pass  # Keep the original order
        else:
            self.logger.error(f"Unsupported ordering: {ordering}")
            raise ValueError(f"Unsupported ordering: {ordering}")

        # Get the hash function
        hash_function_name = hash_method.get('function', 'sha256').replace('-', '').lower()
        self.logger.debug(f"Selected hash function: {hash_function_name}")
        hash_func = getattr(hashlib, hash_function_name, None)
        if not hash_func:
            self.logger.error(f"Unsupported hash function: {hash_function_name}")
            raise ValueError(f"Unsupported hash function: {hash_function_name}")

        current_level = hashes.copy()
        self.logger.debug(f"Initial hashes for Merkle root computation: {current_level}")

        while len(current_level) > 1:
            next_level = []
            self.logger.debug(f"Processing level with {len(current_level)} hashes.")
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = left  # Duplicate the last hash if odd number
                    self.logger.debug(f"Odd number of hashes. Duplicating last hash: {left}")

                self.logger.debug(f"Combining '{left}' + '{right}'")
                try:
                    combined = bytes.fromhex(left) + bytes.fromhex(right)
                except ValueError as e:
                    self.logger.error(f"Error converting hashes to bytes: {e}")
                    raise ValueError(f"Error converting hashes to bytes: {e}")

                new_hash = hash_func(combined).hexdigest()
                self.logger.debug(f"Combined hash: {new_hash}")
                next_level.append(new_hash)
            current_level = next_level
            self.logger.debug(f"Next level hashes: {current_level}")

        final_root = current_level[0]
        self.logger.info(f"Final Merkle root computed: {final_root}")
        return final_root

    def process_item(self, item_path: Path, hash_method: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a STAC Item to compute and return its object hash.

        Parameters:
        - item_path (Path): Path to the Item JSON file.
        - hash_method (Dict[str, Any]): The hash method to use.

        Returns:
        - Dict[str, Any]: A dictionary containing 'node_id', 'type', and 'merkle:object_hash'.
        """
        self.logger.debug(f"Processing Item: {item_path}")
        try:
            with item_path.open('r', encoding='utf-8') as f:
                item_json = json.load(f)

            if item_json.get('type') != 'Feature':
                self.logger.warning(f"Skipping non-Item JSON: {item_path}")
                return {}

            # Compute merkle:object_hash
            object_hash = self.compute_merkle_object_hash(item_json, hash_method)

            # Add merkle:object_hash to 'properties'
            properties = item_json.setdefault('properties', {})
            properties['merkle:object_hash'] = object_hash
            self.logger.debug(f"Added merkle:object_hash to Item '{item_json.get('id', item_path.stem)}'.")

            # Ensure the Merkle extension is listed
            item_json.setdefault('stac_extensions', [])
            extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
            if extension_url not in item_json['stac_extensions']:
                item_json['stac_extensions'].append(extension_url)
                item_json['stac_extensions'].sort()  # Sort for consistent ordering
                self.logger.debug(f"Added Merkle extension to Item '{item_json.get('id', item_path.stem)}'.")

            # Save the updated Item JSON
            with item_path.open('w', encoding='utf-8') as f:
                json.dump(item_json, f, indent=2)
                f.write('\n')
            self.logger.info(f"Processed Item: {item_path}")

            # Return the structured Item node
            return {
                'node_id': item_json.get('id', item_path.stem),
                'type': 'Item',
                'merkle:object_hash': object_hash
            }

        except Exception as e:
            self.logger.error(f"Error processing Item {item_path}: {e}")
            return {}

    def process_collection(self, collection_path: Path, parent_hash_method: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a STAC Collection to compute its merkle:root and builds a hierarchical Merkle node.

        Parameters:
        - collection_path (Path): Path to the Collection JSON file.
        - parent_hash_method (Dict[str, Any]): The hash method inherited from the parent.

        Returns:
        - Dict[str, Any]: The structured Merkle tree node for the collection.
        """
        self.logger.debug(f"Processing Collection: {collection_path}")
        try:
            with collection_path.open('r', encoding='utf-8') as f:
                collection_json = json.load(f)

            if collection_json.get('type') != 'Collection':
                self.logger.warning(f"Skipping non-Collection JSON: {collection_path}")
                return {}

            # Determine the hash_method to use
            hash_method = collection_json.get('merkle:hash_method', parent_hash_method)
            if not hash_method:
                self.logger.error(f"Hash method not specified for {collection_path}")
                raise ValueError(f"Hash method not specified for {collection_path}")

            children = []

            collection_dir = collection_path.parent

            # Process items directly in the collection directory
            for item_file in collection_dir.glob('*.json'):
                if item_file == collection_path:
                    continue
                item_node = self.process_item(item_file, hash_method)
                if item_node:
                    children.append(item_node)

            # Recursively process subdirectories
            for subdirectory in collection_dir.iterdir():
                if subdirectory.is_dir():
                    sub_collection_json = subdirectory / 'collection.json'
                    sub_catalog_json = subdirectory / 'catalog.json'

                    if sub_collection_json.exists():
                        # Process sub-collection
                        sub_collection_node = self.process_collection(sub_collection_json, hash_method)
                        if sub_collection_node:
                            children.append(sub_collection_node)
                    elif sub_catalog_json.exists():
                        # Process sub-catalog
                        sub_catalog_node = self.process_catalog(sub_catalog_json, hash_method)
                        if sub_catalog_node:
                            children.append(sub_catalog_node)
                    elif is_item_directory(subdirectory):
                        # Process item in its own directory
                        item_files = list(subdirectory.glob('*.json'))
                        if item_files:
                            item_file = item_files[0]
                            item_node = self.process_item(item_file, hash_method)
                            if item_node:
                                children.append(item_node)
                    else:
                        # Handle other cases or ignore
                        self.logger.warning(f"Unrecognized structure in {subdirectory}")

            # Compute own merkle:object_hash
            own_object_hash = self.compute_merkle_object_hash(collection_json, hash_method)
            collection_json['merkle:object_hash'] = own_object_hash
            self.logger.debug(f"Computed merkle:object_hash for Collection '{collection_json.get('id', collection_path)}': {own_object_hash}")

            # Collect all hashes: own_object_hash + child hashes
            child_hashes = []
            for child in children:
                if child['type'] in {'Collection', 'Catalog'}:
                    child_hash = child.get('merkle:root')
                    if child_hash:
                        child_hashes.append(child_hash)
                        self.logger.debug(f"Added child merkle:root from '{child['node_id']}': {child_hash}")
                else:
                    child_hash = child.get('merkle:object_hash')
                    if child_hash:
                        child_hashes.append(child_hash)
                        self.logger.debug(f"Added child merkle:object_hash from '{child['node_id']}': {child_hash}")

            # Exclude None values
            child_hashes = [h for h in child_hashes if h]

            # Include own_object_hash
            all_hashes = child_hashes + [own_object_hash]
            self.logger.debug(f"All hashes for Merkle root computation in Collection '{collection_json.get('id', collection_path)}': {all_hashes}")

            # Compute merkle:root
            merkle_root = self.compute_merkle_root(all_hashes, hash_method)
            collection_json['merkle:root'] = merkle_root
            self.logger.debug(f"Computed merkle:root for Collection '{collection_json.get('id', collection_path)}': {merkle_root}")

            collection_json['merkle:hash_method'] = hash_method

            # Ensure the Merkle extension is listed and sorted
            extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
            collection_json.setdefault('stac_extensions', [])
            if extension_url not in collection_json['stac_extensions']:
                collection_json['stac_extensions'].append(extension_url)
                self.logger.debug(f"Added Merkle extension to Collection '{collection_json.get('id', collection_path)}'.")
            collection_json['stac_extensions'].sort()

            # Save the updated Collection JSON
            with collection_path.open('w', encoding='utf-8') as f:
                json.dump(collection_json, f, indent=2)
                f.write('\n')
            self.logger.info(f"Processed Collection: {collection_path}")

            # Build the hierarchical Merkle node
            collection_node = {
                'node_id': collection_json.get('id', str(collection_path)),
                'type': 'Collection',
                'merkle:object_hash': own_object_hash,
                'merkle:root': merkle_root,
                'children': children
            }

            # Sort children by node_id for consistency
            collection_node['children'] = sorted(children, key=lambda x: x['node_id'])


            return collection_node
        
        except Exception as e:
            self.logger.error(f"Error processing Collection {collection_path}: {e}")
            return {}

    def process_catalog(self, catalog_path: Path, parent_hash_method: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processes the root STAC Catalog to compute its merkle:root and builds a hierarchical Merkle node.

        Parameters:
        - catalog_path (Path): Path to the Catalog JSON file.
        - parent_hash_method (Dict[str, Any], optional): The hash method inherited from the parent.

        Returns:
        - Dict[str, Any]: The structured Merkle tree node for the catalog.
        """
        self.logger.debug(f"Processing Catalog: {catalog_path}")
        try:
            with catalog_path.open('r', encoding='utf-8') as f:
                catalog_json = json.load(f)

            if catalog_json.get('type') != 'Catalog':
                self.logger.warning(f"Skipping non-Catalog JSON: {catalog_path}")
                return {}

            # Determine the hash_method to use
            hash_method = catalog_json.get('merkle:hash_method', parent_hash_method)
            if not hash_method:
                self.logger.error(f"Hash method not specified for {catalog_path}")
                raise ValueError(f"Hash method not specified for {catalog_path}")

            children = []

            catalog_dir = catalog_path.parent

            # Process collections in the 'collections' directory
            collections_dir = catalog_dir / 'collections'
            if not collections_dir.exists():
                self.logger.warning(f"No 'collections' directory found in {catalog_dir}")
                # It's possible for a catalog to have no collections
            else:
                for collection_dir in collections_dir.iterdir():
                    if collection_dir.is_dir():
                        collection_json_path = collection_dir / 'collection.json'
                        if collection_json_path.exists():
                            collection_node = self.process_collection(collection_json_path, hash_method)
                            if collection_node:
                                children.append(collection_node)
                        else:
                            self.logger.warning(f"'collection.json' not found in {collection_dir}")

            # Compute own merkle:object_hash
            own_object_hash = self.compute_merkle_object_hash(catalog_json, hash_method)
            catalog_json['merkle:object_hash'] = own_object_hash
            self.logger.debug(f"Computed merkle:object_hash for Catalog '{catalog_json.get('id', catalog_path)}': {own_object_hash}")

            # Collect all hashes: own_object_hash + child hashes
            child_hashes = []
            for child in children:
                if child['type'] in {'Collection', 'Catalog'}:
                    child_hash = child.get('merkle:root')
                    if child_hash:
                        child_hashes.append(child_hash)
                        self.logger.debug(f"Added child merkle:root from '{child['node_id']}': {child_hash}")
                else:
                    child_hash = child.get('merkle:object_hash')
                    if child_hash:
                        child_hashes.append(child_hash)
                        self.logger.debug(f"Added child merkle:object_hash from '{child['node_id']}': {child_hash}")

            # Exclude None values
            child_hashes = [h for h in child_hashes if h]

            # Include own_object_hash
            all_hashes = child_hashes + [own_object_hash]
            self.logger.debug(f"All hashes for Merkle root computation in Catalog '{catalog_json.get('id', catalog_path)}': {all_hashes}")

            # Compute merkle:root
            merkle_root = self.compute_merkle_root(all_hashes, hash_method)
            catalog_json['merkle:root'] = merkle_root
            self.logger.debug(f"Computed merkle:root for Catalog '{catalog_json.get('id', catalog_path)}': {merkle_root}")

            catalog_json['merkle:hash_method'] = hash_method

            # Ensure the Merkle extension is listed and sorted
            extension_url = 'https://stacchain.github.io/merkle-tree/v1.0.0/schema.json'
            catalog_json.setdefault('stac_extensions', [])
            if extension_url not in catalog_json['stac_extensions']:
                catalog_json['stac_extensions'].append(extension_url)
                self.logger.debug(f"Added Merkle extension to Catalog '{catalog_json.get('id', catalog_path)}'.")
            catalog_json['stac_extensions'].sort()

            # Save the updated Catalog JSON
            with catalog_path.open('w', encoding='utf-8') as f:
                json.dump(catalog_json, f, indent=2)
                f.write('\n')
            self.logger.info(f"Processed Catalog: {catalog_path}")

            # Build the hierarchical Merkle node
            catalog_node = {
                'node_id': catalog_json.get('id', str(catalog_path)),
                'type': 'Catalog',
                'merkle:object_hash': own_object_hash,
                'merkle:root': merkle_root,
                'children': children
            }

            # Sort children by node_id for consistency
            catalog_node['children'] = sorted(catalog_node['children'], key=lambda x: x['node_id'])


            return catalog_node

        except Exception as e:
            self.logger.error(f"Error processing Catalog {catalog_path}: {e}")
            return {}


def is_item_directory(directory: Path) -> bool:
    """
    Determines if a given directory contains a single Item JSON file.

    Parameters:
    - directory (Path): The directory to check.

    Returns:
    - bool: True if the directory contains exactly one Item JSON file, False otherwise.
    """
    try:
        item_files = list(directory.glob('*.json'))
        if len(item_files) != 1:
            return False
        with item_files[0].open('r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('type') == 'Feature'
    except Exception:
        return False
