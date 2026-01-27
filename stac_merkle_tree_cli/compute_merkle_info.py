# stac_merkle_cli/compute_merkle_info.py

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List

# Constants for schema versions
EXTENSION_URL = "https://stacchain.github.io/merkle-tree/v1.1.1/schema.json"
FILE_INFO_URL = "https://stac-extensions.github.io/file/v2.1.0/schema.json"


def remove_merkle_fields(data: Any, ignore_links: bool = True) -> Any:
    """
    Recursively removes Merkle-specific fields and optionally 'links' to ensure safe hashing.
    """
    fields_to_remove = {"merkle:object_hash", "merkle:hash_method", "merkle:root"}
    if ignore_links:
        fields_to_remove.add("links")

    if isinstance(data, dict):
        return {
            k: remove_merkle_fields(v, ignore_links)
            for k, v in data.items()
            if k not in fields_to_remove
        }
    elif isinstance(data, list):
        return [remove_merkle_fields(item, ignore_links) for item in data]
    else:
        return data


def compute_merkle_object_hash(
    stac_object: Dict[str, Any], hash_method: Dict[str, Any], ignore_links: bool = True
) -> str:
    """
    Computes the merkle:object_hash for a STAC object.
    """
    fields = hash_method.get("fields", ["*"])

    if fields == ["*"] or fields == ["all"]:
        data_to_hash = remove_merkle_fields(stac_object, ignore_links)
    else:
        # If fields are explicit, we only grab those.
        # Note: If 'links' is in the explicit list, we DO NOT remove it,
        # assuming the user knows what they are doing.
        selected_data = {
            field: stac_object.get(field) for field in fields if field in stac_object
        }
        # We still remove merkle fields to prevent recursion issues
        data_to_hash = remove_merkle_fields(selected_data, ignore_links=False)

    json_str = json.dumps(data_to_hash, sort_keys=True, separators=(",", ":"))
    hash_function_name = hash_method.get("function", "sha256").replace("-", "").lower()
    hash_func = getattr(hashlib, hash_function_name, None)

    if not hash_func:
        raise ValueError(f"Unsupported hash function: {hash_function_name}")

    return hash_func(json_str.encode("utf-8")).hexdigest()


def compute_merkle_root(hashes: List[str], hash_method: Dict[str, Any]) -> str:
    """
    Computes the merkle:root by building a Merkle tree from a list of hashes.
    """
    if not hashes:
        return ""

    hash_function_name = hash_method.get("function", "sha256").replace("-", "").lower()
    hash_func = getattr(hashlib, hash_function_name, None)

    if not hash_func:
        raise ValueError(f"Unsupported hash function: {hash_function_name}")

    current_level = hashes.copy()

    # Sort if ordering is 'ascending' (Standardize this!)
    if hash_method.get("ordering") == "ascending":
        current_level.sort()

    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left

            # Simple concatenation: H(left + right)
            combined = bytes.fromhex(left) + bytes.fromhex(right)
            new_hash = hash_func(combined).hexdigest()
            next_level.append(new_hash)
        current_level = next_level

    return current_level[0]


