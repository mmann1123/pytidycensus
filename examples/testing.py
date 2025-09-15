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


# Debug: Print available counties for CA to help fix lookup
from pytidycensus.utils import _load_national_county_txt

counties = _load_national_county_txt()
ca_counties = [c for c in counties if c["state"] == "CA"]
print("Available CA counties:", [c["county"] for c in ca_counties])

# %%
