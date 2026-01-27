# stac_merkle_cli/verify.py

import json
from pathlib import Path

from .compute_merkle_info import compute_merkle_root

# Default method if not found (matches our CLI defaults)
DEFAULT_HASH_METHOD = {"function": "sha256", "ordering": "ascending"}


def verify_node(node: dict, hash_method: dict = DEFAULT_HASH_METHOD) -> bool:
    """
    Recursively verifies a Merkle Tree Node.
    Returns True if the calculated root matches the stored root.
    """
    node_id = node.get("node_id", "unknown")
    node_type = node.get("type")

    # 1. Base Case: Items (Leaf Nodes)
    # Items have no children, so they verify themselves implicitly by existing.
    # (Deep integrity checks happen in 'compute', here we verify tree structure).
    if node_type == "Item":
        return True

    # 2. Recursive Step: Verify all children first
    children = node.get("children", [])
    for child in children:
        if not verify_node(child, hash_method):
            return False

    # 3. Aggregation Step (The Ripple Effect)
    child_hashes = []
    for child in children:
        if child["type"] == "Item":
            # Leaves contribute their Identity Hash
            child_hashes.append(child["merkle:object_hash"])
        else:
            # Containers contribute their Integrity Root
            child_hashes.append(child["merkle:root"])

    # 4. Include Self
    # The spec says we include the object's own hash in the tree
    if "merkle:object_hash" in node:
        child_hashes.append(node["merkle:object_hash"])

    # 5. Re-Calculate Root
    calculated_root = compute_merkle_root(child_hashes, hash_method)
    stored_root = node.get("merkle:root")

    if calculated_root != stored_root:
        print(f"❌ Verification FAILED for {node_type} '{node_id}'")
        print(f"   Calculated: {calculated_root}")
        print(f"   Stored:     {stored_root}")
        return False

    print(f"✅ Verified {node_type}: {node_id}")
    return True


def verify_tree(catalog_path: str, merkle_tree_file: str = "merkle_tree.json") -> bool:
    """
    Main entry point for verification.
    """
    tree_path = Path(catalog_path) / merkle_tree_file

    if not tree_path.exists():
        print(f"Error: {merkle_tree_file} not found at {tree_path}")
        return False

    print(f"Loading tree from {tree_path}...")
    try:
        with open(tree_path, "r") as f:
            root_node = json.load(f)

        # In a real implementation, you might want to read the hash_method
        # from the catalog.json itself, but for now we use defaults.
        if verify_node(root_node):
            print("\n🎉 Merkle Tree Verification SUCCESS!")
            return True
        else:
            print("\n⛔ Merkle Tree Verification FAILED.")
            return False

    except Exception as e:
        print(f"Error reading tree: {e}")
        return False
