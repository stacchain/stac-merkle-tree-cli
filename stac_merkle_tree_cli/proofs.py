import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Constants
PROOF_REL_TYPE = "merkle-proof"
PROOF_MEDIA_TYPE = "application/json"


def get_sha256_hash(data: str) -> str:
    """Helper to compute SHA256 hash of a hex string."""
    return hashlib.sha256(bytes.fromhex(data)).hexdigest()


def compute_binary_layer_proof(
    hashes: List[str], target_index: int, hash_func_name: str = "sha256"
) -> List[Dict[str, str]]:
    """
    Generates the inclusion proof for a single level of the hierarchy (e.g., items inside one collection).
    Simulates the pairwise binary tree construction to find siblings.
    """
    proof_path = []
    current_hashes = hashes.copy()
    current_index = target_index

    # We only support SHA256 for now as per the rest of the CLI
    # In a full generic version, we'd dynamically load hash_func_name

    while len(current_hashes) > 1:
        next_level_hashes = []

        # Determine sibling for the current node
        is_right_child = (current_index % 2) != 0
        sibling_index = current_index - 1 if is_right_child else current_index + 1

        # Handle odd number of nodes (duplication of last node)
        if sibling_index >= len(current_hashes):
            sibling_index = current_index  # Last node pairs with itself

        sibling_hash = current_hashes[sibling_index]

        # Add to proof
        proof_path.append(
            {"position": "left" if is_right_child else "right", "hash": sibling_hash}
        )

        # Compute next level of the tree
        for i in range(0, len(current_hashes), 2):
            left = current_hashes[i]
            right = current_hashes[i + 1] if i + 1 < len(current_hashes) else left

            combined = bytes.fromhex(left) + bytes.fromhex(right)
            next_hash = hashlib.sha256(combined).hexdigest()
            next_level_hashes.append(next_hash)

        # Move up to next layer
        current_hashes = next_level_hashes
        current_index = current_index // 2

    return proof_path


def find_node_path(
    tree: Dict[str, Any],
    target_id: str,
    current_path: Optional[List[Dict[str, Any]]] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    DFS search to find a node in the merkle_tree.json and return the chain of parent nodes leading to it.
    """
    if current_path is None:
        current_path = []

    # Check if this is the node
    if tree.get("node_id") == target_id:
        return current_path + [tree]

    # Recurse children
    for child in tree.get("children", []):
        result = find_node_path(child, target_id, current_path + [tree])
        if result:
            return result

    return None


def generate_full_proof(
    tree_root: Dict[str, Any], item_node_id: str
) -> Optional[Dict[str, Any]]:
    """
    Constructs the full Merkle Inclusion Proof from an Item to the Global Root.
    Combines proofs from multiple hierarchical levels (Item->Collection, Collection->Catalog, etc).
    """
    # 1. Find the path of nodes from Root -> Item
    # e.g. [CatalogNode, CollectionNode, ItemNode]
    node_chain = find_node_path(tree_root, item_node_id)

    if not node_chain:
        print(f"Warning: Item {item_node_id} not found in Merkle tree structure.")
        return None

    item_node = node_chain[-1]
    full_proof_path = []

    # 2. Iterate up the chain (from Item up to Root)
    # We process pair: (Parent, Child)
    for i in range(len(node_chain) - 1, 0, -1):
        child = node_chain[i]
        parent = node_chain[i - 1]

        # Gather all hashes in the parent's immediate children list
        # "Ripple Effect" logic: Items give object_hash, Collections give root
        sibling_hashes = []
        target_index = -1

        for idx, sibling in enumerate(parent.get("children", [])):
            # Determine the hash used for this sibling
            if sibling["type"] == "Item":
                h = sibling["merkle:object_hash"]
            else:
                h = sibling["merkle:root"]

            sibling_hashes.append(h)

            if sibling["node_id"] == child["node_id"]:
                target_index = idx

        if target_index == -1:
            raise ValueError(
                f"Integrity Error: Child {child['node_id']} not found in parent {parent['node_id']}"
            )

        # Generate the binary tree proof for this specific layer
        layer_proof = compute_binary_layer_proof(sibling_hashes, target_index)

        # Append to the total proof path
        full_proof_path.extend(layer_proof)

    # 3. Construct Final Proof Object
    return {
        "target_hash": item_node["merkle:object_hash"],
        "root": tree_root["merkle:root"],
        "path": full_proof_path,
    }


def update_item_with_link(item_path: Path, proof_filename: str, base_url: str):
    """
    Injects the 'merkle-proof' link into the STAC Item file.
    """
    try:
        with item_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Construct the URL
        proof_url = f"{base_url.rstrip('/')}/{proof_filename}"

        # Remove existing proof link if present
        data["links"] = [
            link for link in data.get("links", []) if link["rel"] != PROOF_REL_TYPE
        ]

        # Add new link
        data["links"].append(
            {"rel": PROOF_REL_TYPE, "href": proof_url, "type": PROOF_MEDIA_TYPE}
        )

        with item_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    except Exception as e:
        print(f"Error updating item {item_path}: {e}")


def generate_item_proofs(merkle_tree_path: Path, output_dir: str, base_url: str):
    """
    Main entry point used by the CLI.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Load the Tree
    with merkle_tree_path.open("r") as f:
        tree_root = json.load(f)

    catalog_dir = merkle_tree_path.parent

    print("Scanning for Items and generating proofs...")

    # 2. Walk the directory to find Items, then generate proofs for them
    count = 0
    for item_file in catalog_dir.rglob("*.json"):
        # Quick check if it's likely an item (has 'Feature')
        # We assume files are valid JSON for speed
        if item_file.name in ["catalog.json", "collection.json"]:
            continue

        try:
            with item_file.open("r") as f:
                # Read just enough to check type
                start_content = f.read(200)
                if (
                    '"Feature"' not in start_content
                    and "'Feature'" not in start_content
                ):
                    continue
                # If it looks like a feature, load fully to get ID
                f.seek(0)
                item_data = json.load(f)

            if item_data.get("type") != "Feature":
                continue

            item_id = item_data["id"]

            # 3. Generate Proof
            proof_obj = generate_full_proof(tree_root, item_id)

            if proof_obj:
                # 4. Save Proof File
                proof_filename = f"{item_id}.proof.json"
                proof_file_path = output_path / proof_filename

                with proof_file_path.open("w") as f:
                    json.dump(proof_obj, f, indent=2)

                # 5. Link Item to Proof
                update_item_with_link(item_file, proof_filename, base_url)
                count += 1

        except Exception as e:
            print(f"Skipping file {item_file}: {e}")

    print(f"Done. Generated {count} proofs in '{output_dir}'.")
