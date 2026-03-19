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

import pytidycensus as tc
# Geography levels that are supported for population estimates
geography_tests = [
    ("us", {}, "United States"),
    ("region", {}, "Census region"),
    ("division", {}, "Census division"),
    ("state", {"state": "VT"}, "State"),
    ("county", {"state": "VT"}, "County"),
    (
        "metropolitan statistical area/micropolitan statistical area",
        {},
        "Metropolitan Statistical Area",
    ),
    ("place", {"state": "VT"}, "Incorporated place"),
]

for geography, params, description in geography_tests:
    result = tc.get_estimates(
        geography=geography,
        variables="POP",  # Population estimate
        year=2022,
        **params,
    )

    assert isinstance(result, pd.DataFrame), f"Failed for {description}"
    assert len(result) > 0, f"No data returned for {description}"

    # Check for geographic identifier column (varies by geography level)
    geo_id_cols = [
        "GEOID",
        "us",
        "region",
        "division",
        "state",
        "county",
        "tract",
        "block group",
        "place",
    ]
    has_geo_id = any(col in result.columns for col in geo_id_cols)
    assert (
        has_geo_id
    ), f"Missing geographic identifier for {description}, columns: {result.columns.tolist()}"

    # Check for estimate column (varies by function)
    estimate_cols = [
        "estimate",
        "POPESTIMATE2022",
        "POPESTIMATE2021",
        "POPESTIMATE2020",
    ]
    has_estimate = any(col in result.columns for col in estimate_cols)
    assert (
        has_estimate
    ), f"Missing estimate column for {description}, columns: {result.columns.tolist()}"

    print(f"✓ {description} geography works")

# %%
from pytidycensus.llm_interface import CensusAssistant

# Initialize assistant
assistant = CensusAssistant(
    census_api_key="your_census_api_key",
    openai_api_key="your_openai_key"  # Optional
)

# Ask for data (use await directly in Jupyter)
response = await assistant.chat("Get median income by county in Texas")
print(response)
# %%
