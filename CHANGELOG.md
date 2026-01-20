# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.4.0] - 2026-01-12

### Added

- **Merkle Proofs**: Added new `proofs` command to generate standalone Merkle Inclusion Proof JSON files and link them in STAC Items (Spec v1.1.1).
- **Deep Integrity**: Added `--deep-integrity` flag to the `compute` command. When enabled, it includes asset `file:checksum` values in the hash calculation.
- **Safer Hashing**: Added `--ignore-links` flag (default: True) to exclude the `links` field from hashing, preventing circular dependency issues.
- **Verification**: Added `verify` command to ensure the `merkle_tree.json` structure matches the computed hashes [#3](https://github.com/stacchain/stac-merkle-tree-cli/pull/3).

### Changed

- Updated default extension URL to `v1.1.1`.
- Refactored `compute` logic to use a safer default field list (excluding links) instead of a wildcard `*`.

## [v0.3.0] - 2024-11-20

### Added

- Merkle tree verification JSON to help Users check the produced merkle values and hierarchical structure of their STAC Catalog post-processing [#2](https://github.com/stacchain/stac-merkle-tree-cli/pull/2)

## [v0.2.0] - 2024-11-16

### Added

- Enhanced collection processing to support nested subdirectories for items [#1](https://github.com/stacchain/stac-merkle-tree-cli/pull/1)
- Test to ensure `merkle:root` values remain the same whether items are nested or not [#1](https://github.com/stacchain/stac-merkle-tree-cli/pull/1)

## [v0.1.0] - 2024-11-16

- first release

[Unreleased]: https://github.com/stacchain/stac-merkle-tree-cli/tree/v0.3.0...main
[v0.3.0]: https://github.com/stacchain/stac-merkle-tree-cli/tree/v0.2.0...v0.3.0
[v0.2.0]: https://github.com/stacchain/stac-merkle-tree-cli/tree/v0.1.0...v0.2.0
[v0.1.0]: https://github.com/stacchain/stac-merkle-tree-cli/tree/v0.1.0
