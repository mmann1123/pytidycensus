"""
Utility functions for data processing and validation.
"""

import importlib.resources
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import us


def validate_state(state: Union[str, int, List[Union[str, int]]]) -> List[str]:
    """
    Validate and convert state identifiers to FIPS codes.

    Parameters
    ----------
    state : str, int, or list
        State name(s), abbreviation(s), or FIPS code(s)

    Returns
    -------
    List[str]
        List of 2-digit FIPS codes

    Raises
    ------
    ValueError
        If state identifier is invalid
    """
    if isinstance(state, (str, int)):
        states = [state]
    else:
        states = state

    fips_codes = []

    for s in states:
        if isinstance(s, int):
            s = str(s).zfill(2)

        # Try FIPS code first
        if isinstance(s, str) and s.isdigit() and len(s) <= 2:
            fips_code = s.zfill(2)
            state_obj = us.states.lookup(fips_code)
            if state_obj:
                fips_codes.append(fips_code)
                continue

        # Try state lookup by name or abbreviation
        state_obj = us.states.lookup(str(s))
        if state_obj:
            fips_codes.append(state_obj.fips)
        else:
            raise ValueError(f"Invalid state identifier: {s}")

    return fips_codes


def validate_county(
    county: Union[str, int, List[Union[str, int]]], state_fips: str
) -> List[str]:
    """
    Validate and convert county identifiers to FIPS codes.

    Parameters
    ----------
    county : str, int, or list
        County name(s) or FIPS code(s)
    state_fips : str
        State FIPS code

    Returns
    -------
    List[str]
        List of 3-digit county FIPS codes

    Raises
    ------
    ValueError
        If county identifier is invalid
    """
    if isinstance(county, (str, int)):
        counties = [county]
    else:
        counties = county

    fips_codes = []

    # Load county lookup from national_county.txt
    county_lookup = _load_national_county_txt()
    state_fips = str(state_fips).zfill(2)

    for c in counties:
        if isinstance(c, int):
            c = str(c).zfill(3)

        # Normalize county name: remove ' County' suffix if present
        if isinstance(c, str) and c.lower().endswith(" county"):
            c = c[:-7].strip()

        # If it's already a FIPS code
        if isinstance(c, str) and c.isdigit() and len(c) <= 3:
            fips_codes.append(c.zfill(3))
        else:
            # Try county name lookup using national_county.txt
            key = (state_fips, str(c).lower().strip())
            fips_code = county_lookup.get(key)
            if fips_code:
                fips_codes.append(fips_code)
            else:
                raise ValueError(f"Could not find county FIPS code for: {c}")
    return fips_codes


def _load_national_county_txt():
    lookup = {}
    try:
        with importlib.resources.open_text(
            "pytidycensus.data", "national_county.txt"
        ) as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 4:
                    continue
                state_abr, state_fips, county_fips, county_name = parts[:4]

                county_name = _normalize_county_name(county_name)
                lookup[(state_fips.zfill(2), county_name.lower().strip())] = (
                    county_fips.zfill(3)
                )
    except FileNotFoundError:
        print("Warning: national_county.txt not found, county lookups may fail.")
    return lookup


@lru_cache(maxsize=128)
def _get_county_data(state_fips: str) -> Dict[str, str]:
    """
    Fetch county data for a given state from Census API.

    This function is cached to avoid repeated API calls for the same state.

    Parameters
    ----------
    state_fips : str
        State FIPS code

    Returns
    -------
    Dict[str, str]
        Dictionary mapping county names (lowercase, normalized) to FIPS codes
    """
    try:
        from .api import CensusAPI

        # Initialize API client
        api = CensusAPI()

        # Get county data for the state
        data = api.get(
            year=2022,  # Use recent year
            dataset="acs",
            variables=["NAME"],
            geography={"for": "county:*", "in": f"state:{state_fips}"},
            survey="acs5",
        )

        county_lookup = {}
        for row in data:
            county_name = row.get("NAME", "")
            county_fips = row.get("county", "")

            if county_name and county_fips:
                # Normalize county name: lowercase, remove "County" suffix, strip whitespace
                normalized_name = county_name.lower().replace(" county", "").strip()
                county_lookup[normalized_name] = county_fips

                # Also add version with "County" for exact matches
                county_lookup[county_name.lower().strip()] = county_fips

        return county_lookup

    except Exception:
        # If API call fails, return empty dict (will fall back to error)
        return {}


