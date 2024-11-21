# stac_merkle_cli/verify_merkle_tree_json.py

import hashlib
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class MerkleTreeVerifier:
    """
    A class to verify the integrity of a Merkle tree JSON structure.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initializes the MerkleTreeVerifier with an optional logger.

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

    def compute_merkle_root(self, hashes: List[str], hash_method: Dict[str, Any]) -> str:
        """
        Computes the Merkle root from a list of hashes based on the provided hash method.

        Parameters:
        - hashes (List[str]): A list of hexadecimal hash strings.
        - hash_method (Dict[str, Any]): The hash method details (function, ordering).

        Returns:
        - str: The computed Merkle root as a hexadecimal string.
        """
        self.logger.debug(f"Starting compute_merkle_root with {len(hashes)} hashes.")
        if not hashes:
            self.logger.warning("Empty hash list provided. Returning empty string.")
            return ''

        # Determine ordering
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
            self.logger.error(f"Unsupported ordering method: {ordering}")
            raise ValueError(f"Unsupported ordering method: {ordering}")

        # Get the hash function
        hash_function_name = hash_method.get('function', 'sha256').replace('-', '').lower()
        self.logger.debug(f"Using hash function: {hash_function_name}")
        hash_func = getattr(hashlib, hash_function_name, None)
        if not hash_func:
            self.logger.error(f"Unsupported hash function: {hash_function_name}")
            raise ValueError(f"Unsupported hash function: {hash_function_name}")

        current_level = hashes.copy()
        self.logger.debug(f"Initial current_level: {current_level}")

        while len(current_level) > 1:
            self.logger.debug(f"Processing level with {len(current_level)} hashes.")
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = left  # Duplicate the last hash if odd number
                    self.logger.debug(f"Odd number of hashes. Duplicating last hash: {left}")

                self.logger.debug(f"Combining hashes: {left} + {right}")
                try:
                    combined = bytes.fromhex(left) + bytes.fromhex(right)
                except ValueError as e:
                    self.logger.error(f"Error converting hashes to bytes: {e}")
                    raise ValueError(f"Error converting hashes to bytes: {e}")

                new_hash = hash_func(combined).hexdigest()
                self.logger.debug(f"New hash: {new_hash}")
                next_level.append(new_hash)
            current_level = next_level
            self.logger.debug(f"Next level hashes: {current_level}")

        self.logger.info(f"Computed Merkle root: {current_level[0]}")
        return current_level[0]

    def calculate_merkle_root_with_discrepancies(self, node: Dict[str, Any], discrepancies: List[str]) -> str:
        """
        Recursively calculates the Merkle root and records discrepancies.

        Parameters:
        - node (Dict[str, Any]): The Merkle tree node to process.
        - discrepancies (List[str]): A list to record discrepancies.

        Returns:
        - str: The recalculated Merkle root.
        """
        node_id = node.get('node_id', 'Unknown')
        node_type = node.get('type', 'Unknown')
        self.logger.debug(f"Processing node: {node_type} '{node_id}'")

        hash_method = node.get('merkle:hash_method', {
            'function': 'sha256',
            'fields': ['*'],
            'ordering': 'ascending',
            'description': 'Default hash method.'
        })
        self.logger.debug(f"Hash method for node '{node_id}': {hash_method}")

        # If the node is an Item, its merkle:root is its own merkle:object_hash
        if node['type'] == 'Item':
            self.logger.debug(f"Node '{node_id}' is an Item. Returning its merkle:object_hash.")
            return node['merkle:object_hash']

        # For Catalogs and Collections, collect child hashes
        child_hashes = []
        for child in node.get('children', []):
            child_root = self.calculate_merkle_root_with_discrepancies(child, discrepancies)
            if child_root:
                child_hashes.append(child_root)
                self.logger.debug(f"Added child hash from node '{child.get('node_id', 'Unknown')}': {child_root}")

        # Include own merkle:object_hash
        own_hash = node.get('merkle:object_hash')
        if own_hash:
            child_hashes.append(own_hash)
            self.logger.debug(f"Added own merkle:object_hash for node '{node_id}': {own_hash}")

        # Compute the Merkle root from child hashes
        self.logger.debug(f"Child hashes for node '{node_id}': {child_hashes}")
        calculated_root = self.compute_merkle_root(child_hashes, hash_method)
        self.logger.debug(f"Calculated root for node '{node_id}': {calculated_root}")

        # Compare with the node's merkle:root
        original_root = node.get('merkle:root')
        self.logger.debug(f"Original merkle:root for node '{node_id}': {original_root}")

        if original_root != calculated_root:
            discrepancy_message = f"{node_type} '{node_id}' has mismatched merkle:root."
            discrepancies.append(discrepancy_message)
            self.logger.warning(discrepancy_message)

        return calculated_root

    def verify_merkle_tree(self, merkle_tree_path: Path) -> bool:
        """
        Verifies that the merkle:root in the Merkle tree JSON matches the recalculated root.

        Parameters:
        - merkle_tree_path (Path): Path to the Merkle tree JSON file.

        Returns:
        - bool: True if the merkle:root matches, False otherwise.
        """
        self.logger.info(f"Verifying Merkle tree at path: {merkle_tree_path}")
        try:
            with merkle_tree_path.open('r', encoding='utf-8') as f:
                merkle_tree = json.load(f)
            self.logger.debug("Loaded Merkle tree JSON successfully.")

            discrepancies = []
            calculated_root = self.calculate_merkle_root_with_discrepancies(merkle_tree, discrepancies)
            self.logger.debug(f"Calculated Merkle root: {calculated_root}")

            original_root = merkle_tree.get('merkle:root')
            self.logger.debug(f"Original merkle:root from JSON: {original_root}")

            if not original_root:
                self.logger.error("Error: 'merkle:root' not found in the JSON.")
                return False

            if calculated_root == original_root:
                self.logger.info(f"Verification Successful: The merkle:root matches ({calculated_root}).")
                return True
            else:
                self.logger.error("Verification Failed:")
                self.logger.error(f" - Expected merkle:root: {original_root}")
                self.logger.error(f" - Calculated merkle:root: {calculated_root}")
                if discrepancies:
                    self.logger.error("Discrepancies found in the following nodes:")
                    for discrepancy in discrepancies:
                        self.logger.error(f" - {discrepancy}")
                return False
        except Exception as e:
            self.logger.error(f"Error verifiying Merkle Tree: {e}")
            return {}