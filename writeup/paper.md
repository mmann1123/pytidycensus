---
title: 'pytidycensus: Simplified Access to US Census Data in Python with Spatial and Temporal Analysis'
tags:
  - Python
  - Census
  - Demographics
  - Spatial Analysis
  - Time Series
  - Geographic Data
  - American Community Survey
authors:
  - name: Michael Mann
    orcid: 0000-0002-6268-6867
    affiliation: 1
  - name: Kyle Walker
    affiliation: 2
affiliations:
 - name: Department of Geography & Environment, The George Washington University, USA
   index: 1
 - name: Texas Christian University, USA
   index: 2
date: 14 November 2024
bibliography: paper.bib
---

# Summary

`pytidycensus` is a Python library that provides streamlined access to the US Census Bureau's Application Programming Interface (API), enabling researchers to retrieve demographic and geographic data from the American Community Survey (ACS), Decennial Census, Population Estimates Program, and Migration Flows datasets. As a port of the widely-used R package `tidycensus` [@walker2023tidycensus], `pytidycensus` integrates seamlessly with the Python scientific computing ecosystem, returning data as pandas DataFrames [@mckinney2010pandas] or GeoPandas GeoDataFrames [@jordahl2020geopandas]. Beyond replicating core functionality, `pytidycensus` introduces several innovations including a large language model (LLM)-powered assistant for natural language variable discovery, sophisticated time series analysis with automatic area interpolation for changing census tract boundaries, and interactive migration flow visualization tools.

# Statement of Need

Researchers in demography, urban planning, public health, and social sciences frequently require access to US Census Bureau data for spatial and temporal analyses. While the Census Bureau provides comprehensive APIs [@uscensus2024api], navigating the complex hierarchy of geographic levels, variable codes, and survey products presents significant barriers to efficient data retrieval. In the Python ecosystem, existing packages such as `cenpy` [@bell2022cenpy] and `censusdis` [@horvath2024censusdis] offer programmatic access to Census data but lack the user-friendly interface and integrated spatial capabilities that have made R's `tidycensus` [@walker2023tidycensus] the de facto standard for Census data access in the R community.

`pytidycensus` addresses this gap by implementing the intuitive API design of `tidycensus` while introducing Python-specific enhancements. The package implements approximately 50% of `tidycensus`'s exported functions, focusing on the most commonly used Census datasets: `get_acs()` for American Community Survey data [@uscensus2024acs], `get_decennial()` for decennial census data, `get_estimates()` for Population Estimates Program data, and `get_flows()` for migration flows. While Public Use Microdata Sample (PUMS) support via `get_pums()` and derived margin-of-error calculation functions (`moe_sum()`, `moe_ratio()`, etc.) are not yet implemented, `pytidycensus` provides substantial functionality for the vast majority of Census data use cases.

The package introduces three key innovations not present in the R version. First, an LLM-powered conversational assistant [@openai2024api; @ollama2024] allows users to discover Census variables through natural language queries rather than browsing thousands of variable codes. Second, the `get_time_series()` function automates the complex process of analyzing demographic change across time periods with shifting census tract boundaries by performing area-weighted interpolation using the `tobler` library [@knaap2020tobler]. Third, interactive flow mapping capabilities enable researchers to explore migration patterns through modern web-based visualization tools. These innovations make Census data more accessible to researchers while maintaining compatibility with the broader scientific Python ecosystem including NumPy [@varoquaux2015numpy], pandas [@mckinney2010pandas], and GeoPandas [@jordahl2020geopandas].

# Key Features

## Core Data Retrieval

The primary functions in `pytidycensus` mirror the `tidycensus` API while leveraging Python idioms. For example, retrieving median household income by county with geographic boundaries requires just a few lines of code:

```python
from pytidycensus import get_acs, get_time_series

census = Census(api_key="YOUR_KEY")

# Get median household income for DC-area counties
income = get_acs(
    geography="county",
    variables="B19013_001E",
    state="MD",
    geometry=True,
    year=2022
)
```

This returns a GeoPandas GeoDataFrame with both attribute data and polygon geometries, ready for spatial analysis or mapping. The function supports all Census geographic levels from blocks to states, handles both wide and tidy output formats, and automatically retrieves margins of error with adjustable confidence levels (90%, 95%, 99%).

The `get_acs()` function supports multiple table types including detailed tables (B/C prefixes), Data Profiles (DP), Subject tables (S), and Comparison Profiles (CP) across both 1-year and 5-year ACS products. Similarly, `get_decennial()` provides access to multiple summary files (PL, SF1, DHC, DP, DDHCA) for the 2000, 2010, and 2020 censuses. The `get_estimates()` function retrieves annual population estimates with demographic breakdowns, while `get_flows()` accesses county-to-county migration data with optional demographic characteristics.

