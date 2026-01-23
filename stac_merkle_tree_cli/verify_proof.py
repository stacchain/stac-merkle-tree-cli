# stac_merkle_tree_cli/verify_proof.py

import hashlib
import json
from typing import Any, Dict


def compute_hash(data: Any) -> str:
    """
    Compute SHA256 hash of data.

    Args:
        data: Dictionary or string to hash

    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, dict):
        # Canonical JSON dump to match CLI logic
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    else:
        # Hashing raw bytes/strings
        encoded = data if isinstance(data, bytes) else data.encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_item(item_json: Dict[str, Any], proof_json: Dict[str, Any]) -> bool:
    """
    Verify a STAC Item against a Merkle Proof.

    Args:
        item_json: The STAC Item JSON object
        proof_json: The Merkle proof JSON object

    Returns:
        True if verification succeeds, False otherwise
    """
    # 1. Clean the Item: Remove fields that change (merkle fields, links)
    #    Note: This must match the '--ignore-links' setting used during generation.
    clean_item = {
        k: v
        for k, v in item_json.items()
        if k
        not in [
            "merkle:object_hash",
            "merkle:root",
            "merkle:hash_method",
            "links",
        ]
    }

    # 2. Calculate the Item's Hash
    current_hash = compute_hash(clean_item)

    # 3. Check if Identity matches
    if current_hash != proof_json["target_hash"]:
        print("❌ Identity Mismatch: Item data has been altered.")
        return False

    # 4. Traverse the Path (The Merkle Proof)
    for step in proof_json["path"]:
        sibling_hash = step["hash"]
        position = step["position"]

        # Combine hashes based on position
        if position == "left":
            combined = bytes.fromhex(sibling_hash) + bytes.fromhex(current_hash)
        else:
            combined = bytes.fromhex(current_hash) + bytes.fromhex(sibling_hash)

        current_hash = hashlib.sha256(combined).hexdigest()

    # 5. Compare against the Trusted Root
    if current_hash == proof_json["root"]:
        print("✅ SUCCESS: Item is verified against the Root.")
        return True
    else:
        print("❌ FAILURE: Cryptographic proof failed.")
        print(f"Calculated Root: {current_hash}")
        print(f"Expected Root:   {proof_json['root']}")
        return False
