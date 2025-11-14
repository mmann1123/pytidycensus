#%% 

import pytidycensus as tc
tc.set_census_api_key("983980b9fc504149e82117c949d7ed44653dc507")

income = tc.get_acs(
    geography="county",
    variables="B19013_001E",
    state="MD",
    geometry=True,
    year=2022
)

income
# %%
poverty_ts = tc.get_time_series(
    geography="tract",
    variables={"poverty_count":"B17001_002E"},
    state="DC",
    years=[2010,2020],
    extensive_variables=["poverty_count"],
    output_type="wide"
)

poverty_ts
# %%