def _normalize_county_name(name: str) -> str:
    """
    Normalize county name for lookup.

    Parameters
    ----------
    name : str
        Raw county name

    Returns
    -------
    str
        Normalized county name
    """
    # Convert to lowercase and strip whitespace
    normalized = name.lower().strip()

    # Remove common suffixes
    for suffix in [
        " county",
        " parish",
        " borough",
        " census area",
        " city and borough",
    ]:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            break

    return normalized


def lookup_county_fips(county_name: str, state_fips: str) -> Optional[str]:
    """
    Look up county FIPS code by name.

    Parameters
    ----------
    county_name : str
        County name to look up
    state_fips : str
        State FIPS code

    Returns
    -------
    Optional[str]
        County FIPS code if found, None otherwise
    """
    # Get county data for the state
    county_data = _get_county_data(state_fips)

    if not county_data:
        return None

    # Try exact match first (case insensitive)
    exact_match = county_data.get(county_name.lower().strip())
    if exact_match:
        return exact_match

    # Try normalized name
    normalized_name = _normalize_county_name(county_name)
    normalized_match = county_data.get(normalized_name)
    if normalized_match:
        return normalized_match

    # Try fuzzy matching using jellyfish (if available via us library)
    try:
        import jellyfish

        best_match = None
        best_score = 0

        for name, fips in county_data.items():
            score = jellyfish.jaro_winkler_similarity(normalized_name, name)
            if score > best_score and score > 0.8:  # 80% similarity threshold
                best_score = score
                best_match = fips

        return best_match
    except ImportError:
        # No fuzzy matching available
        pass

    return None


def validate_year(year: int, dataset: str) -> int:
    """
    Validate year for given dataset.

    Parameters
    ----------
    year : int
        Census year
    dataset : str
        Dataset type ('acs', 'dec', 'estimates')

    Returns
    -------
    int
        Validated year

    Raises
    ------
    ValueError
        If year is not available for dataset
    """
    if dataset == "acs":
        # ACS 5-year: 2009-2023, ACS 1-year: 2005-2023 (except 2020)
        if year < 2005 or year > 2023:
            raise ValueError(f"ACS data not available for year {year}")
    elif dataset == "dec":
        # Decennial census: 1990, 2000, 2010, 2020
        if year not in [1990, 2000, 2010, 2020]:
            raise ValueError(f"Decennial census data not available for year {year}")
    elif dataset == "estimates":
        # Population estimates: varies by type
        if year < 2000 or year > 2023:
            raise ValueError(f"Population estimates not available for year {year}")

    return year


def validate_geography(geography: str) -> str:
    """
    Validate geography parameter.

    Parameters
    ----------
    geography : str
        Geography level

    Returns
    -------
    str
        Validated geography

    Raises
    ------
    ValueError
        If geography is not supported
    """
    valid_geographies = [
        "us",
        "region",
        "division",
        "state",
        "county",
        "tract",
        "block group",
        "block",
        "place",
        "msa",
        "csa",
        "necta",
        "zcta",
        "congressional district",
        "state legislative district (upper chamber)",
        "state legislative district (lower chamber)",
        "public use microdata area",
        "school district (elementary)",
        "school district (secondary)",
        "school district (unified)",
    ]

    # Normalize geography
    geography = geography.lower()
    if geography == "cbg":
        geography = "block group"

    if geography not in valid_geographies:
        raise ValueError(f"Geography '{geography}' not supported")

    return geography


def build_geography_params(
    geography: str,
    state: Optional[Union[str, int, List[Union[str, int]]]] = None,
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    **kwargs,
) -> Dict[str, str]:
    """
    Build geography parameters for Census API call.

    Parameters
    ----------
    geography : str
        Geography level
    state : str, int, or list, optional
        State identifier(s)
    county : str, int, or list, optional
        County identifier(s)
    **kwargs
        Additional geography parameters

    Returns
    -------
    Dict[str, str]
        Geography parameters for API call
    """
    params = {}

    if geography == "us":
        params["for"] = "us:*"
    elif geography == "region":
        params["for"] = "region:*"
    elif geography == "division":
        params["for"] = "division:*"
    elif geography == "state":
        if state:
            state_fips = validate_state(state)
            params["for"] = f"state:{','.join(state_fips)}"
        else:
            params["for"] = "state:*"
    elif geography == "county":
        params["for"] = "county:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
        if county and state:
            county_fips = validate_county(county, state_fips[0])
            params["for"] = f"county:{','.join(county_fips)}"
    elif geography == "tract":
        params["for"] = "tract:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
            if county:
                county_fips = validate_county(county, state_fips[0])
                params["in"] += f" county:{','.join(county_fips)}"
    elif geography == "block group":
        params["for"] = "block group:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
            if county:
                county_fips = validate_county(county, state_fips[0])
                params["in"] += f" county:{','.join(county_fips)}"
    else:
        # For other geographies, use basic format
        params["for"] = f"{geography}:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"

    return params


