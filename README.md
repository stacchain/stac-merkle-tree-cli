# STAC Merkle Tree CLI Tool

A Command-Line Interface (CLI) tool for computing and adding Merkle Tree information to your [SpatioTemporal Asset Catalog (STAC)](https://stacspec.org/) directory structure. This tool ensures metadata integrity for your STAC Items, Collections, and Catalogs by encoding them in a Merkle tree via hashing.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Directory Structure](#directory-structure)
- [Usage](#usage)
  - [Basic Usage](#basic-usage)
  - [Example](#example)
- [Merkle Tree Extension Specification](#merkle-tree-extension-specification)
- [Output](#output)
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
- **Extension Compliance:** Adheres to the [Merkle Tree Extension Specification](#merkle-tree-extension-specification) for STAC.
- **User-Friendly CLI:** Built with the [Click](https://click.palletsprojects.com/) library for an intuitive command-line experience.
- **Customizable Hash Methods:** Supports various hash functions and field selections.

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

After installing the package, you can use the `stac-merkle-tree-cli` command to compute and add Merkle information to your STAC catalog.

```bash
stac-merkle-tree-cli path/to/catalog_directory [OPTIONS]
```

#### Parameters:

- path/to/catalog_directory: (Required) Path to the root directory containing catalog.json.

#### Options:

- --merkle-tree-file TEXT: (Optional) Path to the output Merkle tree structure file. Defaults to merkle_tree.json within the provided catalog_directory.

### Example

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
stac-merkle-tree-cli my_stac_catalog/
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

## Merkle Tree Extension Specification

This tool complies with the [Merkle Tree Extension Specification](https://github.com/stacchain/merkle-tree), which outlines how to encode STAC objects in a Merkle tree to ensure metadata integrity.

### Fields Added

- `merkle:object_hash` (string, REQUIRED in Items, Collections, Catalogs)
  - A cryptographic hash of the object's metadata, used to verify its integrity.
  - For Items: Located within the properties field.
  - For Collections and Catalogs: Located at the top level.
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
  "https://stacchain.github.io/merkle-tree/v1.0.0/schema.json"
]
```

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
    "https://stacchain.github.io/merkle-tree/v1.0.0/schema.json"
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
    "https://stacchain.github.io/merkle-tree/v1.0.0/schema.json"
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
    "https://stacchain.github.io/merkle-tree/v1.0.0/schema.json"
  ]
}
```

## Contributing

Contributions are welcome! If you encounter issues or have suggestions for improvements, please open an issue or submit a pull request on the [GitHub repository](https://github.com/stacchain/stac-merkle-tree-cli).

## Verification Steps

### 1. Run the CLI Tool:

```bash
stac-merkle-tree-cli path/to/catalog_directory
```

### 2. Check the Output:

- **Console Output**: You should see logs indicating the processing of Items, Collections, and the Catalog.

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

- **Merkle Tree JSON**: Verify that the `merkle_tree.json` (or your specified output file) accurately represents the hierarchical structure of your STAC catalog with correct `merkle:object_hash` and `merkle:root` values.

### 3. Verify Integrity:

- **Catalog**: Ensure that the `catalog.json` now includes `merkle:object_hash`, `merkle:root`, and `merkle:hash_method`.

- **Collections**: Each `collection.json` should include `merkle:object_hash`, `merkle:root`, and `merkle:hash_method`.

- **Items**: Each Item's JSON should have `merkle:object_hash` within the properties field.

### 4. Run Tests:

Ensure that all tests pass by executing:

```bash
pytest -v
```
