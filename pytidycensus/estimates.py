"""Population estimates data retrieval functions."""

import warnings
from io import StringIO
from typing import List, Optional, Union

import geopandas as gpd
import pandas as pd
import requests
import urllib3

from .api import CensusAPI
from .geography import get_geography
from .utils import build_geography_params, process_census_data

# Disable SSL warnings for Census site
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PopulationEstimatesError(Exception):
    """Base exception class for Population Estimates errors."""


class InvalidGeographyError(PopulationEstimatesError):
    """Raised when an invalid geography is specified."""


class InvalidVariableError(PopulationEstimatesError):
    """Raised when an invalid variable is specified."""


class DataNotAvailableError(PopulationEstimatesError):
    """Raised when requested data is not available."""


class APIError(PopulationEstimatesError):
    """Raised when there are issues with API requests."""


# Supported geographies
SUPPORTED_GEOGRAPHIES = {
    "us",
    "region",
    "division",
    "state",
    "county",
    "cbsa",
    "metropolitan statistical area/micropolitan statistical area",
    "combined statistical area",
    "place",
}

# Geography aliases
GEOGRAPHY_ALIASES = {"metropolitan statistical area/micropolitan statistical area": "cbsa"}

# Comprehensive variable mapping
VARIABLE_MAPPING = {
    "POP": "POPESTIMATE",
    "BIRTHS": "BIRTHS",
    "DEATHS": "DEATHS",
    "NETMIG": "NETMIG",
    "DOMESTICMIG": "DOMESTICMIG",
    "INTERNATIONALMIG": "INTERNATIONALMIG",
    "NATURALCHG": "NATURALCHG",
    "NPOPCHG": "NPOPCHG",
    "RESIDUAL": "RESIDUAL",
    "ESTIMATESBASE": "ESTIMATESBASE",
    "GQESTIMATES": "GQESTIMATES",
    "GQESTIMATESBASE": "GQESTIMATESBASE",
    "RBIRTH": "RBIRTH",
    "RDEATH": "RDEATH",
    "RNATURALCHG": "RNATURALCHG",
    "RINTERNATIONALMIG": "RINTERNATIONALMIG",
    "RDOMESTICMIG": "RDOMESTICMIG",
    "RNETMIG": "RNETMIG",
}

# Variable descriptions
VARIABLE_DESCRIPTIONS = {
    "POPESTIMATE": "Total population estimate",
    "ESTIMATESBASE": "Population estimates base",
    "BIRTHS": "Births",
    "DEATHS": "Deaths",
    "NATURALCHG": "Natural change (births - deaths)",
    "INTERNATIONALMIG": "International migration",
    "DOMESTICMIG": "Domestic migration",
    "NETMIG": "Net migration",
    "NPOPCHG": "Net population change",
    "RESIDUAL": "Residual",
    "GQESTIMATESBASE": "Group quarters population estimates base",
    "GQESTIMATES": "Group quarters population",
    "RBIRTH": "Birth rate per 1,000 population",
    "RDEATH": "Death rate per 1,000 population",
    "RNATURALCHG": "Natural change rate per 1,000 population",
    "RINTERNATIONALMIG": "International migration rate per 1,000 population",
    "RDOMESTICMIG": "Domestic migration rate per 1,000 population",
    "RNETMIG": "Net migration rate per 1,000 population",
}


def _is_valid_state(state_input: Union[str, int]) -> bool:
    """Check if a state identifier is valid."""
    # Valid state FIPS codes (as strings and integers)
    valid_fips = {
        "01",
        "02",
        "04",
        "05",
        "06",
        "08",
        "09",
        "10",
        "11",
        "12",
        "13",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",
        "38",
        "39",
        "40",
        "41",
        "42",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "50",
        "51",
        "53",
        "54",
        "55",
        "56",
        1,
        2,
        4,
        5,
        6,
        8,
        9,
        10,
        11,
        12,
        13,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        42,
        44,
        45,
        46,
        47,
        48,
        49,
        50,
        51,
        53,
        54,
        55,
        56,
    }

    # Valid state abbreviations
    valid_abbrevs = {
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "DC",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
    }

    # Valid state names (simplified - just a few common ones for validation)
    valid_names = {
        "alabama",
        "alaska",
        "arizona",
        "arkansas",
        "california",
        "colorado",
        "connecticut",
        "delaware",
        "district of columbia",
        "florida",
        "georgia",
        "hawaii",
        "idaho",
        "illinois",
        "indiana",
        "iowa",
        "kansas",
        "kentucky",
        "louisiana",
        "maine",
        "maryland",
        "massachusetts",
        "michigan",
        "minnesota",
        "mississippi",
        "missouri",
        "montana",
        "nebraska",
        "nevada",
        "new hampshire",
        "new jersey",
        "new mexico",
        "new york",
        "north carolina",
        "north dakota",
        "ohio",
        "oklahoma",
        "oregon",
        "pennsylvania",
        "rhode island",
        "south carolina",
        "south dakota",
        "tennessee",
        "texas",
        "utah",
        "vermont",
        "virginia",
        "washington",
        "west virginia",
        "wisconsin",
        "wyoming",
    }

    # Check different formats
    if isinstance(state_input, int) or (isinstance(state_input, str) and state_input.isdigit()):
        return state_input in valid_fips
    elif isinstance(state_input, str):
        return (
            state_input.upper() in valid_abbrevs
            or state_input.lower() in valid_names
            or state_input in valid_fips
        )

    return False


