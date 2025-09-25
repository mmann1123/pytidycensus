"""Knowledge base for pytidycensus Census Assistant.

Contains detailed examples, variable mappings, and common use cases.
"""

# Common research topics mapped to variable codes
VARIABLE_MAPPINGS = {
    "population": {
        "total_population": "B01003_001E",
        "population_by_age_sex": "B01001_001E",
        "male_population": "B01001_002E",
        "female_population": "B01001_026E",
        "median_age": "B01002_001E",
    },
    "income": {
        "median_household_income": "B19013_001E",
        "per_capita_income": "B19301_001E",
        "mean_household_income": "B19025_001E",
        "median_family_income": "B19113_001E",
        "household_income_under_25k": "B19001_002E",
        "household_income_25k_to_50k": ["B19001_005E", "B19001_006E", "B19001_007E"],
        "household_income_over_100k": ["B19001_014E", "B19001_015E", "B19001_016E", "B19001_017E"],
    },
    "poverty": {
        "below_poverty": "B17001_002E",
        "total_for_poverty_status": "B17001_001E",
        "poverty_rate_children": "B17020_002E",
        "poverty_rate_seniors": "B17001_015E",
        "families_below_poverty": "B17012_002E",
    },
    "housing": {
        "total_housing_units": "B25001_001E",
        "occupied_housing_units": "B25002_002E",
        "vacant_housing_units": "B25002_003E",
        "owner_occupied": "B25003_002E",
        "renter_occupied": "B25003_003E",
        "median_home_value": "B25077_001E",
        "median_rent": "B25064_001E",
        "median_rooms": "B25018_001E",
    },
    "education": {
        "total_education_pop": "B15003_001E",
        "less_than_high_school": ["B15003_002E", "B15003_016E"],
        "high_school_graduate": "B15003_017E",
        "some_college": ["B15003_018E", "B15003_019E", "B15003_020E"],
        "bachelor_degree": "B15003_022E",
        "graduate_degree": "B15003_025E",
        "percent_bachelor_or_higher": "B15002_015E",
    },
    "race_ethnicity": {
        "white_alone": "B02001_002E",
        "black_alone": "B02001_003E",
        "asian_alone": "B02001_005E",
        "hispanic_or_latino": "B03003_003E",
        "not_hispanic_or_latino": "B03003_002E",
        "two_or_more_races": "B02001_008E",
    },
    "employment": {
        "labor_force": "B23025_002E",
        "employed": "B23025_004E",
        "unemployed": "B23025_005E",
        "not_in_labor_force": "B23025_007E",
        "unemployment_rate": "B23025_005E",  # Needs calculation: unemployed/labor_force
    },
    "transportation": {
        "drove_alone": "B08301_010E",
        "carpooled": "B08301_011E",
        "public_transportation": "B08301_016E",
        "walked": "B08301_019E",
        "worked_from_home": "B08301_021E",
        "mean_travel_time": "B08303_001E",
    },
}

# Geographic hierarchy and requirements
GEOGRAPHY_INFO = {
    "state": {
        "description": "US states and territories",
        "requires_state": False,
        "typical_count": "51 areas (50 states + DC)",
        "sample_size": "Very large",
        "use_cases": ["State comparisons", "National analysis", "Large-scale trends"],
    },
    "county": {
        "description": "Counties and county equivalents",
        "requires_state": True,
        "typical_count": "~3,100 nationwide, varies by state",
        "sample_size": "Large",
        "use_cases": ["Regional analysis", "Local government areas", "Metro comparisons"],
    },
    "place": {
        "description": "Cities, towns, and census designated places",
        "requires_state": True,
        "typical_count": "Thousands per state",
        "sample_size": "Varies widely",
        "use_cases": ["City analysis", "Urban/rural comparison", "Municipal planning"],
    },
    "tract": {
        "description": "Census tracts (~4,000 people each)",
        "requires_state": True,
        "typical_count": "~85,000 nationwide",
        "sample_size": "Medium (neighborhood level)",
        "use_cases": ["Neighborhood analysis", "Equity studies", "Local planning"],
    },
    "block group": {
        "description": "Census block groups (~600-3,000 people)",
        "requires_state": True,
        "typical_count": "~240,000 nationwide",
        "sample_size": "Small (high margins of error)",
        "use_cases": ["Very local analysis", "Site selection", "Detailed mapping"],
    },
    "zcta": {
        "description": "ZIP Code Tabulation Areas",
        "requires_state": False,
        "typical_count": "~33,000 nationwide",
        "sample_size": "Varies widely",
        "use_cases": ["Market analysis", "Service areas", "ZIP code studies"],
    },
}

