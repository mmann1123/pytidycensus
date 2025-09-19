# %% [markdown]
# # Working with Census microdata
#
# [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mmann1123/pytidycensus/blob/main/examples/05_pums_data.ipynb)
#
# Introduction to Public Use Microdata Sample (PUMS) analysis.
#
# ### Census API Key
#
# To use pytidycensus, you need a free API key from the US Census Bureau. Get one at: https://api.census.gov/data/key_signup.html
#
# Set your API key:

# %%
import pytidycensus as tc
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

tc.set_census_api_key("YOUR API KEY GOES HERE")

# %% [markdown]
# ## Understanding PUMS Data
#
# PUMS provides individual-level responses that can be used for custom analysis.

# %%
# Note: PUMS functionality would be implemented in future versions
# This is a conceptual example of what PUMS analysis might look like

print("PUMS data analysis capabilities:")
print("- Individual-level demographic data")
print("- Custom crosstabulations")
print("- Statistical modeling on microdata")
print("- Geographic resolution: PUMAs (100K+ population)")

# %% [markdown]
# ## PUMS Variable Dictionary
#
# PUMS has hundreds of variables describing individuals and households:

# %%
# Example of what PUMS variable exploration would look like
# pums_vars = tc.load_pums_variables(2022, survey="acs1")
# person_vars = pums_vars[pums_vars['level'] == 'person']
# housing_vars = pums_vars[pums_vars['level'] == 'housing']

print("Example PUMS variables:")
print("Person-level: Age, Race, Education, Income, Employment")
print("Housing-level: Bedrooms, Value, Rent, Utilities")

# %% [markdown]
# ## Survey Weights and Statistical Analysis
#
# PUMS data requires proper handling of survey weights for accurate estimates:

# %%
# Conceptual example of weighted analysis
print("Survey weight considerations:")
print("- Person weights (PWGTP) for person-level analysis")
print("- Housing weights (WGTP) for housing-level analysis")
print("- Replicate weights for variance estimation")
print("- Use survey packages for proper statistical inference")
