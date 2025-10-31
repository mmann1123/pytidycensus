"""Utility functions for data processing and validation."""

import importlib.resources
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import us
import yaml
from geopandas import GeoDataFrame


def get_credentials():
    try:
        with open("credentials.yaml") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        with open("../credentials.yaml") as f:
            return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_county_lookup() -> pd.DataFrame:
    """Load county lookup table from national_county.txt.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: state_abbrev, state_fips, county_fips, county_name
    """
    # Get the path to the data file using importlib.resources (modern approach)
    try:
        # Try using importlib.resources (Python 3.9+)
        from importlib import resources

        data_path = resources.files("pytidycensus.data") / "national_county.txt"
        with data_path.open() as f:
            county_df = pd.read_csv(
                f,
                names=[
                    "state_abbrev",
                    "state_fips",
                    "county_fips",
                    "county_name",
                    "h1",
                ],
                dtype={"state_fips": str, "county_fips": str},
            )
    except (ImportError, AttributeError, FileNotFoundError):
        # Fallback to traditional path method
        data_path = os.path.join(os.path.dirname(__file__), "data", "national_county.txt")
        county_df = pd.read_csv(
            data_path,
            names=["state_abbrev", "state_fips", "county_fips", "county_name", "h1"],
            dtype={"state_fips": str, "county_fips": str},
        )

    # Convert state abbreviations to full state names using the us library
    county_df["state_name"] = county_df["state_abbrev"].apply(
        lambda abbrev: (us.states.lookup(abbrev).name if us.states.lookup(abbrev) else abbrev)
    )

    # Create full GEOID for county-level matching (state + county)
    county_df["county_geoid"] = county_df["state_fips"] + county_df["county_fips"]

    # For county-level entries, combine county name with state name
    county_df["full_name"] = county_df["county_name"] + ", " + county_df["state_name"]

    # Create state-level entries for state matching
    state_df = county_df.drop_duplicates("state_fips")[["state_name", "state_fips"]].copy()
    state_df["county_geoid"] = state_df["state_fips"]  # State GEOID is just state FIPS
    state_df["full_name"] = state_df["state_name"]  # Use full state name for states

    # Combine state and county data
    lookup_df = pd.concat(
        [
            state_df[["county_geoid", "full_name"]],
            county_df[["county_geoid", "full_name"]],
        ],
        ignore_index=True,
    ).rename(columns={"full_name": "county_name"})

    return lookup_df


def add_name_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add NAME column using national_county.txt lookup table for geographic areas.

    Works for state, county, and tract level geographies by matching GEOID.
    For tract-level data, shows county and state name without tract number.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with GEOID column

    Returns
    -------
    pd.DataFrame
        DataFrame with NAME column added
    """
    if "GEOID" not in df.columns or "NAME" in df.columns:
        return df

    # Load county lookup data
    county_lookup = load_county_lookup()

    # Create a copy to work with
    df_copy = df.copy()

    # Create lookup key based on GEOID length
    # State: 2 chars, County: 5 chars, Tract: 11 chars (use first 5 for county lookup)
    def get_lookup_key(geoid):
        geoid_str = str(geoid)
        if len(geoid_str) <= 5:
            # State or county level - use as is
            return geoid_str
        else:
            # Tract level or higher - extract county portion (first 5 characters)
            return geoid_str[:5]

    df_copy["lookup_geoid"] = df_copy["GEOID"].apply(get_lookup_key)

    # Merge with lookup table to add NAME column
    df_with_name = df_copy.merge(
        county_lookup, left_on="lookup_geoid", right_on="county_geoid", how="left"
    )

    # Rename the county_name column to NAME and drop the extra columns
    if "county_name" in df_with_name.columns:
        df_with_name["NAME"] = df_with_name["county_name"]
        df_with_name = df_with_name.drop(["county_name", "county_geoid", "lookup_geoid"], axis=1)

    return df_with_name


def validate_state(state: Union[str, int, List[Union[str, int]]]) -> List[str]:
    """Validate and convert state identifiers to FIPS codes.

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

        # Handle string inputs (strip whitespace and normalize case)
        if isinstance(s, str):
            s = s.strip()

        # Special case for District of Columbia (FIPS 11)
        # DC is not in us.states.lookup() but us.states.DC works
        if isinstance(s, str):
            s_lower = s.lower()
            if s_lower in ["dc", "d.c.", "district of columbia"]:
                fips_codes.append("11")
                continue

        # Try FIPS code first
        if isinstance(s, str) and s.isdigit() and len(s) <= 2:
            fips_code = s.zfill(2)
            # Special case for DC FIPS code
            if fips_code == "11":
                fips_codes.append("11")
                continue
            # Regular FIPS lookup
            state_obj = us.states.lookup(fips_code)
            if state_obj:
                fips_codes.append(fips_code)
                continue

        # Try direct attribute access for common abbreviations (handles DC)
        if isinstance(s, str) and len(s) == 2:
            try:
                state_obj = getattr(us.states, s.upper(), None)
                if state_obj:
                    fips_codes.append(state_obj.fips)
                    continue
            except AttributeError:
                pass

        # Try state lookup by name or abbreviation
        state_obj = us.states.lookup(str(s))
        if state_obj:
            fips_codes.append(state_obj.fips)
        else:
            raise ValueError(f"Invalid state identifier: {s}")

    return fips_codes


