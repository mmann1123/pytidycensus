# %% [markdown]
# # Other Census Bureau datasets
#
# [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mmann1123/pytidycensus/blob/main/examples/04_other_datasets.ipynb)
#
# ## Population Estimates Program (PEP)
#
#   - Purpose: Provides annual population estimates between decennial censuses
#   - Frequency: Updated annually
#   - Geographic Coverage: US, regions, divisions, states, counties, metro areas, places
#   - Time Range: 2010-present (function supports 2015+)
#
#
# ### Specific Datasets Within PEP
#
#   1. Population Totals (product=`"population"`)
#     - Basic population counts by geography
#     - Annual estimates for intercensal years
#   2. Components of Change (product=`"components"`)
#     - Births, deaths, migration flows
#     - Natural change calculations
#     - Domestic and international migration
#   3. Population Characteristics (product=`"characteristics"`)
#     - Demographics by Age, Sex, Race, Hispanic Origin (ASRH)
#     - Population breakdowns by key demographic categories
#
#
# ### Key Parameters
# - **`product`**: "population", "components", "characteristics"
# - **`variables`**: "POP", "BIRTHS", "DEATHS", migration variables, rates
# - **`breakdown`**: ["SEX", "RACE", "ORIGIN", "AGEGROUP"] for demographics
# - **`vintage`**: Dataset version (e.g., 2024 for most recent)
# - **`year`**: Specific data year (defaults to vintage)
# - **`time_series`**: Get multi-year data
# - **`geometry`**: Add geographic boundaries
# - **`output`**: "tidy" (default) or "wide" format
#
# ### Data Sources
# - **2020+**: CSV files from Census Bureau FTP servers
# - **2015-2019**: Census API (requires API key)
# - **Automatic handling**: No user intervention needed
#
# ### Geographic Support
# All major Census geographies: US, regions, divisions, states, counties, CBSAs, CSAs, places

# %% [markdown]
# ## Mapping Migration Estimates
#
# Let's create a map of net migration rates:
#
# ### Census API Key
#
# To use pytidycensus, you need a free API key from the US Census Bureau. Get one at: https://api.census.gov/data/key_signup.html
#

# %%
import pytidycensus as tc
import pandas as pd
import matplotlib.pyplot as plt

tc.set_census_api_key("YOUR API KEY GOES HERE")


# %% [markdown]
# Ignore the next cell. It is just to show how users can load their credentials using the new utility function.

# %%
import os

# Try to get API key from environment
api_key = os.environ.get("CENSUS_API_KEY")

# For documentation builds without a key, we'll mock the responses
try:
    tc.set_census_api_key(api_key)
    print("Using Census API key from environment")
except Exception:
    print("Using example API key for documentation")
    # This won't make real API calls during documentation builds
    tc.set_census_api_key("EXAMPLE_API_KEY_FOR_DOCS")

# %% [markdown]
# ## Product Types and Variables
#
# The `get_estimates()` function supports three main products:
#
# 1. **population** (default) - Basic population totals
# 2. **components** - Components of population change
# 3. **characteristics** - Population by demographics
#
# ### Available Variables
#
# Common variables include:
# - **POP**: Total population
# - **BIRTHS**: Births
# - **DEATHS**: Deaths
# - **DOMESTICMIG**: Domestic migration
# - **INTERNATIONALMIG**: International migration
# - **NETMIG**: Net migration
# - **NATURALCHG**: Natural change (births - deaths)
# - **RNETMIG**: Net migration rate

# %%

# Get county data with geometry for mapping
counties_geo = tc.get_estimates(
    geography="county",
    variables="RNETMIG",  # Net migration rate
    year=2022,
    geometry=True,
    state=["CA", "NV", "AZ"],  # Western states
)

print("County data with geometry:", counties_geo.shape)
print("Data types:", type(counties_geo))
counties_geo.head(3)

# %% [markdown]
# ## Mapping with Geometry
#
# Because we set `geometry=True`, the returned GeoDataFrame includes geometry data for mapping.

