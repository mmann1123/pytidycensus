"""
Population estimates data retrieval functions.
"""

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


def get_estimates(
    geography: str,
    variables: Optional[Union[str, List[str]]] = None,
    breakdown: Optional[List[str]] = None,
    breakdown_labels: bool = False,
    year: int = 2022,
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
    """
    Obtain data from the US Census Bureau Population Estimates Program.

    Parameters
    ----------
    geography : str
        The geography of your data (e.g., 'county', 'state', 'us').
    variables : str or list of str, optional
        Variable ID(s) to retrieve. Common variables include:
        - "POP" (total population)
        - "DENSITY" (population density)
        - "BIRTHS" (births)
        - "DEATHS" (deaths)
        - "DOMESTICMIG" (domestic migration)
        - "INTERNATIONALMIG" (international migration)
    breakdown : list of str, optional
        Breakdown variables (e.g., ["SEX", "AGEGROUP", "RACE", "HISP"]).
    breakdown_labels : bool, default False
        Whether to include labels for breakdown categories.
    year : int, default 2022
        Year of population estimates.
    state : str, int, or list, optional
        State(s) to retrieve data for. Accepts names, abbreviations, or FIPS codes.
    county : str, int, or list, optional
        County(ies) to retrieve data for. Must be used with state.
    time_series : bool, default False
        Whether to retrieve time series data.
    output : str, default "tidy"
        Output format ("tidy" or "wide").
    geometry : bool, default False
        Whether to include geometry for mapping.
    keep_geo_vars : bool, default False
        Whether to keep all geographic variables from shapefiles.
    api_key : str, optional
        Census API key. If not provided, looks for CENSUS_API_KEY environment variable.
    show_call : bool, default False
        Whether to print the API call URL.
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
    # Validate inputs
    year = validate_year(year, "estimates")
    geography = validate_geography(geography)

    if not variables:
        variables = ["POP"]  # Default to total population

    # Ensure variables is a list
    if isinstance(variables, str):
        variables = [variables]

    # Add breakdown variables to the request
    all_variables = variables.copy()
    if breakdown:
        all_variables.extend(breakdown)

    # Initialize API client
    api = CensusAPI(api_key)

    # Build geography parameters
    geo_params = build_geography_params(geography, state, county, **kwargs)

    # Determine the appropriate estimates dataset
    dataset_path = "pep"
    if time_series:
        dataset_path += "/components"
    else:
        dataset_path += "/charagegroups" if breakdown else "/population"

    # Make API request
    try:
        print(f"Getting data from the {year} Population Estimates Program")

        data = api.get(
            year=year,
            dataset=dataset_path,
            variables=all_variables,
            geography=geo_params,
            show_call=show_call,
        )

        # Process data
        df = process_census_data(data, variables, output)

        # Add breakdown labels if requested
        if breakdown_labels and breakdown:
            df = _add_breakdown_labels(df, breakdown)

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
        raise Exception(f"Failed to retrieve population estimates: {str(e)}")


def _add_breakdown_labels(df: pd.DataFrame, breakdown: List[str]) -> pd.DataFrame:
    """
    Add human-readable labels for breakdown categories.

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


def get_estimates_variables(year: int = 2022) -> pd.DataFrame:
    """
    Get available population estimates variables for a given year.

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
