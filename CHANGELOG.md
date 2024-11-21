# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Logging to cli tool and associated scripts [#5](https://github.com/stacchain/stac-merkle-tree-cli/pull/5)
- `verify` command to cli with accompanying script to ensure that the Merkle tree verification json produced by the `compute` command matches [#3](https://github.com/stacchain/stac-merkle-tree-cli/pull/3)

### Changed

- Moved compute and verifcation logic into classes for better oop functionality [#5](https://github.com/stacchain/stac-merkle-tree-cli/pull/5)

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
