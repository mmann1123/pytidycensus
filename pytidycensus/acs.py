"""
American Community Survey (ACS) data retrieval functions.
"""

import warnings
from typing import Any, Dict, List, Optional, Union

import geopandas as gpd
import pandas as pd

from .api import CensusAPI
from .geography import get_geography
from .utils import (
    add_margin_of_error,
    build_geography_params,
    process_census_data,
    validate_geography,
    validate_state,
    validate_year,
)


def get_acs(
    geography: str,
    variables: Optional[Union[str, List[str], Dict[str, str]]] = None,
    table: Optional[str] = None,
    cache_table: bool = False,
    year: int = 2022,
    survey: str = "acs5",
    state: Optional[Union[str, int, List[Union[str, int]]]] = None,
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    zcta: Optional[Union[str, List[str]]] = None,
    output: str = "tidy",
    geometry: bool = False,
    keep_geo_vars: bool = False,
    shift_geo: bool = False,
    summary_var: Optional[str] = None,
    moe_level: int = 90,
    api_key: Optional[str] = None,
    show_call: bool = False,
    **kwargs,
) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """
    Obtain data from the American Community Survey (ACS).

    Parameters
    ----------
    geography : str
        The geography of your data (e.g., 'county', 'tract', 'block group').
    variables : str, list of str, or dict, optional
        Variable ID(s) to retrieve. Can be a single variable, list of variables,
        or dictionary mapping custom names to variable IDs. If not provided, must specify table.
    table : str, optional
        ACS table ID to retrieve all variables from.
    cache_table : bool, default False
        Whether to cache table names for faster future access.
    year : int, default 2022
        Year of ACS data (2009-2022 for 5-year, 2005-2022 for 1-year).
    survey : str, default "acs5"
        ACS survey type ("acs1", "acs3", or "acs5").
    state : str, int, or list, optional
        State(s) to retrieve data for. Accepts names, abbreviations, or FIPS codes.
    county : str, int, or list, optional
        County(ies) to retrieve data for. Must be used with state.
    zcta : str or list of str, optional
        ZIP Code Tabulation Area(s) to retrieve data for. Geography must be "zcta".
    output : str, default "tidy"
        Output format ("tidy" or "wide").
    geometry : bool, default False
        Whether to include geometry for mapping.
    keep_geo_vars : bool, default False
        Whether to keep all geographic variables from shapefiles.
    shift_geo : bool, default False
        (Deprecated) If True, warn user to use alternative geometry shifting.
    summary_var : str, optional
        Summary variable from the ACS to include for comparison (e.g. total population).
    moe_level : int, default 90
        Confidence level for margin of error (90, 95, or 99).
    api_key : str, optional
        Census API key. If not provided, looks for CENSUS_API_KEY environment variable.
    show_call : bool, default False
        Whether to print the API call URL.
    **kwargs
        Additional parameters passed to geography functions.

    Returns
    -------
    pandas.DataFrame or geopandas.GeoDataFrame
        ACS data, optionally with geometry.

    Examples
    --------
    >>> import pytidycensus as tc
    >>> tc.set_census_api_key("your_key_here")
    >>>
    >>> # Get median household income by county in Texas
    >>> tx_income = tc.get_acs(
    ...     geography="county",
    ...     variables="B19013_001",
    ...     state="TX",
    ...     year=2022
    ... )
    >>>
    >>> # Get data with geometry for mapping
    >>> tx_income_geo = tc.get_acs(
    ...     geography="county",
    ...     variables="B19013_001",
    ...     state="TX",
    ...     geometry=True
    ... )
    >>>
    >>> # Get data with named variables
    >>> tx_demo = tc.get_acs(
    ...     geography="county",
    ...     variables={"total_pop": "B01003_001", "median_income": "B19013_001"},
    ...     state="TX",
    ...     year=2022
    ... )
    """
    # R tidycensus mirrored validations and messages
    if shift_geo:
        import warnings

        warnings.warn(
            "The `shift_geo` argument is deprecated and will be removed in a future release. "
            "We recommend using alternative geometry shifting methods instead.",
            DeprecationWarning,
        )

    # Survey-specific messages (mirror R tidycensus)
    if survey == "acs1":
        print(f"Getting data from the {year} 1-year ACS")
        print(
            "The 1-year ACS provides data for geographies with populations of 65,000 and greater."
        )
    elif survey == "acs3":
        startyear = year - 2
        print(f"Getting data from the {startyear}-{year} 3-year ACS")
        print(
            "The 3-year ACS provides data for geographies with populations of 20,000 and greater."
        )
    elif survey == "acs5":
        startyear = year - 4
        print(f"Getting data from the {startyear}-{year} 5-year ACS")

    # Error message for 1-year 2020 ACS (mirrors R tidycensus)
    if year == 2020 and survey == "acs1":
        raise ValueError(
            "The regular 1-year ACS for 2020 was not released and is not available in pytidycensus. "
            "Due to low response rates, the Census Bureau instead released a set of experimental estimates for the 2020 1-year ACS. "
            "These estimates can be downloaded at https://www.census.gov/programs-surveys/acs/data/experimental-data/1-year.html. "
            "1-year ACS data can still be accessed for other years by supplying an appropriate year to the `year` parameter."
        )

    # Validate inputs
    year = validate_year(year, "acs")
    geography = validate_geography(geography)

    # Survey validation (mirror R tidycensus)
    if survey == "acs5" and year < 2009:
        raise ValueError(
            "5-year ACS support begins with the 2005-2009 5-year ACS. Consider using decennial Census data instead."
        )

    if survey == "acs1" and year < 2005:
        raise ValueError(
            "1-year ACS support begins with the 2005 1-year ACS. Consider using decennial Census data instead."
        )

    if survey == "acs3" and (year < 2007 or year > 2013):
        raise ValueError(
            "3-year ACS support begins with the 2005-2007 3-year ACS and ends with the 2011-2013 3-year ACS. For newer data, use the 1-year or 5-year ACS."
        )

    if survey not in ["acs1", "acs3", "acs5"]:
        raise ValueError("Survey must be 'acs1', 'acs3', or 'acs5'")

    # Geography-specific validations (mirror R tidycensus)
    if geography == "block":
        raise ValueError(
            "Block data are not available in the ACS. Use `get_decennial()` to access block data from the 2010 Census."
        )

    # Handle geography aliases (mirror R tidycensus)
    if geography == "cbg":
        geography = "block group"

    if geography == "cbsa":
        geography = "metropolitan statistical area/micropolitan statistical area"

    if geography == "zcta":
        geography = "zip code tabulation area"
        if not zcta and not state:
            raise ValueError(
                "ZCTA data requires specifying either `zcta` parameter or `state`."
            )

    if shift_geo and not geometry:
        raise ValueError(
            "`shift_geo` is only available when requesting feature geometry with `geometry = TRUE`"
        )

    if not variables and not table:
        raise ValueError(
            "Either a vector of variables or an ACS table must be specified."
        )

    if variables and table:
        raise ValueError(
            "Specify variables or a table to retrieve; they cannot be combined."
        )

    if table and len(table) > 1 if isinstance(table, list) else False:
        raise ValueError("Only one table may be requested per call.")

    # MOE level validation
    if moe_level not in [90, 95, 99]:
        raise ValueError("moe_level must be 90, 95, or 99")

    # Handle named variables (dictionary support - mirror R tidycensus functionality)
    variable_names = None
    if isinstance(variables, dict):
        variable_names = variables
        variables = list(variables.values())

    # Handle table request
    if table:
        # Load variables for the table
        from .variables import load_variables

        var_df = load_variables(year, "acs", survey, cache=cache_table)
        table_vars = var_df[var_df["name"].str.startswith(table + "_")]["name"].tolist()
        if not table_vars:
            raise ValueError(f"No variables found for table {table}")
        variables = table_vars

    # Ensure variables is a list
    if isinstance(variables, str):
        variables = [variables]

    # Process variables to ensure proper ACS format with E suffix
    processed_variables = []
    for var in variables:
        # For ACS, variables need 'E' suffix for estimates
        if not var.endswith("E") and not var.endswith("M"):
            # Add 'E' suffix for estimate variables
            processed_variables.append(var + "E")
        else:
            processed_variables.append(var)

    # Add margin of error variables for ACS
    all_variables = []
    for var in processed_variables:
        all_variables.append(var)
        # Add corresponding MOE variable
        if var.endswith("E"):
            moe_var = var[:-1] + "M"
            all_variables.append(moe_var)

    # Initialize API client
    api = CensusAPI(api_key)

    # Build geography parameters
    geo_params = build_geography_params(geography, state, county, **kwargs)

    # Handle summary variable
    summary_data = None
    if summary_var:
        # Process summary variable to ensure proper ACS format
        if not summary_var.endswith("E") and not summary_var.endswith("M"):
            summary_var = summary_var + "E"

        # Add summary variable to API request
        if summary_var not in all_variables:
            all_variables.append(summary_var)
            # Add MOE for summary variable too
            if summary_var.endswith("E"):
                summary_moe = summary_var[:-1] + "M"
                if summary_moe not in all_variables:
                    all_variables.append(summary_moe)

    # Make API request
    try:
        # Remove duplicate print that was moved up to validation section

        data = api.get(
            year=year,
            dataset="acs",
            variables=all_variables,
            geography=geo_params,
            survey=survey,
            show_call=show_call,
        )

        # convert to wide if requesting geometry
        if geometry:
            output = "wide"

        # Process data (use processed variables with E suffix)
        df = process_census_data(
            data, all_variables, output
        )  #        df = process_census_data(data, processed_variables, output)

        # Add margin of error handling with MOE level adjustment
        df = add_margin_of_error(df, all_variables, moe_level=moe_level, output=output)
        #        df = add_margin_of_error(df, processed_variables, moe_level=moe_level)

        # Handle named variables (replace variable codes with custom names)
        if variable_names and output == "tidy":
            # Create reverse mapping from processed variable codes to original names
            # Need to map both original and processed variable codes
            code_to_name = {}
            for custom_name, original_code in variable_names.items():
                # Map the processed code (with E suffix) to the custom name
                processed_code = (
                    original_code + "E"
                    if not original_code.endswith("E")
                    and not original_code.endswith("M")
                    else original_code
                )
                code_to_name[processed_code] = custom_name
                # Also map the original code just in case
                code_to_name[original_code] = custom_name
                code_to_name[original_code + "_moe"] = custom_name + "_moe"

            df["variable"] = df["variable"].map(lambda x: code_to_name.get(x, x))
        elif variable_names and output == "wide":
            # Rename columns for wide format
            rename_dict = {}
            for custom_name, original_code in variable_names.items():
                # Handle processed variable names (with E suffix)
                processed_code = (
                    original_code + "E"
                    if not original_code.endswith("E")
                    and not original_code.endswith("M")
                    else original_code
                )
                if processed_code in df.columns:
                    rename_dict[processed_code] = custom_name
                # Also try original code
                if original_code in df.columns:
                    rename_dict[original_code] = custom_name
                # Also rename MOE columns
                if processed_code.endswith("E"):
                    moe_col = original_code + "_moe"
                else:
                    moe_col = processed_code + "_moe"
                if moe_col in df.columns:
                    rename_dict[moe_col] = custom_name + "_moe"
            df = df.rename(columns=rename_dict)

        # Handle summary variable joining (mirror R tidycensus)
        if summary_var:
            summary_col = summary_var
            if summary_col in df.columns:
                if output == "tidy":
                    # In tidy format, join summary value by GEOID
                    summary_df = df[df["variable"] == summary_var][
                        ["GEOID", "value"]
                    ].copy()
                    summary_df = summary_df.rename(columns={"value": "summary_value"})
                    # Remove summary variable from main data
                    df = df[df["variable"] != summary_var]
                    # Join summary values
                    df = df.merge(summary_df, on="GEOID", how="left")
                else:
                    # In wide format, rename summary column
                    df = df.rename(columns={summary_var: "summary_value"})

        # Add geometry if requested
        if geometry:
            gdf = get_geography(
                geography=geography,
                year=year,
                state=state,
                county=county,
                keep_geo_vars=keep_geo_vars,
                **kwargs,
            )

            # Merge with census data
            if "GEOID" in df.columns and "GEOID" in gdf.columns:
                result = gdf.merge(df, on="GEOID", how="inner")
                return result
            else:
                print("Warning: Could not merge with geometry - GEOID column missing")
                return df

        return df

    except Exception as e:
        raise Exception(f"Failed to retrieve ACS data: {str(e)}")


def get_acs_variables(year: int = 2022, survey: str = "acs5") -> pd.DataFrame:
    """
    Get available ACS variables for a given year and survey.

    Parameters
    ----------
    year : int, default 2022
        ACS year
    survey : str, default "acs5"
        Survey type ("acs1" or "acs5")

    Returns
    -------
    pd.DataFrame
        Available variables with metadata
    """
    from .variables import load_variables

    return load_variables(year, "acs", survey)