def _validate_estimates_inputs(
    geography: str,
    product: Optional[str],
    variables: Optional[Union[str, List[str]]],
    breakdown: Optional[List[str]],
    vintage: int,
    year: Optional[int],
    state: Optional[Union[str, int, List[Union[str, int]]]],
    county: Optional[Union[str, int, List[Union[str, int]]]],
    **kwargs,
) -> None:
    """Comprehensive input validation for get_estimates function."""

    # Validate year range
    actual_year = year if year is not None else vintage
    if actual_year < 2015:
        raise DataNotAvailableError(
            f"Population Estimates data not available for year {actual_year}. "
            f"Available years: 2015-{vintage}. "
            f"For earlier data, consider using Decennial Census data with get_decennial()."
        )

    if actual_year > vintage:
        raise DataNotAvailableError(
            f"Year {actual_year} is not available in vintage {vintage} dataset. "
            f"Available years in this vintage: 2015-{vintage}. "
            f"Consider using vintage={actual_year} if available."
        )

    # Validate and normalize geography
    geography_lower = geography.lower()
    if geography_lower in GEOGRAPHY_ALIASES:
        geography_lower = GEOGRAPHY_ALIASES[geography_lower]

    if geography_lower not in SUPPORTED_GEOGRAPHIES:
        # Create helpful error message with suggestions
        available = sorted(SUPPORTED_GEOGRAPHIES)
        closest_matches = []
        for geo in available:
            if geography_lower in geo or geo in geography_lower:
                closest_matches.append(geo)

        error_msg = (
            f"Geography '{geography}' not supported. Available options: {', '.join(available)}"
        )
        if closest_matches:
            error_msg += f". Did you mean: {', '.join(closest_matches[:3])}?"

        raise InvalidGeographyError(error_msg)

    # Validate variables
    if variables:
        valid_variables = _get_valid_variables_for_product(product or "population", actual_year)
        var_list = [variables] if isinstance(variables, str) else variables

        if var_list != ["all"]:
            invalid_vars = []
            for var in var_list:
                if var.upper() not in valid_variables and var != "all":
                    invalid_vars.append(var)

            if invalid_vars:
                error_msg = f"Invalid variables: {', '.join(invalid_vars)}. "
                error_msg += f"Available variables for {product or 'population'} product: "
                error_msg += f"{', '.join(sorted(valid_variables)[:10])}"
                if len(valid_variables) > 10:
                    error_msg += f" and {len(valid_variables) - 10} more"
                raise InvalidVariableError(error_msg)

    # Validate state codes
    if state is not None:
        state_list = [state] if not isinstance(state, (list, tuple)) else state
        for s in state_list:
            if not _is_valid_state(s):
                raise InvalidGeographyError(
                    f"Invalid state identifier: '{s}'. "
                    f"Use state names (e.g., 'Texas'), abbreviations (e.g., 'TX'), "
                    f"or FIPS codes (e.g., '48' or 48)."
                )

    # Validate breakdown/product combinations
    if breakdown:
        if geography_lower not in ["state"]:
            raise DataNotAvailableError(
                f"Demographic breakdowns not available for '{geography}' geography. "
                f"Currently supported: state. County, CBSA, and CSA support coming soon."
            )

        valid_breakdowns = {"SEX", "RACE", "ORIGIN", "AGE", "AGEGROUP"}
        invalid_breakdowns = [b for b in breakdown if b.upper() not in valid_breakdowns]
        if invalid_breakdowns:
            raise InvalidVariableError(
                f"Invalid breakdown dimensions: {', '.join(invalid_breakdowns)}. "
                f"Available: {', '.join(valid_breakdowns)}"
            )


def _get_valid_variables_for_product(product: str, year: int) -> set:
    """Get valid variables for a given product and year."""
    # Population variables (available in all years)
    population_vars = {"POP", "POPESTIMATE", "ESTIMATESBASE", "NAME"}

    # Components variables (available in all years)
    components_vars = {
        "BIRTHS",
        "DEATHS",
        "NATURALCHG",
        "NETMIG",
        "NPOPCHG",
        "DOMESTICMIG",
        "INTERNATIONALMIG",
        "RESIDUAL",
        "RBIRTH",
        "RDEATH",
        "RNATURALCHG",
        "RINTERNATIONALMIG",
        "RDOMESTICMIG",
        "RNETMIG",
    }

    # Characteristics variables (population estimates by demographics)
    characteristics_vars = {"POP", "NAME"}

    if product == "components":
        return components_vars | {"NAME"}
    elif product == "characteristics":
        return characteristics_vars
    else:  # population
        return population_vars | components_vars  # Population product can access both


def _filter_variables_for_dataset(dataset_path: str, variables: List[str]) -> List[str]:
    """Filter variables to only include those compatible with the selected dataset.

    Dataset compatibility:
    - pep/population: POP, NAME, and geographic variables
    - pep/components: BIRTHS, DEATHS, NATURALCHG, NETMIG, etc. (no POP)
    - pep/charagegroups: POP, NAME, demographic breakdowns
    """
    # Define variables available in each dataset
    population_vars = {"POP", "NAME"}
    components_vars = {
        "BIRTHS",
        "DEATHS",
        "DOMESTICMIG",
        "INTERNATIONALMIG",
        "NETMIG",
        "NATURALCHG",
        "NPOPCHG",
        "RESIDUAL",
        "NAME",
    }
    charagegroups_vars = {"POP", "NAME"}  # Plus demographic variables

    # Geographic variables are available in all datasets
    geo_vars = {"GEOID", "state", "county", "place", "cbsa", "csa", "for", "in"}

    filtered = []

    for var in variables:
        var_upper = var.upper()

        # Always include geographic and standard variables
        if var_upper in geo_vars or var in geo_vars:
            filtered.append(var)
            continue

        # Filter based on dataset
        if dataset_path == "pep/population" and var_upper in population_vars:
            filtered.append(var)
        elif dataset_path == "pep/components" and var_upper in components_vars:
            filtered.append(var)
        elif dataset_path == "pep/charagegroups" and var_upper in charagegroups_vars:
            filtered.append(var)
        # Skip variables not compatible with this dataset

    return filtered


def _get_api_dataset_path(product: str, variables: List[str]) -> str:
    """Determine the correct API dataset path based on product and variables.

    Returns:
    - "pep/population" for basic population estimates
    - "pep/components" for components of population change
    - "pep/charagegroups" for characteristics (age, sex, race, Hispanic origin)
    """
    # For characteristics product, use charagegroups dataset
    if product == "characteristics":
        return "pep/charagegroups"

    # Check if ALL variables are components variables
    components_vars = {
        "BIRTHS",
        "DEATHS",
        "DOMESTICMIG",
        "INTERNATIONALMIG",
        "NETMIG",
        "NATURALCHG",
        "NPOPCHG",
        "RESIDUAL",
    }

    # Only use components dataset if:
    # 1. Product is explicitly "components", OR
    # 2. ALL requested variables are components variables (no mixed requests)
    if product == "components":
        return "pep/components"

    # Check if all variables are components variables
    if variables and all(var.upper() in components_vars for var in variables):
        return "pep/components"

    # Default to population dataset for basic population estimates and mixed requests
    return "pep/population"