# %%
# Create a map of net migration rates
fig, ax = plt.subplots(figsize=(15, 10))

# Create migration categories for better visualization
counties_geo["migration_category"] = pd.cut(
    counties_geo["RNETMIG2022"],
    bins=[-float("inf"), -10, -5, 5, 10, float("inf")],
    labels=[
        "High Out-migration",
        "Moderate Out-migration",
        "Stable",
        "Moderate In-migration",
        "High In-migration",
    ],
)

# Plot the map
counties_geo.plot(
    column="migration_category",
    legend=True,
    ax=ax,
    cmap="RdYlBu",
    edgecolor="white",
    linewidth=0.1,
)

ax.set_title("Net Migration Rates by County: Western States (2022)", fontsize=16)
ax.set_axis_off()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Geographic Levels
#
# Population estimates support multiple geographic levels beyond states:

# %%
# Metropolitan areas (CBSAs)
metros = tc.get_estimates(geography="cbsa", variables="POP", year=2022)

print(f"Metro areas: {metros.shape[0]} CBSAs")
print("Largest metropolitan areas:")
metros_largest = metros.nlargest(10, "POPESTIMATE2022")
print(metros_largest[["NAME", "POPESTIMATE2022"]])

# %%
# County-level data for Texas
tx_counties = tc.get_estimates(
    geography="county", variables="POP", state="TX", year=2022
)

print(f"Texas counties: {tx_counties.shape[0]} counties")
print("Largest Texas counties by population:")
tx_largest = tx_counties.nlargest(10, "POPESTIMATE2022")
print(tx_largest[["NAME", "POPESTIMATE2022"]])

# %%
# Get time series data for select states
time_series_states = tc.get_estimates(
    geography="state",
    variables="POP",
    time_series=True,
    vintage=2023,  # Use 2023 vintage for data through 2023
    state=["CA", "TX", "FL", "NY"],  # Focus on large states
)

print("Time series data shape:", time_series_states.shape)
print("Years available:", sorted(time_series_states["year"].unique()))
time_series_states.head(10)

# %%
# Plot population trends
plt.figure(figsize=(12, 8))

for state in time_series_states["NAME"].unique():
    state_data = time_series_states[time_series_states["NAME"] == state]
    plt.plot(
        state_data["year"], state_data["estimate"], marker="o", linewidth=2, label=state
    )

plt.title("Population Trends: Large States (2020-2023)", fontsize=16)
plt.xlabel("Year", fontsize=12)
plt.ylabel("Population", fontsize=12)
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# %%


# %% [markdown]
# ## Basic Population Estimates
#
# Let's start with basic population estimates by state:

# %%
# Get population estimates for US states
us_pop_estimates = tc.get_estimates(geography="state", variables="POP", year=2022)

print(f"Shape: {us_pop_estimates.shape}")
print("Data format:", us_pop_estimates.columns.tolist())
us_pop_estimates.head()

# %%
# Get components of population change
us_components = tc.get_estimates(
    geography="state",
    product="components",  # Specify components product
    variables=["BIRTHS", "DEATHS", "DOMESTICMIG", "INTERNATIONALMIG"],
    year=2022,
    output="tidy",  # Tidy format for easier analysis
)

print("Components data shape:", us_components.shape)
print("Variables available:", us_components["variable"].unique())
us_components.head(10)

# %% [markdown]
# ## Demographic Breakdowns
#
# One of the most powerful features is demographic breakdowns using the `breakdown` parameter. This accesses the Age, Sex, Race, Hispanic Origin (ASRH) datasets:

# %%
# Get population by sex for all states
pop_by_sex = tc.get_estimates(
    geography="state",
    variables="POP",
    breakdown=["SEX"],
    breakdown_labels=True,  # Include human-readable labels
    year=2022,
)

print("Population by sex data:")
print(pop_by_sex.head(10))

# Check the breakdown categories
if "SEX_label" in pop_by_sex.columns:
    print("\nSex categories:", pop_by_sex["SEX_label"].unique())

# %%
