"""
Decennial Census data retrieval functions.
"""

import warnings
from typing import Any, Dict, List, Optional, Union

import geopandas as gpd
import pandas as pd

from .api import CensusAPI
from .geography import get_geography
from .utils import (
    build_geography_params,
    process_census_data,
    validate_geography,
    validate_state,
    validate_year,
)


def get_decennial(
    geography: str,
    variables: Optional[Union[str, List[str], Dict[str, str]]] = None,
    table: Optional[str] = None,
    cache_table: bool = False,
    year: int = 2020,
    sumfile: Optional[str] = None,
    state: Optional[Union[str, int, List[Union[str, int]]]] = None,
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    output: str = "tidy",
    geometry: bool = False,
    keep_geo_vars: bool = False,
    shift_geo: bool = False,
    summary_var: Optional[str] = None,
    pop_group: Optional[str] = None,
    pop_group_label: bool = False,
    api_key: Optional[str] = None,
    show_call: bool = False,
    **kwargs,
) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """
    Obtain data from the US Decennial Census.

    Parameters
    ----------
    geography : str
        The geography of your data (e.g., 'county', 'tract', 'block group').
    variables : str, list of str, or dict, optional
        Variable ID(s) to retrieve. Can be a single variable, list of variables,
        or dictionary mapping custom names to variable IDs. If not provided, must specify table.
    table : str, optional
        Census table ID to retrieve all variables from.
    cache_table : bool, default False
        Whether to cache table names for faster future access.
    year : int, default 2020
        Census year (2000, 2010, or 2020). Note: 1990 data is not available via the API.
    sumfile : str, optional
        Summary file to use. Defaults to 'pl' for 2020, 'sf1' for earlier years.
        Available options vary by year.
    state : str, int, or list, optional
        State(s) to retrieve data for. Accepts names, abbreviations, or FIPS codes.
    county : str, int, or list, optional
        County(ies) to retrieve data for. Must be used with state.
    output : str, default "tidy"
        Output format ("tidy" or "wide").
    geometry : bool, default False
        Whether to include geometry for mapping.
    keep_geo_vars : bool, default False
        Whether to keep all geographic variables from shapefiles.
    shift_geo : bool, default False
        (Deprecated) If True, warn user to use alternative geometry shifting.
    summary_var : str, optional
        Summary variable from the decennial Census to include for comparison.
    pop_group : str, optional
        Population group code for which you'd like to request data (for selected sumfiles).
    pop_group_label : bool, default False
        If True, return a pop_group_label column with the population group description.
    api_key : str, optional
        Census API key. If not provided, looks for CENSUS_API_KEY environment variable.
    show_call : bool, default False
        Whether to print the API call URL.
    **kwargs
        Additional parameters passed to geography functions.

    Returns
    -------
    pandas.DataFrame or geopandas.GeoDataFrame
        Decennial Census data, optionally with geometry.

    Examples
    --------
    >>> import pytidycensus as tc
    >>> tc.set_census_api_key("your_key_here")
    >>>
    >>> # Get total population by state for 2020
    >>> pop_2020 = tc.get_decennial(
    ...     geography="state",
    ...     variables="P1_001N",
    ...     year=2020
    ... )
    >>>
    >>> # Get race/ethnicity data with geometry
    >>> race_data = tc.get_decennial(
    ...     geography="county",
    ...     variables=["P1_003N", "P1_004N", "P1_005N"],
    ...     state="CA",
    ...     year=2020,
    ...     geometry=True
    ... )
    >>>
    >>> # Get data with named variables and summary variable
    >>> pop_data = tc.get_decennial(
    ...     geography="county",
    ...     variables={"total": "P1_001N", "white": "P1_003N"},
    ...     state="TX",
    ...     year=2020,
    ...     summary_var="P1_001N"
    ... )
    """
    # R tidycensus mirrored validations and messages
    if shift_geo:
        warnings.warn(
            "The `shift_geo` argument is deprecated and will be removed in a future release. "
            "We recommend using alternative geometry shifting methods instead.",
            DeprecationWarning,
        )

    print(f"Getting data from the {year} decennial Census")

    # Validate inputs (mirror R tidycensus)
    year = validate_year(year, "dec")
    geography = validate_geography(geography)

    # 1990 data not available (mirror R tidycensus)
    if year == 1990:
        raise ValueError(
            "The 1990 decennial Census endpoint has been removed by the Census Bureau. "
            "We will support 1990 data again when the endpoint is updated; in the meantime, "
            "we recommend using NHGIS (https://nhgis.org) and the ipumsr Python package."
        )

    # Handle geography aliases (mirror R tidycensus)
    if geography == "cbg":
        geography = "block group"

    if geography == "cbsa":
        geography = "metropolitan statistical area/micropolitan statistical area"

    if geography == "zcta":
        geography = "zip code tabulation area"

    # Geography-specific validations (mirror R tidycensus)
    if geography == "voting district" and year != 2020:
        raise ValueError("`year` must be 2020 for voting districts.")

    if year == 2020 and sumfile == "pl" and geography == "public use microdata area":
        raise ValueError("PUMAs are not available in the 2020 PL file.")

    if year == 2020 and sumfile == "pl" and geography == "zip code tabulation area":
        raise ValueError("ZCTAs are not available in the 2020 PL file.")

    if shift_geo and not geometry:
        raise ValueError(
            "`shift_geo` is only available when requesting feature geometry with `geometry = TRUE`"
        )

    if not variables and not table:
        raise ValueError("Either a vector of variables or a table must be specified.")

    if variables and table:
        raise ValueError(
            "Specify variables or a table to retrieve; they cannot be combined."
        )

    if table and len(table) > 1 if isinstance(table, list) else False:
        raise ValueError("Only one table may be requested per call.")

    # Set default summary file (mirror R tidycensus logic)
    if sumfile is None:
        if year == 2020:
            sumfile = "pl"
        else:
            sumfile = "sf1"

    # Summary file specific messages (mirror R tidycensus)
    if sumfile == "sf3":
        print("Using Census Summary File 3")
        if year > 2001:
            raise ValueError(
                "Summary File 3 was not released in 2010. Use Summary File 1 or tables from the American Community Survey via get_acs() instead."
            )
    elif sumfile == "sf1":
        print("Using Census Summary File 1")
    elif sumfile == "pl":
        print("Using the PL 94-171 Redistricting Data Summary File")
    elif sumfile == "dhc":
        print("Using the Demographic and Housing Characteristics File")
    elif sumfile == "dp":
        print("Using the Demographic Profile")
    elif sumfile == "ddhca":
        print("Using the Detailed DHC-A File")
        if not pop_group:
            raise ValueError(
                "You must specify a population group to use the DDHC-A file. Specify `pop_group` parameter."
            )

    # Handle named variables (dictionary support)
    variable_names = None
    if isinstance(variables, dict):
        variable_names = variables
        variables = list(variables.values())

    # Handle table request
    if table:
        # Load variables for the table
        from .variables import load_variables

        var_df = load_variables(year, "dec", sumfile, cache=cache_table)
        table_vars = var_df[var_df["name"].str.startswith(table + "_")]["name"].tolist()
        if not table_vars:
            raise ValueError(f"No variables found for table {table}")
        variables = table_vars

    # Ensure variables is a list
    if isinstance(variables, str):
        variables = [variables]

    # Initialize API client
    api = CensusAPI(api_key)

    # Build geography parameters
    geo_params = build_geography_params(geography, state, county, **kwargs)

    # Handle summary variable
    all_variables = variables.copy()
    if summary_var and summary_var not in all_variables:
        all_variables.append(summary_var)
        variable_names[summary_var] = "summary_value"
    # Make API request
    try:
        data = api.get(
            year=year,
            dataset="dec",
            variables=all_variables,
            geography=geo_params,
            survey=sumfile,
            show_call=show_call,
        )

        # Process data
        df = process_census_data(data, all_variables, output)

        # Handle named variables (replace variable codes with custom names)
        if variable_names and output == "tidy":
            # Create reverse mapping from variable codes to names
            code_to_name = {code: name for name, code in variable_names.items()}
            df["variable"] = df["variable"].map(lambda x: code_to_name.get(x, x))
            df = df.rename(columns=variable_names)  # rename summary file
        elif variable_names and output == "wide":
            # Rename columns for wide format
            rename_dict = {
                code: name
                for name, code in variable_names.items()
                if code in df.columns
            }
            df = df.rename(columns=rename_dict)

        # # Handle summary variable joining (mirror R tidycensus)
        if summary_var:
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
                if summary_var in df.columns:
                    df = df.rename(columns={summary_var: "summary_value"})

        # Convert Census missing values to NA (mirror R tidycensus)
        missing_values = [
            -111111111,
            -222222222,
            -333333333,
            -444444444,
            -555555555,
            -666666666,
            -777777777,
            -888888888,
            -999999999,
        ]

        # Replace missing values in numeric columns
        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
        for col in numeric_cols:
            df[col] = df[col].replace(missing_values, pd.NA)

        # Add geometry if requested
        result = df
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
            else:
                print("Warning: Could not merge with geometry - GEOID column missing")
                result = df

        # Give users a heads-up about differential privacy in 2020 data (mirror R tidycensus)
        if year == 2020:
            import warnings

            warnings.warn(
                "Note: 2020 decennial Census data use differential privacy, a technique that introduces "
                "errors into data to preserve respondent confidentiality. Small counts should be "
                "interpreted with caution. See https://www.census.gov/library/fact-sheets/2021/"
                "protecting-the-confidentiality-of-the-2020-census-redistricting-data.html for additional guidance.",
                UserWarning,
            )

        return result

    except Exception as e:
        raise Exception(f"Failed to retrieve decennial Census data: {str(e)}")


def get_decennial_variables(
    year: int = 2020, sumfile: Optional[str] = None
) -> pd.DataFrame:
    """
    Get available decennial Census variables for a given year.

    Parameters
    ----------
    year : int, default 2020
        Census year
    sumfile : str, optional
        Summary file. Defaults to 'pl' for 2020, 'sf1' for earlier years.

    Returns
    -------
    pd.DataFrame
        Available variables with metadata
    """
    if sumfile is None:
        if year == 2020:
            sumfile = "pl"
        else:
            sumfile = "sf1"

    from .variables import load_variables

    return load_variables(year, "dec", sumfile)
