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

## Next Steps

- Explore comprehensive [Jupyter notebook examples](examples.rst)
- Check the [API reference](api/modules.rst) for detailed function documentation
- Visit the [GitHub repository](https://github.com/mmann1123/pytidycensus) for the latest updates