def _validate_and_set_product(
    product: Optional[str],
    geography: str,
    variables: Optional[Union[str, List[str]]],
    breakdown: Optional[List[str]],
    year: int,
) -> str:
    """Validate and set the product parameter based on inputs.

    Returns the appropriate product type:
    - "characteristics" for demographic breakdowns (ASRH datasets)
    - "components" for components of population change
    - "population" for basic population totals (default)
    """
    # Define valid products
    valid_products = ["population", "components", "characteristics"]

    # If product explicitly provided, validate it
    if product is not None:
        if product not in valid_products:
            raise ValueError(
                f"Product '{product}' not supported. Available options: {', '.join(valid_products)}"
            )

        # Validate product/geography combinations for characteristics
        if product == "characteristics":
            if geography not in ["state"]:  # Temporarily limit to state only
                raise ValueError(
                    f"Characteristics product currently only supported for state geography. "
                    f"County, CBSA, and CSA support coming soon."
                )

        return product

    # Auto-determine product based on inputs

    # If breakdown is specified, must use characteristics
    if breakdown is not None:
        if geography not in ["state"]:  # Temporarily limit to state only
            raise ValueError(
                f"Demographic breakdowns currently only supported for state geography. "
                f"County, CBSA, and CSA support coming soon."
            )
        return "characteristics"

    # If variables suggest components of change, use components
    if variables and isinstance(variables, (list, str)):
        var_list = [variables] if isinstance(variables, str) else variables
        components_vars = {
            "BIRTHS",
            "DEATHS",
            "DOMESTICMIG",
            "INTERNATIONALMIG",
            "NETMIG",
            "NATURALCHG",
            "NPOPCHG",
            "RESIDUAL",
        }

        # If any component variables are requested and no population variables
        if any(v.upper() in components_vars for v in var_list):
            pop_vars = {"POP", "POPESTIMATE", "ESTIMATESBASE"}
            if not any(v.upper() in pop_vars for v in var_list):
                return "components"

    # Default to population for basic totals
    return "population"


def get_estimates(
    geography: str,
    product: Optional[str] = None,
    variables: Optional[Union[str, List[str]]] = None,
    breakdown: Optional[List[str]] = None,
    breakdown_labels: bool = False,
    vintage: int = 2024,
    year: Optional[int] = None,
    state: Optional[Union[str, int, List[Union[str, int]]]] = None,
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    time_series: bool = False,
    output: str = "tidy",
    geometry: bool = False,
    keep_geo_vars: bool = False,
    api_key: Optional[str] = None,
    show_call: bool = False,
    **kwargs,
) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """Obtain data from the US Census Bureau Population Estimates Program.

    The Population Estimates Program (PEP) produces estimates of the population for the United States,
    its states, counties, cities, and towns. For years 2020 and later, data is retrieved from flat
    CSV files. For years 2019 and earlier, data comes from the Census API.

    Parameters
    ----------
    geography : str
        The geography of your data. Options include:
        - 'us' (United States)
        - 'region' (Census regions)
        - 'division' (Census divisions)
        - 'state' (States and DC)
        - 'county' (Counties)
        - 'cbsa' (Core Based Statistical Areas)
        - 'metropolitan statistical area/micropolitan statistical area' (alias for cbsa)
        - 'combined statistical area' (Combined Statistical Areas)
        - 'place' (Incorporated places and Census designated places)
    product : str, optional
        The data product. Options include:
        - 'population' (population totals)
        - 'components' (components of population change)
        - 'characteristics' (population by demographics)
        For years 2020+, only 'characteristics' requires this parameter.
    variables : str or list of str, optional
        Variable ID(s) to retrieve. Use 'all' to get all available variables.
        Common variables include: 'POP', 'BIRTHS', 'DEATHS', 'DOMESTICMIG', 'INTERNATIONALMIG'
    breakdown : list of str, optional
        Population breakdown for characteristics product. Options include:
        - 'AGEGROUP' (age groups)
        - 'SEX' (sex)
        - 'RACE' (race)
        - 'HISP' (Hispanic origin)
        Can be combined, e.g., ['SEX', 'RACE']
    breakdown_labels : bool, default False
        Whether to include human-readable labels for breakdown categories.
    vintage : int, default 2024
        The PEP vintage (dataset version year). Recommended to use the most recent.
    year : int, optional
        The specific data year. Defaults to vintage if not specified.
    state : str, int, or list, optional
        State(s) to retrieve data for. Accepts names, abbreviations, or FIPS codes.
    county : str, int, or list, optional
        County(ies) to retrieve data for. Must be used with state.
    time_series : bool, default False
        Whether to retrieve time series data back to 2010.
    output : str, default "tidy"
        Output format ("tidy" or "wide").
    geometry : bool, default False
        Whether to include geometry for mapping.
    keep_geo_vars : bool, default False
        Whether to keep all geographic variables from shapefiles.
    api_key : str, optional
        Census API key for years 2019 and earlier.
    show_call : bool, default False
        Whether to print the API call URL (for API-based requests).
    **kwargs
        Additional parameters passed to geography functions.

    Returns
    -------
    pandas.DataFrame or geopandas.GeoDataFrame
        Population estimates data, optionally with geometry.

    Examples
    --------
    >>> import pytidycensus as tc
    >>> tc.set_census_api_key("your_key_here")
    >>>
    >>> # Get total population estimates by state
    >>> state_pop = tc.get_estimates(
    ...     geography="state",
    ...     variables="POP",
    ...     year=2022
    ... )
    >>>
    >>> # Get population by age and sex for counties in Texas
    >>> tx_pop_demo = tc.get_estimates(
    ...     geography="county",
    ...     variables="POP",
    ...     breakdown=["SEX", "AGEGROUP"],
    ...     state="TX",
    ...     breakdown_labels=True
    ... )
    """
    # Handle vintage/year parameters like R tidycensus
    if year is None:
        year = vintage

    # Warn if using post-2020 year without explicit vintage
    if year > 2020 and vintage == 2024 and year != vintage:
        warnings.warn(
            f"Using vintage {vintage} data for year {year}. Consider setting vintage={year} if available.",
            UserWarning,
        )

    # Comprehensive input validation
    try:
        _validate_estimates_inputs(
            geography,
            product,
            variables,
            breakdown,
            vintage,
            year,
            state,
            county,
            **kwargs,
        )
    except (InvalidGeographyError, InvalidVariableError, DataNotAvailableError) as e:
        raise e
    except Exception as e:
        raise PopulationEstimatesError(f"Input validation failed: {str(e)}")

    # Normalize geography
    geography = geography.lower()
    if geography in GEOGRAPHY_ALIASES:
        geography = GEOGRAPHY_ALIASES[geography]

    # Validate and set product parameter
    product = _validate_and_set_product(product, geography, variables, breakdown, year)

    # Handle variables
    if not variables:
        variables = ["POP"]  # Default to total population
    elif variables == "all":
        # Will be handled in the data processing functions
        variables = ["all"]
    elif isinstance(variables, str):
        variables = [variables]

    try:
        if year >= 2020:
            print(
                f"Getting data from the {vintage} Population Estimates Program (vintage {vintage})"
            )
        else:
            print(f"Getting data from the {year} Population Estimates Program")

        # For years 2020 and later, use CSV files instead of API
        if year >= 2020:
            df = _get_estimates_from_csv(
                geography,
                product,
                variables,
                breakdown,
                vintage,
                year,
                state,
                county,
                time_series,
                output,
            )
        else:
            # Use API for years before 2020
            df = _get_estimates_from_api(
                geography,
                product,
                variables,
                breakdown,
                year,
                state,
                county,
                time_series,
                output,
                api_key,
                show_call,
                **kwargs,
            )

        # Validate results
        if df is None or df.empty:
            raise DataNotAvailableError(
                f"No data returned for the requested combination. "
                f"This may indicate that the specific geography/variable combination "
                f"is not available for year {year}."
            )

        # Add breakdown labels if requested
        if breakdown_labels and breakdown:
            try:
                df = _add_breakdown_labels(df, breakdown)
            except Exception as e:
                warnings.warn(f"Could not add breakdown labels: {str(e)}", UserWarning)

        # Add geometry if requested
        if geometry:
            try:
                gdf = get_geography(
                    geography=geography,
                    year=year,
                    state=state,
                    county=county,
                    keep_geo_vars=keep_geo_vars,
                    **kwargs,
                )

                # Check if geometry merge will work
                if "GEOID" not in df.columns or "GEOID" not in gdf.columns:
                    raise DataNotAvailableError(
                        "Cannot add geometry: GEOID column missing from data or geography. "
                        "This may indicate incompatible geography selections."
                    )

                df_before_merge = len(df)
                result = gdf.merge(df, on="GEOID", how="inner")

                if len(result) == 0:
                    raise DataNotAvailableError(
                        "No matching geographic boundaries found for the requested data. "
                        "The geography and data parameters may be incompatible."
                    )
                elif len(result) < df_before_merge * 0.5:  # Lost more than half the data
                    warnings.warn(
                        f"Geometry merge resulted in significant data loss: "
                        f"{df_before_merge} -> {len(result)} rows. "
                        f"Some geographic boundaries may be missing.",
                        UserWarning,
                    )

                return result

            except Exception as e:
                if isinstance(e, (DataNotAvailableError, InvalidGeographyError)):
                    raise e
                else:
                    raise PopulationEstimatesError(f"Failed to add geometry: {str(e)}")

        return df

    except (
        InvalidGeographyError,
        InvalidVariableError,
        DataNotAvailableError,
        APIError,
    ) as e:
        # Re-raise our custom exceptions without wrapping
        raise e
    except Exception as e:
        # Wrap unexpected exceptions
        raise PopulationEstimatesError(f"Failed to retrieve population estimates: {str(e)}")