def process_item(
    item_path: Path,
    hash_method: Dict[str, Any],
    ignore_links: bool = True,
) -> Dict[str, Any]:
    """
    Processes a STAC Item.
    Opportunistically checks for file:checksum to ensure the extension is listed.
    """
    try:
        with item_path.open("r", encoding="utf-8") as f:
            item_json = json.load(f)

        if item_json.get("type") != "Feature":
            return {}

        # --- Opportunistic Deep Integrity Logic ---
        # If ANY asset has a checksum, ensure the File Info extension is present
        has_checksums = False
        assets = item_json.get("assets", {})
        for asset in assets.values():
            if "file:checksum" in asset:
                has_checksums = True
                break

        if has_checksums:
            item_json.setdefault("stac_extensions", [])
            if FILE_INFO_URL not in item_json["stac_extensions"]:
                item_json["stac_extensions"].append(FILE_INFO_URL)

        # Compute object hash
        object_hash = compute_merkle_object_hash(item_json, hash_method, ignore_links)

        # Update JSON
        item_json.setdefault("properties", {})["merkle:object_hash"] = object_hash

        item_json.setdefault("stac_extensions", [])
        if EXTENSION_URL not in item_json["stac_extensions"]:
            item_json["stac_extensions"].append(EXTENSION_URL)
            item_json["stac_extensions"].sort()

        # Atomic write pattern: write to temp file, then move
        temp_path = item_path.with_suffix(".tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(item_json, f, indent=2)
                f.write("\n")
            temp_path.replace(item_path)
        except Exception:
            if temp_path.exists():
                os.remove(temp_path)
            raise

        print(f"Processed Item: {item_path.name}")

        return {
            "node_id": item_json.get("id", item_path.stem),
            "type": "Item",
            "merkle:object_hash": object_hash,
        }

    except Exception as e:
        print(f"Error processing Item {item_path}: {e}")
        return {}


def process_collection(
    collection_path: Path,
    parent_hash_method: Dict[str, Any],
    ignore_links: bool,
) -> Dict[str, Any]:
    """
    Processes a Collection.
    CRITICAL: Aggregates 'merkle:root' from child Collections, but 'merkle:object_hash' from child Items.
    """
    try:
        with collection_path.open("r", encoding="utf-8") as f:
            collection_json = json.load(f)

        hash_method = collection_json.get("merkle:hash_method", parent_hash_method)
        children_nodes = []
        collection_dir = collection_path.parent

        # 1. Find and Process Children
        # Look for direct Item files
        for item_file in collection_dir.glob("*.json"):
            if item_file.name in ["collection.json", "catalog.json"]:
                continue

            # Simple check if it's an item
            with open(item_file) as f_check:
                if "Feature" not in f_check.read(100):
                    continue

            node = process_item(item_file, hash_method, ignore_links)
            if node:
                children_nodes.append(node)

        # Look for sub-directories (could be items or sub-collections)
        for sub_dir in collection_dir.iterdir():
            if not sub_dir.is_dir():
                continue

            sub_coll = sub_dir / "collection.json"
            sub_cat = sub_dir / "catalog.json"

            if sub_coll.exists():
                node = process_collection(sub_coll, hash_method, ignore_links)
                if node:
                    children_nodes.append(node)
            elif sub_cat.exists():
                # Technically a Collection shouldn't contain a Catalog, but we handle it safely
                pass
            else:
                # Check for Item in folder (e.g /item-id/item-id.json)
                item_files = list(sub_dir.glob("*.json"))
                if len(item_files) == 1:
                    node = process_item(item_files[0], hash_method, ignore_links)
                    if node:
                        children_nodes.append(node)

        # 2. Collect Hashes for the Merkle Tree (The Ripple Effect Logic)
        tree_hashes = []
        for child in children_nodes:
            if child["type"] == "Item":
                # Leaf: use object hash
                tree_hashes.append(child["merkle:object_hash"])
            else:
                # Container: use ROOT hash to capture deep changes
                tree_hashes.append(child["merkle:root"])

        # Include self in the tree
        own_object_hash = compute_merkle_object_hash(
            collection_json, hash_method, ignore_links
        )
        collection_json["merkle:object_hash"] = own_object_hash
        tree_hashes.append(own_object_hash)

        # 3. Compute Root
        merkle_root = compute_merkle_root(tree_hashes, hash_method)

        # 4. Save
        collection_json["merkle:root"] = merkle_root
        collection_json["merkle:hash_method"] = hash_method

        collection_json.setdefault("stac_extensions", [])
        if EXTENSION_URL not in collection_json["stac_extensions"]:
            collection_json["stac_extensions"].append(EXTENSION_URL)
            collection_json["stac_extensions"].sort()

        # Atomic write pattern: write to temp file, then move
        temp_path = collection_path.with_suffix(".tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(collection_json, f, indent=2)
                f.write("\n")
            temp_path.replace(collection_path)
        except Exception:
            if temp_path.exists():
                os.remove(temp_path)
            raise

        print(
            f"Processed Collection: {collection_path.name} -> Root: {merkle_root[:8]}..."
        )

        return {
            "node_id": collection_json.get("id", str(collection_path)),
            "type": "Collection",
            "merkle:object_hash": own_object_hash,
            "merkle:root": merkle_root,
            "children": children_nodes,
        }

    except Exception as e:
        print(f"Error processing Collection {collection_path}: {e}")
        return {}


def process_catalog(
    catalog_path: Path,
    parent_hash_method: Dict[str, Any],
    ignore_links: bool = True,
) -> Dict[str, Any]:
    """
    Processes the Root Catalog.
    """
    try:
        with catalog_path.open("r", encoding="utf-8") as f:
            catalog_json = json.load(f)

        hash_method = catalog_json.get("merkle:hash_method", parent_hash_method)
        children_nodes = []
        catalog_dir = catalog_path.parent

        # Process 'collections' folder if exists, or direct subfolders
        scan_dirs = [catalog_dir]
        if (catalog_dir / "collections").exists():
            scan_dirs.append(catalog_dir / "collections")

        for scan_dir in scan_dirs:
            for item in scan_dir.iterdir():
                if item.is_dir():
                    coll_path = item / "collection.json"
                    if coll_path.exists():
                        node = process_collection(coll_path, hash_method, ignore_links)
                        if node:
                            children_nodes.append(node)

        # Ripple Effect Aggregation
        tree_hashes = []
        for child in children_nodes:
            # Catalogs only contain Collections/Catalogs, so we always use Root
            tree_hashes.append(child["merkle:root"])

        own_object_hash = compute_merkle_object_hash(
            catalog_json, hash_method, ignore_links
        )
        catalog_json["merkle:object_hash"] = own_object_hash
        tree_hashes.append(own_object_hash)

        merkle_root = compute_merkle_root(tree_hashes, hash_method)

        catalog_json["merkle:root"] = merkle_root
        catalog_json["merkle:hash_method"] = hash_method

        catalog_json.setdefault("stac_extensions", [])
        if EXTENSION_URL not in catalog_json["stac_extensions"]:
            catalog_json["stac_extensions"].append(EXTENSION_URL)
            catalog_json["stac_extensions"].sort()

        # Atomic write pattern: write to temp file, then move
        temp_path = catalog_path.with_suffix(".tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(catalog_json, f, indent=2)
                f.write("\n")
            temp_path.replace(catalog_path)
        except Exception:
            if temp_path.exists():
                os.remove(temp_path)
            raise

        print(f"Processed Root Catalog: {catalog_path.name}")

        return {
            "node_id": catalog_json.get("id", str(catalog_path)),
            "type": "Catalog",
            "merkle:object_hash": own_object_hash,
            "merkle:root": merkle_root,
            "children": children_nodes,
        }

    except Exception as e:
        print(f"Error processing Catalog {catalog_path}: {e}")
        return {}
