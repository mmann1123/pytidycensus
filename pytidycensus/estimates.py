"""
Population estimates data retrieval functions.
"""

from typing import Any, Dict, List, Optional, Union
import requests
from io import StringIO
import urllib3

# Disable SSL warnings for Census site
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

    try:
        print(f"Getting data from the {year} Population Estimates Program")

        # For years 2020 and later, use CSV files instead of API
        if year >= 2020:
            df = _get_estimates_from_csv(
                geography, variables, breakdown, year, state, county, time_series, output
            )
        else:
            # Use API for years before 2020
            df = _get_estimates_from_api(
                geography, variables, breakdown, year, state, county, time_series, 
                output, api_key, show_call, **kwargs
            )

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


def _get_estimates_from_csv(
    geography: str,
    variables: List[str],
    breakdown: Optional[List[str]],
    year: int,
    state: Optional[Union[str, int, List[Union[str, int]]]],
    county: Optional[Union[str, int, List[Union[str, int]]]],
    time_series: bool,
    output: str,
) -> pd.DataFrame:
    """Get estimates data from CSV files for years 2020+."""
    
    # Map vintage year to dataset year range
    vintage_map = {
        2020: "2020-2024",
        2021: "2020-2024", 
        2022: "2020-2024",
        2023: "2020-2024",
        2024: "2020-2024"
    }
    
    if year not in vintage_map:
        raise ValueError(f"Year {year} not supported for CSV-based estimates")
    
    dataset_range = vintage_map[year]
    
    # Build CSV URL based on geography
    base_url = f"https://www2.census.gov/programs-surveys/popest/datasets/{dataset_range}"
    
    if geography == "state":
        csv_url = f"{base_url}/state/totals/NST-EST2024-ALLDATA.csv"
    elif geography == "county":
        csv_url = f"{base_url}/counties/totals/co-est2024-alldata.csv"
    elif geography == "us":
        # US data is not available in the same CSV format for years 2020+
        # Use state data and aggregate or fallback to API for earlier years
        raise ValueError(f"US geography not supported for CSV-based estimates (years 2020+). Use earlier years or state data.")
    else:
        raise ValueError(f"Geography '{geography}' not supported for CSV-based estimates")
    
    # Download and read CSV
    try:
        response = requests.get(csv_url, verify=False)  # Disable SSL verification for Census site
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), encoding='latin1')
    except Exception as e:
        # Try alternative encoding
        try:
            response = requests.get(csv_url, verify=False)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text), encoding='utf-8')
        except Exception as e2:
            raise Exception(f"Failed to download CSV: {e}, {e2}")
    
    # Process the CSV data
    df = _process_estimates_csv(df, geography, variables, breakdown, year, state, county, output)
    
    return df


