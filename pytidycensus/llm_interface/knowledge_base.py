"""Knowledge base for pytidycensus Census Assistant.

Contains detailed examples, variable mappings, and common use cases.
"""

# Common research topics mapped to variable codes
# IMPORTANT: Always include denominator/total variables for proper normalization
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
    output='wide',
    api_key="your_key"
)
# Calculate percentage with Bachelor's degree
data['bachelor_rate'] = (data['B15003_022E'] / data['B01003_001E']) * 100

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
    output='wide',
    api_key="your_key"
)

# Calculate rent as % of income
data['rent_as_pct_income'] = (data['B25064_001E'] / data['B19013_001E']) * 100

# Calculate home value as % of income
data['home_value_as_pct_income'] = (data['B25077_001E'] / data['B19013_001E']) * 100
""",
    "poverty_analysis": """
# Poverty rate analysis
import pytidycensus as tc

data = tc.get_acs(
    geography="county",
    variables=[
        "B17001_002E",  # Count below poverty line
        "B17001_001E",  # Total for poverty status
        "B01003_001E",  # Total population
    ],
    state="TX",
    year=2022,
    output='wide',
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
    output='wide',
    api_key="your_key"
)

# This returns a GeoPandas GeoDataFrame ready for mapping
data.explore(column='B19013_001E', legend=True)
""",
    "dc_analysis": """
# Washington DC inequality analysis
import pytidycensus as tc

# DC can be specified as "DC", "11", or "District of Columbia"
data = tc.get_acs(
    geography="tract",
    variables=[
        "B17001_002E",  # Below poverty line
        "B17001_001E",  # Total for poverty status (denominator)
        "B19001_002E",  # Low income households (<$25k)
        "B19001_001E",  # Total households (denominator)
        "B01003_001E",  # Total population
    ],
    state="DC",  # Works with "DC", "11", or "District of Columbia"
    year=2022,
    geometry=True,  # Include geographic boundaries
    api_key="your_key"
)

# Calculate rates for proper analysis
data['poverty_rate'] = data['B17001_002E'] / data['B17001_001E']
data['low_income_rate'] = data['B19001_002E'] / data['B19001_001E']

data.explore(column="poverty_rate", legend=True, cmap="OrRd")

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


# Normalization variable mappings - critical for proper analysis
NORMALIZATION_MAPPINGS = {
    # Income variables need total households for rates
    "income": {
        "denominators": {
            "total_households": "B19001_001E",  # For household income distributions
            "total_families": "B19101_001E",  # For family income distributions
            "total_population": "B01003_001E",  # For per capita calculations
        },
        "examples": [
            "To calculate % of households earning <$25k: B19001_002E / B19001_001E",
            "To calculate % of households earning >$100k: sum(B19001_014E:B19001_017E) / B19001_001E",
        ],
    },
    # Education variables need total population 25+ for rates
    "education": {
        "denominators": {
            "total_education_pop": "B15003_001E",  # Total population 25+ for education
            "total_population": "B01003_001E",  # For general population rates
        },
        "examples": [
            "College graduation rate: B15003_022E / B15003_001E",
            "High school completion: (B15003_001E - sum(B15003_002E:B15003_016E)) / B15003_001E",
        ],
    },
    # Housing variables need total housing units or occupied units
    "housing": {
        "denominators": {
            "total_housing_units": "B25001_001E",  # All housing units
            "occupied_housing_units": "B25002_002E",  # Only occupied units
            "total_households": "B11001_001E",  # Households (for household-level analysis)
        },
        "examples": [
            "Homeownership rate: B25003_002E / B25003_001E",
            "Vacancy rate: B25002_003E / B25001_001E",
            "Median rent burden: needs B25070 (rent burden) with B25070_001E (total)",
        ],
    },
    # Employment variables need total population 16+ or labor force
    "employment": {
        "denominators": {
            "total_labor_force": "B23025_002E",  # Labor force (employed + unemployed)
            "total_working_age": "B23025_001E",  # Total population 16+
            "civilian_labor_force": "B23025_002E",  # Civilian labor force
        },
        "examples": [
            "Unemployment rate: B23025_005E / B23025_002E",
            "Labor force participation: B23025_002E / B23025_001E",
        ],
    },
    # Poverty variables need total population for poverty determination
    "poverty": {
        "denominators": {
            "total_for_poverty": "B17001_001E",  # Total pop for poverty status
            "total_families": "B17012_001E",  # Total families for family poverty
            "total_children": "B17020_001E",  # Total children for child poverty
            "total_population": "B01003_001E",  # General population
        },
        "examples": [
            "Poverty rate: B17001_002E / B17001_001E",
            "Child poverty rate: B17020_002E / B17020_001E",
            "Family poverty rate: B17012_002E / B17012_001E",
        ],
    },
    # Race/ethnicity variables need total population
    "race_ethnicity": {
        "denominators": {
            "total_population": "B02001_001E",  # Total for race analysis
            "total_hispanic_origin": "B03003_001E",  # Total for Hispanic/Latino analysis
        },
        "examples": [
            "% White alone: B02001_002E / B02001_001E",
            "% Hispanic/Latino: B03003_003E / B03003_001E",
        ],
    },
    # Transportation variables need total workers
    "transportation": {
        "denominators": {
            "total_workers": "B08301_001E",  # Total workers 16+ (commuting universe)
            "total_households": "B08201_001E",  # For vehicle availability
        },
        "examples": [
            "% drove alone: B08301_010E / B08301_001E",
            "% work from home: B08301_021E / B08301_001E",
            "% no vehicle: B08201_002E / B08201_001E",
        ],
    },
    # Age/sex analysis
    "demographics": {
        "denominators": {
            "total_population": "B01001_001E",  # For age/sex distributions
            "total_male": "B01001_002E",  # For male-specific rates
            "total_female": "B01001_026E",  # For female-specific rates
        },
        "examples": [
            "% under 18: sum(B01001_003E:B01001_006E + B01001_027E:B01001_030E) / B01001_001E",
            "% over 65: sum(B01001_020E:B01001_025E + B01001_044E:B01001_049E) / B01001_001E",
        ],
    },
}


