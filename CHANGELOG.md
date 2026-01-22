# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.4.0] - 2026-01-22

### Added

- **Merkle Proofs**: Added new `proofs` command to generate standalone Merkle Inclusion Proof JSON files for each Item and link them in STAC Items. Enables verification of individual items without downloading the entire catalog. [#6](https://github.com/stacchain/stac-merkle-tree-cli/pull/6)
- **Opportunistic File Integrity**: The `compute` command now automatically detects and includes `file:checksum` values in hash calculations when present in asset metadata. [#6](https://github.com/stacchain/stac-merkle-tree-cli/pull/6)
- **Verification Command**: Added `verify` command to recursively validate the integrity of a Merkle tree by recalculating `merkle:root` values and comparing them to stored values. [#3](https://github.com/stacchain/stac-merkle-tree-cli/pull/3)
- **Link Ignore Option**: Added `--ignore-links / --include-links` flag (default: `--ignore-links`) to exclude the `links` field from hashing, preventing circular dependency issues. [#6](https://github.com/stacchain/stac-merkle-tree-cli/pull/6)

### Changed

- Updated default extension URL to `v1.1.1`. [#6](https://github.com/stacchain/stac-merkle-tree-cli/pull/6)
- Refactored CLI from single command to Click Group with three subcommands: `compute`, `proofs`, and `verify`. [#6](https://github.com/stacchain/stac-merkle-tree-cli/pull/6)

## [v0.3.0] - 2024-11-20

### Added

- Merkle tree verification JSON to help Users check the produced merkle values and hierarchical structure of their STAC Catalog post-processing [#2](https://github.com/stacchain/stac-merkle-tree-cli/pull/2)

## [v0.2.0] - 2024-11-16

### Added

- Enhanced collection processing to support nested subdirectories for items [#1](https://github.com/stacchain/stac-merkle-tree-cli/pull/1)
- Test to ensure `merkle:root` values remain the same whether items are nested or not [#1](https://github.com/stacchain/stac-merkle-tree-cli/pull/1)

## [v0.1.0] - 2024-11-16

- first release

[Unreleased]: https://github.com/stacchain/stac-merkle-tree-cli/tree/v0.4.0...main
[v0.4.0]: https://github.com/stacchain/stac-merkle-tree-cli/tree/v0.3.0...v0.4.0
[v0.3.0]: https://github.com/stacchain/stac-merkle-tree-cli/tree/v0.2.0...v0.3.0
[v0.2.0]: https://github.com/stacchain/stac-merkle-tree-cli/tree/v0.1.0...v0.2.0
[v0.1.0]: https://github.com/stacchain/stac-merkle-tree-cli/tree/v0.1.0
