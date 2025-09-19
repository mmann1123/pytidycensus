# %% [markdown]
# # Basic usage of pytidycensus
#
# [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mmann1123/pytidycensus/blob/main/examples/01_basic_usage.ipynb)
#
# This notebook demonstrates the basic functionality of **pytidycensus**, a Python library for accessing US Census Bureau data with pandas and GeoPandas support.
#
# ## Setup
#
# First, let's install and import the necessary packages:

# %%
# Uncomment to install if running in Colab
# !pip install pytidycensus matplotlib

import pytidycensus as tc
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set styling
plt.style.use("default")
sns.set_palette("husl")

# %% [markdown]
# ## Census API Key
#
# To use pytidycensus, you need a free API key from the US Census Bureau. Get one at: https://api.census.gov/data/key_signup.html
#
# Set your API key:

# %%
# Replace with your actual API key
tc.set_census_api_key("Your API Key Here")

# # Alternatively, set as environment variable:
# import os
# os.environ['CENSUS_API_KEY'] = 'Your API Key Here'

# %% [markdown]
# Ignore this cell. I am just loading my credentials from a yaml file in the parent directory.

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
# ## Core Functions
#
# pytidycensus provides two main functions:
#
# - **`get_decennial()`**: Access to 2000, 2010, and 2020 decennial US Census APIs
# - **`get_acs()`**: Access to 1-year and 5-year American Community Survey APIs
#
# ### Example: Median Age by State (2020 Census)
#
# Let's look at median age by state from the 2020 Census:

# %%
# Get median age by state from 2020 Census
age_2020 = tc.get_decennial(
    geography="state",
    variables="P13_001N",  # Median age variable
    year=2020,
    sumfile="dhc",  # Demographic and Housing Characteristics file
)

print(f"Data shape: {age_2020.shape}")
age_2020.head()

# %% [markdown]
# The function returns a pandas DataFrame with four columns:
#
# - **`GEOID`**: Identifier for the geographical unit
# - **`NAME`**: Descriptive name of the geographical unit
# - **`variable`**: Census variable represented in the row
# - **`value`**: Value of the variable for that unit
#
# ### Visualizing the Data
#
# Since we have a tidy DataFrame, we can easily visualize it:

# %%
# Create a horizontal bar plot
plt.figure(figsize=(10, 12))

# Sort by median age and plot
age_sorted = age_2020.sort_values("estimate", ascending=True).reset_index(drop=True)
plt.barh(range(len(age_sorted)), age_sorted["estimate"])
plt.yticks(range(len(age_sorted)), age_sorted["state"])
plt.xlabel("Median Age (years)")
plt.title("Median Age by State (2020 Census)", fontsize=14, fontweight="bold")
plt.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Geography in pytidycensus
#
# pytidycensus supports many geographic levels. Here are the most commonly used:
#
# | Geography | Definition | Example Usage |
# |-----------|------------|---------------|
# | `"us"` | United States | National data |
# | `"state"` | State or equivalent | State-level data |
# | `"county"` | County or equivalent | County-level data |
# | `"tract"` | Census tract | Neighborhood-level data |
# | `"block group"` | Census block group | Sub-neighborhood data |
# | `"place"` | Census-designated place | City/town data |
# | `"zcta"` | ZIP Code Tabulation Area | ZIP code areas |
#
# ### Example: County Data
#
# Let's get population data for counties in Texas:

# %%
# Get total population for Texas counties
tx_pop = tc.get_decennial(
    geography="county",
    variables="P1_001N",  # Total population
    state="TX",  # Filter to Texas
    year=2020,
)

print(f"Number of Texas counties: {len(tx_pop)}")
tx_pop.head()

# %% [markdown]
# ## Searching for Variables
#
# The Census has thousands of variables. Use `load_variables()` to search for what you need:

# %%
# Load variables for 2022 5-year ACS
variables_2022 = tc.load_variables(2022, "acs", "acs5", cache=True)

print(f"Total variables available: {len(variables_2022)}")
variables_2022.head()

# %%
# Search for income-related variables
income_vars = tc.search_variables("median household income", 2022, "acs", "acs5")
print(f"Found {len(income_vars)} income-related variables")
income_vars[["name", "label"]].head(10)

# %% [markdown]
# ## Working with ACS Data
#
# American Community Survey (ACS) data includes estimates with margins of error, since it's based on a sample rather than a complete count.
#
# ### Example: Median Household Income
#
# Let's get median household income for Vermont counties:

# %%
# Get median household income for Vermont tracts
vt_income = tc.get_acs(
    geography="tract",
    variables={"medincome": "B19013_001"},  # Can use dictionary for variable names
    state="VT",
    year=2022,
    output="wide",  # Get data in wide format
)

vt_income

