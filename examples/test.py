# %%
# Import the necessary pytidycensus library
import pytidycensus as tc

# Set your Census API key

# Get data for selected variables at the tract level in Washington DC
data_tract = tc.get_acs(
    geography="tract",
    variables=[
        "B15003_002E",
        "B15003_022E",
        "B15003_025E",  # Education variables
        "B23025_002E",
        "B23025_004E",  # Employment variables
        "B19013_001E",
        "B19301_001E",
        "B19001_002E",
        "B19001_014E",  # Income variables
    ],
    state="DC",  # State code for District of Columbia
    year=2022,
)

# Print the first few rows of the data for verification
print(data_tract.head())

# %%