def _get_estimates_from_csv(
    geography: str,
    product: str,  # Now always provided after validation
    variables: List[str],
    breakdown: Optional[List[str]],
    vintage: int,
    year: int,
    state: Optional[Union[str, int, List[Union[str, int]]]],
    county: Optional[Union[str, int, List[Union[str, int]]]],
    time_series: bool,
    output: str,
) -> pd.DataFrame:
    """Get estimates data from CSV files for years 2020+."""

    # Build CSV URL based on geography and vintage
    base_url = f"https://www2.census.gov/programs-surveys/popest/datasets/2020-{vintage}"

    # Handle characteristics product (uses ASRH datasets)
    if product == "characteristics":
        if geography == "state":
            csv_url = f"{base_url}/state/asrh/sc-est{vintage}-alldata6.csv"
        elif geography == "county":
            if state:
                # State-specific county file
                state_code = _get_state_fips(state[0] if isinstance(state, list) else state)
                csv_url = f"{base_url}/counties/asrh/cc-est{vintage}-alldata-{state_code}.csv"
            else:
                # All counties file
                csv_url = f"{base_url}/counties/asrh/cc-est{vintage}-alldata.csv"
        elif geography == "cbsa":
            csv_url = f"{base_url}/metro/asrh/cbsa-est{vintage}-alldata-char.csv"
        elif geography == "combined statistical area":
            csv_url = f"{base_url}/metro/asrh/csa-est{vintage}-alldata-char.csv"
        else:
            raise ValueError(f"Geography '{geography}' not supported for characteristics product")

    # Handle population/components products (uses totals datasets)
    else:
        if geography == "us":
            csv_url = f"{base_url}/state/totals/NST-EST{vintage}-ALLDATA.csv"
        elif geography == "region":
            csv_url = f"{base_url}/state/totals/NST-EST{vintage}-ALLDATA.csv"
        elif geography == "division":
            if vintage < 2022:
                raise ValueError("Divisions not available for vintages before 2022")
            csv_url = f"{base_url}/state/totals/NST-EST{vintage}-ALLDATA.csv"
        elif geography == "state":
            csv_url = f"{base_url}/state/totals/NST-EST{vintage}-ALLDATA.csv"
        elif geography == "county":
            csv_url = f"{base_url}/counties/totals/co-est{vintage}-alldata.csv"
        elif geography == "cbsa":
            if vintage == 2022:
                csv_url = f"{base_url}/metro/totals/cbsa-est{vintage}.csv"
            else:
                csv_url = f"{base_url}/metro/totals/cbsa-est{vintage}-alldata.csv"
        elif geography == "combined statistical area":
            if vintage == 2022:
                csv_url = f"{base_url}/metro/totals/csa-est{vintage}.csv"
            else:
                csv_url = f"{base_url}/metro/totals/csa-est{vintage}-alldata.csv"
        elif geography == "place":
            csv_url = f"{base_url}/cities/totals/sub-est{vintage}.csv"
        else:
            raise ValueError(f"Geography '{geography}' not supported for CSV-based estimates")

    # Download and read CSV
    try:
        response = requests.get(csv_url, verify=False, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), encoding="latin1")

        if df.empty:
            raise DataNotAvailableError(f"Retrieved empty dataset from {csv_url}")

    except requests.exceptions.Timeout:
        raise APIError(
            f"Request timeout while downloading data from Census Bureau. Please try again later."
        )
    except requests.exceptions.ConnectionError:
        raise APIError(
            f"Connection error while accessing Census Bureau data. Please check your internet connection."
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise DataNotAvailableError(
                f"Data not available for the requested combination. "
                f"The Census Bureau may not have published this dataset yet. "
                f"URL: {csv_url}"
            )
        else:
            raise APIError(f"HTTP error {e.response.status_code} while downloading data: {e}")
    except pd.errors.ParserError as e:
        # Try alternative encoding
        try:
            response = requests.get(csv_url, verify=False, timeout=30)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text), encoding="utf-8")

            if df.empty:
                raise DataNotAvailableError(f"Retrieved empty dataset from {csv_url}")

        except Exception as e2:
            raise APIError(
                f"Failed to parse CSV data from Census Bureau. "
                f"This may indicate a data format issue. "
                f"Original error: {e}. Retry with UTF-8: {e2}"
            )
    except Exception as e:
        raise APIError(f"Unexpected error downloading data from Census Bureau: {str(e)}")

    # Process the CSV data
    df = _process_estimates_csv(
        df,
        geography,
        product,
        variables,
        breakdown,
        vintage,
        year,
        state,
        county,
        time_series,
        output,
    )

    return df