def needs_normalization(variable_code: str, variable_label: str = "") -> bool:
    """Check if a specific variable needs normalization for proper analysis.

    Simple rule: If variable name/label contains median, mean, average, rate,
    or ends in _001E (totals), it doesn't need normalization.
    """
    # Combine code and label for checking
    full_text = f"{variable_code} {variable_label}".lower()

    # Keywords that indicate the variable is already a rate/median/total
    no_norm_keywords = [
        "median",
        "mean",
        "average",
        "rate",
        "percent",
        "percentage",
        "per capita",
        "ratio",
        "index",
    ]

    # Check if any keyword is present
    if any(keyword in full_text for keyword in no_norm_keywords):
        return False

    # Variables ending in _001E are usually totals (denominators)
    if variable_code.endswith("_001E"):
        return False

    # Otherwise, count variables typically need normalization
    return True


def get_normalization_variables_for_codes(
    variable_codes: list, variable_labels: list = None
) -> dict:
    """Get normalization variables needed for specific variable codes.

    Simple approach: Only add normalization for count variables that don't contain
    'median', 'mean', 'rate', etc. in their name/label.
    """
    normalization_vars = {}

    if variable_labels is None:
        variable_labels = [""] * len(variable_codes)

    for var_code, var_label in zip(variable_codes, variable_labels):
        if not needs_normalization(var_code, var_label):
            continue

        # Simple table-based mapping for common denominators
        table = var_code.split("_")[0]  # Extract table prefix (e.g., "B17001")

        if table.startswith("B19"):  # Income tables
            if table == "B19001":  # Household income by income categories
                normalization_vars["B19001_001E"] = "total_households_for_income"
        elif table.startswith("B17"):  # Poverty tables
            if table == "B17001":  # Poverty status
                normalization_vars["B17001_001E"] = "total_population_for_poverty"
            elif table == "B17020":  # Age by poverty status
                normalization_vars["B17020_001E"] = "total_children_for_poverty"
        elif table.startswith("B15"):  # Education tables
            normalization_vars["B15003_001E"] = "total_population_25_plus"
        elif table.startswith("B25"):  # Housing tables
            if table in ["B25003", "B25002"]:  # Tenure, vacancy
                normalization_vars["B25001_001E"] = "total_housing_units"
            else:
                normalization_vars["B25002_002E"] = "occupied_housing_units"
        elif table.startswith("B23"):  # Employment tables
            normalization_vars["B23025_002E"] = "total_labor_force"
        elif table.startswith("B02"):  # Race tables
            normalization_vars["B02001_001E"] = "total_population_for_race"
        elif table.startswith("B03"):  # Hispanic origin tables
            normalization_vars["B03003_001E"] = "total_population_for_hispanic_origin"
        elif table.startswith("B08"):  # Transportation tables
            if table == "B08301":  # Commuting
                normalization_vars["B08301_001E"] = "total_workers"
            elif table == "B08201":  # Vehicle availability
                normalization_vars["B08201_001E"] = "total_households_for_vehicles"
        elif table.startswith("B01"):  # Demographics tables
            normalization_vars["B01001_001E"] = "total_population"

    return normalization_vars


def get_normalization_variables(topic: str) -> dict:
    """Get normalization variables needed for proper analysis of a topic."""
    topic_lower = topic.lower()

    # Direct matches
    if topic_lower in NORMALIZATION_MAPPINGS:
        return NORMALIZATION_MAPPINGS[topic_lower]

    # Fuzzy matching
    matches = {}
    for key, norm_info in NORMALIZATION_MAPPINGS.items():
        if topic_lower in key or key in topic_lower:
            matches[key] = norm_info

    return matches


def get_dataset_info(dataset: str) -> dict:
    """Get information about a Census dataset."""
    return DATASET_GUIDANCE.get(dataset.lower(), {})
