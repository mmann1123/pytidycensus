# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of pytidycensus
- Support for American Community Survey (ACS) data via `get_acs()`
- Support for Decennial Census data via `get_decennial()`
- Support for Population Estimates data via `get_estimates()`
- Automatic geometry retrieval with TIGER/Line shapefiles
- Variable caching and search functionality
- Comprehensive Jupyter notebook examples
- Full Sphinx documentation with API reference

### Dependencies
- pandas >= 1.3.0
- geopandas >= 0.10.0 (optional, for spatial features)
- requests >= 2.25.0
- us >= 2.0.0
- appdirs >= 1.4.0

## [0.1.0] - 2024-XX-XX

### Added
- Initial public release
- Core Census API functionality
- Basic documentation and examples