def _get_state_fips(state_input: Union[str, int]) -> str:
    """Convert state name/abbreviation to FIPS code."""
    state_map = {
        "AL": "01",
        "AK": "02",
        "AZ": "04",
        "AR": "05",
        "CA": "06",
        "CO": "08",
        "CT": "09",
        "DE": "10",
        "FL": "12",
        "GA": "13",
        "HI": "15",
        "ID": "16",
        "IL": "17",
        "IN": "18",
        "IA": "19",
        "KS": "20",
        "KY": "21",
        "LA": "22",
        "ME": "23",
        "MD": "24",
        "MA": "25",
        "MI": "26",
        "MN": "27",
        "MS": "28",
        "MO": "29",
        "MT": "30",
        "NE": "31",
        "NV": "32",
        "NH": "33",
        "NJ": "34",
        "NM": "35",
        "NY": "36",
        "NC": "37",
        "ND": "38",
        "OH": "39",
        "OK": "40",
        "OR": "41",
        "PA": "42",
        "RI": "44",
        "SC": "45",
        "SD": "46",
        "TN": "47",
        "TX": "48",
        "UT": "49",
        "VT": "50",
        "VA": "51",
        "WA": "53",
        "WV": "54",
        "WI": "55",
        "WY": "56",
        "DC": "11",
    }

    if isinstance(state_input, int):
        return str(state_input).zfill(2)

    state_str = str(state_input).upper()

    if state_str in state_map:
        return state_map[state_str]
    elif state_str.isdigit():
        return state_str.zfill(2)
    else:
        # Try to find by name (simplified)
        return state_str


def _get_estimates_from_api(
    geography: str,
    product: str,  # Now always provided after validation
    variables: List[str],
    breakdown: Optional[List[str]],
    year: int,
    state: Optional[Union[str, int, List[Union[str, int]]]],
    county: Optional[Union[str, int, List[Union[str, int]]]],
    time_series: bool,
    output: str,
    api_key: Optional[str],
    show_call: bool,
    **kwargs,
) -> pd.DataFrame:
    """Get estimates data from Census API for years before 2020."""

    # Add breakdown variables to the request
    all_variables = variables.copy()
    if breakdown:
        all_variables.extend(breakdown)

    # Initialize API client
    api = CensusAPI(api_key)

    # Build geography parameters
    geo_params = build_geography_params(geography, state, county, **kwargs)

    # Determine the appropriate estimates dataset based on product and variables
    dataset_path = _get_api_dataset_path(product, variables)

    # Filter variables for dataset compatibility
    dataset_variables = _filter_variables_for_dataset(dataset_path, all_variables)

    if not dataset_variables:
        raise ValueError(f"No compatible variables found for dataset {dataset_path}")

    # Make API request
    data = api.get(
        year=year,
        dataset=dataset_path,
        variables=dataset_variables,
        geography=geo_params,
        show_call=show_call,
    )

    # Process data - only process the variables that were actually retrieved
    retrieved_variables = [
        v for v in variables if v.upper() in [dv.upper() for dv in dataset_variables]
    ]
    df = process_census_data(data, retrieved_variables, output)

    return df


def _process_estimates_csv(
    df: pd.DataFrame,
    geography: str,
    product: Optional[str],
    variables: List[str],
    breakdown: Optional[List[str]],
    vintage: int,
    year: int,
    state: Optional[Union[str, int, List[Union[str, int]]]],
    county: Optional[Union[str, int, List[Union[str, int]]]],
    time_series: bool,
    output: str,
) -> pd.DataFrame:
    """Process raw CSV estimates data into the expected format."""

    # Handle characteristics product (ASRH datasets)
    if product == "characteristics":
        return _process_characteristics_csv(
            df,
            geography,
            variables,
            breakdown,
            vintage,
            year,
            state,
            county,
            time_series,
            output,
        )

    # Handle population/components products (totals datasets)

    # Filter by year using different methods depending on file structure
    if "DATE" in df.columns:
        # DATE codes: 1=4/1/2020 estimate, 2=4/1/2020 estimates base, 3=7/1/2020, 4=7/1/2021, 5=7/1/2022, 6=7/1/2023, etc.
        date_map = {2020: 3, 2021: 4, 2022: 5, 2023: 6, 2024: 7}
        if year in date_map:
            df = df[df["DATE"] == date_map[year]]

    # Pivot data from wide to long format for consistent processing
    # All CSVs have year-suffixed columns like POPESTIMATE2022, BIRTHS2022, etc.

    # Create base result with GEOID and NAME
    result_df = _create_base_result(df, geography)

    # Filter by geographic selections
    result_df = _apply_geographic_filters(result_df, geography, state, county)

    # Get requested variables
    result_df = _extract_variables(result_df, variables, year, vintage, time_series)

    # Reshape output format
    if time_series or (
        output == "tidy"
        and len([col for col in result_df.columns if col not in ["GEOID", "NAME"]]) > 1
    ):
        id_vars = ["GEOID"]
        if "NAME" in result_df.columns:
            id_vars.append("NAME")

        value_vars = [col for col in result_df.columns if col not in id_vars]

        if time_series:
            # For time series, create year column
            result_df = pd.melt(
                result_df,
                id_vars=id_vars,
                value_vars=value_vars,
                var_name="variable",
                value_name="estimate",
            )

            # Extract year from variable name (e.g., POPESTIMATE2022 -> 2022)
            result_df["year"] = result_df["variable"].str.extract(r"(\d{4})$")[0].astype(int)

            # Clean up variable names (remove year suffix)
            result_df["variable"] = result_df["variable"].str.replace(r"\d{4}$", "", regex=True)

            # Reorder columns
            result_df = result_df[
                (
                    ["GEOID", "NAME", "variable", "year", "estimate"]
                    if "NAME" in result_df.columns
                    else ["GEOID", "variable", "year", "estimate"]
                )
            ]
        else:
            # Regular tidy format
            result_df = pd.melt(
                result_df,
                id_vars=id_vars,
                value_vars=value_vars,
                var_name="variable",
                value_name="estimate",
            )

    return result_df


