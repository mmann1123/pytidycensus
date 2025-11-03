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
    state="11",  # State code for District of Columbia
    year=2022,
)

# Print the first few rows of the data for verification
print(data_tract.head())

# %%


import pytidycensus as tc

# Set your Census API key

# Define the variables and geographies for Washington DC city
variables = {
    "income": ["B19013_001E", "B17001_002E", "B17001_001E"],
    "education": ["B15003_022E", "B15003_001E"],
    "housing": ["B25077_001E", "B25064_001E", "B25001_001E"],
    "employment": ["B23025_002E", "B23025_005E"],
}

# Retrieve data for 2020
data_2020 = tc.get_acs(
    geography="place",
    variables=[v for sublist in variables.values() for v in sublist],
    state="DC",
    year=2020,
)

# Calculate rates or percentages
data_2020["poverty_rate"] = data_2020["B17001_002E"] / data_2020["B17001_001E"]
data_2020["college_education_rate"] = data_2020["B15003_022E"] / data_2020["B15003_001E"]
data_2020["unemployment_rate"] = data_2020["B23025_005E"] / data_2020["B23025_002E"]

# Retrieve data for 2023
data_2023 = tc.get_acs(
    geography="place",
    variables=[v for sublist in variables.values() for v in sublist],
    state="DC",
    year=2023,
)

# Calculate rates or percentages
data_2023["poverty_rate"] = data_2023["B17001_002E"] / data_2023["B17001_001E"]
data_2023["college_education_rate"] = data_2023["B15003_022E"] / data_2023["B15003_001E"]
data_2023["unemployment_rate"] = data_2023["B23025_005E"] / data_2023["B23025_002E"]

# %%
from pytidycensus.time_series import get_time_series

variables = {2010: {"total_pop": "P001001"}, 2020: {"total_pop": "P1_001N"}}


data = get_time_series(
    geography="tract",
    variables=variables,
    years=[2010, 2020],
    dataset="decennial",
    extensive_variables=["total_pop"],
    state="DC",
    base_year=2020,
    geometry=True,
)
data
# %%


# %%

# %%


# %%
dc_2023 = tc.get_acs(
    geography="tract",
    variables={
        "total_pop": "B01003_001E",  # Total population
        "poverty_count": "B17001_002E",  # Population below poverty line
        "poverty_total": "B17001_001E",  # Total population for poverty calculation
    },
    state="DC",
    year=2023,
    survey="acs5",
    geometry=True,
    output="wide",
)

dc_2023
# %%
from pytidycensus.time_series import get_time_series

# Define years for time series (ACS 5-year data)
# Using 2015-2022 for reliable geometry downloads
years = [2019, 2020, 2021]

print(f"Downloading median household income data for DC tracts...")
print(f"Years: {years}")
print(f"This will take a few minutes...\n")

# Download time series data with automatic boundary alignment
dc_income = tc.get_time_series(
    geography="tract",
    variables={"median_income": "B19013_001E"},
    years=years,
    dataset="acs5",
    state="DC",
    base_year=2021,  # Align all data to 2021 boundaries
    intensive_variables=["median_income"],  # Median is an intensive variable
    geometry=True,
    output="wide",
)
dc_income
# %%
dc_income
# %%
data
# %%
