import hashlib
import logging
import json
from pathlib import Path
from typing import List, Dict, Any

def compute_merkle_root(hashes: List[str], hash_method: Dict[str, Any]) -> str:
    """
    Computes the Merkle root from a list of hashes based on the provided hash method.
    """
    if not hashes:
        return ''

    # Determine ordering
    ordering = hash_method.get('ordering', 'ascending')
    if ordering == 'ascending':
        hashes.sort()
    elif ordering == 'descending':
        hashes.sort(reverse=True)
    elif ordering == 'unsorted':
        pass  # Keep the original order
    else:
        raise ValueError(f"Unsupported ordering method: {ordering}")

    # Get the hash function
    hash_function_name = hash_method.get('function', 'sha256').replace('-', '').lower()
    hash_func = getattr(hashlib, hash_function_name, None)
    if not hash_func:
        raise ValueError(f"Unsupported hash function: {hash_function_name}")

    current_level = hashes.copy()

    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            if i + 1 < len(current_level):
                right = current_level[i + 1]
            else:
                right = left  # Duplicate the last hash if odd number

            combined = bytes.fromhex(left) + bytes.fromhex(right)
            new_hash = hash_func(combined).hexdigest()
            next_level.append(new_hash)
        current_level = next_level

    return current_level[0]

def verify_merkle_tree(merkle_tree_path: Path) -> bool:
    """
    Verifies that the merkle:root in the Merkle tree JSON matches the recalculated root.
    """
    try:
        with merkle_tree_path.open('r', encoding='utf-8') as f:
            merkle_tree = json.load(f)

        discrepancies = []
        calculated_root = calculate_merkle_root_with_discrepancies(merkle_tree, discrepancies)

        original_root = merkle_tree.get('merkle:root')

        if not original_root:
            print("Error: 'merkle:root' not found in the JSON.")
            return False

        if calculated_root == original_root:
            print(f"Verification Successful: The merkle:root matches ({calculated_root}).")
            return True
        else:
            print(f"Verification Failed:")
            print(f" - Expected merkle:root: {original_root}")
            print(f" - Calculated merkle:root: {calculated_root}")
            if discrepancies:
                print("Discrepancies found in the following nodes:")
                for discrepancy in discrepancies:
                    print(f" - {discrepancy}")
            return False

    except Exception as e:
        print(f"Error during verification: {e}")
        return False

def calculate_merkle_root_with_discrepancies(node: Dict[str, Any], discrepancies: List[str]) -> str:
    """
    Recursively calculates the Merkle root and records discrepancies.
    """
    hash_method = node.get('merkle:hash_method', {
        'function': 'sha256',
        'fields': ['*'],
        'ordering': 'ascending',
        'description': 'Default hash method.'
    })

    # If the node is an Item, its merkle:root is its own merkle:object_hash
    if node['type'] == 'Item':
        return node['merkle:object_hash']

    # For Catalogs and Collections, collect child hashes
    child_hashes = []
    for child in node.get('children', []):
        child_root = calculate_merkle_root_with_discrepancies(child, discrepancies)
        if child_root:
            child_hashes.append(child_root)

    # Include own merkle:object_hash
    own_hash = node.get('merkle:object_hash')
    if own_hash:
        child_hashes.append(own_hash)

    # Compute the Merkle root from child hashes
    calculated_root = compute_merkle_root(child_hashes, hash_method)

    # Compare with the node's merkle:root
    original_root = node.get('merkle:root')
    if original_root != calculated_root:
        discrepancies.append(f"{node['type']} '{node['node_id']}' has mismatched merkle:root.")

    return calculated_root