def validate_county(county: Union[str, int, List[Union[str, int]]], state_fips: str) -> List[str]:
    """Validate and convert county identifiers to FIPS codes.

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
        with importlib.resources.open_text("pytidycensus.data", "national_county.txt") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 4:
                    continue
                state_abr, state_fips, county_fips, county_name = parts[:4]

                county_name = _normalize_county_name(county_name)
                lookup[(state_fips.zfill(2), county_name.lower().strip())] = county_fips.zfill(3)
    except FileNotFoundError:
        print("Warning: national_county.txt not found, county lookups may fail.")
    return lookup


@lru_cache(maxsize=128)
def _get_county_data(state_fips: str) -> Dict[str, str]:
    """Fetch county data for a given state from Census API.

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
    """Normalize county name for lookup.

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
    """Look up county FIPS code by name.

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
    """Validate year for given dataset.

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


def check_overlapping_acs_periods(years: List[int], survey: str) -> None:
    """Check for and warn about overlapping ACS periods.

    Overlapping ACS periods (e.g., 2018 and 2019 for ACS5) share common years
    and should not be used for statistical comparisons or trend analysis.

    Parameters
    ----------
    years : list of int
        Years being requested
    survey : str
        Survey type ('acs1', 'acs3', or 'acs5')

    Warnings
    --------
    UserWarning
        If overlapping periods are detected
    """
    import warnings

    if len(years) < 2:
        return

    # Determine the survey window
    if survey == "acs5":
        window = 5
    elif survey == "acs3":
        window = 3
    elif survey == "acs1":
        return  # 1-year estimates don't overlap
    else:
        return

    # Check for overlapping periods
    sorted_years = sorted(years)
    overlapping_pairs = []

    for i in range(len(sorted_years) - 1):
        year1 = sorted_years[i]
        year2 = sorted_years[i + 1]

        # Years overlap if they're within the survey window
        if year2 - year1 < window:
            overlapping_pairs.append((year1, year2))

    if overlapping_pairs:
        overlap_str = ", ".join([f"{y1}-{y2}" for y1, y2 in overlapping_pairs])

        warnings.warn(
            f"\n{'='*70}\n"
            f"WARNING: Overlapping ACS {window}-year periods detected\n"
            f"{'='*70}\n\n"
            f"Overlapping year pairs: {overlap_str}\n\n"
            f"For ACS {window}-year estimates:\n"
            f"  - Each year represents {window} years of data\n"
            f"  - Example: {sorted_years[0]} ACS{window} = {sorted_years[0]-window+1}-{sorted_years[0]} data\n\n"
            f"IMPORTANT: Overlapping periods share common years of data and should\n"
            f"NOT be used for:\n"
            f"  - Statistical hypothesis testing\n"
            f"  - Formal trend analysis\n"
            f"  - Comparing changes over time with statistical inference\n\n"
            f"WHY: The shared years create statistical dependence between periods,\n"
            f"violating independence assumptions required for valid comparisons.\n\n"
            f"RECOMMENDATIONS:\n"
            f"  1. Use non-overlapping years (e.g., {sorted_years[0]}, {sorted_years[0]+window}, {sorted_years[0]+window*2})\n"
            f"  2. Use ACS 1-year estimates if available for your geography\n"
            f"  3. Only use overlapping periods for descriptive purposes\n\n"
            f"For more information, see:\n"
            f"https://www.census.gov/programs-surveys/acs/guidance/comparing-acs-data.html\n"
            f"{'='*70}\n",
            UserWarning,
            stacklevel=3,
        )


def validate_geography(geography: str, dataset: str = None) -> str:
    """Validate geography parameter.

    Parameters
    ----------
    geography : str
        Geography level
    dataset : str, optional
        Dataset type ("acs", "decennial", "estimates") for context-aware validation

    Returns
    -------
    str
        Validated geography

    Raises
    ------
    ValueError
        If geography is not recognized
    NotImplementedError
        If geography is recognized but not implemented for the specified dataset
    """
    # Implemented geographies (common to all datasets)
    common_implemented_geographies = [
        "us",
        "region",
        "division",
        "state",
        "county",
        "tract",
        "block group",
        "place",
        "metropolitan statistical area/micropolitan statistical area",
        "zip code tabulation area",
        "congressional district",
        "state legislative district (upper chamber)",
        "state legislative district (lower chamber)",
        "public use microdata area",
        "school district (elementary)",
        "school district (secondary)",
        "school district (unified)",
    ]

    # Dataset-specific geographies
    decennial_only_geographies = [
        "block",  # Only available in Decennial Census
    ]

    # Legacy aliases that redirect to implemented geographies
    legacy_aliases = {
        "cbg": "block group",
        "msa": "metropolitan statistical area/micropolitan statistical area",
        "zcta": "zip code tabulation area",
    }

    # Recognized but unimplemented geographies (regardless of dataset)
    unimplemented_geographies = [
        "county subdivision",
        "subminor civil division",
        "place/remainder (or part)",
        "county (or part)",
        "consolidated city",
        "place (or part)",
        "alaska native regional corporation",
        "american indian area/alaska native area/hawaiian home land",
        "tribal subdivision/remainder",
        "american indian area/alaska native area (reservation or statistical entity only)",
        "american indian area (off-reservation trust land only)/hawaiian home land",
        "tribal census tract",
        "tribal block group",
        "state (or part)",
        "american indian area/alaska native area/hawaiian home land (or part)",
        "american indian area/alaska native area (reservation or statistical entity only) (or part)",
        "american indian area (off-reservation trust land only)/hawaiian home land (or part)",
        "tribal census tract (or part)",
        "tribal block group (or part)",
        "principal city (or part)",
        "metropolitan division",
        "metropolitan statistical area/micropolitan statistical area (or part)",
        "metropolitan division (or part)",
        "combined statistical area",
        "combined statistical area (or part)",
        "urban area",
        "csa",
        "necta",
    ]

    # Normalize geography
    geography = geography.lower()

    # Handle legacy aliases
    if geography in legacy_aliases:
        geography = legacy_aliases[geography]

    # Check if geography is implemented for all datasets
    if geography in common_implemented_geographies:
        return geography

    # Check if geography is available only in specific datasets
    if geography in decennial_only_geographies:
        if dataset == "acs":
            raise NotImplementedError(
                f"Geography '{geography}' is not available in ACS data. "
                f"Block-level data is only available in Decennial Census."
            )
        elif dataset in ["decennial", None]:  # Allow for decennial or when dataset not specified
            return geography
        else:
            raise NotImplementedError(
                f"Geography '{geography}' is not available in {dataset} data. "
                f"Block-level data is only available in Decennial Census."
            )

    # Check if geography is recognized but unimplemented
    if geography in unimplemented_geographies:
        if geography in ["csa", "necta"]:
            geography_names = {
                "csa": "combined statistical area",
                "necta": "New England city and town area",
            }
            raise NotImplementedError(
                f"Geography '{geography}' ({geography_names.get(geography, geography)}) "
                f"is not yet implemented in pytidycensus."
            )
        else:
            raise NotImplementedError(
                f"Geography '{geography}' is recognized but not yet implemented in pytidycensus. "
                f"Please check the Census API documentation for the correct parameters or "
                f"consider contributing an implementation."
            )

    # Unknown geography
    raise ValueError(
        f"Geography '{geography}' is not recognized. "
        f"Please check the spelling or refer to the Census API documentation."
    )

    return geography


def build_geography_params(
    geography: str,
    state: Optional[Union[str, int, List[Union[str, int]]]] = None,
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    **kwargs,
) -> Dict[str, str]:
    """Build geography parameters for Census API call.

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

    Raises
    ------
    NotImplementedError
        If geography is recognized but not yet implemented
    """
    params = {}

    # Fully implemented geographies
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
    elif geography == "zip code tabulation area":
        # ZCTAs are national geographies that cannot be filtered by state
        params["for"] = "zip code tabulation area:*"
        # Note: ZCTAs ignore state parameter since they can cross state boundaries
    elif geography == "metropolitan statistical area/micropolitan statistical area":
        # CBSAs are also national geographies
        params["for"] = "metropolitan statistical area/micropolitan statistical area:*"
        # Note: CBSAs ignore state parameter since they can cross state boundaries
    elif geography == "place":
        # Basic implementation - may need enhancement for specific use cases
        params["for"] = f"{geography}:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
    elif geography == "congressional district":
        # Basic implementation - may need enhancement for specific use cases
        params["for"] = f"{geography}:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
    elif geography == "state legislative district (upper chamber)":
        # Basic implementation - may need enhancement for specific use cases
        params["for"] = f"{geography}:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
    elif geography == "state legislative district (lower chamber)":
        # Basic implementation - may need enhancement for specific use cases
        params["for"] = f"{geography}:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
    elif geography == "public use microdata area":
        # Basic implementation - may need enhancement for specific use cases
        params["for"] = f"{geography}:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
    elif geography == "school district (elementary)":
        # Basic implementation - may need enhancement for specific use cases
        params["for"] = f"{geography}:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
    elif geography == "school district (secondary)":
        # Basic implementation - may need enhancement for specific use cases
        params["for"] = f"{geography}:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
    elif geography == "school district (unified)":
        # Basic implementation - may need enhancement for specific use cases
        params["for"] = f"{geography}:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
    elif geography == "block":
        # Block geography - only available in Decennial Census
        params["for"] = "block:*"
        if state:
            state_fips = validate_state(state)
            params["in"] = f"state:{','.join(state_fips)}"
            if county:
                county_fips = validate_county(county, state_fips[0])
                params["in"] += f" county:{','.join(county_fips)}"

    # Unimplemented geographies that are recognized in Census API
    elif geography in [
        "county subdivision",
        "subminor civil division",
        "place/remainder (or part)",
        "county (or part)",
        "consolidated city",
        "place (or part)",
        "alaska native regional corporation",
        "american indian area/alaska native area/hawaiian home land",
        "tribal subdivision/remainder",
        "american indian area/alaska native area (reservation or statistical entity only)",
        "american indian area (off-reservation trust land only)/hawaiian home land",
        "tribal census tract",
        "tribal block group",
        "state (or part)",
        "american indian area/alaska native area/hawaiian home land (or part)",
        "american indian area/alaska native area (reservation or statistical entity only) (or part)",
        "american indian area (off-reservation trust land only)/hawaiian home land (or part)",
        "tribal census tract (or part)",
        "tribal block group (or part)",
        "principal city (or part)",
        "metropolitan division",
        "metropolitan statistical area/micropolitan statistical area (or part)",
        "metropolitan division (or part)",
        "combined statistical area",
        "combined statistical area (or part)",
        "urban area",
        "county (or part)",
    ]:
        raise NotImplementedError(
            f"Geography '{geography}' is recognized but not yet implemented in pytidycensus. "
            f"Please check the Census API documentation for the correct parameters or "
            f"consider contributing an implementation."
        )

    # Handle legacy aliases and abbreviations
    elif geography in ["msa", "csa", "necta", "zcta"]:
        if geography == "msa":
            # Redirect to full name
            return build_geography_params(
                "metropolitan statistical area/micropolitan statistical area",
                state=state,
                county=county,
                **kwargs,
            )
        elif geography == "zcta":
            # Redirect to full name
            return build_geography_params(
                "zip code tabulation area", state=state, county=county, **kwargs
            )
        elif geography in ["csa", "necta"]:
            # These are not implemented yet
            geography_names = {
                "csa": "combined statistical area",
                "necta": "New England city and town area",
            }
            raise NotImplementedError(
                f"Geography '{geography}' ({geography_names.get(geography, geography)}) "
                f"is not yet implemented in pytidycensus."
            )
    else:
        # Unknown geography
        raise ValueError(
            f"Geography '{geography}' is not recognized. "
            f"Please check the spelling or refer to the Census API documentation."
        )

    return params


def process_census_data(
    data: List[Dict[str, Any]], variables: List[str], output: str = "tidy"
) -> pd.DataFrame:
    """Process raw Census API response into pandas DataFrame.

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
            if df[var].dtype == "Int8" or df[var].dtype == "Int32" or df[var].dtype == "Int16":
                df[var] = df[var].astype("Int64")

    # Create GEOID from geography columns
    geo_cols = [
        col for col in df.columns if col in ["state", "county", "tract", "block group", "place"]
    ]

    # Handle special geography identifiers that are already GEOID-like
    geoid_like_cols = [
        "metropolitan statistical area/micropolitan statistical area",
        "zip code tabulation area",
        "us",
        "region",
        "division",
        "congressional district",
        "state legislative district (upper chamber)",
        "state legislative district (lower chamber)",
        "public use microdata area",
        "school district (elementary)",
        "school district (secondary)",
        "school district (unified)",
    ]

    # Check if we have a geoid-like column
    geoid_source_col = None
    for col in geoid_like_cols:
        if col in df.columns:
            geoid_source_col = col
            break

    if geoid_source_col:
        # Use the existing geoid-like column as GEOID
        df["GEOID"] = df[geoid_source_col].astype(str)
        # Remove the original column since we now have GEOID
        df = df.drop(columns=[geoid_source_col])
    elif geo_cols:
        # Build GEOID from multiple geography columns for hierarchical geographies
        df["GEOID"] = df[geo_cols].fillna("").astype(str).agg("".join, axis=1)

    geo_cols = ["GEOID"]

    # Reorder columns to put geographic identifiers first
    if output == "wide" and isinstance(df, (pd.DataFrame, GeoDataFrame)):
        # Get all columns
        all_cols = list(df.columns)

        # Get the remaining columns (excluding geo cols and geometry)
        if isinstance(df, GeoDataFrame):
            remaining_cols = [col for col in all_cols if col not in geo_cols and col != "geometry"]
            # Reorder: geo columns first, then data columns, then geometry last
            df = df[geo_cols + remaining_cols + ["geometry"]]
        else:
            remaining_cols = [col for col in all_cols if col not in geo_cols]
            # Reorder: geo columns first, then data columns
            df = df[geo_cols + remaining_cols]

    # Create NAME column using lookup table for state/county level data
    if "NAME" not in df.columns:
        # First try existing name fields from API response
        name_cols = [col for col in df.columns if "name" in col.lower()]
        if name_cols:
            df["NAME"] = df[name_cols[0]]
        else:
            # Use national_county.txt lookup table for state/county level data
            df = add_name_column(df)

    df.replace(missing_codes, pd.NA, inplace=True)

    if output == "tidy":
        # Reshape to long format
        id_vars = [col for col in df.columns if col not in variables]

        df_long = df.melt(
            id_vars=id_vars,
            value_vars=variables,
            var_name="variable",
            value_name="estimate",
        )
        df_long["estimate"] = pd.to_numeric(df_long["estimate"], errors="coerce")

        return df_long

    return df


