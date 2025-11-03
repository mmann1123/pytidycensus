"""Geographic boundary data retrieval and processing using pygris."""

import warnings
from typing import List, Optional, Union

import geopandas as gpd
import pygris

from .utils import validate_county, validate_state


def _normalize_column_names(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Normalize column names from pygris to ensure consistent naming.

    Different file types (cartographic vs TIGER/Line) and years may use
    different column names. This function standardizes them.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Geographic data from pygris

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame with normalized column names
    """
    # Map alternate column names to standard names
    column_mapping = {
        "STATE": "STATEFP",
        "COUNTY": "COUNTYFP",
        "TRACT": "TRACTCE",
        "BLKGRP": "BLKGRPCE",
    }

    # Apply mappings only if standard column doesn't exist
    for alt_name, std_name in column_mapping.items():
        if alt_name in gdf.columns and std_name not in gdf.columns:
            gdf[std_name] = gdf[alt_name]

    return gdf


def _pygris_with_fallback(pygris_func, cb: bool = True, year: Optional[int] = None, **kwargs):
    """Call a pygris function with automatic fallback from cb=True to cb=False.

    This handles the issue where Census Bureau's GENZ2020 cartographic boundary files
    are protected by Cloudflare and return HTML instead of shapefiles. If a download
    fails with cb=True, we automatically retry with cb=False (detailed TIGER/Line files).

    Parameters
    ----------
    pygris_func : callable
        The pygris function to call (e.g., pygris.states)
    cb : bool, default True
        Whether to use cartographic boundary files
    year : int, optional
        Year for the data
    **kwargs
        Additional arguments to pass to the pygris function

    Returns
    -------
    geopandas.GeoDataFrame
        Geographic boundary data

    Raises
    ------
    Exception
        If both cb=True and cb=False attempts fail
    """
    try:
        # Try with the requested cb setting
        return pygris_func(cb=cb, year=year, **kwargs)
    except Exception as e:
        # Check if this looks like the GENZ2020 HTML download issue
        error_msg = str(e).lower()
        is_html_error = (
            "does not exist in the file system" in error_msg
            or "not recognized as a supported dataset name" in error_msg
            or "vsizip" in error_msg
        )

        # If cb=True failed with a file system error, try cb=False as fallback
        if cb and is_html_error:
            warnings.warn(
                f"Failed to download cartographic boundary files (cb=True) for year {year}. "
                f"This is a known issue with Census Bureau's 2020 GENZ files. "
                f"Automatically retrying with detailed TIGER/Line files (cb=False). "
                f"Original error: {str(e)[:100]}",
                UserWarning,
            )
            try:
                return pygris_func(cb=False, year=year, **kwargs)
            except Exception as fallback_error:
                # Both attempts failed - raise an informative error
                raise Exception(
                    f"Failed to download geography data with both cb=True and cb=False. "
                    f"cb=True error: {str(e)[:100]}... "
                    f"cb=False error: {str(fallback_error)[:100]}..."
                )
        else:
            # Not the HTML error, or cb was already False - just re-raise
            raise


def get_geography(
    geography: str,
    year: int = 2022,
    state: Optional[Union[str, int, List[Union[str, int]]]] = None,
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    keep_geo_vars: bool = False,
    cache_dir: Optional[str] = None,
    cb: bool = True,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Download and load geographic boundary data using pygris.

    Parameters
    ----------
    geography : str
        Geography type (e.g., 'county', 'tract', 'block group', 'state', 'zcta', 'place')
    year : int, default 2022
        Census year for boundaries
    state : str, int, or list, optional
        State(s) to filter data for. Can be state name, abbreviation, or FIPS code.
    county : str, int, or list, optional
        County(ies) to filter data for (requires state). Can be county name or FIPS code.
    keep_geo_vars : bool, default False
        Whether to keep all geographic variables
    cache_dir : str, optional
        Directory for caching downloaded files (currently not used with pygris)
    cb : bool, default True
        If True, download generalized cartographic boundary files (1:500k).
        If False, download detailed TIGER/Line files.
        Note: For 2020 state-level data, cartographic boundaries may fail due to
        Census Bureau access restrictions. The function will automatically fall back
        to detailed TIGER/Line files (cb=False) if this occurs.
    **kwargs
        Additional parameters passed to underlying pygris functions

    Returns
    -------
    geopandas.GeoDataFrame
        Geographic boundary data

    Notes
    -----
    Automatic Fallback: If downloading cartographic boundary files (cb=True) fails
    with file system errors (common for 2020 state-level GENZ files), the function
    will automatically retry with detailed TIGER/Line files (cb=False) and issue
    a warning. This ensures robust data retrieval without requiring manual intervention.

    Examples
    --------
    >>> # Get county boundaries for Texas
    >>> tx_counties = get_geography("county", state="TX", year=2022)
    >>>
    >>> # Get tract boundaries for Harris County, TX
    >>> harris_tracts = get_geography(
    ...     "tract",
    ...     state="TX",
    ...     county="201",
    ...     year=2022
    ... )
    >>>
    >>> # Get 2020 state boundaries (will auto-fallback if needed)
    >>> states_2020 = get_geography("state", year=2020)
    """
    # Normalize geography names to match pygris conventions
    geography_lower = geography.lower()

    # Map pytidycensus geography names to pygris functions
    if geography_lower == "state":
        gdf = _get_states(year=year, cb=cb, **kwargs)
        gdf = _normalize_column_names(gdf)
        if state:
            state_fips_list = validate_state(state)
            gdf = gdf[gdf["STATEFP"].isin(state_fips_list)]

    elif geography_lower == "county":
        # Handle state filtering
        state_arg = None
        if state:
            state_codes = validate_state(state)
            if len(state_codes) == 1:
                # pygris can handle single state efficiently
                state_arg = state_codes[0]
            # If multiple states, we'll download all and filter below

        gdf = _get_counties(state=state_arg, year=year, cb=cb, **kwargs)
        gdf = _normalize_column_names(gdf)

        # Filter by multiple states if needed
        if state and len(validate_state(state)) > 1:
            state_fips_list = validate_state(state)
            gdf = gdf[gdf["STATEFP"].isin(state_fips_list)]

        # Filter by county if specified
        if county and state:
            state_for_county = (
                validate_state(state)[0]
                if isinstance(state, (str, int))
                else validate_state(state[0])[0]
            )
            county_fips_list = validate_county(county, state_for_county)
            gdf = gdf[gdf["COUNTYFP"].isin(county_fips_list)]

    elif geography_lower == "tract":
        if not state:
            raise ValueError("State must be specified for tract geography")

        state_codes = validate_state(state)
        if len(state_codes) > 1:
            raise ValueError("Only one state can be specified for tract geography")

        state_fips = state_codes[0]
        county_arg = None

        # Handle county filtering
        if county:
            county_codes = validate_county(county, state_fips)
            if len(county_codes) == 1:
                county_arg = county_codes[0]

        gdf = _get_tracts(state=state_fips, county=county_arg, year=year, cb=cb, **kwargs)
        gdf = _normalize_column_names(gdf)

        # Filter by multiple counties if needed
        if county and county_arg is None:
            county_fips_list = validate_county(county, state_fips)
            gdf = gdf[gdf["COUNTYFP"].isin(county_fips_list)]

    elif geography_lower == "block group":
        if not state:
            raise ValueError("State must be specified for block group geography")

        state_codes = validate_state(state)
        if len(state_codes) > 1:
            raise ValueError("Only one state can be specified for block group geography")

        state_fips = state_codes[0]
        county_arg = None

        # Handle county filtering
        if county:
            county_codes = validate_county(county, state_fips)
            if len(county_codes) == 1:
                county_arg = county_codes[0]

        gdf = _get_block_groups(state=state_fips, county=county_arg, year=year, cb=cb, **kwargs)
        gdf = _normalize_column_names(gdf)

        # Filter by multiple counties if needed
        if county and county_arg is None:
            county_fips_list = validate_county(county, state_fips)
            gdf = gdf[gdf["COUNTYFP"].isin(county_fips_list)]

    elif geography_lower in ["zcta", "zip code tabulation area"]:
        gdf = _get_zctas(year=year, cb=cb, **kwargs)

    elif geography_lower == "place":
        if not state:
            raise ValueError("State must be specified for place geography")

        state_codes = validate_state(state)
        if len(state_codes) > 1:
            raise ValueError("Only one state can be specified for place geography")

        state_fips = state_codes[0]
        gdf = _get_places(state=state_fips, year=year, cb=cb, **kwargs)

    elif geography_lower in [
        "metropolitan statistical area/micropolitan statistical area",
        "cbsa",
        "metro",
    ]:
        gdf = _get_cbsas(year=year, cb=cb, **kwargs)

    else:
        raise ValueError(
            f"Geography '{geography}' not supported. "
            f"Supported geographies: state, county, tract, block group, zcta, place, "
            f"metropolitan statistical area/micropolitan statistical area"
        )

    # Standardize GEOID column if needed
    if "GEOID" not in gdf.columns:
        if geography_lower == "state" and "STATEFP" in gdf.columns:
            gdf["GEOID"] = gdf["STATEFP"]
        elif geography_lower == "county" and "STATEFP" in gdf.columns and "COUNTYFP" in gdf.columns:
            gdf["GEOID"] = gdf["STATEFP"] + gdf["COUNTYFP"]
        elif (
            geography_lower == "tract"
            and "STATEFP" in gdf.columns
            and "COUNTYFP" in gdf.columns
            and "TRACTCE" in gdf.columns
        ):
            gdf["GEOID"] = gdf["STATEFP"] + gdf["COUNTYFP"] + gdf["TRACTCE"]
        elif (
            geography_lower == "block group"
            and "STATEFP" in gdf.columns
            and "COUNTYFP" in gdf.columns
            and "TRACTCE" in gdf.columns
            and "BLKGRPCE" in gdf.columns
        ):
            gdf["GEOID"] = gdf["STATEFP"] + gdf["COUNTYFP"] + gdf["TRACTCE"] + gdf["BLKGRPCE"]
        elif (
            geography_lower
            in [
                "metropolitan statistical area/micropolitan statistical area",
                "cbsa",
                "metro",
            ]
            and "CBSAFP" in gdf.columns
        ):
            gdf["GEOID"] = gdf["CBSAFP"]
        elif geography_lower in ["zcta", "zip code tabulation area"]:
            # pygris ZCTA files may use different column names depending on year
            if "ZCTA5CE20" in gdf.columns:
                gdf["GEOID"] = gdf["ZCTA5CE20"]
            elif "ZCTA5CE10" in gdf.columns:
                gdf["GEOID"] = gdf["ZCTA5CE10"]
            elif "GEOID20" in gdf.columns:
                gdf["GEOID"] = gdf["GEOID20"]
            elif "GEOID10" in gdf.columns:
                gdf["GEOID"] = gdf["GEOID10"]

    # Clean up columns if not keeping all geo vars
    if not keep_geo_vars:
        # Keep essential columns
        essential_cols = ["GEOID", "NAME", "geometry"]
        if geography_lower == "state":
            essential_cols.extend(["STATEFP", "STUSPS"])
        elif geography_lower == "county":
            essential_cols.extend(["STATEFP", "COUNTYFP", "NAMELSAD"])
        elif geography_lower in ["tract", "block group"]:
            essential_cols.extend(["STATEFP", "COUNTYFP", "TRACTCE"])
            if geography_lower == "block group":
                essential_cols.append("BLKGRPCE")
        elif geography_lower in [
            "metropolitan statistical area/micropolitan statistical area",
            "cbsa",
            "metro",
        ]:
            essential_cols.extend(["CBSAFP", "NAMELSAD"])
        elif geography_lower in ["zcta", "zip code tabulation area"]:
            # Keep both 2010 and 2020 ZCTA codes since they may vary by year
            essential_cols.extend(["ZCTA5CE20", "ZCTA5CE10", "GEOID20", "GEOID10"])

        # Keep only columns that exist
        cols_to_keep = [col for col in essential_cols if col in gdf.columns]
        gdf = gdf[cols_to_keep]

    # Ensure CRS is set
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4269")

    return gdf


def _get_states(year: Optional[int] = None, cb: bool = True, **kwargs) -> gpd.GeoDataFrame:
    """Get state boundaries using pygris with automatic fallback to cb=False on failure."""
    return _pygris_with_fallback(pygris.states, cb=cb, year=year, **kwargs)


def _get_counties(
    state: Optional[str] = None, year: Optional[int] = None, cb: bool = True, **kwargs
) -> gpd.GeoDataFrame:
    """Get county boundaries using pygris with automatic fallback to cb=False on failure."""
    return _pygris_with_fallback(
        lambda cb, year, **kw: pygris.counties(state=state, cb=cb, year=year, **kw),
        cb=cb,
        year=year,
        **kwargs,
    )


def _get_tracts(
    state: str,
    county: Optional[str] = None,
    year: Optional[int] = None,
    cb: bool = True,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Get tract boundaries using pygris with automatic fallback to cb=False on failure."""
    return _pygris_with_fallback(
        lambda cb, year, **kw: pygris.tracts(state=state, county=county, cb=cb, year=year, **kw),
        cb=cb,
        year=year,
        **kwargs,
    )


def _get_block_groups(
    state: str,
    county: Optional[str] = None,
    year: Optional[int] = None,
    cb: bool = True,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Get block group boundaries using pygris with automatic fallback to cb=False on failure."""
    return _pygris_with_fallback(
        lambda cb, year, **kw: pygris.block_groups(
            state=state, county=county, cb=cb, year=year, **kw
        ),
        cb=cb,
        year=year,
        **kwargs,
    )


def _get_zctas(year: Optional[int] = None, cb: bool = True, **kwargs) -> gpd.GeoDataFrame:
    """Get ZCTA boundaries using pygris with automatic fallback to cb=False on failure."""
    return _pygris_with_fallback(pygris.zctas, cb=cb, year=year, **kwargs)


def _get_places(
    state: str, year: Optional[int] = None, cb: bool = True, **kwargs
) -> gpd.GeoDataFrame:
    """Get place boundaries using pygris with automatic fallback to cb=False on failure."""
    return _pygris_with_fallback(
        lambda cb, year, **kw: pygris.places(state=state, cb=cb, year=year, **kw),
        cb=cb,
        year=year,
        **kwargs,
    )


def _get_cbsas(year: Optional[int] = None, cb: bool = True, **kwargs) -> gpd.GeoDataFrame:
    """Get CBSA boundaries using pygris with automatic fallback to cb=False on failure."""
    return _pygris_with_fallback(pygris.core_based_statistical_areas, cb=cb, year=year, **kwargs)


def get_state_boundaries(year: int = 2022, cb: bool = True, **kwargs) -> gpd.GeoDataFrame:
    """Get US state boundaries.

    Parameters
    ----------
    year : int, default 2022
        Census year for boundaries
    cb : bool, default True
        If True, download generalized cartographic boundary files
    **kwargs
        Additional parameters

    Returns
    -------
    geopandas.GeoDataFrame
        State boundaries
    """
    return get_geography("state", year=year, cb=cb, **kwargs)


def get_county_boundaries(
    state: Optional[Union[str, int, List[Union[str, int]]]] = None,
    year: int = 2022,
    cb: bool = True,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Get US county boundaries, optionally filtered by state.

    Parameters
    ----------
    state : str, int, or list, optional
        State(s) to filter by
    year : int, default 2022
        Census year for boundaries
    cb : bool, default True
        If True, download generalized cartographic boundary files
    **kwargs
        Additional parameters

    Returns
    -------
    geopandas.GeoDataFrame
        County boundaries
    """
    return get_geography("county", year=year, state=state, cb=cb, **kwargs)


def get_tract_boundaries(
    state: Union[str, int],
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    year: int = 2022,
    cb: bool = True,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Get census tract boundaries for a state, optionally filtered by county.

    Parameters
    ----------
    state : str or int
        State to get tracts for
    county : str, int, or list, optional
        County(ies) to filter by
    year : int, default 2022
        Census year for boundaries
    cb : bool, default True
        If True, download generalized cartographic boundary files
    **kwargs
        Additional parameters

    Returns
    -------
    geopandas.GeoDataFrame
        Tract boundaries
    """
    return get_geography("tract", year=year, state=state, county=county, cb=cb, **kwargs)


def get_block_group_boundaries(
    state: Union[str, int],
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    year: int = 2022,
    cb: bool = True,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Get block group boundaries for a state, optionally filtered by county.

    Parameters
    ----------
    state : str or int
        State to get block groups for
    county : str, int, or list, optional
        County(ies) to filter by
    year : int, default 2022
        Census year for boundaries
    cb : bool, default True
        If True, download generalized cartographic boundary files
    **kwargs
        Additional parameters

    Returns
    -------
    geopandas.GeoDataFrame
        Block group boundaries
    """
    return get_geography("block group", year=year, state=state, county=county, cb=cb, **kwargs)
