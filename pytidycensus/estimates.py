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
    "place"
}

# Geography aliases
GEOGRAPHY_ALIASES = {
    "metropolitan statistical area/micropolitan statistical area": "cbsa"
}

# Comprehensive variable mapping
VARIABLE_MAPPING = {
    'POP': 'POPESTIMATE',
    'BIRTHS': 'BIRTHS', 
    'DEATHS': 'DEATHS',
    'NETMIG': 'NETMIG',
    'DOMESTICMIG': 'DOMESTICMIG',
    'INTERNATIONALMIG': 'INTERNATIONALMIG',
    'NATURALCHG': 'NATURALCHG',
    'NPOPCHG': 'NPOPCHG',
    'RESIDUAL': 'RESIDUAL',
    'ESTIMATESBASE': 'ESTIMATESBASE',
    'GQESTIMATES': 'GQESTIMATES',
    'GQESTIMATESBASE': 'GQESTIMATESBASE',
    'RBIRTH': 'RBIRTH',
    'RDEATH': 'RDEATH',
    'RNATURALCHG': 'RNATURALCHG',
    'RINTERNATIONALMIG': 'RINTERNATIONALMIG',
    'RDOMESTICMIG': 'RDOMESTICMIG',
    'RNETMIG': 'RNETMIG'
}

# Variable descriptions
VARIABLE_DESCRIPTIONS = {
    'POPESTIMATE': 'Total population estimate',
    'ESTIMATESBASE': 'Population estimates base',
    'BIRTHS': 'Births',
    'DEATHS': 'Deaths',
    'NATURALCHG': 'Natural change (births - deaths)',
    'INTERNATIONALMIG': 'International migration',
    'DOMESTICMIG': 'Domestic migration',
    'NETMIG': 'Net migration',
    'NPOPCHG': 'Net population change',
    'RESIDUAL': 'Residual',
    'GQESTIMATESBASE': 'Group quarters population estimates base',
    'GQESTIMATES': 'Group quarters population',
    'RBIRTH': 'Birth rate per 1,000 population',
    'RDEATH': 'Death rate per 1,000 population',
    'RNATURALCHG': 'Natural change rate per 1,000 population',
    'RINTERNATIONALMIG': 'International migration rate per 1,000 population',
    'RDOMESTICMIG': 'Domestic migration rate per 1,000 population',
    'RNETMIG': 'Net migration rate per 1,000 population'
}

from .api import CensusAPI
from .geography import get_geography
from .utils import (
    build_geography_params,
    process_census_data,
    validate_geography,
    validate_state,
    validate_year,
)


