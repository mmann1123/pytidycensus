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


orange = tc.get_acs(
    state="CA",
    county="Orange",
    geography="tract",
    variables="B19013_001",  # Median household income
    geometry=True,
    year=2022,
)


# %%
orange

# %%
