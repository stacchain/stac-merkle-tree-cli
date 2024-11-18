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

Navigate to the directory containing your catalog.json file and run the command as follows:

```bash
stac-merkle-tree-cli path/to/catalog.json
```

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
stac-merkle-tree-cli my_stac_catalog/catalog.json
```

Expected Output:

```
Processed Item: /path/to/my_stac_catalog/collections/collection1/item1.json
Processed Item: /path/to/my_stac_catalog/collections/collection1/item2.json
Processed Collection: /path/to/my_stac_catalog/collections/collection1/collection.json
Processed Item: /path/to/my_stac_catalog/collections/collection2/item1.json
Processed Item: /path/to/my_stac_catalog/collections/collection2/item2.json
Processed Collection: /path/to/my_stac_catalog/collections/collection2/collection.json
Processed Catalog: /path/to/my_stac_catalog/catalog.json
Merkle info computation and addition completed.
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
    "merkle:object_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "merkle:hash_method": {
      "function": "sha256",
      "fields": ["*"],
      "ordering": "ascending",
      "description": "Computed by excluding Merkle fields and including merkle:object_hash values in ascending order to build the Merkle tree."
    }
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