def add_margin_of_error(
    df: pd.DataFrame, variables: List[str], moe_level: int = 90, output: str = "tidy"
) -> pd.DataFrame:
    """Add margin of error columns for ACS data with confidence level adjustment.

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
        # For tidy format, we need to create a separate 'moe' column
        # Ensure variable column is string type for str accessor
        df["variable"] = df["variable"].astype(str)
        # First, separate estimate and MOE rows
        estimate_rows = df[~df["variable"].str.endswith("M")].copy()
        moe_rows = df[df["variable"].str.endswith("M")].copy()

        # Adjust MOE values by confidence level
        moe_rows["estimate"] *= adjustment_factor

        # Create variable mapping: remove 'M' suffix from MOE variables
        moe_rows["variable"] = moe_rows["variable"].str.replace(r"M$", "E", regex=True)

        # Merge estimate and MOE data
        if not moe_rows.empty:
            # Merge on all columns except 'estimate'
            merge_cols = [col for col in estimate_rows.columns if col != "estimate"]
            result = estimate_rows.merge(
                moe_rows[merge_cols + ["estimate"]].rename(columns={"estimate": "moe"}),
                on=merge_cols,
                how="left",
            )
        else:
            # No MOE data available
            result = estimate_rows.copy()
            result["moe"] = pd.NA

        # Remove 'E' suffix from variable names to match R tidycensus format
        result["variable"] = result["variable"].str.replace(r"E$", "", regex=True)

        return result
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
            df[f"{var}_moe"] = df[moe_var].astype(float, errors="ignore") * adjustment_factor
            df = df.drop(columns=[moe_var])

    df.replace(missing_codes, pd.NA, inplace=True)

    return df