## Spatial Integration

By integrating with GeoPandas [@jordahl2020geopandas] and `pygris` [@walker2024pygris] for geographic boundary retrieval, `pytidycensus` enables seamless spatial analysis workflows. Users can combine demographic data with geographic boundaries in a single function call, eliminating the need for manual shapefile downloads and spatial joins.

## Time Series with Boundary Interpolation

Analyzing demographic change over time is complicated by the fact that census tract boundaries change between decennial censuses. The `get_time_series()` function addresses this challenge by automatically performing area-weighted interpolation to normalize historical data to current boundaries:

```python
# Compare poverty rates from 2010 to 2020 with consistent boundaries
dc_data = get_time_series(
    geography="tract",
    variables={
        "total_pop": "B01003_001E",      # Total population
        "poverty_count": "B17001_002E",  # Population below poverty line
        "poverty_total": "B17001_001E"   # Total for poverty calculation
    },
    years=[2015, 2020],
    dataset="acs5",
    state="DC",
    base_year=2020,  # Use 2020 boundaries for all years
    extensive_variables=["total_pop", "poverty_count", "poverty_total"],  # All are counts
    geometry=True,
    output="wide"
)
```

This function uses the `tobler` library [@knaap2020tobler] to perform extensive-to-extensive interpolation, properly accounting for the areal redistribution of count data across changing boundaries. Built-in validation ensures conservation of totals and proper handling of intensive (%) versus extensive (count) variables.

The `get_time_series()` function requires users to specify which variables are extensive through the `extensive_variables` parameter. All variables not designated as extensive are treated as intensive and excluded from interpolation calculations, preventing mathematically invalid operations. This design ensures that derived rates and percentages are correctly calculated from properly interpolated count data, maintaining the statistical integrity of temporal comparisons across changing geographic boundaries.

## LLM-Powered Variable Discovery

Discovering the correct variable codes among the thousands available in Census products is a common pain point. The integrated LLM assistant provides a conversational interface for variable discovery and suggests complete `pytidycensus` query code. Users can run the CLI with their API keys from the terminal:

```bash
python -m pytidycensus.llm_interface.cli --census-key YOUR_CENSUS_KEY --openai-key YOUR_OPENAI_KEY
```

Then type a request to receive both variable recommendations and ready-to-use code:

```text
📊 You: Get median income by county in Texas

🤔 Thinking...

🏛️  Assistant: To analyze the median income by county in Texas, we will use the `get_acs()`
function from pytidycensus to retrieve the necessary data. We will specifically request
the median household income variable (`B19013_001E`) along with the total number of
households (`B19001_001E`) to ensure proper normalization.

Here's the code example to get the median income by county in Texas for the most recent
available year:
```

```python
from pytidycensus import get_acs

income_data = get_acs(
    geography="county",
    variables=["B19013_001E","B19001_001E"],
    state="TX",
    year=2022
)
```

The assistant understands natural language queries, suggests relevant variables, and generates complete code examples. It supports both cloud-based models via OpenAI [@openai2024api] and local models via Ollama [@ollama2024], with typical conversations costing less than $0.01.

# Software Architecture

`pytidycensus` follows a modular architecture with separate modules for each Census dataset (ACS, Decennial, Estimates, Flows) and supporting functionality (geography, variable caching, LLM interface). Core dependencies include pandas [@mckinney2010pandas] for tabular data, GeoPandas [@jordahl2020geopandas] for spatial data, `pygris` [@walker2024pygris] for boundary retrieval, and `tobler` [@knaap2020tobler] for spatial interpolation. The LLM interface is an optional component requiring OpenAI or Ollama API access.

The package employs a comprehensive caching system to minimize redundant API calls, stores variable metadata locally for faster lookups, and provides detailed error messages to guide users when geographic level or dataset combinations are unsupported. Extensive unit and integration tests ensure reliability across different Census products and geographic configurations.

# Example Application

A typical research workflow might involve analyzing gentrification patterns through temporal changes in educational attainment. Using `pytidycensus`, a researcher can retrieve bachelor's degree attainment rates for census tracts in a city across multiple years, automatically handle boundary changes through area interpolation, join the results with tract geometries, and produce choropleth maps showing educational change—all within a few dozen lines of Python code. The resulting GeoPandas GeoDataFrames integrate seamlessly with visualization libraries like matplotlib, seaborn, and plotly, as well as spatial analysis tools in the PySAL ecosystem.

# Acknowledgements

We acknowledge Kyle Walker for creating the original `tidycensus` R package and for his contributions to accessible Census data tooling through `pygris` and related projects. We thank the US Census Bureau for providing comprehensive public APIs and documentation. Development of the time series interpolation functionality builds upon the spatial interpolation methods implemented in the `tobler` library by the PySAL developers.

# References
