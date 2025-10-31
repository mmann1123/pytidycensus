<!-- # pytidycensus -->
                                         
![pytidycensus logo](docs/static/logo.png)

[![Python package](https://github.com/mmann1123/pytidycensus/actions/workflows/python-package.yml/badge.svg)](https://github.com/mmann1123/pytidycensus/actions/workflows/python-package.yml)
[![Documentation Status](https://github.com/mmann1123/pytidycensus/actions/workflows/docs.yml/badge.svg)](https://mmann1123.github.io/pytidycensus)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17127531.svg)](https://doi.org/10.5281/zenodo.17127531)


**pytidycensus** is a Python library that provides an integrated interface to several United States Census Bureau APIs and geographic boundary files. It allows users to return Census and American Community Survey (ACS) data as pandas DataFrames, and optionally returns GeoPandas GeoDataFrames with feature geometry for mapping and spatial analysis.

In version 1.0, pytidycensus introduces a conversational interface powered by Large Language Models (LLMs) to help users discover variables, choose geographic levels, and generate code snippets for data retrieval. This feature aims to make accessing Census data more intuitive and user-friendly.

**This package is a Python port of the popular R package [tidycensus](https://walker-data.com/tidycensus/) created by Kyle Walker.**


## Supported Datasets

- **American Community Survey (ACS)**:  1-year and 5-year estimates (2005-2022) using `get_acs()` 
- **Decennial Census**:  1990, 2000, 2010, and 2020 using `get_decennial()`
- **Population Estimates Program**:  Annual population estimates and components of change using `get_estimates()`
- **Migration Flows**:  County-to-county migration data (2010-2018) using `get_flows()`

## Geographic Levels

pytidycensus supports all major Census geographic levels:

- US, Regions, Divisions
- States, Counties  
- Census Tracts, Block Groups
- Places, ZCTAs
- Congressional Districts
- And more...

## Features

- **Simple API**: Clean, consistent interface for all Census datasets
- **Pandas Integration**: Returns familiar pandas DataFrames
- **Spatial Support**: Optional GeoPandas integration for mapping with TIGER/Line shapefiles
- **Time Series Analysis**: Collect multi-year data with automatic area interpolation for changing boundaries
- **Multiple Datasets**: Support for ACS, Decennial Census, Population Estimates, and Migration Flows
- **Geographic Flexibility**: From national to block group level data
- **Migration Analysis**: County-to-county population movement patterns with demographic breakdowns
- **Caching**: Built-in caching for variables and geography data
- **Comprehensive Testing**: Full test suite with high coverage
- **LLM Assistant**: Conversational interface for variable discovery and code generation

## Installation

### From PyPI (Recommended)

```bash
pip install pytidycensus
```

### Latest Version with Additional Features

To install with optional dependencies:

```bash
# For mapping functionality 
pip install purify census[map]

# For LLM assistant
pip install pytidycensus[LLM]

# For time series analysis with area interpolation
pip install pytidycensus[time]

# For development tools
pip install pytidycensus[dev]

# For documentation tools
pip install pytidycensus[docs]

# For all optional dependencies (including visualization)
pip install pytidycensus[all]
```

To install the latest development version directly from GitHub:

```bash
pip install git+https://github.com/mmann1123/pytidycensus.git
```

### For Contributors

Clone the repository and install in development mode:

```bash
git clone https://github.com/mmann1123/pytidycensus.git
cd pytidycensus
pip install -e .[all]
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
    "Total_Population": "B01003_001",
    "Median_Household_Income": "B19013_001", 
    "Median_Home_Value": "B25077_001"
}

ca_demo = tc.get_acs(
    geography="county",
    variables=demo_vars,
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

### Population Estimates Program

The Population Estimates Program (PEP) provides annual population estimates and components of change. For years 2020+, data is retrieved from CSV files; for earlier years, it uses the Census API.

```python
# Get total population estimates by state
state_pop = tc.get_estimates(
    geography="state",
    variables="POP",
    year=2022
)

# Get components of population change
components = tc.get_estimates(
    geography="state", 
    variables=["BIRTHS", "DEATHS", "DOMESTICMIG", "INTERNATIONALMIG"],
    year=2022
)

# Get demographic breakdowns (characteristics)
demographics = tc.get_estimates(
    geography="state",
    variables="POP",
    breakdown=["SEX", "RACE"],
    breakdown_labels=True,
    year=2022
)

# Time series data
time_series = tc.get_estimates(
    geography="state",
    variables="POP",
    time_series=True,
    vintage=2023
)
```

## Time Series Analysis

pytidycensus provides powerful time series functionality that automatically handles changing geographic boundaries through area interpolation. This is particularly useful for tract-level analysis where boundaries change between Census years.

### Installation for Time Series

```bash
# Install with time series support
pip install pytidycensus[time]
```

### Basic Time Series

```python
# Get ACS data across multiple years with area interpolation
data = tc.get_time_series(
    geography="tract",
    variables={"total_pop": "B01003_001E", "median_income": "B19013_001E"},
    years=[2015, 2020],
    dataset="acs5",
    state="DC",
    base_year=2020,  # Use 2020 boundaries as base
    extensive_variables=["total_pop"],      # Counts/totals
    intensive_variables=["median_income"],  # Rates/medians
    geometry=True,
    output="wide"
)
```

### Decennial Census Time Series

```python
# Handle different variable codes across years
variables = {
    2010: {"total_pop": "P001001"},    # 2010 uses P001001
    2020: {"total_pop": "P1_001N"}     # 2020 uses P1_001N
}

data = tc.get_time_series(
    geography="tract",
    variables=variables,
    years=[2010, 2020],
    dataset="decennial",
    state="DC",
    base_year=2020,
    extensive_variables=["total_pop"],
    geometry=True
)
```

### Time Period Comparison

```python
# Compare specific time periods
comparison = tc.compare_time_periods(
    data=data,
    base_period=2015,
    comparison_period=2020,
    variables=["total_pop", "median_income"],
    calculate_change=True,
    calculate_percent_change=True
)

# Results include columns like:
# total_pop_2015, total_pop_2020, total_pop_change, total_pop_pct_change
```

### Key Features

- **Automatic Area Interpolation**: Handles changing tract boundaries using the `tobler` library
- **Variable Classification**: Distinguishes between extensive (counts) and intensive (rates) variables
- **Flexible Output**: Wide format (multi-index columns) or tidy format (long form)
- **Built-in Validation**: Checks interpolation accuracy and data conservation
- **Multiple Datasets**: Support for both ACS and Decennial Census time series

### Geographic Boundary Handling

- **Stable Geographies** (state, county): No interpolation needed
- **Changing Geographies** (tract, block group): Automatic area interpolation
- **Base Year Selection**: Choose which year's boundaries to use as the reference

For detailed examples, see [examples/time_series_analysis_comprehensive.py](examples/time_series_analysis_comprehensive.py).


### Migration Flows

The Migration Flows API provides data on population movement between geographic areas based on American Community Survey (ACS) 5-year estimates.

```python
# Get county-to-county migration flows for Texas
tx_flows = tc.get_flows(
    geography="county",
    state="TX",
    year=2018,
    output="wide"
)

# Get flows with demographic breakdowns (2006-2015 only)
ca_flows = tc.get_flows(
    geography="county",
    breakdown=["AGE", "SEX"],
    breakdown_labels=True,
    state="CA",
    year=2015,
    output="tidy"
)

# MSA-level migration flows
msa_flows = tc.get_flows(
    geography="metropolitan statistical area",
    year=2018
)

# Flows with geometry for mapping (when TIGER server is available)
try:
    flows_geo = tc.get_flows(
        geography="county",
        state="FL",
        year=2018,
        geometry=True
    )
except RuntimeError:
    # Fallback without geometry if server issues
    flows_geo = tc.get_flows(
        geography="county",
        state="FL",
        year=2018,
        geometry=False
    )

# See examples/09_migration_flows_example.ipynb for comprehensive tutorial
```

## LLM Assistant
For users interested in leveraging Large Language Models (LLMs) to interact with Census data, pytidycensus offers a conversational interface. This feature helps users discover relevant variables, choose appropriate geographic levels, and generate code snippets for data retrieval.

Please refer to the [LLM Assistant Documentation](docs/llm_assistant.md) for detailed instructions on setup and usage.


#### Example: Spatial Analysis with Geometry

```
👤 User: I need Wisconsin county income data for mapping
🏛️ Assistant: I understand. What additional details do you need for this analysis?

👤 User: Include geographic boundaries
🏛️ Assistant: I understand. What additional details do you need for this analysis?

👤 User: 2020 ACS data
🏛️ Assistant: 2020 ACS data is a good choice. Should I use the 5-year estimates for better coverage?

👤 User: Generate the mapping-ready code
🏛️ Assistant: I'll generate the pytidycensus code for you now.

📋 Final State: geography=county, variables=['B19013_001'], state=WI, year=2020, geometry=True
```

**Generated Code:**
```python
import pytidycensus as tc

# Get Census data (wide format with cleaned variable names)
data = tc.get_acs(
    geography="county",
    variables=["B19013_001E"],
    state="WI",
    year=2020,
    output="wide",
    geometry=True,
    api_key=census_api_key
)

print(data.head())

# Ready for mapping with GeoPandas
data.plot(column='B19013_001', legend=True)
```

**Result:** GeoPandas GeoDataFrame ready for mapping with clean column name `B19013_001`

## Documentation

Full documentation is available at: [https://mmann1123.github.io/pytidycensus/](https://mmann1123.github.io/pytidycensus/)

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
Michael Mann. (2025). mmann1123/pytidycensus: Pulling_dats (v0.1.1). Zenodo. https://doi.org/10.5281/zenodo.17127531
```

```bibtex
@software{michael_mann_2025_17127531,
  author       = {Michael Mann},
  title        = {mmann1123/pytidycensus: Pulling\_dats},
  month        = sep,
  year         = 2025,
  publisher    = {Zenodo},
  version      = {v0.1.1},
  doi          = {10.5281/zenodo.17127531},
  url          = {https://doi.org/10.5281/zenodo.17127531},
  swhid        = {swh:1:dir:3b2349029a986051469f46880930526c33d2dac5
                   ;origin=https://doi.org/10.5281/zenodo.17127530;vi
                   sit=swh:1:snp:2ff62e0d63a7af64334553edefe8f76a906d
                   c93f;anchor=swh:1:rel:ad19678c36a258e13eee43c8f5fa
                   5ff2d9e4047f;path=mmann1123-pytidycensus-27d849c
                  },
}
```

[![GWU Geography & Environment](docs/static/GWU_GE.png)](https://geography.columbian.gwu.edu/)