# %% [markdown]
# Notice that ACS data returns `estimate` and `moe` (margin of error) columns instead of a single `value` column.
#
# ### Visualizing Uncertainty
#
# We can visualize the uncertainty around estimates using error bars:

# %%
# Clean county names and create visualization
vt_clean = vt_income.copy()
vt_clean = vt_clean.sort_values("medincome")
vt_clean.dropna(subset=["medincome"], inplace=True)
plt.figure(figsize=(10, 6))

# Create error bar plot
plt.errorbar(
    vt_clean["medincome"],
    range(len(vt_clean)),
    xerr=vt_clean["medincome_moe"],  # Using margin of error as error bars
    fmt="o",
    color="red",
    markersize=8,
    capsize=5,
    capthick=2,
)

plt.xlabel("ACS Estimate (bars represent margin of error)")
plt.title(
    "Median Household Income by County in Vermont\n2018-2022 American Community Survey"
)
plt.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Data Output Formats
#
# By default, pytidycensus returns data in "tidy" format. You can also request "wide" format:
#
# ### Tidy Format (Default)

# %%
# Multiple variables in tidy format
ca_demo_tidy = tc.get_acs(
    geography="county",
    variables={
        "total_pop": "B01003_001",
        "median_income": "B19013_001",
        "median_age": "B01002_001",
    },
    state="CA",
    year=2022,
    output="tidy",  # This is the default
)

print(f"Tidy format shape: {ca_demo_tidy.shape}")
ca_demo_tidy

# %% [markdown]
# ### Wide Format

# %%
# Same data in wide format
ca_demo_wide = tc.get_acs(
    geography="county",
    variables={
        "total_pop": "B01003_001",
        "median_income": "B19013_001",
        "median_age": "B01002_001",
    },
    state="CA",
    year=2022,
    output="wide",
)

print(f"Wide format shape: {ca_demo_wide.shape}")
ca_demo_wide.head()

# %% [markdown]
# ## Multiple Variables Analysis
#
# Let's analyze the relationship between different demographic variables:

# %%
# Create scatter plot of median age vs median income
plt.figure(figsize=(10, 6))

plt.scatter(
    ca_demo_wide["median_age"],
    ca_demo_wide["median_income"],
    s=ca_demo_wide["total_pop"] / 5000,  # Size by population
    alpha=0.6,
)

plt.xlabel("Median Age (years)")
plt.ylabel("Median Household Income ($)")
plt.title(
    "Median Age vs Median Income by California County\n(Bubble size = Population)"
)
plt.grid(alpha=0.3)

# Add correlation coefficient
correlation = ca_demo_wide["median_age"].corr(ca_demo_wide["median_income"])
plt.text(
    0.05,
    0.95,
    f"Correlation: {correlation:.3f}",
    transform=plt.gca().transAxes,
    fontsize=12,
    bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
)

plt.tight_layout()
plt.show()

# %% [markdown]
# ## Working with Different Survey Types
#
# The ACS has different survey periods:
#
# - **5-year ACS** (`survey="acs5"`): More reliable for small areas, 5-year average
# - **1-year ACS** (`survey="acs1"`): More current, only for areas with 65,000+ population

# %%
# Compare 1-year vs 5-year estimates for large cities
cities_5yr = tc.get_acs(
    geography="place", variables="B19013_001", state="CA", year=2022, survey="acs5"
)

cities_1yr = tc.get_acs(
    geography="place", variables="B19013_001", state="CA", year=2022, survey="acs1"
)

print(f"5-year ACS places: {len(cities_5yr)}")
print(f"1-year ACS places: {len(cities_1yr)}")
print("\n1-year ACS is only available for larger places:")
cities_1yr.head()

# %% [markdown]
# ## Summary
#
# In this notebook, we learned:
#
# 1. **Setup**: How to install pytidycensus and set your API key
# 2. **Core functions**: `get_decennial()` and `get_acs()` for different data sources
# 3. **Geographic levels**: From national to neighborhood-level data
# 4. **Variable search**: Using `load_variables()` and `search_variables()`
# 5. **Data formats**: Tidy vs wide format output
# 6. **Uncertainty**: Working with ACS margins of error
# 7. **Visualization**: Creating plots with matplotlib
#
# ## Next Steps
#
# - **Spatial Analysis**: See `02_spatial_data.ipynb` for mapping examples
# - **Advanced ACS**: Explore `03_margins_of_error.ipynb` for statistical techniques
# - **Other Datasets**: Check `04_other_datasets.ipynb` for population estimates
# - **Microdata**: Learn about PUMS data in `05_pums_data.ipynb`
#
# ## Resources
#
# - [pytidycensus Documentation](https://mmann1123.github.io/pytidycensus)
# - [Census Variable Search](https://api.census.gov/data.html)
# - [Census Bureau Data](https://www.census.gov/data.html)
