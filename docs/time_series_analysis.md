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

This tutorial demonstrates how to conduct time series analysis using US Census data, with a focus on comparing decennial census years and handling changing geographic boundaries over time.

## Overview

Time series analysis with Census data requires careful attention to:
1. **Data consistency** - comparing like-with-like across survey types
2. **Boundary changes** - census tracts and other geographies change over time
3. **Variable definitions** - ensuring variables measure the same concepts across years

## Survey Types and Temporal Comparability

### Rule 1: Compare Like Survey Types

**IMPORTANT**: Only compare surveys of the same type and duration:

- **ACS 1-year ↔ ACS 1-year**: For large areas (65,000+ population) with high temporal precision
- **ACS 3-year ↔ ACS 3-year**: Legacy surveys (discontinued after 2013)
- **ACS 5-year ↔ ACS 5-year**: For all areas, most stable estimates
- **Decennial ↔ Decennial**: Every 10 years, complete population count

### Why This Matters

```python
# ❌ WRONG: Don't mix survey types
# This compares a 1-year snapshot to a 5-year average
acs1_2019 = tc.get_acs(geography="state", variables=["B19013_001E"], year=2019, survey="acs1")
acs5_2019 = tc.get_acs(geography="state", variables=["B19013_001E"], year=2019, survey="acs5")

# ✅ CORRECT: Compare same survey types across years
acs5_2015 = tc.get_acs(geography="state", variables=["B19013_001E"], year=2015, survey="acs5")
acs5_2020 = tc.get_acs(geography="state", variables=["B19013_001E"], year=2020, survey="acs5")
```

### Survey Characteristics

| Survey Type | Coverage | Sample Size | Margin of Error | Best For |
|-------------|----------|-------------|-----------------|----------|
| **Decennial** | Complete count | All households | Very low | Decade comparisons, small areas |
| **ACS 5-year** | Sample survey | ~3.5M addresses/year | Lower | Small geographies, stable trends |
| **ACS 1-year** | Sample survey | ~3.5M addresses | Higher | Large areas, recent estimates |

## Case Study: DC Population and Poverty Changes (2010-2020)

Let's analyze how Washington DC's population and poverty patterns changed between the 2010 and 2020 decennial censuses, using pytidycensus's built-in time series functionality that automatically handles boundary changes.

### Step 1: Load Required Libraries

```{code-cell} ipython3
import pytidycensus as tc
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# The time series functionality includes automatic area interpolation
# Install with: pip install pytidycensus[time]
try:
    from pytidycensus.time_series import get_time_series, compare_time_periods
    print("✅ Time series functionality available")
except ImportError:
    print("⚠️ Install time series support: pip install pytidycensus[time]")

# Set your Census API key
# tc.set_census_api_key("YOUR_API_KEY_HERE")
```

```{code-cell} ipython3
:tags: ["hide-cell"]
# ignore this, I am just reading in my api key privately
# Read API key from environment variable (for GitHub Actions)
import os
import pytidycensus as tc

# Try to get API key from environment 
api_key = os.environ.get('CENSUS_API_KEY')

# For documentation builds without a key, we'll mock the responses
try:
    tc.set_census_api_key(api_key)
    print("Using Census API key from environment")
except Exception:
    print("Using example API key for documentation")
    # This won't make real API calls during documentation builds
    tc.set_census_api_key("EXAMPLE_API_KEY_FOR_DOCS")
```

