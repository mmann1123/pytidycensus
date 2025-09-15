# %%


import pytidycensus as tc
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import warnings

warnings.filterwarnings("ignore")

tc.set_census_api_key("983980b9fc504149e82117c949d7ed44653dc507")


# orange = tc.get_acs(
#     state="CA",
#     county="Orange",
#     geography="tract",
#     variables="B19013_001",  # Median household income
#     geometry=True,
#     year=2022,
# )


# %%
race_vars = {
    "White": "P2_005N",
    "Black": "P2_006N",
    "Asian": "P2_008N",
    "Hispanic": "P2_002N",
}


harris = tc.get_decennial(
    geography="tract",
    variables=race_vars,
    state="TX",
    county="Harris",
    geometry=True,
    summary_var="P2_001N",  # Total population
    year=2020,
    sumfile="pl",
)


# %%
harris.head()

# %%