def _get_estimates_from_api(
    geography: str,
    variables: List[str],
    breakdown: Optional[List[str]],
    year: int,
    state: Optional[Union[str, int, List[Union[str, int]]]],
    county: Optional[Union[str, int, List[Union[str, int]]]],
    time_series: bool,
    output: str,
    api_key: Optional[str],
    show_call: bool,
    **kwargs
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

    # Determine the appropriate estimates dataset
    if time_series:
        dataset_path = "pep/components"
    else:
        dataset_path = "pep/population"

    # Make API request
    data = api.get(
        year=year,
        dataset=dataset_path,
        variables=all_variables,
        geography=geo_params,
        show_call=show_call,
    )

    # Process data
    df = process_census_data(data, variables, output)
    
    return df


def _process_estimates_csv(
    df: pd.DataFrame,
    geography: str,
    variables: List[str],
    breakdown: Optional[List[str]],
    year: int,
    state: Optional[Union[str, int, List[Union[str, int]]]],
    county: Optional[Union[str, int, List[Union[str, int]]]],
    output: str,
) -> pd.DataFrame:
    """Process raw CSV estimates data into the expected format."""
    
    # Filter by year if multiple years in dataset
    if 'DATE' in df.columns:
        # DATE codes: 1=4/1/2020 estimate, 2=4/1/2020 estimates base, 3=7/1/2020, 4=7/1/2021, 5=7/1/2022, 6=7/1/2023, etc.
        date_map = {2020: 3, 2021: 4, 2022: 5, 2023: 6, 2024: 7}
        if year in date_map:
            df = df[df['DATE'] == date_map[year]]
    
    # Filter by state if specified
    if state is not None and geography in ['county', 'state']:
        if isinstance(state, (str, int)):
            state = [state]
        
        state_fips = []
        
        # State name/abbreviation to FIPS mapping (partial)
        state_map = {
            'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08', 
            'CT': '09', 'DE': '10', 'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16',
            'IL': '17', 'IN': '18', 'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22',
            'ME': '23', 'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28',
            'MO': '29', 'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34',
            'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39', 'OK': '40',
            'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45', 'SD': '46', 'TN': '47',
            'TX': '48', 'UT': '49', 'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54',
            'WI': '55', 'WY': '56', 'DC': '11'
        }
        
        for s in state:
            if isinstance(s, str):
                s = s.upper()
                if len(s) == 2 and s in state_map:  # abbreviation
                    state_fips.append(state_map[s])
                elif s.isdigit():  # FIPS code as string
                    state_fips.append(s.zfill(2))
                else:
                    # Could be state name - simplified mapping
                    state_fips.append(s)
            else:
                state_fips.append(str(s).zfill(2))
        
        if 'STATE' in df.columns:
            df = df[df['STATE'].astype(str).str.zfill(2).isin(state_fips)]
    
    # Filter by county if specified
    if county is not None and geography == 'county':
        if isinstance(county, (str, int)):
            county = [county]
        
        county_fips = []
        for c in county:
            county_fips.append(str(c).zfill(3))
        
        if 'COUNTY' in df.columns:
            df = df[df['COUNTY'].astype(str).str.zfill(3).isin(county_fips)]
    
    # Filter to only actual geographic units (not totals/regions)
    if geography == 'state' and 'STATE' in df.columns:
        # Filter to only states (STATE codes 01-56, exclude 00 which is totals)
        df = df[(df['STATE'].astype(str) != '00') & (df['STATE'].astype(int).between(1, 56))].copy()
        df['GEOID'] = df['STATE'].astype(str).str.zfill(2)
    elif geography == 'county' and 'STATE' in df.columns and 'COUNTY' in df.columns:
        # Filter to only counties (COUNTY > 000)
        df = df[df['COUNTY'].astype(str) != '000'].copy()
        df['GEOID'] = df['STATE'].astype(str).str.zfill(2) + df['COUNTY'].astype(str).str.zfill(3)
    elif geography == 'us':
        # Filter to only US total (STATE == 00)
        if 'STATE' in df.columns:
            df = df[df['STATE'].astype(str) == '00'].copy()
        df['GEOID'] = '1'
    
    # Map variables to column names (simplified mapping)
    variable_map = {
        'POP': 'POPESTIMATE' + str(year),
        'BIRTHS': 'BIRTHS' + str(year), 
        'DEATHS': 'DEATHS' + str(year),
        'NETMIG': 'NETMIG' + str(year),
        'DOMESTICMIG': 'DOMESTICMIG' + str(year),
        'INTERNATIONALMIG': 'INTERNATIONALMIG' + str(year)
    }
    
    # Select requested columns
    result_cols = ['GEOID']
    if 'NAME' in df.columns:
        result_cols.append('NAME')
    elif 'CTYNAME' in df.columns and geography == 'county':
        # For county data, create a NAME column from CTYNAME
        df['NAME'] = df['CTYNAME']
        result_cols.append('NAME')
    
    for var in variables:
        if var in variable_map and variable_map[var] in df.columns:
            result_cols.append(variable_map[var])
        elif var in df.columns:
            result_cols.append(var)
    
    # Select only available columns
    available_cols = [col for col in result_cols if col in df.columns]
    df = df[available_cols]
    
    # Reshape to tidy format if requested
    if output == "tidy" and len(variables) > 1:
        id_vars = ['GEOID']
        if 'NAME' in df.columns:
            id_vars.append('NAME')
        
        value_vars = [col for col in df.columns if col not in id_vars]
        df = pd.melt(df, id_vars=id_vars, value_vars=value_vars, 
                    var_name='variable', value_name='estimate')
    
    return df


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
