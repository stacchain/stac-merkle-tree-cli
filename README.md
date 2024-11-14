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
- [Error Handling](#error-handling)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

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

Ensure your STAC catalog follows the directory structure below for optimal processing:

```bash
catalog/
├── catalog.json
├── collections/
│   ├── collection1/
│   │   ├── collection.json
│   │   ├── item1.json
│   │   ├── item2.json
│   │   └── ...
│   ├── collection2/
│   │   ├── collection.json
│   │   ├── item1.json
│   │   └── ...
│   └── ...
```

- **Catalog Level**:
  - `catalog.json`: Root catalog file.
  - `collections/`: Directory containing all collections.
- **Collections Level**:
  - Each collection has its own directory inside `collections/`, named after the collection.
  - Inside each collection directory:
    - `collection.json`: Collection metadata.
    - `item.json`, `item2.json`, ...: Items belonging to the collection.

## Usage

### Basic Usage

After installing the package, you can use the `stac-merkle-tree-cli` command to compute and add Merkle information to your STAC catalog.

Navigate to the directory containing your catalog.json file and run the command as follows:

```bash
stac-merkle-cli path/to/catalog.json
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
│   │   └── item2.json
│   └── collection2/
│       ├── collection.json
│       ├── item1.json
│       └── item2.json

```

Run the tool:

```bash
stac-merkle-tree-cli ./my_stac_catalog/catalog.json
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
