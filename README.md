# pytidycensus

[![Python package](https://github.com/mmann1123/pytidycensus/actions/workflows/python-package.yml/badge.svg)](https://github.com/mmann1123/pytidycensus/actions/workflows/python-package.yml)
[![Documentation Status](https://github.com/mmann1123/pytidycensus/actions/workflows/docs.yml/badge.svg)](https://mmann1123.github.io/pytidycensus)

**pytidycensus** is a Python library that provides an integrated interface to several United States Census Bureau APIs and geographic boundary files. It allows users to return Census and American Community Survey (ACS) data as pandas DataFrames, and optionally returns GeoPandas GeoDataFrames with feature geometry for mapping and spatial analysis.

This package is a Python port of the popular R package [tidycensus](https://walker-data.com/tidycensus/) created by Kyle Walker.

## Features

- **Simple API**: Clean, consistent interface for all Census datasets
- **Pandas Integration**: Returns familiar pandas DataFrames
- **Spatial Support**: Optional GeoPandas integration for mapping with TIGER/Line shapefiles
- **Multiple Datasets**: Support for ACS, Decennial Census, and Population Estimates
- **Geographic Flexibility**: From national to block group level data
- **Caching**: Built-in caching for variables and geography data
- **Comprehensive Testing**: Full test suite with high coverage

## Installation

```bash
pip install pytidycensus
```

For development:

```bash
git clone https://github.com/mmann1123/pytidycensus
cd pytidycensus
pip install -e .[dev,docs]
```

## Quick Start

First, obtain a free API key from the [US Census Bureau](https://api.census.gov/data/key_signup.html):

```python
import pytidycensus as tc

# Set your API key
tc.set_census_api_key("your_key_here")

# Get median household income by county in Texas
tx_income = tc.get_acs(
    geography="county",
    variables="B19013_001",
    state="TX",
    year=2022
)

print(tx_income.head())
```

## Examples

### ACS Data with Geometry

```python
# Get data with geographic boundaries for mapping
tx_income_geo = tc.get_acs(
    geography="county",
    variables="B19013_001", 
    state="TX",
    geometry=True
)

# Plot the data
import matplotlib.pyplot as plt
tx_income_geo.plot(column='value', legend=True, figsize=(12, 8))
plt.title("Median Household Income by County in Texas")
plt.show()
```

### Multiple Variables

```python
# Get multiple demographic variables
demo_vars = {
    "B01003_001": "Total Population",
    "B19013_001": "Median Household Income", 
    "B25077_001": "Median Home Value"
}

ca_demo = tc.get_acs(
    geography="county",
    variables=list(demo_vars.keys()),
    state="CA",
    year=2022,
    output="wide"
)
```

### Decennial Census

```python
# Get 2020 Census population data
pop_2020 = tc.get_decennial(
    geography="state",
    variables="P1_001N",  # Total population
    year=2020
)
```

### Searching for Variables

```python
# Find variables related to income
income_vars = tc.search_variables("income", 2022, "acs", "acs5")
print(income_vars[['name', 'label']].head())
```

## Supported Datasets

- **American Community Survey (ACS)**: 1-year and 5-year estimates (2005-2022)
- **Decennial Census**: 1990, 2000, 2010, and 2020 
- **Population Estimates Program**: Annual population estimates and components of change

## Geographic Levels

pytidycensus supports all major Census geographic levels:

- US, Regions, Divisions
- States, Counties  
- Census Tracts, Block Groups
- Places, ZCTAs
- Congressional Districts
- And more...

## Documentation

Full documentation is available at: https://mmann1123.github.io/pytidycensus/

## Contributing

Contributions are welcome! Please see our [contributing guidelines](CONTRIBUTING.md) for details.

## Testing

Run the test suite:

```bash
pytest
```

With coverage:

```bash
pytest --cov=pytidycensus --cov-report=html
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Kyle Walker for creating the original [tidycensus](https://walker-data.com/tidycensus/) R package
- The US Census Bureau for providing comprehensive APIs and data access
- The pandas and GeoPandas communities for excellent geospatial Python tools

## Citation

If you use pytidycensus in your research, please cite:

```
pytidycensus: Python interface to US Census Bureau APIs
https://github.com/mmann1123/pytidycensus
```