def _filter_variables_for_dataset(dataset_path: str, variables: List[str]) -> List[str]:
    """
    Filter variables to only include those compatible with the selected dataset.
    
    Dataset compatibility:
    - pep/population: POP, NAME, and geographic variables
    - pep/components: BIRTHS, DEATHS, NATURALCHG, NETMIG, etc. (no POP)
    - pep/charagegroups: POP, NAME, demographic breakdowns
    """
    # Define variables available in each dataset
    population_vars = {"POP", "NAME"}
    components_vars = {"BIRTHS", "DEATHS", "DOMESTICMIG", "INTERNATIONALMIG", 
                      "NETMIG", "NATURALCHG", "NPOPCHG", "RESIDUAL", "NAME"}
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
    """
    Determine the correct API dataset path based on product and variables.
    
    Returns:
    - "pep/population" for basic population estimates
    - "pep/components" for components of population change  
    - "pep/charagegroups" for characteristics (age, sex, race, Hispanic origin)
    """
    # For characteristics product, use charagegroups dataset
    if product == "characteristics":
        return "pep/charagegroups"
    
    # Check if ALL variables are components variables
    components_vars = {"BIRTHS", "DEATHS", "DOMESTICMIG", "INTERNATIONALMIG", 
                      "NETMIG", "NATURALCHG", "NPOPCHG", "RESIDUAL"}
    
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
    year: int
) -> str:
    """
    Validate and set the product parameter based on inputs.
    
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
            raise ValueError(f"Product '{product}' not supported. Available options: {', '.join(valid_products)}")
        
        # Validate product/geography combinations for characteristics
        if product == "characteristics":
            if geography not in ["state", "county", "cbsa", "combined statistical area"]:
                raise ValueError(f"Characteristics product not supported for geography '{geography}'. "
                               f"Supported geographies: state, county, cbsa, combined statistical area")
        
        return product
    
    # Auto-determine product based on inputs
    
    # If breakdown is specified, must use characteristics
    if breakdown is not None:
        if geography not in ["state", "county", "cbsa", "combined statistical area"]:
            raise ValueError(f"Demographic breakdowns not supported for geography '{geography}'. "
                           f"Supported geographies: state, county, cbsa, combined statistical area")
        return "characteristics"
    
    # If variables suggest components of change, use components
    if variables and isinstance(variables, (list, str)):
        var_list = [variables] if isinstance(variables, str) else variables
        components_vars = {"BIRTHS", "DEATHS", "DOMESTICMIG", "INTERNATIONALMIG", 
                          "NETMIG", "NATURALCHG", "NPOPCHG", "RESIDUAL"}
        
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
    """
    Obtain data from the US Census Bureau Population Estimates Program.

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
        print(f"Warning: Using vintage {vintage} data for year {year}. Consider setting vintage={year} if available.")
    
    # Validate inputs
    if year < 2015:
        raise ValueError("Population Estimates data not available for years prior to 2015.")
    
    # Validate and normalize geography
    geography = geography.lower()
    if geography in GEOGRAPHY_ALIASES:
        geography = GEOGRAPHY_ALIASES[geography]
    
    if geography not in SUPPORTED_GEOGRAPHIES:
        raise ValueError(f"Geography '{geography}' not supported. Available options: {', '.join(sorted(SUPPORTED_GEOGRAPHIES))}")
    
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
            print(f"Getting data from the {vintage} Population Estimates Program (vintage {vintage})")
        else:
            print(f"Getting data from the {year} Population Estimates Program")

        # For years 2020 and later, use CSV files instead of API
        if year >= 2020:
            df = _get_estimates_from_csv(
                geography, product, variables, breakdown, vintage, year, state, county, time_series, output
            )
        else:
            # Use API for years before 2020
            df = _get_estimates_from_api(
                geography, product, variables, breakdown, year, state, county, time_series, 
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
    df = _process_estimates_csv(df, geography, product, variables, breakdown, vintage, year, state, county, time_series, output)
    
    return df


def _get_state_fips(state_input: Union[str, int]) -> str:
    """Convert state name/abbreviation to FIPS code."""
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
    retrieved_variables = [v for v in variables if v.upper() in [dv.upper() for dv in dataset_variables]]
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
        return _process_characteristics_csv(df, geography, variables, breakdown, vintage, year, state, county, time_series, output)
    
    # Handle population/components products (totals datasets)
    
    # Filter by year using different methods depending on file structure
    if 'DATE' in df.columns:
        # DATE codes: 1=4/1/2020 estimate, 2=4/1/2020 estimates base, 3=7/1/2020, 4=7/1/2021, 5=7/1/2022, 6=7/1/2023, etc.
        date_map = {2020: 3, 2021: 4, 2022: 5, 2023: 6, 2024: 7}
        if year in date_map:
            df = df[df['DATE'] == date_map[year]]
    
    # Pivot data from wide to long format for consistent processing
    # All CSVs have year-suffixed columns like POPESTIMATE2022, BIRTHS2022, etc.
    
    # Create base result with GEOID and NAME
    result_df = _create_base_result(df, geography)
    
    # Filter by geographic selections
    result_df = _apply_geographic_filters(result_df, geography, state, county)
    
    # Get requested variables
    result_df = _extract_variables(result_df, variables, year, vintage, time_series)
    
    # Reshape output format
    if time_series or (output == "tidy" and len([col for col in result_df.columns if col not in ['GEOID', 'NAME']]) > 1):
        id_vars = ['GEOID']
        if 'NAME' in result_df.columns:
            id_vars.append('NAME')
        
        value_vars = [col for col in result_df.columns if col not in id_vars]
        
        if time_series:
            # For time series, create year column
            result_df = pd.melt(result_df, id_vars=id_vars, value_vars=value_vars, 
                              var_name='variable', value_name='estimate')
            
            # Extract year from variable name (e.g., POPESTIMATE2022 -> 2022)
            result_df['year'] = result_df['variable'].str.extract(r'(\d{4})$')[0].astype(int)
            
            # Clean up variable names (remove year suffix)
            result_df['variable'] = result_df['variable'].str.replace(r'\d{4}$', '', regex=True)
            
            # Reorder columns
            result_df = result_df[['GEOID', 'NAME', 'variable', 'year', 'estimate'] if 'NAME' in result_df.columns 
                                else ['GEOID', 'variable', 'year', 'estimate']]
        else:
            # Regular tidy format
            result_df = pd.melt(result_df, id_vars=id_vars, value_vars=value_vars, 
                              var_name='variable', value_name='estimate')
    
    return result_df


def _create_base_result(df: pd.DataFrame, geography: str) -> pd.DataFrame:
    """Create base result DataFrame with GEOID and NAME columns."""
    
    if geography == "us":
        # US total (SUMLEV == 010 or STATE == 00)
        if 'SUMLEV' in df.columns:
            df_filtered = df[df['SUMLEV'].astype(str) == '10'].copy()
        else:
            df_filtered = df[df['STATE'].astype(str) == '00'].copy()
        df_filtered['GEOID'] = '1'
        
    elif geography == "region":
        # Census regions (SUMLEV == 020)
        if 'SUMLEV' in df.columns:
            df_filtered = df[df['SUMLEV'].astype(str) == '20'].copy()
            df_filtered['GEOID'] = df_filtered['REGION'].astype(str)
        else:
            raise ValueError("Region data not available in this dataset")
            
    elif geography == "division":
        # Census divisions (SUMLEV == 030)
        if 'SUMLEV' in df.columns:
            df_filtered = df[df['SUMLEV'].astype(str) == '30'].copy()
            df_filtered['GEOID'] = df_filtered['DIVISION'].astype(str)
        else:
            raise ValueError("Division data not available in this dataset")
            
    elif geography == "state":
        # States (SUMLEV == 040 or STATE codes 01-56)
        if 'SUMLEV' in df.columns:
            df_filtered = df[df['SUMLEV'].astype(str) == '40'].copy()
            df_filtered['GEOID'] = df_filtered['STATE'].astype(str).str.zfill(2)
        else:
            df_filtered = df[(df['STATE'].astype(str) != '00') & 
                           (df['STATE'].astype(int).between(1, 56))].copy()
            df_filtered['GEOID'] = df_filtered['STATE'].astype(str).str.zfill(2)
            
    elif geography == "county":
        # Counties (SUMLEV == 050 or COUNTY != 000)
        if 'SUMLEV' in df.columns:
            df_filtered = df[df['SUMLEV'].astype(str) == '50'].copy()
        else:
            df_filtered = df[df['COUNTY'].astype(str) != '000'].copy()
        
        df_filtered['GEOID'] = (df_filtered['STATE'].astype(str).str.zfill(2) + 
                              df_filtered['COUNTY'].astype(str).str.zfill(3))
        
        # Create county name
        if 'CTYNAME' in df_filtered.columns and 'STNAME' in df_filtered.columns:
            df_filtered['NAME'] = df_filtered['CTYNAME'] + ', ' + df_filtered['STNAME']
        elif 'CTYNAME' in df_filtered.columns:
            df_filtered['NAME'] = df_filtered['CTYNAME']
            
    elif geography == "cbsa":
        # Core Based Statistical Areas
        if 'CBSA' in df.columns:
            if 'LSAD' in df.columns:
                # Filter to actual CBSAs (not divisions)
                df_filtered = df[df['LSAD'].isin(['Metropolitan Statistical Area', 
                                                'Micropolitan Statistical Area'])].copy()
            else:
                df_filtered = df.copy()
            df_filtered['GEOID'] = df_filtered['CBSA'].astype(str)
        else:
            raise ValueError("CBSA data not available in this dataset")
            
    elif geography == "combined statistical area":
        # Combined Statistical Areas
        if 'CSA' in df.columns:
            if 'LSAD' in df.columns:
                df_filtered = df[df['LSAD'] == 'Combined Statistical Area'].copy()
            else:
                df_filtered = df.copy()
            df_filtered['GEOID'] = df_filtered['CSA'].astype(str)
        else:
            raise ValueError("Combined Statistical Area data not available in this dataset")
            
    elif geography == "place":
        # Places (SUMLEV == 162)
        if 'SUMLEV' in df.columns:
            df_filtered = df[df['SUMLEV'].astype(str) == '162'].copy()
            df_filtered['GEOID'] = (df_filtered['STATE'].astype(str).str.zfill(2) + 
                                  df_filtered['PLACE'].astype(str).str.zfill(5))
            
            # Create place name with state
            if 'NAME' in df_filtered.columns and 'STNAME' in df_filtered.columns:
                df_filtered['NAME'] = df_filtered['NAME'] + ', ' + df_filtered['STNAME']
        else:
            raise ValueError("Place data not available in this dataset")
    else:
        raise ValueError(f"Unsupported geography: {geography}")
    
    # Ensure we have a NAME column
    if 'NAME' not in df_filtered.columns and 'NAME' in df.columns:
        df_filtered['NAME'] = df['NAME']
        
    return df_filtered


def _apply_geographic_filters(
    df: pd.DataFrame, 
    geography: str, 
    state: Optional[Union[str, int, List[Union[str, int]]]], 
    county: Optional[Union[str, int, List[Union[str, int]]]]
) -> pd.DataFrame:
    """Apply state and county filters to the DataFrame."""
    
    # Filter by state if specified
    if state is not None and geography in ['county', 'state', 'place']:
        if isinstance(state, (str, int)):
            state = [state]
        
        state_fips = []
        for s in state:
            state_fips.append(_get_state_fips(s))
        
        if geography in ['state', 'place']:
            df = df[df['GEOID'].str[:2].isin(state_fips)]
        elif geography == 'county':
            df = df[df['GEOID'].str[:2].isin(state_fips)]
    
    # Filter by county if specified
    if county is not None and geography == 'county':
        if isinstance(county, (str, int)):
            county = [county]
        
        county_fips = [str(c).zfill(3) for c in county]
        df = df[df['GEOID'].str[2:5].isin(county_fips)]
    
    return df


def _extract_variables(df: pd.DataFrame, variables: List[str], year: int, vintage: int, time_series: bool = False) -> pd.DataFrame:
    """Extract requested variables from the DataFrame."""
    
    # Handle 'all' variables request
    if variables == ["all"]:
        if time_series:
            # Find all variable patterns across all years
            all_year_cols = [col for col in df.columns if any(col.startswith(v) for v in VARIABLE_MAPPING.values())]
            unique_vars = set()
            for col in all_year_cols:
                for var_name in VARIABLE_MAPPING.values():
                    if col.startswith(var_name):
                        unique_vars.add(var_name)
            variables = list(unique_vars)
        else:
            # Find all year-suffixed columns for the specific year
            year_cols = [col for col in df.columns if col.endswith(str(year)) and col not in ['GEOID', 'NAME']]
            variables = []
            for col in year_cols:
                for short_name, full_name in VARIABLE_MAPPING.items():
                    if col.startswith(full_name):
                        variables.append(short_name)
                        break
            if not variables:
                variables = [col.replace(str(year), '') for col in year_cols]
    
    # Map variables to actual column names
    result_cols = ['GEOID']
    if 'NAME' in df.columns:
        result_cols.append('NAME')
    
    if time_series:
        # For time series, get all years available for each variable
        for var in variables:
            full_var = VARIABLE_MAPPING.get(var, var)
            
            # Find all year columns for this variable
            year_cols = [col for col in df.columns if col.startswith(full_var) and col[len(full_var):].isdigit()]
            result_cols.extend(year_cols)
    else:
        # For single year, get just the requested year
        for var in variables:
            full_var = VARIABLE_MAPPING.get(var, var)
            
            # Try different column name patterns
            possible_cols = [
                f"{full_var}{year}",  # POPESTIMATE2022
                f"{full_var}_{year}",  # POPESTIMATE_2022
                f"{var}{year}",       # POP2022 (if user provided full name)
                var,                   # Exact match
            ]
            
            for col in possible_cols:
                if col in df.columns:
                    result_cols.append(col)
                    break
    
    # Select available columns
    available_cols = [col for col in result_cols if col in df.columns]
    return df[available_cols]


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
    """Process characteristics (ASRH) CSV data."""
    
    # This is a complex implementation that would handle the demographic breakdowns
    # For now, return a placeholder that indicates this feature is not yet implemented
    
    raise NotImplementedError("Characteristics product is not yet implemented. Use product='population' or product='components' instead.")


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


def discover_available_variables(vintage: int = 2024, geography: str = "state") -> pd.DataFrame:
    """
    Discover all available variables in a PEP dataset.
    
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
        df = pd.read_csv(StringIO(response.text), encoding='latin1', nrows=1)  # Just get headers
        
        # Extract variable information
        variables = []
        descriptions = []
        
        # Define variable patterns and descriptions
        var_patterns = {
            r'POPESTIMATE(\d{4})': 'Total population estimate',
            r'ESTIMATESBASE(\d{4})': 'Population estimates base',
            r'BIRTHS(\d{4})': 'Births',
            r'DEATHS(\d{4})': 'Deaths', 
            r'NATURALCHG(\d{4})': 'Natural change (births - deaths)',
            r'INTERNATIONALMIG(\d{4})': 'International migration',
            r'DOMESTICMIG(\d{4})': 'Domestic migration',
            r'NETMIG(\d{4})': 'Net migration',
            r'NPOPCHG[_-]?(\d{4})': 'Net population change',
            r'RESIDUAL(\d{4})': 'Residual',
            r'GQESTIMATESBASE(\d{4})': 'Group quarters population estimates base',
            r'GQESTIMATES(\d{4})': 'Group quarters population',
            r'RBIRTH(\d{4})': 'Birth rate per 1,000 population',
            r'RDEATH(\d{4})': 'Death rate per 1,000 population',
            r'RNATURALCHG(\d{4})': 'Natural change rate per 1,000 population',
            r'RINTERNATIONALMIG(\d{4})': 'International migration rate per 1,000 population',
            r'RDOMESTICMIG(\d{4})': 'Domestic migration rate per 1,000 population',
            r'RNETMIG(\d{4})': 'Net migration rate per 1,000 population'
        }
        
        import re
        
        for col in df.columns:
            if col in ['SUMLEV', 'REGION', 'DIVISION', 'STATE', 'COUNTY', 'NAME', 'STNAME', 'CTYNAME']:
                continue
                
            matched = False
            for pattern, desc in var_patterns.items():
                match = re.match(pattern, col)
                if match:
                    year = match.group(1)
                    var_base = col.replace(year, '')
                    if var_base not in [v.split('_')[0] for v in variables]:  # Avoid duplicates
                        variables.append(f"{var_base}_{year}")
                        descriptions.append(f"{desc} ({year})")
                    matched = True
                    break
            
            if not matched:
                variables.append(col)
                descriptions.append("Unknown variable")
        
        result_df = pd.DataFrame({
            'variable': variables,
            'description': descriptions
        })
        
        return result_df
        
    except Exception as e:
        print(f"Warning: Could not discover variables: {e}")
        return pd.DataFrame({'variable': [], 'description': []})


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
