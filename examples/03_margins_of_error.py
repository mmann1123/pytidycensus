# %% [markdown]
# # Margins of error in the ACS
#
# [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mmann1123/pytidycensus/blob/main/examples/03_margins_of_error.ipynb)
#
# Understanding and working with uncertainty in American Community Survey data.

# %%
import pytidycensus as tc
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# %% [markdown]
# ## Census API Key
#
# To use pytidycensus, you need a free API key from the US Census Bureau. Get one at: https://api.census.gov/data/key_signup.html
#

# %%

tc.set_census_api_key("Your API Key Here")

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
# ## Understanding ACS Uncertainty
#
# Unlike decennial Census counts, ACS data are estimates with margins of error.

# %%
# Example: Aging populations in Ramsey County, MN
age_vars = [f"B01001_0{i:02d}" for i in range(20, 26)] + [
    f"B01001_0{i:02d}" for i in range(44, 50)
]

ramsey = tc.get_acs(
    geography="tract",
    variables=age_vars,
    state="MN",
    county="Ramsey",
    year=2022,
    output="wide",
)
ramsey.head()

# %%
# Show cases where MOE exceeds estimate
ramsey["moe_ratio"] = (
    ramsey["B01001_020_moe"] / ramsey["B01001_020E"]
)  # Example MOE column
print("Cases where margin of error exceeds estimate: 'GEOID'")
print(ramsey[ramsey["moe_ratio"] > 1]["GEOID"].head())

# %% [markdown]
# ## Aggregating Data and MOE Calculations
#
# When combining estimates, we need to properly calculate the margin of error.


# %%
# Custom MOE calculation functions (simplified versions)
def moe_sum(moes, estimates):
    """Calculate MOE for sum of estimates"""
    return np.sqrt(sum(moe**2 for moe in moes))


# Aggregate population over 65 by tract
ramsey_65plus = (
    ramsey.groupby("GEOID")
    .agg(
        {
            "B01001_020E": "sum",
            "B01001_020_moe": lambda x: moe_sum(x, ramsey.loc[x.index, "B01001_020E"]),
        }
    )
    .rename(columns={"B01001_020_moe": "moe_sum"})
)

print("Aggregated estimates with proper MOE calculation:")
print(ramsey_65plus.head())

# %% [markdown]
# ## Visualization with Confidence Intervals

# %%
# Create error bar plot showing uncertainty
fig, ax = plt.subplots(figsize=(12, 8))

sample_data = ramsey_65plus.head(10)
x = range(len(sample_data))

ax.errorbar(
    x,
    sample_data["B01001_020E"],
    yerr=sample_data["moe_sum"],
    fmt="o",
    capsize=5,
    capthick=2,
)
ax.set_xlabel("Census Tract")
ax.set_ylabel("Population 65+")
ax.set_title("Population 65+ by Census Tract with Margins of Error")
plt.xticks(x, [f"Tract {i+1}" for i in x], rotation=45)
plt.tight_layout()
plt.show()

# %%
