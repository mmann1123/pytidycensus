# Getting Started

This guide will help you get started with pytidycensus, a Python library for accessing US Census data.

## Installation

Install pytidycensus using pip:

```bash
pip install pytidycensus
```

For development installation:

```bash
git clone https://github.com/walkerke/tidycensus
cd tidycensus/pytidycensus
pip install -e .
```

## Census API Key

To use pytidycensus, you need a free API key from the US Census Bureau:

1. Visit https://api.census.gov/data/key_signup.html
2. Fill out the form to request an API key
3. Check your email for the API key

Once you have your key, set it in Python:

```python
import pytidycensus as tc
tc.set_census_api_key("your_api_key_here")
```

Alternatively, you can set it as an environment variable:

```bash
export CENSUS_API_KEY="your_api_key_here"
```

## Basic Usage

### Getting ACS Data

The American Community Survey (ACS) is the most commonly used Census dataset:

```python
import pytidycensus as tc

# Get median household income by state
income_data = tc.get_acs(
    geography="state",
    variables="B19013_001",
    year=2022
)

print(income_data.head())
```

### Adding Geography

To include geographic boundaries for mapping:

```python
# Get data with geometry
income_geo = tc.get_acs(
    geography="state",
    variables="B19013_001", 
    year=2022,
    geometry=True
)

# Now you can map it
income_geo.plot(column='value', legend=True)
```

### Multiple Variables

You can request multiple variables at once:

```python
# Get population and median income
demo_data = tc.get_acs(
    geography="county",
    variables=["B01003_001", "B19013_001"],  # Population, Median Income
    state="CA",
    year=2022
)
```

### Searching for Variables

Find variables by searching their descriptions:

```python
# Search for income-related variables
income_vars = tc.search_variables("income", 2022, "acs", "acs5")
print(income_vars[['name', 'label']].head(10))
```

## Data Formats

### Tidy Format (Default)

By default, data is returned in "tidy" format where each row represents one geography-variable combination:

```python
data = tc.get_acs(
    geography="state",
    variables=["B01003_001", "B19013_001"],
    output="tidy"  # This is the default
)
# Result: One row per state-variable combination
```

### Wide Format

You can also get data in "wide" format where each row represents one geography:

```python
data = tc.get_acs(
    geography="state",
    variables=["B01003_001", "B19013_001"],
    output="wide"
)
# Result: One row per state, variables as columns
```

## Geographic Levels

pytidycensus supports many geographic levels:

- `"us"` - United States
- `"region"` - Census regions
- `"division"` - Census divisions  
- `"state"` - States
- `"county"` - Counties
- `"tract"` - Census tracts
- `"block group"` - Block groups
- `"place"` - Places/cities
- `"zcta"` - ZIP Code Tabulation Areas

### Geographic Filtering

Filter data to specific geographies:

```python
# County data for Texas only
tx_counties = tc.get_acs(
    geography="county",
    variables="B01003_001",
    state="TX"
)

# Tract data for Harris County, Texas
harris_tracts = tc.get_acs(
    geography="tract", 
    variables="B01003_001",
    state="TX",
    county="201"  # Harris County FIPS code
)
```
We have implemented a county name lookup, so you can also use:

```python
    county="Harris County"  # instead of FIPS code
```

## Survey Types

The ACS has different survey periods:

- `"acs5"` - 5-year estimates (default, more reliable for small areas)
- `"acs1"` - 1-year estimates (more current, less reliable for small areas)

```python
# Get 1-year ACS data
current_data = tc.get_acs(
    geography="state",
    variables="B01003_001",
    survey="acs1",
    year=2022
)
```

## Margin of Error

ACS data includes margins of error. These are automatically included:

```python
data = tc.get_acs(
    geography="state",
    variables="B19013_001"
)

# The result includes both estimate and margin of error
print(data.columns)
# ['GEOID', 'NAME', 'variable', 'value', 'B19013_001_moe']
```

## Population Estimates Program

The Population Estimates Program provides annual population estimates and demographic characteristics. For years 2020 and later, pytidycensus retrieves data from CSV files; for earlier years (2015-2019), it uses the Census API.

### Basic Population Estimates

```python
# Get total population by state for 2022
state_pop = tc.get_estimates(
    geography="state",
    variables="POP", 
    vintage=2022
)
```

### Components of Population Change