def _create_base_result(df: pd.DataFrame, geography: str) -> pd.DataFrame:
    """Create base result DataFrame with GEOID and NAME columns."""

    if geography == "us":
        # US total (SUMLEV == 010 or STATE == 00)
        if "SUMLEV" in df.columns:
            df_filtered = df[df["SUMLEV"].astype(str) == "10"].copy()
        else:
            df_filtered = df[df["STATE"].astype(str) == "00"].copy()
        df_filtered["GEOID"] = "1"

    elif geography == "region":
        # Census regions (SUMLEV == 020)
        if "SUMLEV" in df.columns:
            df_filtered = df[df["SUMLEV"].astype(str) == "20"].copy()
            df_filtered["GEOID"] = df_filtered["REGION"].astype(str)
        else:
            raise ValueError("Region data not available in this dataset")

    elif geography == "division":
        # Census divisions (SUMLEV == 030)
        if "SUMLEV" in df.columns:
            df_filtered = df[df["SUMLEV"].astype(str) == "30"].copy()
            df_filtered["GEOID"] = df_filtered["DIVISION"].astype(str)
        else:
            raise ValueError("Division data not available in this dataset")

    elif geography == "state":
        # States (SUMLEV == 040 or STATE codes 01-56)
        if "SUMLEV" in df.columns:
            df_filtered = df[df["SUMLEV"].astype(str) == "40"].copy()
            df_filtered["GEOID"] = df_filtered["STATE"].astype(str).str.zfill(2)
        else:
            df_filtered = df[
                (df["STATE"].astype(str) != "00") & (df["STATE"].astype(int).between(1, 56))
            ].copy()
            df_filtered["GEOID"] = df_filtered["STATE"].astype(str).str.zfill(2)

    elif geography == "county":
        # Counties (SUMLEV == 050 or COUNTY != 000)
        if "SUMLEV" in df.columns:
            df_filtered = df[df["SUMLEV"].astype(str) == "50"].copy()
        else:
            df_filtered = df[df["COUNTY"].astype(str) != "000"].copy()

        df_filtered["GEOID"] = df_filtered["STATE"].astype(str).str.zfill(2) + df_filtered[
            "COUNTY"
        ].astype(str).str.zfill(3)

        # Create county name
        if "CTYNAME" in df_filtered.columns and "STNAME" in df_filtered.columns:
            df_filtered["NAME"] = df_filtered["CTYNAME"] + ", " + df_filtered["STNAME"]
        elif "CTYNAME" in df_filtered.columns:
            df_filtered["NAME"] = df_filtered["CTYNAME"]

    elif geography == "cbsa":
        # Core Based Statistical Areas
        if "CBSA" in df.columns:
            if "LSAD" in df.columns:
                # Filter to actual CBSAs (not divisions)
                df_filtered = df[
                    df["LSAD"].isin(
                        [
                            "Metropolitan Statistical Area",
                            "Micropolitan Statistical Area",
                        ]
                    )
                ].copy()
            else:
                df_filtered = df.copy()
            df_filtered["GEOID"] = df_filtered["CBSA"].astype(str)
        else:
            raise ValueError("CBSA data not available in this dataset")

    elif geography == "combined statistical area":
        # Combined Statistical Areas
        if "CSA" in df.columns:
            if "LSAD" in df.columns:
                df_filtered = df[df["LSAD"] == "Combined Statistical Area"].copy()
            else:
                df_filtered = df.copy()
            df_filtered["GEOID"] = df_filtered["CSA"].astype(str)
        else:
            raise ValueError("Combined Statistical Area data not available in this dataset")

    elif geography == "place":
        # Places (SUMLEV == 162)
        if "SUMLEV" in df.columns:
            df_filtered = df[df["SUMLEV"].astype(str) == "162"].copy()
            df_filtered["GEOID"] = df_filtered["STATE"].astype(str).str.zfill(2) + df_filtered[
                "PLACE"
            ].astype(str).str.zfill(5)

            # Create place name with state
            if "NAME" in df_filtered.columns and "STNAME" in df_filtered.columns:
                df_filtered["NAME"] = df_filtered["NAME"] + ", " + df_filtered["STNAME"]
        else:
            raise ValueError("Place data not available in this dataset")
    else:
        raise ValueError(f"Unsupported geography: {geography}")

    # Ensure we have a NAME column
    if "NAME" not in df_filtered.columns and "NAME" in df.columns:
        df_filtered["NAME"] = df["NAME"]

    return df_filtered


def _apply_geographic_filters(
    df: pd.DataFrame,
    geography: str,
    state: Optional[Union[str, int, List[Union[str, int]]]],
    county: Optional[Union[str, int, List[Union[str, int]]]],
) -> pd.DataFrame:
    """Apply state and county filters to the DataFrame."""

    # Filter by state if specified
    if state is not None and geography in ["county", "state", "place"]:
        if isinstance(state, (str, int)):
            state = [state]

        state_fips = []
        for s in state:
            state_fips.append(_get_state_fips(s))

        if geography in ["state", "place"]:
            df = df[df["GEOID"].str[:2].isin(state_fips)]
        elif geography == "county":
            df = df[df["GEOID"].str[:2].isin(state_fips)]

    # Filter by county if specified
    if county is not None and geography == "county":
        if isinstance(county, (str, int)):
            county = [county]

        county_fips = [str(c).zfill(3) for c in county]
        df = df[df["GEOID"].str[2:5].isin(county_fips)]

    return df


def _extract_variables(
    df: pd.DataFrame,
    variables: List[str],
    year: int,
    vintage: int,
    time_series: bool = False,
) -> pd.DataFrame:
    """Extract requested variables from the DataFrame."""

    # Handle 'all' variables request
    if variables == ["all"]:
        if time_series:
            # Find all variable patterns across all years
            all_year_cols = [
                col
                for col in df.columns
                if any(col.startswith(v) for v in VARIABLE_MAPPING.values())
            ]
            unique_vars = set()
            for col in all_year_cols:
                for var_name in VARIABLE_MAPPING.values():
                    if col.startswith(var_name):
                        unique_vars.add(var_name)
            variables = list(unique_vars)
        else:
            # Find all year-suffixed columns for the specific year
            year_cols = [
                col
                for col in df.columns
                if col.endswith(str(year)) and col not in ["GEOID", "NAME"]
            ]
            variables = []
            for col in year_cols:
                for short_name, full_name in VARIABLE_MAPPING.items():
                    if col.startswith(full_name):
                        variables.append(short_name)
                        break
            if not variables:
                variables = [col.replace(str(year), "") for col in year_cols]

    # Map variables to actual column names
    result_cols = ["GEOID"]
    if "NAME" in df.columns:
        result_cols.append("NAME")

    if time_series:
        # For time series, get all years available for each variable
        for var in variables:
            full_var = VARIABLE_MAPPING.get(var, var)

            # Find all year columns for this variable
            year_cols = [
                col
                for col in df.columns
                if col.startswith(full_var) and col[len(full_var) :].isdigit()
            ]
            result_cols.extend(year_cols)
    else:
        # For single year, get just the requested year
        for var in variables:
            full_var = VARIABLE_MAPPING.get(var, var)

            # Try different column name patterns
            possible_cols = [
                f"{full_var}{year}",  # POPESTIMATE2022
                f"{full_var}_{year}",  # POPESTIMATE_2022
                f"{var}{year}",  # POP2022 (if user provided full name)
                var,  # Exact match
            ]

            for col in possible_cols:
                if col in df.columns:
                    result_cols.append(col)
                    break

    # Select available columns
    available_cols = [col for col in result_cols if col in df.columns]
    return df[available_cols]