**Note on Data Availability**: Some older Tiger/Line shapefiles may have broken download links. If you encounter 404 errors for 2010 geometries, you can:
1. Use ACS data instead (more reliable geometry downloads)
2. Download geometries manually from [Census Tiger/Line files](https://www2.census.gov/geo/tiger/)
3. Focus on geographic levels that haven't changed (counties, states)

### Step 2: Define Variables and Years for Analysis

For decennial census comparison, we need to specify different variable codes for different years:

```{code-cell} ipython3
# Define year-specific variable mappings for decennial census
# Variable codes changed between 2010 and 2020
variables = {
    2010: {"total_pop": "P001001"},    # 2010 decennial variable
    2020: {"total_pop": "P1_001N"}     # 2020 decennial variable
}

print("Variable mapping for decennial census time series:")
for year, var_dict in variables.items():
    print(f"  {year}: {var_dict}")
```

### Step 3: Get Decennial Time Series Data with Automatic Interpolation

```{code-cell} ipython3
# Use get_time_series for automatic boundary handling
dc_data = tc.get_time_series(
    geography="tract",
    variables=variables,  # Year-specific variable mapping
    years=[2010, 2020],
    dataset="decennial",
    state="DC",
    base_year=2020,  # Use 2020 boundaries as the reference
    extensive_variables=["total_pop"],  # Population is a count variable
    geometry=True,
    output="wide"
)

print(f"Time series data shape: {dc_data.shape}")
print(f"2010 Total Population (interpolated): {dc_data[(2010, 'total_pop')].sum():,}")
print(f"2020 Total Population: {dc_data[(2020, 'total_pop')].sum():,}")
print("\nSample of multi-index columns:")
print(dc_data.columns[:10].tolist())
```

### Step 4: Use compare_time_periods for Analysis

```{code-cell} ipython3
# Use the built-in comparison function for detailed analysis
dc_comparison = tc.compare_time_periods(
    data=dc_data,
    base_period=2010,
    comparison_period=2020,
    variables=["total_pop"],
    calculate_change=True,
    calculate_percent_change=True
)

print(f"Comparison data shape: {dc_comparison.shape}")
print(f"Available columns: {list(dc_comparison.columns)}")

# Summary statistics
total_change = dc_comparison['total_pop_change'].sum()
percent_change = (total_change / dc_comparison['total_pop_2010'].sum()) * 100

print(f"\nPopulation Change Summary (2010-2020):")
print(f"Total population change: {total_change:+,} people")
print(f"Overall percent change: {percent_change:+.1f}%")
print(f"Tracts with growth: {(dc_comparison['total_pop_change'] > 0).sum()}")
print(f"Tracts with decline: {(dc_comparison['total_pop_change'] < 0).sum()}")
```

### Step 5: Visualize Population Changes

The `get_time_series()` function automatically handled area interpolation. Now let's visualize the results:

```{code-cell} ipython3
# Create visualization of population changes
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 6))

# 2010 Population (interpolated to 2020 boundaries)
dc_comparison.plot(
    column='total_pop_2010',
    cmap='Blues',
    legend=True,
    ax=ax1,
    edgecolor='white',
    linewidth=0.5,
    legend_kwds={'label': 'Population', 'shrink': 0.8}
)
ax1.set_title('2010 Population\n(Interpolated to 2020 Boundaries)', fontsize=12)
ax1.axis('off')

# 2020 Population
dc_comparison.plot(
    column='total_pop_2020',
    cmap='Blues',
    legend=True,
    ax=ax2,
    edgecolor='white',
    linewidth=0.5,
    legend_kwds={'label': 'Population', 'shrink': 0.8}
)
ax2.set_title('2020 Population', fontsize=12)
ax2.axis('off')

# Population Change
dc_comparison.plot(
    column='total_pop_change',
    cmap='RdBu_r',
    legend=True,
    ax=ax3,
    edgecolor='white',
    linewidth=0.5,
    legend_kwds={'label': 'Change', 'shrink': 0.8}
)
ax3.set_title('Population Change\n(2010-2020)', fontsize=12)
ax3.axis('off')

plt.tight_layout()
plt.show()
```

### Step 6: ACS Poverty Analysis for Complementary Insights

Since poverty data isn't available in the decennial census, let's use ACS data with the new time series functionality:

```{code-cell} ipython3
# Get ACS poverty time series data (2012 vs 2020 for temporal separation)
acs_variables = {
    "total_pop": "B01003_001E",      # Total population
    "poverty_count": "B17001_002E",  # Population below poverty
    "poverty_total": "B17001_001E"   # Total for poverty calculation
}

dc_poverty_data = tc.get_time_series(
    geography="tract",
    variables=acs_variables,
    years=[2012, 2020],  # 2008-2012 ACS vs 2016-2020 ACS
    dataset="acs5",
    state="DC",
    base_year=2020,  # Use 2020 boundaries
    extensive_variables=["total_pop", "poverty_count", "poverty_total"],
    geometry=True,
    output="wide"
)

print(f"ACS time series data shape: {dc_poverty_data.shape}")
print(f"2012 Total Population (interpolated): {dc_poverty_data[(2012, 'total_pop')].sum():,}")
print(f"2020 Total Population: {dc_poverty_data[(2020, 'total_pop')].sum():,}")
```

```{code-cell} ipython3
# Calculate poverty rates and use compare_time_periods for analysis
# First calculate poverty rates for both years
dc_poverty_data['poverty_rate_2012'] = (dc_poverty_data[(2012, 'poverty_count')] /
                                        dc_poverty_data[(2012, 'poverty_total')] * 100)
dc_poverty_data['poverty_rate_2020'] = (dc_poverty_data[(2020, 'poverty_count')] /
                                        dc_poverty_data[(2020, 'poverty_total')] * 100)

# Add poverty rate columns to the multi-index structure
dc_poverty_data[(2012, 'poverty_rate')] = dc_poverty_data['poverty_rate_2012']
dc_poverty_data[(2020, 'poverty_rate')] = dc_poverty_data['poverty_rate_2020']

# Use compare_time_periods for detailed analysis
poverty_comparison = tc.compare_time_periods(
    data=dc_poverty_data,
    base_period=2012,
    comparison_period=2020,
    variables=["poverty_count", "poverty_rate"],
    calculate_change=True,
    calculate_percent_change=True
)

print("Poverty Analysis Summary (2012-2020):")
print(f"Average poverty rate change: {poverty_comparison['poverty_rate_change'].mean():.1f} percentage points")
print(f"Total poverty count change: {poverty_comparison['poverty_count_change'].sum():+,.0f}")
print(f"Tracts with decreasing poverty: {(poverty_comparison['poverty_rate_change'] < 0).sum()}")
print(f"Tracts with increasing poverty: {(poverty_comparison['poverty_rate_change'] > 0).sum()}")
```

```{code-cell} ipython3
# Create streamlined poverty visualization
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 6))

# 2012 poverty rates (interpolated)
poverty_comparison.plot(
    column='poverty_rate_2012',
    cmap='Reds',
    legend=True,
    ax=ax1,
    edgecolor='white',
    linewidth=0.3,
    vmin=0,
    vmax=40,
    legend_kwds={'label': 'Poverty Rate (%)', 'shrink': 0.8}
)
ax1.set_title('2012 Poverty Rate\n(Interpolated to 2020 Boundaries)', fontsize=12)
ax1.axis('off')

# 2020 poverty rates
poverty_comparison.plot(
    column='poverty_rate_2020',
    cmap='Reds',
    legend=True,
    ax=ax2,
    edgecolor='white',
    linewidth=0.3,
    vmin=0,
    vmax=40,
    legend_kwds={'label': 'Poverty Rate (%)', 'shrink': 0.8}
)
ax2.set_title('2020 Poverty Rate', fontsize=12)
ax2.axis('off')

# Poverty change
poverty_comparison.plot(
    column='poverty_rate_change',
    cmap='RdBu_r',
    legend=True,
    ax=ax3,
    edgecolor='white',
    linewidth=0.3,
    vmin=-15,
    vmax=15,
    legend_kwds={'label': 'Change (pp)', 'shrink': 0.8}
)
ax3.set_title('Poverty Rate Change\n2012-2020 (percentage points)', fontsize=12)
ax3.axis('off')

plt.tight_layout()
plt.show()
```

## Key Insights and Best Practices

### 1. Benefits of the New Time Series Functions

The `get_time_series()` and `compare_time_periods()` functions provide:
- **Automatic Area Interpolation**: Handles boundary changes transparently using tobler
- **Population Conservation**: Preserves total counts across boundary changes
- **Variable Classification**: Properly handles extensive (counts) vs intensive (rates) variables
- **Streamlined Analysis**: Reduces complex workflows to simple function calls
- **Built-in Validation**: Automatic checks for interpolation accuracy

### 2. Summary Results

```{code-cell} ipython3
# Summary of both analyses using the new streamlined approach
print("=== DECENNIAL POPULATION CHANGE (2010-2020) ===")
print(f"Total population change: {dc_comparison['total_pop_change'].sum():+,} people")
print(f"Overall percent change: {(dc_comparison['total_pop_change'].sum() / dc_comparison['total_pop_2010'].sum() * 100):+.1f}%")
print(f"Tracts with population growth: {(dc_comparison['total_pop_change'] > 0).sum()}")
print(f"Tracts with population decline: {(dc_comparison['total_pop_change'] < 0).sum()}")

print(f"\n=== ACS POVERTY RATE CHANGE (2012-2020) ===")
print(f"Average poverty rate change: {poverty_comparison['poverty_rate_change'].mean():+.1f} percentage points")
print(f"Total poverty count change: {poverty_comparison['poverty_count_change'].sum():+,.0f} people")
print(f"Tracts with poverty reduction: {(poverty_comparison['poverty_rate_change'] < 0).sum()}")
print(f"Tracts with poverty increase: {(poverty_comparison['poverty_rate_change'] > 0).sum()}")
```

### 3. Technical Considerations

**Coordinate Reference Systems:**
- Use projected CRS (like EPSG:3857) for accurate area calculations
- Transform back to geographic CRS (EPSG:4326) for mapping

**Variable Classification:**
- **Extensive variables**: Counts, totals (population, households) - use area-weighted sums
- **Intensive variables**: Rates, densities, percentages - use area-weighted averages

**Data Quality:**
- Functions automatically validate interpolation results
- Built-in checks for conservation of totals
- Handles edge cases (zero population, missing data)
- Clear warnings when issues are detected

### 3. Alternative Approaches for Stable Geographies

#### Simple County-Level Analysis (No Boundary Changes)

```{code-cell} ipython3
# For stable geographies, the new functions automatically skip interpolation
print("=== County-Level Analysis (No Interpolation Needed) ===")

county_data = tc.get_time_series(
    geography="county",
    variables={
        2010: {"total_pop": "P001001"},
        2020: {"total_pop": "P1_001N"}
    },
    years=[2010, 2020],
    dataset="decennial",
    state="DC",
    geometry=False  # Faster processing for summary stats
)

county_comparison = tc.compare_time_periods(
    data=county_data,
    base_period=2010,
    comparison_period=2020,
    variables=["total_pop"]
)

print(f"2010 population: {county_comparison['total_pop_2010'].iloc[0]:,}")
print(f"2020 population: {county_comparison['total_pop_2020'].iloc[0]:,}")
print(f"Change: {county_comparison['total_pop_change'].iloc[0]:+,}")
print(f"Percent change: {county_comparison['total_pop_pct_change'].iloc[0]:+.1f}%")
```

#### Multi-State Analysis for Pattern Detection

```{code-cell} ipython3
# Option 2: Compare multiple states to identify broader patterns
states = ["DC", "MD", "VA"]  # DC Metro area
state_changes = []

for state in states:
    try:
        pop_2010 = tc.get_decennial(
            geography="state",
            variables={"total_pop": "P001001"},
            state=state,
            year=2010
        )

        pop_2020 = tc.get_decennial(
            geography="state",
            variables={"total_pop": "P1_001N"},
            state=state,
            year=2020
        )

        change = pop_2020.iloc[0]['total_pop'] - pop_2010.iloc[0]['total_pop']
        pct_change = (change / pop_2010.iloc[0]['total_pop']) * 100

        state_changes.append({
            'State': pop_2010.iloc[0]['NAME'],
            'Pop_2010': pop_2010.iloc[0]['total_pop'],
            'Pop_2020': pop_2020.iloc[0]['total_pop'],
            'Change': change,
            'Pct_Change': pct_change
        })

    except Exception as e:
        print(f"Error processing {state}: {e}")

# Display results
if state_changes:
    df_changes = pd.DataFrame(state_changes)
    print("\nDC Metro Area Population Changes (2010-2020):")
    print(df_changes.to_string(index=False, formatters={
        'Pop_2010': '{:,}'.format,
        'Pop_2020': '{:,}'.format,
        'Change': '{:,}'.format,
        'Pct_Change': '{:.1f}%'.format
    }))
```

#### Using Census Relationship Files

```{code-cell} ipython3
# Option 3: Use crosswalk files (for advanced users)
print("Advanced Alternative: Census Bureau provides relationship files that map")
print("geographic changes between years:")
print("https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.html")
print()
print("These files provide precise allocation ratios for:")
print("- Block to block relationships")
print("- Tract to tract relationships")
print("- County subdivision changes")
print()
print("Benefits:")
print("- Official Census Bureau methodology")
print("- Precise allocation weights")
print("- No need for geometric calculations")
```

## Conclusion

The new `get_time_series()` and `compare_time_periods()` functions in pytidycensus dramatically simplify temporal Census analysis while maintaining analytical rigor:

### Key Advantages

1. **Simplified Workflow**: Complex multi-step processes reduced to single function calls
2. **Automatic Boundary Handling**: Built-in area interpolation using industry-standard methods
3. **Survey Consistency**: Ensures proper comparison of like survey types (ACS5↔ACS5, Decennial↔Decennial)
4. **Variable Intelligence**: Automatic classification and proper handling of extensive vs intensive variables
5. **Built-in Validation**: Automatic quality checks and conservation tests

### Best Practices with New Functions

- **Variable Classification**: Correctly specify `extensive_variables` (counts) and `intensive_variables` (rates)
- **Base Year Selection**: Choose the most appropriate year for reference boundaries
- **Survey Types**: Only compare like survey types across years
- **Geographic Stability**: Functions automatically detect when interpolation is/isn't needed

### Next Steps

- Explore time series with multiple variables (housing, education, employment)
- Apply to different geographic scales and regions
- Combine with statistical modeling for trend analysis
- Use results for policy evaluation and urban planning

### Installation

```bash
# For full time series functionality
pip install pytidycensus[time]

# This includes automatic area interpolation capabilities
```

The streamlined approach enables researchers to focus on analysis and interpretation rather than complex spatial data processing, while maintaining the highest standards of methodological rigor.