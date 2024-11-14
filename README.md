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

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/stacchain/stac-merkle-tree-cli.git
   cd stac-merkle-tree-cli
   ```

2. **Install Required Python Libraries**: The tool relies on the click library for the CLI interface. Install it using pip:

   ```bash
   pip install click
   ```

3. **Make the Script Executable (Optional)**: If you're on a Unix-like system and want to run the script directly:

   ```bash
   chmod +x compute_merkle_info.py
   ```