def _apply_geography_filter(df: pd.DataFrame, geography: str, state, county) -> pd.DataFrame:
    """Apply geography filtering to ASRH data."""

    # Geography filtering based on SUMLEV codes
    geography_sumlevs = {
        "state": [40],
        "county": [50],
        "cbsa": [310],  # Core Based Statistical Areas
        "combined statistical area": [320],  # Combined Statistical Areas
    }

    if geography in geography_sumlevs:
        df = df[df["SUMLEV"].isin(geography_sumlevs[geography])]

    # State filtering
    if state is not None:
        state_codes = []
        if isinstance(state, (list, tuple)):
            for s in state:
                state_codes.append(_get_state_fips(s))
        else:
            state_codes.append(_get_state_fips(state))

        df = df[df["STATE"].astype(str).str.zfill(2).isin(state_codes)]

    # County filtering
    if county is not None and "COUNTY" in df.columns:
        county_codes = []
        if isinstance(county, (list, tuple)):
            county_codes = [str(c).zfill(3) for c in county]
        else:
            county_codes = [str(county).zfill(3)]

        df = df[df["COUNTY"].astype(str).str.zfill(3).isin(county_codes)]

    return df


def _apply_breakdown_filter(df: pd.DataFrame, breakdown: List[str]) -> pd.DataFrame:
    """Apply demographic breakdown filtering to ASRH data."""

    # Breakdown dimension mapping
    breakdown_dims = {
        "SEX": "SEX",
        "ORIGIN": "ORIGIN",
        "RACE": "RACE",
        "AGE": "AGE",
        "AGEGROUP": "AGE",  # Handle both AGE and AGEGROUP
    }

    # Normalize breakdown names
    requested_dims = set()
    for b in breakdown:
        if b.upper() in breakdown_dims:
            requested_dims.add(breakdown_dims[b.upper()])

    # ASRH data has specific structure - handle common breakdown combinations:
    # 1. RACE only: SEX=0, ORIGIN=0, RACE!=0, AGE=0
    # 2. SEX+RACE: SEX!=0, ORIGIN=0, RACE!=0, AGE=0
    # 3. ORIGIN is only available in fully crossed tables (with RACE/SEX)

    if requested_dims == {"RACE"}:
        # Race-only breakdown
        df = df[(df["SEX"] == 0) & (df["ORIGIN"] == 0) & (df["RACE"] != 0) & (df["AGE"] == 0)]

    elif requested_dims == {"SEX", "RACE"}:
        # Sex and race breakdown
        df = df[(df["SEX"] != 0) & (df["ORIGIN"] == 0) & (df["RACE"] != 0) & (df["AGE"] == 0)]

    elif requested_dims == {"SEX"}:
        # Sex-only not available in pure form - sum across all races for each sex
        # Filter to get sex breakdown with ORIGIN=0, AGE=0, any RACE, then aggregate
        sex_data = df[(df["SEX"] != 0) & (df["ORIGIN"] == 0) & (df["RACE"] != 0) & (df["AGE"] == 0)]
        # Group by sex and sum across races to get sex totals
        if not sex_data.empty:
            # Identify year columns for aggregation
            year_cols = [col for col in sex_data.columns if col.startswith("POPESTIMATE")]
            id_cols = ["STATE", "NAME", "SEX", "GEOID"]

            # Sum across races for each sex
            groupby_cols = [col for col in id_cols if col in sex_data.columns and col != "SEX"] + [
                "SEX"
            ]
            agg_dict = {col: "sum" for col in year_cols if col in sex_data.columns}

            if agg_dict:
                df = sex_data.groupby(groupby_cols, as_index=False).agg(agg_dict)
                # Set other dimensions to indicate totals (these columns may not exist yet)
                if "ORIGIN" not in df.columns:
                    df["ORIGIN"] = 0
                if "RACE" not in df.columns:
                    df["RACE"] = 0
                if "AGE" not in df.columns:
                    df["AGE"] = 0
            else:
                df = pd.DataFrame()  # Empty if no year columns found
        else:
            df = pd.DataFrame()  # Empty if no data found

    elif requested_dims == {"ORIGIN"}:
        # Origin-only breakdown - provide origin totals across race categories
        # Get the least detailed origin breakdown available
        df = df[(df["SEX"] == 0) & (df["ORIGIN"] != 0) & (df["RACE"] == 1) & (df["AGE"] == 0)]

    elif requested_dims == {"ORIGIN", "RACE"}:
        # Origin and race breakdown
        df = df[(df["SEX"] == 0) & (df["ORIGIN"] != 0) & (df["RACE"] != 0) & (df["AGE"] == 0)]

    elif "ORIGIN" in requested_dims and "SEX" in requested_dims:
        # Any combination with ORIGIN and SEX - use fully crossed data
        if "RACE" in requested_dims:
            # All three dimensions
            df = df[(df["SEX"] != 0) & (df["ORIGIN"] != 0) & (df["RACE"] != 0) & (df["AGE"] == 0)]
        else:
            # ORIGIN + SEX, aggregate across races
            df = df[(df["SEX"] != 0) & (df["ORIGIN"] != 0) & (df["RACE"] == 1) & (df["AGE"] == 0)]

    else:
        # Default: include total records only
        df = df[(df["SEX"] == 0) & (df["ORIGIN"] == 0) & (df["RACE"] == 0) & (df["AGE"] == 0)]

    return df


def _reshape_characteristics_tidy(
    df: pd.DataFrame,
    variables: List[str],
    year_columns: List[str],
    breakdown_cols: List[str],
) -> pd.DataFrame:
    """Reshape characteristics data to tidy format."""

    # Identify ID columns (non-estimate columns)
    id_cols = [col for col in df.columns if col not in year_columns]

    # Melt the year columns
    df_melted = pd.melt(
        df,
        id_vars=id_cols,
        value_vars=year_columns,
        var_name="year_col",
        value_name="estimate",
    )

    # Extract year from column name
    df_melted["year"] = df_melted["year_col"].str.extract(r"(\d{4})").astype(int)
    df_melted.drop("year_col", axis=1, inplace=True)

    # Add variable column (always POP for characteristics)
    df_melted["variable"] = "POP"

    return df_melted