# Common code examples for different use cases
CODE_EXAMPLES = {
    "demographic_profile": """
# Get demographic profile for a state
import pytidycensus as tc

data = tc.get_acs(
    geography="state",
    variables=[
        "B01003_001E",  # Total population
        "B19013_001E",  # Median household income
        "B25077_001E",  # Median home value
        "B15003_022E",  # Bachelor's degree
    ],
    state="CA",
    year=2022,
    api_key="your_key"
)
""",
    "housing_analysis": """
# Housing affordability analysis
import pytidycensus as tc

data = tc.get_acs(
    geography="place",
    variables=[
        "B25077_001E",  # Median home value
        "B25064_001E",  # Median rent
        "B19013_001E",  # Median household income
        "B25003_002E",  # Owner occupied
        "B25003_003E",  # Renter occupied
    ],
    state="CA",
    year=2022,
    api_key="your_key"
)
""",
    "poverty_analysis": """
# Poverty rate analysis
import pytidycensus as tc

data = tc.get_acs(
    geography="county",
    variables=[
        "B17001_002E",  # Below poverty line
        "B17001_001E",  # Total for poverty status
        "B01003_001E",  # Total population
    ],
    state="TX",
    year=2022,
    api_key="your_key"
)

# Calculate poverty rate
data['poverty_rate'] = (data['B17001_002E'] / data['B17001_001E']) * 100
""",
    "with_geography": """
# Get data with geographic boundaries
import pytidycensus as tc

data = tc.get_acs(
    geography="tract",
    variables=["B19013_001E"],  # Median income
    state="CA",
    county="Los Angeles",
    geometry=True,  # Include geographic boundaries
    year=2022,
    api_key="your_key"
)

# This returns a GeoPandas GeoDataFrame ready for mapping
data.plot(column='B19013_001E', legend=True)
""",
}

# Dataset guidance
DATASET_GUIDANCE = {
    "acs5": {
        "name": "American Community Survey 5-Year",
        "years_available": "2009-present",
        "geographic_coverage": "All levels down to block group",
        "sample_size": "Large (5 years combined)",
        "margins_of_error": "Smaller (more reliable)",
        "when_to_use": "Small geographies, detailed analysis, stable estimates",
        "limitations": "5-year averages, less current",
    },
    "acs1": {
        "name": "American Community Survey 1-Year",
        "years_available": "2005-present",
        "geographic_coverage": "Areas with 65,000+ people",
        "sample_size": "Smaller (1 year only)",
        "margins_of_error": "Larger (less reliable)",
        "when_to_use": "Current data, large geographies, trend analysis",
        "limitations": "Limited geographies, higher uncertainty",
    },
    "decennial": {
        "name": "Decennial Census",
        "years_available": "2000, 2010, 2020",
        "geographic_coverage": "All levels down to block",
        "sample_size": "100% count (no sampling)",
        "margins_of_error": "None (complete enumeration)",
        "when_to_use": "Precise counts, small geographies, baseline data",
        "limitations": "Limited variables, only every 10 years",
    },
}


def get_variables_for_topic(topic: str) -> dict:
    """Get variable codes for a research topic."""
    topic_lower = topic.lower()

    # Direct matches
    if topic_lower in VARIABLE_MAPPINGS:
        return VARIABLE_MAPPINGS[topic_lower]

    # Fuzzy matching
    matches = {}
    for key, variables in VARIABLE_MAPPINGS.items():
        if topic_lower in key or key in topic_lower:
            matches[key] = variables

    return matches


def get_geography_guidance(geography: str) -> dict:
    """Get guidance for a specific geography level."""
    return GEOGRAPHY_INFO.get(geography.lower(), {})


def get_code_example(use_case: str) -> str:
    """Get code example for a specific use case."""
    return CODE_EXAMPLES.get(use_case, "")


def get_dataset_info(dataset: str) -> dict:
    """Get information about a Census dataset."""
    return DATASET_GUIDANCE.get(dataset.lower(), {})