def process_census_data(
    data: List[Dict[str, Any]], variables: List[str], output: str = "tidy"
) -> pd.DataFrame:
    """
    Process raw Census API response into pandas DataFrame.

    Parameters
    ----------
    data : List[Dict[str, Any]]
        Raw Census API response
    variables : List[str]
        Variable codes requested
    output : str, default "tidy"
        Output format ("tidy" or "wide")

    Returns
    -------
    pd.DataFrame
        Processed data
    """
    df = pd.DataFrame(data)

    # Replace ACS missing value codes with NaN
    missing_codes = [
        -111111111,
        -222222222,
        -333333333,
        -444444444,
        -555555555,
        -666666666,
        -777777777,
    ]

    # Convert numeric columns
    for var in variables:
        if var in df.columns:
            df[var] = pd.to_numeric(df[var], errors="coerce")

    # Create GEOID from geography columns
    geo_cols = [
        col for col in df.columns if col in ["state", "county", "tract", "block group"]
    ]
    if geo_cols:
        df["GEOID"] = df[geo_cols].fillna("").astype(str).agg("".join, axis=1)

    # Create NAME column from available name fields
    if "NAME" not in df.columns:
        name_cols = [col for col in df.columns if "name" in col.lower()]
        if name_cols:
            df["NAME"] = df[name_cols[0]]

    df.replace(missing_codes, pd.NA, inplace=True)

    if output == "tidy":
        # Reshape to long format
        id_vars = [col for col in df.columns if col not in variables]

        df_long = df.melt(
            id_vars=id_vars,
            value_vars=variables,
            var_name="variable",
            value_name="value",
        )

        return df_long

    return df


def add_margin_of_error(
    df: pd.DataFrame, variables: List[str], moe_level: int = 90, output: str = "tidy"
) -> pd.DataFrame:
    """
    Add margin of error columns for ACS data with confidence level adjustment.

    Parameters
    ----------
    df : pd.DataFrame
        Census data
    variables : List[str]
        Variable codes
    moe_level : int, default 90
        Confidence level (90, 95, or 99)

    Returns
    -------
    pd.DataFrame
        Data with margin of error columns
    """
    import numpy as np

    # Replace ACS missing value codes with NaN
    missing_codes = [
        -111111111,
        -222222222,
        -333333333,
        -444444444,
        -555555555,
        -666666666,
        -777777777,
    ]

    # MOE adjustment factors for different confidence levels
    # Census provides 90% MOE by default
    moe_factors = {
        90: 1.0,  # No adjustment needed
        95: 1.96 / 1.645,  # Convert from 90% to 95%
        99: 2.576 / 1.645,  # Convert from 90% to 99%
    }

    if moe_level not in moe_factors:
        raise ValueError("moe_level must be 90, 95, or 99")

    adjustment_factor = moe_factors[moe_level]

    if output == "tidy":
        # Multiply 'value' by adjustment_factor where 'variable' ends with 'M'
        df.loc[df["variable"].str.endswith("M"), "value"] *= adjustment_factor

        # Rename variable names ending in 'M' to end with '_moe'
        df.loc[df["variable"].str.endswith("M"), "variable"] = df.loc[
            df["variable"].str.endswith("M"), "variable"
        ].str.replace(r"M$", "_moe", regex=True)
    else:
        # ACS variables have corresponding MOE variables with 'M' suffix
        # moe_mapping = {}
        # for var in variables:
        #     moe_var = var.replace("E", "M", 1) if "E" in var else f"{var}"
        #     if moe_var in df.columns:
        #         moe_mapping[var] = moe_var

        # Build mapping: {E_var: M_var}
        moe_mapping = {
            var[:-1]: var[:-1] + "M"
            for var in variables
            if var.endswith("E") and (var[:-1] + "M") in variables
        }

        # Rename and adjust MOE columns
        for var, moe_var in moe_mapping.items():
            # Apply confidence level adjustment
            df[f"{var}_moe"] = (
                df[moe_var].astype(float, errors="ignore") * adjustment_factor
            )
            df = df.drop(columns=[moe_var])

    df.replace(missing_codes, pd.NA, inplace=True)

    return df