def _process_characteristics_csv(
    df: pd.DataFrame,
    geography: str,
    variables: List[str],
    breakdown: Optional[List[str]],
    vintage: int,
    year: int,
    state: Optional[Union[str, int, List[Union[str, int]]]],
    county: Optional[Union[str, int, List[Union[str, int]]]],
    time_series: bool,
    output: str,
) -> pd.DataFrame:
    """Process characteristics (ASRH) CSV data with demographic breakdowns."""

    print(f"Processing characteristics data with breakdown: {breakdown}")

    # Apply geography filtering
    df = _apply_geography_filter(df, geography, state, county)

    # Apply breakdown filtering
    if breakdown:
        df = _apply_breakdown_filter(df, breakdown)

    # Handle variables and years
    if time_series:
        year_columns = [col for col in df.columns if col.startswith("POPESTIMATE")]
        if not year_columns:
            year_columns = [f"POPESTIMATE{year}"]
    else:
        year_columns = [f"POPESTIMATE{year}"]

    # Select relevant columns
    id_cols = ["STATE", "COUNTY", "CBSA", "CSA", "PLACE", "NAME", "GEOID"]
    breakdown_cols = ["SEX", "ORIGIN", "RACE", "AGE"] if breakdown else []

    # Build column list based on available columns
    keep_cols = []
    for col in id_cols + breakdown_cols + year_columns:
        if col in df.columns:
            keep_cols.append(col)

    df = df[keep_cols]

    # Create GEOID if not present
    if "GEOID" not in df.columns:
        if geography == "state" and "STATE" in df.columns:
            df["GEOID"] = df["STATE"].astype(str).str.zfill(2)
        elif geography == "county" and "STATE" in df.columns and "COUNTY" in df.columns:
            df["GEOID"] = df["STATE"].astype(str).str.zfill(2) + df["COUNTY"].astype(str).str.zfill(
                3
            )

    # Reshape data based on output format
    if output == "tidy":
        return _reshape_characteristics_tidy(df, variables, year_columns, breakdown_cols)
    else:
        return df


def _add_breakdown_labels(df: pd.DataFrame, breakdown: List[str]) -> pd.DataFrame:
    """Add human-readable labels for breakdown categories.

    Parameters
    ----------
    df : pd.DataFrame
        Population estimates data
    breakdown : List[str]
        Breakdown variables

    Returns
    -------
    pd.DataFrame
        Data with added label columns
    """
    # Define label mappings
    label_mappings = {
        "SEX": {"0": "Total", "1": "Male", "2": "Female"},
        "AGEGROUP": {
            "0": "Total",
            "1": "0-4 years",
            "2": "5-9 years",
            "3": "10-14 years",
            "4": "15-19 years",
            "5": "20-24 years",
            "6": "25-29 years",
            "7": "30-34 years",
            "8": "35-39 years",
            "9": "40-44 years",
            "10": "45-49 years",
            "11": "50-54 years",
            "12": "55-59 years",
            "13": "60-64 years",
            "14": "65-69 years",
            "15": "70-74 years",
            "16": "75-79 years",
            "17": "80-84 years",
            "18": "85+ years",
        },
        "RACE": {
            "0": "Total",
            "1": "White alone",
            "2": "Black or African American alone",
            "3": "American Indian and Alaska Native alone",
            "4": "Asian alone",
            "5": "Native Hawaiian and Other Pacific Islander alone",
            "6": "Two or More Races",
        },
        "HISP": {
            "0": "Total",
            "1": "Not Hispanic or Latino",
            "2": "Hispanic or Latino",
        },
    }

    # Add label columns
    for var in breakdown:
        if var in df.columns and var in label_mappings:
            df[f"{var}_label"] = df[var].astype(str).map(label_mappings[var])

    return df


def discover_available_variables(vintage: int = 2024, geography: str = "state") -> pd.DataFrame:
    """Discover all available variables in a PEP dataset.

    Parameters
    ----------
    vintage : int, default 2024
        The vintage year of the dataset
    geography : str, default "state"
        The geography to check for available variables

    Returns
    -------
    pd.DataFrame
        DataFrame with variable names and descriptions
    """
    try:
        # Download a sample CSV to discover variables
        if geography == "state":
            csv_url = f"https://www2.census.gov/programs-surveys/popest/datasets/2020-{vintage}/state/totals/NST-EST{vintage}-ALLDATA.csv"
        elif geography == "county":
            csv_url = f"https://www2.census.gov/programs-surveys/popest/datasets/2020-{vintage}/counties/totals/co-est{vintage}-alldata.csv"
        else:
            raise ValueError("Only state and county supported for variable discovery")

        response = requests.get(csv_url, verify=False)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), encoding="latin1", nrows=1)  # Just get headers

        # Extract variable information
        variables = []
        descriptions = []

        # Define variable patterns and descriptions
        var_patterns = {
            r"POPESTIMATE(\d{4})": "Total population estimate",
            r"ESTIMATESBASE(\d{4})": "Population estimates base",
            r"BIRTHS(\d{4})": "Births",
            r"DEATHS(\d{4})": "Deaths",
            r"NATURALCHG(\d{4})": "Natural change (births - deaths)",
            r"INTERNATIONALMIG(\d{4})": "International migration",
            r"DOMESTICMIG(\d{4})": "Domestic migration",
            r"NETMIG(\d{4})": "Net migration",
            r"NPOPCHG[_-]?(\d{4})": "Net population change",
            r"RESIDUAL(\d{4})": "Residual",
            r"GQESTIMATESBASE(\d{4})": "Group quarters population estimates base",
            r"GQESTIMATES(\d{4})": "Group quarters population",
            r"RBIRTH(\d{4})": "Birth rate per 1,000 population",
            r"RDEATH(\d{4})": "Death rate per 1,000 population",
            r"RNATURALCHG(\d{4})": "Natural change rate per 1,000 population",
            r"RINTERNATIONALMIG(\d{4})": "International migration rate per 1,000 population",
            r"RDOMESTICMIG(\d{4})": "Domestic migration rate per 1,000 population",
            r"RNETMIG(\d{4})": "Net migration rate per 1,000 population",
        }

        import re

        for col in df.columns:
            if col in [
                "SUMLEV",
                "REGION",
                "DIVISION",
                "STATE",
                "COUNTY",
                "NAME",
                "STNAME",
                "CTYNAME",
            ]:
                continue

            matched = False
            for pattern, desc in var_patterns.items():
                match = re.match(pattern, col)
                if match:
                    year = match.group(1)
                    var_base = col.replace(year, "")
                    if var_base not in [v.split("_")[0] for v in variables]:  # Avoid duplicates
                        variables.append(f"{var_base}_{year}")
                        descriptions.append(f"{desc} ({year})")
                    matched = True
                    break

            if not matched:
                variables.append(col)
                descriptions.append("Unknown variable")

        result_df = pd.DataFrame({"variable": variables, "description": descriptions})

        return result_df

    except Exception as e:
        print(f"Warning: Could not discover variables: {e}")
        return pd.DataFrame({"variable": [], "description": []})


def get_estimates_variables(year: int = 2022) -> pd.DataFrame:
    """Get available population estimates variables for a given year.

    Parameters
    ----------
    year : int, default 2022
        Estimates year

    Returns
    -------
    pd.DataFrame
        Available variables with metadata
    """
    from .variables import load_variables

    return load_variables(year, "pep", "population")
