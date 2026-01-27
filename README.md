# STAC Merkle Tree CLI Tool

A Command-Line Interface (CLI) tool for computing and adding Merkle Tree information to your [SpatioTemporal Asset Catalog (STAC)](https://stacspec.org/) directory structure. This tool ensures metadata integrity for your STAC Items, Collections, and Catalogs by encoding them in a Merkle tree via hashing.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Directory Structure](#directory-structure)
- [Usage](#usage)
  - [1. `compute`](#1-compute)
  - [2. `proofs`](#2-proofs)
  - [3. `verify`](#3-verify)
  - [4. `verify-proof`](#4-verify-proof)
  - [How to Verify a Proof (Client-Side)](#how-to-verify-a-proof-client-side)
- [File Integrity (Opportunistic Checksums)](#file-integrity-opportunistic-checksums)
- [Merkle Tree Extension Specification](#merkle-tree-extension-specification)
- [Contributing](#contributing)

## Overview

The **STAC Merkle Tree CLI Tool** automates the process of computing and embedding Merkle Tree information into your STAC catalog. By integrating this tool into your workflow, you can:

- **Ensure Metadata Integrity:** Verify that your STAC objects (Items, Collections, Catalogs) have not been tampered with.
- **Facilitate Verification:** Enable users to verify the integrity of STAC objects using the Merkle hashes.
- **Maintain Consistency:** Automatically compute and update Merkle information across your entire catalog hierarchy.

## Features

- **Recursive Processing:** Traverses the entire STAC catalog, including Catalogs, Collections, and Items.
- **Merkle Hash Computation:** Computes `merkle:object_hash` for each STAC object based on specified hashing methods.
- **Merkle Root Calculation:** Builds Merkle trees for Collections and Catalogs to compute `merkle:root`.
- **Merkle Proof Generation:** Generates standalone JSON proof files to verify individual items without downloading the whole catalog.
- **Opportunistic File Integrity:** Automatically includes `file:checksum` in hashes when present in asset metadata (no flag required).
- **Extension Compliance:** Adheres to the [Merkle Tree Extension Specification](#merkle-tree-extension-specification) for STAC.
- **User-Friendly CLI:** Built with the [Click](https://click.palletsprojects.com/) library for an intuitive command-line experience.
- **Lightweight & Fast:** Pure JSON processing with no external file downloads or dependencies.

## Prerequisites

- **Python 3.6 or higher**
- **pip** (Python package installer)

## General Installation

```bash
pip install stac-merkle-tree-cli
```

## Building for Development

1. **Clone the Repository**

   ```bash
   git clone https://github.com/stacchain/stac-merkle-tree-cli.git
   cd stac-merkle-tree-cli
   ```

2. **Install the Package**

   ```bash
   pip install -e .
   ```

## Directory Structure

Ensure your STAC catalog follows one of the directory structures below for optimal processing:

### Standard Flat Structure

In this structure, all items are at the same level as the `collection.json` file:

```bash
collection/
├── collection.json
├── item1.json
├── item2.json
└── ...
```

### Nested Structure

In this structure, items can be nested inside their own subdirectories within a collection:

```bash
collection/
├── collection.json
├── item1/
│   └── item1.json
├── item2/
│   └── item2.json
└── ...
```

### Catalog with Collections and Nested Items

A full STAC catalog with collections, where items can be either at the same level as the `collection.json` or nested within subdirectories:

```bash
catalog/
├── catalog.json
├── collections/
│   ├── collection1/
│   │   ├── collection.json
│   │   ├── item1.json
│   │   ├── item2/
│   │   │   └── item2.json
│   ├── collection2/
│   │   ├── collection.json
│   │   ├── item1/
│   │   │   └── item1.json
│   │   └── item2.json
└── ...
```

- **Catalog Level**:
  - `catalog.json`: Root catalog file.
  - `collections/`: Directory containing all collections.
- **Collections Level**:
  - Each collection has its own directory inside `collections/`, named after the collection.
  - Inside each collection directory:
    - `collection.json`: Collection metadata.
    - `item.json`, `item2.json`, ...: Items belonging to the collection, either at the same level or nested within subdirectories.

## Usage

### Basic Usage

After installing the package, you can use the `stac-merkle-tree-cli` command to compute or verify Merkle information in your STAC catalog.

### Commands:

### 1. `compute`

The compute command computes and adds Merkle information (`merkle:object_hash`, `merkle:root`, `merkle:hash_method`) to your STAC catalog. The tool automatically includes `file:checksum` values in the hash computation when they are present in asset metadata.

```bash
stac-merkle-tree-cli compute path/to/catalog_directory [OPTIONS]
```

#### Parameters:

- `path/to/catalog_directory`: (Required) Path to the root directory containing `catalog.json`.

#### Options:

- `--merkle-tree-file TEXT`: (Optional) Path to the output Merkle tree structure file. Defaults to `merkle_tree.json` within the provided catalog_directory.
- `--ignore-links / --include-links`: (Optional) Exclude the "links" field from hashing to prevent circular dependencies. Defaults to `--ignore-links` (True).

#### Example

Assuming your directory structure is as follows:

```bash
my_stac_catalog/
├── catalog.json
├── collections/
│   ├── collection1/
│   │   ├── collection.json
│   │   ├── item1.json
│   │   └── item2/
│   │       └── item2.json
│   └── collection2/
│       ├── collection.json
│       ├── item1/
│       │   └── item1.json
│       └── item2.json
```

Run the tool:

```bash
stac-merkle-tree-cli compute my_stac_catalog/
```

Expected Output:

```
Processed Item: /path/to/my_stac_catalog/collections/collection1/item1.json
Processed Item: /path/to/my_stac_catalog/collections/collection1/item2/item2.json
Processed Collection: /path/to/my_stac_catalog/collections/collection1/collection.json
Processed Item: /path/to/my_stac_catalog/collections/collection2/item1/item1.json
Processed Item: /path/to/my_stac_catalog/collections/collection2/item2.json
Processed Collection: /path/to/my_stac_catalog/collections/collection2/collection.json
Processed Catalog: /path/to/my_stac_catalog/catalog.json
Merkle tree structure saved to /path/to/my_stac_catalog/merkle_tree.json
```

### 2. `proofs`

The `proofs` command generates standalone Merkle Inclusion Proof JSON files for every Item in the catalog. It also updates each Item to add a `merkle-proof` link pointing to its specific proof file.

```bash
stac-merkle-tree-cli proofs path/to/catalog_directory [OPTIONS]
```

#### Parameters:

- `path/to/catalog_directory`: (Required) Path to the root directory containing `catalog.json` and `merkle_tree.json` (generated by the `compute` command).

#### Options:

- `--base-url TEXT`: (Required) The base URL where the proof files will be hosted (e.g., `https://my-stac-bucket.s3.amazonaws.com/proofs`).
- `--output-dir TEXT`: (Optional) Directory to save the generated proof files. Defaults to `./proofs`.

#### Example:

Run the command:

```bash
stac-merkle-tree-cli proofs my_stac_catalog/ --base-url "https://example.com/stac/proofs"
```

Expected Output:

```
Scanning for Items and generating proofs...
Done. Generated 42 proofs in './proofs'.
```

#### Proof File Structure

Each proof file is named `{item_id}.proof.json` and contains the Merkle inclusion proof path from the Item to the catalog root:

```json
{
  "target_hash": "ce9f56e695ab1751b8f0c8d9ef1f1ecedaf04574ec3077e70e7426ec9fc61ea4",
  "root": "2c637f0bae066e89de80839f3468f73e396e9d1498faefc469f0fd1039e19e0c",
  "path": [
    {
      "position": "right",
      "hash": "17789b31f8ae304de8dbe2350a15263dbf5e31adfc0d17a997e7e55f4cfc2f53"
    },
    {
      "position": "left",
      "hash": "6ae6f97edd2994b632b415ff810af38639faa84544aa8a33a88bdf867a649374"
    }
  ]
}
```

#### Item Link Update

Each Item's `links` array is updated with a reference to its proof file:

```json
{
  "links": [
    {
      "rel": "merkle-proof",
      "href": "https://example.com/stac/proofs/item_id.proof.json",
      "type": "application/json"
    }
  ]
}
```

### 3. `verify`

The `verify` command validates the integrity of a STAC Catalog by recalculating `merkle:root` values and comparing them to the stored values in the Merkle tree structure.

```bash
stac-merkle-tree-cli verify path/to/catalog_directory
```

#### Parameters:

- `path/to/catalog_directory`: (Required) Path to the root directory containing `catalog.json` and `merkle_tree.json`.

#### Example:

Run the command:

```bash
stac-merkle-tree-cli verify my_stac_catalog/
```

Example Output (Success):

```bash
✅ Verified Item: DEM1_SAR_DGE_30_20101212T230244_20140325T230302_ADS_000000_1jTi
✅ Verified Collection: COP-DEM
✅ Verified Catalog: Catalogue

🎉 Merkle Tree Verification SUCCESS!
```

Example Output (Failure):

```bash
❌ Verification FAILED for Collection 'COP-DEM'
   Calculated: f0ed08b316b917a98c085e699c090af1cea964b697dd0bc44491ebced4d0006c
   Stored:     5808b480d9bed10e7663d52c218571d053c7b5df42a5aefc11e216c66c711f77

⛔ Merkle Tree Verification FAILED.
```

## How to Verify a Proof (Client-Side)

You can verify a proof using the `verify-proof` command shown above. However, for clients who do not have this CLI installed, the verification logic is simple enough to implement in any language. Here is a standalone Python snippet demonstrating how to verify an Item against its proof file:

```python
import json
import hashlib

def compute_hash(data):
    """Compute SHA256 hash of data."""
    if isinstance(data, dict):
        # Canonical JSON dump to match CLI logic
        encoded = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
    else:
        # Hashing raw bytes/strings
        encoded = data if isinstance(data, bytes) else data.encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()

def verify_item(item_json, proof_json):
    """
    Verify a STAC Item against a Merkle Proof.
    """
    # 1. Clean the Item: Remove fields that change (merkle fields)
    #    Note: 'links' should be removed ONLY if you used '--ignore-links' (default)
    #    during the 'compute' step. If you used '--include-links', remove 'links' from this list.
    fields_to_remove = ["merkle:object_hash", "merkle:root", "merkle:hash_method", "links"]

    clean_item = {
        k: v for k, v in item_json.items()
        if k not in fields_to_remove
    }

    # 2. Calculate the Item's Hash
    current_hash = compute_hash(clean_item)

    # 3. Check if Identity matches
    if current_hash != proof_json['target_hash']:
        print("❌ Identity Mismatch: Item data has been altered.")
        return False

    # 4. Traverse the Path (The Merkle Proof)
    for step in proof_json['path']:
        sibling_hash = step['hash']
        position = step['position']

        # Combine hashes based on position
        if position == 'left':
            combined = bytes.fromhex(sibling_hash) + bytes.fromhex(current_hash)
        else:
            combined = bytes.fromhex(current_hash) + bytes.fromhex(sibling_hash)

        current_hash = hashlib.sha256(combined).hexdigest()

    # 5. Compare against the Trusted Root
    if current_hash == proof_json['root']:
        print("✅ SUCCESS: Item is verified against the Root.")
        return True
    else:
        print("❌ FAILURE: Cryptographic proof failed.")
        print(f"Calculated Root: {current_hash}")
        print(f"Expected Root:   {proof_json['root']}")
        return False

# Example Usage
if __name__ == "__main__":
    with open("item.json") as f:
        item = json.load(f)

    with open("item.proof.json") as f:
        proof = json.load(f)

    verify_item(item, proof)
```

### Why This Snippet Matters

**Transparency:** It proves there is no "magic" in the tool. The verification logic is standard cryptography (SHA256) that can be implemented in Python, JavaScript, Go, or any language.

**Zero Dependencies:** A data consumer (e.g., a scientist or a frontend developer) can verify your data without needing to install the CLI tool. This snippet uses only Python's standard libraries (`json` and `hashlib`).

**Trust:** It demonstrates that the Merkle implementation relies on standard, open cryptography (SHA256), not proprietary logic.

**Portability:** Because the logic is simple (standard JSON serialization + SHA256), developers can easily port this snippet to JavaScript, Go, Rust, or other languages.

### 4. `verify-proof`

The `verify-proof` command verifies a single STAC Item against its Merkle Proof file. This is useful for data consumers who have downloaded an Item and its proof file and want to verify integrity without needing the entire catalog.

```bash
stac-merkle-tree-cli verify-proof path/to/item.json path/to/item.proof.json
```

#### Parameters:

- `path/to/item.json`: (Required) Path to the STAC Item JSON file to verify.
- `path/to/item.proof.json`: (Required) Path to the corresponding Merkle Proof JSON file.

#### Options:

- `--ignore-links / --include-links`: (Default: `--ignore-links`) Exclude or include the `links` field from the verification hash. **Important:** This must match the setting used when generating the proof with the `proofs` command. If the proof was generated with `--include-links`, you must use `--include-links` when verifying.

#### Example:

Run the command (default: ignoring links):

```bash
stac-merkle-tree-cli verify-proof my_item.json my_item.proof.json
```

Or, if the proof was generated with `--include-links`:

```bash
stac-merkle-tree-cli verify-proof my_item.json my_item.proof.json --include-links
```

Example Output (Success):

```bash
✅ SUCCESS: Item is verified against the Root.
✅ Verification SUCCESS
```

Example Output (Failure - Data Tampered):

```bash
❌ Identity Mismatch: Item data has been altered.
❌ Verification FAILED
```

Example Output (Failure - Invalid Proof):

```bash
❌ FAILURE: Cryptographic proof failed.
Calculated Root: abc123def456...
Expected Root:   xyz789uvw012...
❌ Verification FAILED
```

#### How It Works

The `verify-proof` command performs the following steps:

1. **Load Files:** Reads the Item JSON and Proof JSON files.
2. **Clean Item:** Removes transient fields (`merkle:object_hash`, `merkle:root`, `merkle:hash_method`, `links`) that may change between versions.
3. **Compute Hash:** Calculates the SHA256 hash of the cleaned Item using canonical JSON serialization.
4. **Verify Identity:** Checks if the computed hash matches the `target_hash` in the proof.
5. **Traverse Proof Path:** Follows the Merkle proof path, combining hashes at each step.
6. **Verify Root:** Compares the final calculated root against the trusted `root` in the proof file.

If all steps succeed, the Item is cryptographically verified to be part of the original catalog.

#### Use Cases

- **Data Consumer Verification:** A scientist downloads an Item and proof file from a data provider and verifies integrity locally.
- **CI/CD Validation:** Automated tests verify that generated proofs are valid before publishing.
- **Offline Verification:** Verify data integrity without network access to the original catalog.

### Using the CLI to Verify Proofs

You can verify a single Item against its proof file using the CLI command shown above. This performs the same verification as the Python snippet below, making it convenient for users who have the tool installed.

## File Integrity (Opportunistic Checksums)

This tool automatically detects and includes file checksums in the Merkle tree computation when they are present in your STAC Items.

### How It Works

1. **During Ingestion/ETL:** Your data pipeline should calculate `file:checksum` for each asset and include it in the Item's asset metadata using the [File Info Extension](https://github.com/stac-extensions/file).
2. **During Merkle Computation:** The CLI automatically detects these checksums and includes them in the hash calculation, strengthening the integrity verification.
3. **No Configuration Needed:** The tool works opportunistically—if checksums exist, they are used; if not, the tool continues with available metadata.

### Recommended: Use the File Info Extension

We **strongly recommend** adding the [File Info Extension](https://github.com/stac-extensions/file) (`https://stac-extensions.github.io/file/v2.1.0/schema.json`) to your STAC Items during ingestion. This extension provides a standardized way to specify file-related details including checksums.

**Benefits:**
- **Standardized Format:** Follows the STAC specification for file metadata
- **Stronger Integrity:** Including file checksums in the Merkle tree provides end-to-end verification of both metadata and data
- **Automatic Detection:** This CLI automatically detects and includes checksums when the extension is present
- **Interoperability:** Other STAC tools can rely on this standardized field

### Example Asset with Checksum

```json
{
  "assets": {
    "data": {
      "href": "https://example.com/data.tif",
      "type": "image/tiff; application=geotiff",
      "file:checksum": "1220abc123def456...",
      "file:size": 1024000
    }
  }
}
```

When checksums are present, the File Info extension is automatically added to the Item:

```json
{
  "stac_extensions": [
    "https://stacchain.github.io/merkle-tree/v1.1.1/schema.json",
    "https://stac-extensions.github.io/file/v2.1.0/schema.json"
  ]
}
```

### Checksum Format

File checksums must follow the [Multihash specification](https://github.com/multiformats/multihash) and be encoded as hexadecimal strings with lowercase letters. Examples:

- **SHA256:** `1220` + hex string (e.g., `12209f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08`)
- **SHA1:** `1114` + hex string (e.g., `1114a94a8fe5ccb19ba61c4c0873d391e987982fbbd3`)
- **BLAKE2b-128:** `90e4` + hex string (e.g., `90e4021044a8995dd50b6657a037a7839304535b`)

## Merkle Tree Extension Specification

This tool complies with the [Merkle Tree Extension Specification](https://github.com/stacchain/merkle-tree), which outlines how to encode STAC objects in a Merkle tree to ensure metadata integrity.

### Fields Added

- `merkle:object_hash` (string, REQUIRED in Items, Collections, Catalogs)
  - A cryptographic hash of the object's metadata, used to verify its integrity.
  - For Items: Located within the properties field.
  - For Collections and Catalogs: Located at the top level.
  - Automatically includes `file:checksum` values when present in asset metadata.
- `merkle:hash_method` (object, REQUIRED in Collections and Catalogs)
  - Describes the method used to compute `merkle:object_hash` and `merkle:root`, including:
    - `function`: The hash function used (e.g., sha256).
    - `fields`: Fields included in the hash computation (e.g., ["*"] for all fields).
    - `ordering`: How child hashes are ordered when building the Merkle tree (e.g., ascending).
    - `description`: Additional details about the hash computation method.
- `merkle:root` (string, REQUIRED in Collections and Catalogs)
  - The Merkle root hash representing the Collection or Catalog, computed from child object hashes.

### Extension URL

All STAC objects processed by this tool will include the Merkle extension URL in their stac_extensions array:

```json
"stac_extensions": [
  "https://stacchain.github.io/merkle-tree/v1.1.1/schema.json"
]
```

### Link Relations

This tool adds the following relation type to STAC Items when running the `proofs` command:

| Relation Type | Description |
|---|---|
| `merkle-proof` | Points to a JSON file containing the Merkle Inclusion Proof for this Item. This allows clients to verify the integrity of the Item without downloading the entire catalog. |

## Output

After running the tool, each STAC object will be updated with the appropriate Merkle fields.

### Merkle Tree Structure (merkle_tree.json)

The tool generates a `merkle_tree.json` file that represents the hierarchical Merkle tree of your STAC catalog. Below is an example of the `merkle_tree.json` structure:

```json
{
  "node_id": "Catalogue",
  "type": "Catalog",
  "merkle:object_hash": "b14fd102417c1d673f481bc053d19946aefdc27d84c584989b23c676c897bd5a",
  "merkle:root": "2c637f0bae066e89de80839f3468f73e396e9d1498faefc469f0fd1039e19e0c",
  "children": [
    {
      "node_id": "COP-DEM",
      "type": "Collection",
      "merkle:object_hash": "17789b31f8ae304de8dbe2350a15263dbf5e31adfc0d17a997e7e55f4cfc2f53",
      "merkle:root": "2f4aa32184fbe70bd385d5b6b6e6d4ec5eb8b2e43611b441febcdf407c4e0030",
      "children": [
        {
          "node_id": "DEM1_SAR_DGE_30_20101212T230244_20140325T230302_ADS_000000_1jTi",
          "type": "Item",
          "merkle:object_hash": "ce9f56e695ab1751b8f0c8d9ef1f1ecedaf04574ec3077e70e7426ec9fc61ea4"
        }
      ]
    },
    {
      "node_id": "TERRAAQUA",
      "type": "Collection",
      "merkle:object_hash": "6ae6f97edd2994b632b415ff810af38639faa84544aa8a33a88bdf867a649374",
      "merkle:root": "6ae6f97edd2994b632b415ff810af38639faa84544aa8a33a88bdf867a649374",
      "children": []
    },
    {
      "node_id": "S2GLC",
      "type": "Collection",
      "merkle:object_hash": "84ab0e102924c012d4cf2a3b3e10ed4f768f695001174cfd5d9c75d4335b7a48",
      "merkle:root": "33631c1a3d9339ffc66b3f3a3eb3de8f558bcabe4900494b55ca17aff851e661",
      "children": [
        {
          "node_id": "S2GLC_T30TWT_2017",
          "type": "Item",
          "merkle:object_hash": "3a3803a0dae5dbaf9561aeb4cce2770bf38b5da4b71ca67398fb24d48c43a68f"
        }
      ]
    }
  ]
}
```

#### Structure Explanation:

- **Root Node** (Catalogue):
  - node_id: Identifier of the Catalog.
  - type: Specifies that this node is a Catalog.
  - merkle:object_hash: Hash of the Catalog's metadata.
  - merkle:root: The Merkle root representing the entire Catalog.
  - children: Array containing child nodes, which can be Collections or Items.
- **Child Nodes** (e.g., COP-DEM, TERRAAQUA, S2GLC):

  - node_id: Identifier of the Collection.
  - type: Specifies that this node is a Collection.
  - merkle:object_hash: Hash of the Collection's metadata.
  - merkle:root: The Merkle root representing the Collection, calculated from its children.
  - children: Array containing child nodes, which can be Items or further sub-Collections.

- **Leaf Nodes** (e.g., DEM1_SAR_DGE_30_20101212T230244_20140325T230302_ADS_000000_1jTi, S2GLC_T30TWT_2017):
  - node_id: Identifier of the Item.
  - type: Specifies that this node is an Item.
  - merkle:object_hash: Hash of the Item's metadata.
  - No merkle:root or children: As Items are leaf nodes, they do not contain these fields.

### Catalog (catalog.json)

```json
{
  "type": "Catalog",
  "stac_version": "1.1.0",
  "id": "my-catalog",
  "description": "My STAC Catalog",
  "links": [],
  "stac_extensions": [
    "https://stacchain.github.io/merkle-tree/v1.1.1/schema.json"
  ],
  "merkle:object_hash": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
  "merkle:root": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
  "merkle:hash_method": {
    "function": "sha256",
    "fields": ["*"],
    "ordering": "ascending",
    "description": "Computed by excluding Merkle fields and including merkle:object_hash values in ascending order to build the Merkle tree."
  }
}
```

### Collection (collections/collection1/collection.json)

```json
{
  "type": "Collection",
  "stac_version": "1.1.0",
  "id": "collection1",
  "description": "My STAC Collection",
  "extent": {},
  "links": [],
  "stac_extensions": [
    "https://stacchain.github.io/merkle-tree/v1.1.1/schema.json"
  ],
  "merkle:object_hash": "fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321",
  "merkle:root": "0987654321fedcba0987654321fedcba0987654321fedcba0987654321fedcba",
  "merkle:hash_method": {
    "function": "sha256",
    "fields": ["*"],
    "ordering": "ascending",
    "description": "Computed by excluding Merkle fields and including merkle:object_hash values in ascending order to build the Merkle tree."
  }
}
```

### Item (collections/collection1/item1.json)

```json
{
  "type": "Feature",
  "stac_version": "1.1.0",
  "id": "item1",
  "properties": {
    "merkle:object_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
  },
  "geometry": {},
  "links": [],
  "assets": {},
  "stac_extensions": [
    "https://stacchain.github.io/merkle-tree/v1.1.1/schema.json"
  ]
}
```

## Contributing

Contributions are welcome! If you encounter issues or have suggestions for improvements, please open an issue or submit a pull request on the [GitHub repository](https://github.com/stacchain/stac-merkle-tree-cli).

## Verification Steps

### 1. Compute Merkle Tree

Use the `compute` command to process your STAC catalog and generate a Merkle tree structure.

```bash
stac-merkle-tree-cli compute path/to/catalog_directory
```

#### Options:

--merkle-tree-file <file_path>: Specify the output file name for the Merkle tree JSON (default is merkle_tree.json).

#### Example Output:

```ruby
Processed Item: /path/to/catalog_directory/collections/collection1/item1.json
Processed Item: /path/to/catalog_directory/collections/collection1/item2/item2.json
Processed Collection: /path/to/catalog_directory/collections/collection1/collection.json
Processed Item: /path/to/catalog_directory/collections/collection2/item1/item1.json
Processed Item: /path/to/catalog_directory/collections/collection2/item2.json
Processed Collection: /path/to/catalog_directory/collections/collection2/collection.json
Processed Catalog: /path/to/catalog_directory/catalog.json
Merkle tree structure saved to /path/to/catalog_directory/merkle_tree.json
```

- The tool will generate a `merkle_tree.json` file (or the specified output file), which represents the hierarchical structure of your STAC catalog, including `merkle:object_hash` and `merkle:root` values.

### 2. Verify Merkle Tree

Use the verify command to validate the integrity of the generated Merkle tree JSON file.

```bash
stac-merkle-tree-cli verify path/to/catalog_directory/merkle_tree.json
```

#### Example Output (Success):

```bash
Verification Successful: The merkle:root matches.
```

#### Example Output (Failure):

```bash
Verification Failed:
 - Expected merkle:root: 5808b480d9bed10e7663d52c218571d053c7b5df42a5aefc11e216c66c711f77
 - Calculated merkle:root: f0ed08b316b917a98c085e699c090af1cea964b697dd0bc44491ebced4d0006c
Discrepancies found in the following nodes:
 - Collection 'COP-DEM' has mismatched merkle:root.
 - Catalog 'Catalogue' has mismatched merkle:root.
```

### 3. Validate STAC Structure Updates

Ensure that the STAC files (e.g., `catalog.json`, `collection.json`, item files) have been updated correctly:

#### Catalog:

- `catalog.json` should include:

  - `merkle:object_hash`
  - `merkle:root`
  - `merkle:hash_method`

#### Collections:

- Each `collection.json` should include:
  - `merkle:object_hash`
  - `merkle:root`
  - `merkle:hash_method`

#### Items:

- Each Item JSON should have `merkle:object_hash` within its properties field.

### 4. Verify Output File

Review the generated merkle_tree.json file to confirm:

- Proper hierarchical representation of the catalog.
- Correct merkle:object_hash and merkle:root values for each node

### 5. Run Tests:

Ensure that all tests pass by executing:

```bash
pytest -v
```