```python
# Get births, deaths, and migration data
components = tc.get_estimates(
    geography="state",
    variables=["BIRTHS", "DEATHS", "DOMESTICMIG", "INTERNATIONALMIG"],
    vintage=2022
)
```

### Demographic Breakdowns

Use the `breakdown` parameter to get population estimates by demographics:

```python
# Population by sex and race
demographics = tc.get_estimates(
    geography="state",
    variables="POP",
    breakdown=["SEX", "RACE"],
    breakdown_labels=True,  # Include human-readable labels
    year=2022
)
```

### Geographic Levels

Population estimates support multiple geographies:

```python
# County-level data for Texas
tx_counties = tc.get_estimates(
    geography="county",
    variables="POP",
    state="TX",
    year=2022
)

# Metro areas (CBSAs)
metros = tc.get_estimates(
    geography="cbsa", 
    variables="POP",
    year=2022
)
```

### Time Series Data

Get population estimates across multiple years:

```python
# Time series for states from 2020-2023
time_series = tc.get_estimates(
    geography="state",
    variables="POP",
    time_series=True,
    vintage=2023
)
```

### Data Products

Use the `product` parameter to specify the type of data:

```python
# Basic population totals (default)
population = tc.get_estimates(
    geography="state",
    product="population",  # or omit for default
    variables="POP",
    year=2022
)

# Components of population change
components = tc.get_estimates(
    geography="state", 
    product="components",
    variables=["BIRTHS", "DEATHS"],
    year=2022
)

# Population characteristics by demographics
characteristics = tc.get_estimates(
    geography="state",
    product="characteristics",
    variables="POP",
    breakdown=["SEX"],
    year=2022
)
```

## Advanced Time Series Analysis

pytidycensus provides powerful time series functionality for analyzing demographic changes over time with automatic handling of changing geographic boundaries.

### Installation for Time Series

```bash
# Install with time series support (includes tobler for area interpolation)
pip install pytidycensus[time]
```

### Basic Time Series Analysis

The `get_time_series()` function automatically handles boundary changes and variable differences across years:

```python
# ACS time series with automatic boundary handling
data = tc.get_time_series(
    geography="tract",
    variables={"total_pop": "B01003_001E", "median_income": "B19013_001E"},
    years=[2015, 2020],
    dataset="acs5",
    state="DC",
    base_year=2020,  # Use 2020 boundaries as reference
    extensive_variables=["total_pop"],      # Counts/totals
    intensive_variables=["median_income"],  # Rates/medians
    geometry=True,
    output="wide"
)
```

### Decennial Census Time Series

Handle different variable codes across decennial years:

```python
# Different variable codes for different years
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
    extensive_variables=["total_pop"]
)
```

### Time Period Comparisons

Use `compare_time_periods()` for detailed change analysis:

```python
# Systematic comparison between time periods
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

- **Automatic Area Interpolation**: Handles changing tract boundaries using tobler
- **Variable Classification**: Distinguishes between extensive (counts) and intensive (rates) variables
- **Built-in Validation**: Checks interpolation accuracy and data conservation
- **Flexible Output**: Wide format (multi-index columns) or tidy format (long form)
- **Multiple Datasets**: Support for both ACS and Decennial Census

### Geographic Boundary Handling

- **Stable Geographies** (state, county): No interpolation needed
- **Changing Geographies** (tract, block group): Automatic area interpolation
- **Base Year Selection**: Choose which year's boundaries to use as reference

### Example: County-Level Analysis (Stable Boundaries)

```python
# For stable geographies, interpolation is automatically skipped
county_data = tc.get_time_series(
    geography="county",
    variables={"total_pop": "B01003_001E", "median_income": "B19013_001E"},
    years=[2018, 2022],
    dataset="acs5",
    state="CA",
    geometry=False  # Faster for summary statistics
)

comparison = tc.compare_time_periods(
    data=county_data,
    base_period=2018,
    comparison_period=2022,
    variables=["total_pop", "median_income"]
)
```

For detailed examples and advanced techniques, see the [Time Series Analysis Tutorial](time_series_analysis.md).

## Next Steps

- Explore comprehensive [Jupyter notebook examples](examples.rst)
- Check the [API reference](api/modules.rst) for detailed function documentation
- Visit the [GitHub repository](https://github.com/mmann1123/pytidycensus) for the latest updates

## Come study with us at The George Washington University

![GWU Geography & Environment](static/GWU_GE.png)