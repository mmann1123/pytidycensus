---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Time Series Analysis with Census Data

This guide provides a quick introduction to analyzing demographic changes over time using pytidycensus. For complete tutorials with detailed examples, see:

- **Example 06**: Simple time series with stable geographies (states, counties)
- **Example 07**: Advanced time series with changing boundaries (tracts, block groups)
- **Example 10**: Interactive 3D visualization of time series data

## The Golden Rule

**CRITICAL**: Only compare surveys of the same type and duration:

- **ACS 5-year ↔ ACS 5-year**: Most stable, available for all areas
- **ACS 1-year ↔ ACS 1-year**: Recent trends for large areas only
- **Decennial ↔ Decennial**: Complete counts every 10 years

Never mix survey types (e.g., don't compare ACS 1-year with ACS 5-year or with Decennial Census).

## Quick Example 1: Simple Comparison (Stable Geographies)

For stable geographies like states or counties that don't change boundaries, time series analysis is straightforward:

```python
import pytidycensus as tc
import pandas as pd

# Get median household income for multiple years
income_2015 = tc.get_acs(
    geography="state",
    variables={"median_income": "B19013_001E"},
    state=["CA", "NY", "TX"],
    year=2015,
    survey="acs5"
)

income_2022 = tc.get_acs(
    geography="state",
    variables={"median_income": "B19013_001E"},
    state=["CA", "NY", "TX"],
    year=2022,
    survey="acs5"
)

# Merge and calculate change
comparison = pd.merge(
    income_2015[['NAME', 'median_income']].rename(columns={'median_income': '2015'}),
    income_2022[['NAME', 'median_income']].rename(columns={'median_income': '2022'}),
    on='NAME'
)
comparison['change'] = comparison['2022'] - comparison['2015']
comparison['pct_change'] = (comparison['change'] / comparison['2015']) * 100
```

See **Example 06** in the examples folder for a complete tutorial on simple time series analysis.

## Quick Example 2: Advanced Analysis (Changing Boundaries)

When census tract or block group boundaries change over time, pytidycensus can automatically handle this with area interpolation:

```python
from pytidycensus.time_series import get_time_series, compare_time_periods

# Automatically interpolate data across changing boundaries
dc_data = tc.get_time_series(
    geography="tract",
    variables={"total_pop": "B01003_001E"},
    years=[2012, 2022],
    dataset="acs5",
    state="DC",
    base_year=2022,  # Use 2022 boundaries as reference
    extensive_variables=["total_pop"],
    geometry=True
)

# Compare time periods with built-in functions
comparison = tc.compare_time_periods(
    data=dc_data,
    base_period=2012,
    comparison_period=2022,
    variables=["total_pop"],
    calculate_change=True,
    calculate_percent_change=True
)
```

The `get_time_series()` function automatically:

- Detects boundary changes between years
- Performs area-weighted interpolation
- Preserves population totals
- Returns data on consistent boundaries for easy comparison

See **Example 07** in the examples folder for a complete tutorial on advanced time series analysis with changing boundaries.

## Key Concepts

### Survey Types Matter

| Survey | Duration | Best For |
|--------|----------|----------|
| **ACS 5-year** | 60-month average | Small geographies, stable trends |
| **ACS 1-year** | 12-month estimate | Large areas (65k+ pop), recent data |
| **Decennial** | Complete count | Decade comparisons, benchmarking |

### Variable Types

- **Extensive variables** (counts): Population, households, housing units
  - Use area-weighted sums for interpolation
- **Intensive variables** (rates): Percentages, densities, median income
  - Use area-weighted averages for interpolation

### Boundary Changes

- **States/Counties**: Boundaries rarely change - simple comparison works
- **Tracts/Block Groups**: Boundaries change regularly - need interpolation
- **ZIP codes**: Not recommended for time series (unstable boundaries)

## Installation

```bash
# For time series with automatic boundary handling
pip install pytidycensus[time]

# Basic pytidycensus (manual comparison only)
pip install pytidycensus
```

## Complete Examples

For step-by-step tutorials with visualizations and detailed explanations:

- **examples/06_simple_time_series_tutorial.ipynb**: Basic time series with stable geographies
- **examples/07_advanced_time_series_tutorial.ipynb**: Advanced analysis with changing boundaries
- **examples/10_interactive_3d_time_series.ipynb**: Interactive 3D visualization of time series data

These tutorials cover:

- Data collection and preparation
- Handling variable code changes across years
- Visualization techniques
- Statistical analysis
- Best practices and common pitfalls
