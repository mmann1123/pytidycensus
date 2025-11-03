"""Migration flows data from the American Community Survey (ACS).

This module provides functionality to retrieve migration flow data from
the Census Migration Flows API, which tracks population movement between
geographic areas.
"""

import os
import warnings
from typing import List, Optional, Union

import pandas as pd

from .api import CensusAPI
from .utils import validate_county, validate_state


def identify_geoid_type(geoid: Union[str, int, None]) -> str:
    """Identify the geographic level of a GEOID based on its length.

    Parameters
    ----------
    geoid : str, int, or None
        A Census GEOID code

    Returns
    -------
    str
        Geographic type: 'county', 'county subdivision', 'state', 'tract', or 'unknown'

    Examples
    --------
    >>> identify_geoid_type('12133')
    'county'
    >>> identify_geoid_type('3400557510')
    'county subdivision'
    >>> identify_geoid_type(None)
    'unknown'
    """
    if geoid is None:
        return "unknown"

    geoid_str = str(geoid)
    geoid_len = len(geoid_str)

    if geoid_len == 2:
        return "state"
    elif geoid_len == 5:
        return "county"
    elif geoid_len == 10:
        return "county subdivision"
    elif geoid_len == 11:
        return "tract"
    else:
        return "unknown"


def get_flows(
    geography: str,
    variables: Optional[List[str]] = None,
    breakdown: Optional[List[str]] = None,
    breakdown_labels: bool = False,
    year: int = 2018,
    output: str = "tidy",
    state: Optional[Union[str, List[str]]] = None,
    county: Optional[Union[str, List[str]]] = None,
    msa: Optional[Union[str, List[str]]] = None,
    geometry: bool = False,
    api_key: Optional[str] = None,
    moe_level: int = 90,
    show_call: bool = False,
) -> pd.DataFrame:
    """Retrieve migration flow data from the Census Migration Flows API.

    The Migration Flows API provides data on population movement between geographic
    areas based on American Community Survey 5-year estimates.

    Parameters
    ----------
    geography : str
        Geographic level for the data. Must be one of:
        - "county"
        - "county subdivision"
        - "metropolitan statistical area"
    variables : list of str, optional
        Census variable names to retrieve. If None, returns default flow variables.
    breakdown : list of str, optional
        Demographic breakdown characteristics. Available for years 2006-2015 only.
        Options include: AGE, SEX, RACE, HSGP, REL, HHT, TEN, ENG, POB, YEARS,
        ESR, OCC, WKS, SCHL, AHINC, APINC, HISP_ORIGIN.
    breakdown_labels : bool, default False
        If True, replace breakdown variable codes with descriptive labels.
    year : int, default 2018
        ACS 5-year survey ending year. Available years: 2010-2018.
    output : str, default "tidy"
        Output format. Options:
        - "tidy": Long format focusing on core migration variables (MOVEDIN, MOVEDOUT, MOVEDNET)
        - "wide": Wide format matching API response structure (recommended for breakdown variables)
    state : str or list of str, optional
        State(s) to filter by. Can be state abbreviation, name, or FIPS code.
    county : str or list of str, optional
        County(ies) to filter by. Can be county name or FIPS code.
    msa : str or list of str, optional
        Metropolitan Statistical Area(s) to filter by.
    geometry : bool, default False
        If True, include geographic centroids for mapping flows.
        Raises RuntimeError if geometry data cannot be downloaded.

        Centroids are calculated in EPSG:2163 (US National Atlas Equal Area)
        projection for accuracy and to properly position Alaska and Hawaii,
        then transformed back to EPSG:4269 (NAD83) for compatibility.

        Note: The Census API may return mixed geographic levels in GEOID2
        (destination). For example, when requesting county-level flows,
        GEOID2 may contain both 5-digit county codes and 10-digit county
        subdivision codes. When geometry=True, centroids for both counties
        and subdivisions will be automatically retrieved.
    api_key : str, optional
        Census API key. If None, uses CENSUS_API_KEY environment variable.
    moe_level : int, default 90
        Confidence level for margin of error. Options: 90, 95, 99.
    show_call : bool, default False
        If True, print the API call URL.

    Returns
    -------
    pandas.DataFrame or geopandas.GeoDataFrame
        Migration flow data. If geometry=True, returns GeoDataFrame with
        origin and destination centroids.

        GEOID columns contain Census geographic identifiers:
        - GEOID1, GEOID2: Origin and destination GEOIDs
        - 5-digit codes: County level (e.g., '12133' = Washington County, FL)
        - 10-digit codes: County subdivision level (e.g., '3400557510' =
          Pemberton township, Burlington County, NJ)
        - First 5 digits of subdivision codes represent the parent county

        Use identify_geoid_type() to determine the geographic level of any GEOID.

    Examples
    --------
    Get county-to-county migration flows for Texas:

    >>> import pytidycensus as tc
    >>> tx_flows = tc.get_flows(
    ...     geography="county",
    ...     state="TX",
    ...     year=2018
    ... )

    Get flows with demographic breakdowns (pre-2016 only):

    >>> flows_by_age = tc.get_flows(
    ...     geography="county",
    ...     breakdown=["AGE", "SEX"],
    ...     breakdown_labels=True,
    ...     state="CA",
    ...     year=2015
    ... )
    """
    # Input validation
    _validate_flows_parameters(geography, year, breakdown, moe_level, output)

    # Load migration recodes data for breakdown processing
    mig_recodes = _load_migration_recodes()

    # Prepare variables list
    variables_list = _prepare_variables(variables, breakdown, mig_recodes)

    # Make API call
    flows_data = _load_migration_flows(
        geography=geography,
        variables=variables_list,
        year=year,
        state=state,
        county=county,
        msa=msa,
        api_key=api_key,
        show_call=show_call,
    )

    # Process breakdown variables if specified
    if breakdown:
        flows_data = _process_breakdown_variables(
            flows_data, breakdown, mig_recodes, breakdown_labels
        )

    # Transform output format
    flows_data = _transform_flows_output(flows_data, output, moe_level, variables_list)

    # Add geometry if requested
    if geometry:
        flows_data = _add_flows_geometry(flows_data, geography)

    return flows_data


def _validate_flows_parameters(geography, year, breakdown, moe_level, output):
    """Validate input parameters for get_flows function."""
    # Geography validation
    valid_geographies = ["county", "county subdivision", "metropolitan statistical area"]
    if geography not in valid_geographies:
        raise ValueError(f'Geography must be one of: {", ".join(valid_geographies)}')

    # Year validation
    if year < 2010:
        raise ValueError("Migration flows are available beginning in 2010")

    if year > 2018:
        warnings.warn(
            f"Migration flows API may not have data for {year}. " "Latest confirmed year is 2018."
        )

    # MSA availability
    if geography == "metropolitan statistical area" and year <= 2012:
        raise ValueError(
            "MSA-level data is only available beginning with 2013 (2009-2013 5-year ACS)"
        )

    # Breakdown characteristics
    if breakdown and year > 2015:
        raise ValueError("Breakdown characteristics are only available for surveys before 2016")

    # MOE level validation
    if moe_level not in [90, 95, 99]:
        raise ValueError("moe_level must be 90, 95, or 99")

    # Output format validation
    if output not in ["tidy", "wide"]:
        raise ValueError('output must be "tidy" or "wide"')


def _load_migration_recodes():
    """Load migration variable recodes from CSV file."""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    recode_file = os.path.join(data_dir, "mig-flow-recode.csv")

    try:
        recodes = pd.read_csv(recode_file)
        # Convert ordered column to boolean
        recodes["ordered"] = recodes["ordered"].map({"TRUE": True, "FALSE": False})
        return recodes
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Migration recode file not found: {recode_file}. "
            "This file is required for breakdown variable processing."
        )


def _prepare_variables(variables, breakdown, mig_recodes):
    """Prepare variables list for API call."""
    # Default core migration variables
    always_vars = [
        "GEOID1",
        "GEOID2",
        "FULL1_NAME",
        "FULL2_NAME",
        "MOVEDIN",
        "MOVEDIN_M",
        "MOVEDOUT",
        "MOVEDOUT_M",
        "MOVEDNET",
        "MOVEDNET_M",
    ]

    # All possible breakdown characteristics from recodes
    all_breakdown_vars = mig_recodes["characteristic"].unique().tolist()

    # Start with always variables
    variables_list = always_vars.copy()

    # Add breakdown variables if specified
    if breakdown:
        variables_list.extend(breakdown)

    # Add user-specified variables (avoiding duplicates)
    if variables:
        for var in variables:
            if var not in variables_list and var not in all_breakdown_vars:
                variables_list.append(var)

    return variables_list


def _load_migration_flows(geography, variables, year, state, county, msa, api_key, show_call):
    """Load migration flows data from Census API."""
    # Initialize API client
    api = CensusAPI(api_key)

    # Build API endpoint
    base_url = f"https://api.census.gov/data/{year}/acs/flows"

    # Prepare variables string
    vars_string = ",".join(variables)

    # Build geography specification
    for_clause, in_clause = _build_geography_clauses(geography, year, state, county, msa)

    # Build query parameters
    params = {"get": vars_string, "for": for_clause, "key": api.api_key}

    if in_clause:
        params["in"] = in_clause

    if show_call:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        print(f"API call: {base_url}?{query_string}")

    # Make API request
    response = api.session.get(base_url, params=params)

    if response.status_code != 200:
        error_msg = response.text
        if "not available" in error_msg:
            raise ValueError(
                "One or more requested variables is likely not available "
                "at the requested geography."
            )
        else:
            raise RuntimeError(f"API error: {error_msg}")

    # Parse response
    data = response.json()

    # Convert to DataFrame
    df = pd.DataFrame(data[1:], columns=data[0])

    # Remove auto-returned geography columns that we don't need
    geo_cols_to_remove = [
        "state",
        "county",
        "county subdivision",
        "metropolitan statistical area/micropolitan statistical area",
        "metropolitan statistical areas",
    ]
    for col in geo_cols_to_remove:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Convert numeric columns
    string_vars = [
        v
        for v in variables
        if any(x in v for x in ["_NAME", "GEOID", "STATE", "COUNTY", "MCD", "METRO"])
    ]
    numeric_vars = [v for v in variables if v not in string_vars]

    for col in numeric_vars:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _build_geography_clauses(geography, year, state, county, msa):
    """Build 'for' and 'in' clauses for API geography specification."""
    for_clause = f"{geography}:*"
    in_clause = None

    if geography == "county":
        if county:
            # Validate and format county codes
            if isinstance(county, str):
                county = [county]
            # Get state code for county validation
            if state:
                if isinstance(state, str):
                    state_for_county = validate_state(state)[0]
                else:
                    state_for_county = validate_state(state[0])[0]
            else:
                raise ValueError("State must be specified when filtering by county")

            county_codes = []
            for c in county:
                county_codes.extend(validate_county(state_for_county, c))
            for_clause = f"county:{','.join(county_codes)}"

        if state:
            # Validate and format state codes
            if isinstance(state, str):
                state = [state]
            # validate_state returns a list, so we need to flatten
            state_codes = []
            for s in state:
                state_codes.extend(validate_state(s))
            in_clause = f"state:{','.join(state_codes)}"

    elif geography == "county subdivision":
        if state:
            if isinstance(state, str):
                state = [state]
            # validate_state returns a list, so we need to flatten
            state_codes = []
            for s in state:
                state_codes.extend(validate_state(s))

            if county:
                if isinstance(county, str):
                    county = [county]
                county_codes = []
                for c in county:
                    county_codes.extend(validate_county(state_codes[0], c))
                in_clause = f"state:{state_codes[0]} county:{','.join(county_codes)}"
            else:
                in_clause = f"state:{','.join(state_codes)}"

    elif geography == "metropolitan statistical area":
        # API geography name differs for years <= 2015
        if year <= 2015:
            geography_name = "metropolitan statistical areas"
        else:
            geography_name = "metropolitan statistical area/micropolitan statistical area"

        if msa:
            if isinstance(msa, str):
                msa = [msa]
            for_clause = f"{geography_name}:{','.join(msa)}"
        else:
            for_clause = f"{geography_name}:*"

    return for_clause, in_clause


def _process_breakdown_variables(data, breakdown, mig_recodes, breakdown_labels):
    """Process breakdown variables with codes and labels."""
    # Zero-pad breakdown variable codes
    mig_recodes["characteristic"].unique().tolist()

    for var in breakdown:
        if var in data.columns:
            data[var] = data[var].astype(str).str.zfill(2)

    # Add labels if requested
    if breakdown_labels:
        for var in breakdown:
            if var in data.columns:
                # Create lookup from recodes
                var_recodes = mig_recodes[mig_recodes["characteristic"] == var]
                lookup = dict(
                    zip(var_recodes["code"].astype(str).str.zfill(2), var_recodes["desc"])
                )

                # Map labels
                data[f"{var}_label"] = data[var].map(lookup)

                # Create ordered categorical if specified
                if var_recodes["ordered"].iloc[0]:
                    categories = var_recodes.sort_values("code")["desc"].tolist()
                    data[f"{var}_label"] = pd.Categorical(
                        data[f"{var}_label"], categories=categories, ordered=True
                    )

    return data


def _transform_flows_output(data, output, moe_level, variables):
    """Transform data to requested output format and apply MOE adjustments."""
    # Calculate MOE adjustment factor
    if moe_level == 90:
        moe_factor = 1.0
    elif moe_level == 95:
        moe_factor = 1.96 / 1.645
    elif moe_level == 99:
        moe_factor = 2.56 / 1.645

    if output == "wide":
        # Apply MOE factor to margin of error columns
        moe_cols = [col for col in data.columns if col.endswith("_M")]
        for col in moe_cols:
            data[col] = data[col] * moe_factor

    elif output == "tidy":
        # For flows data, tidy format is less useful due to the complexity of breakdown variables
        # We'll provide a simplified tidy transformation that focuses on core migration variables

        # Identify core migration variables (estimate and MOE pairs)
        core_vars = ["MOVEDIN", "MOVEDOUT", "MOVEDNET"]

        # Find which core variables are actually present
        available_vars = [var for var in core_vars if var in data.columns]

        if not available_vars:
            # If no core variables, just apply MOE factor and return as-is
            warnings.warn(
                "No core migration variables found for tidy transformation. "
                "Returning wide format with MOE adjustment."
            )
            moe_cols = [col for col in data.columns if col.endswith("_M")]
            for col in moe_cols:
                if col in data.columns:
                    data[col] = data[col] * moe_factor
            return data

        # Create tidy format for core migration variables only
        tidy_rows = []

        # Get ID columns (non-numeric or specific geographic identifiers)
        id_cols = [
            col
            for col in data.columns
            if not pd.api.types.is_numeric_dtype(data[col])
            or col in ["GEOID1", "GEOID2"]
            or col.endswith("_label")
        ]  # Include breakdown labels

        for _, row in data.iterrows():
            for var in available_vars:
                if var in data.columns:
                    tidy_row = {}

                    # Copy ID columns
                    for id_col in id_cols:
                        if id_col in data.columns:
                            tidy_row[id_col] = row[id_col]

                    # Add variable info
                    tidy_row["variable"] = var
                    tidy_row["estimate"] = row.get(var, None)

                    # Add MOE if available
                    moe_col = f"{var}_M"
                    if moe_col in data.columns:
                        tidy_row["moe"] = row.get(moe_col, None) * moe_factor
                    else:
                        tidy_row["moe"] = None

                    tidy_rows.append(tidy_row)

        # Convert to DataFrame
        data = pd.DataFrame(tidy_rows)

        # Ensure numeric columns are properly typed
        if "estimate" in data.columns:
            data["estimate"] = pd.to_numeric(data["estimate"], errors="coerce")
        if "moe" in data.columns:
            data["moe"] = pd.to_numeric(data["moe"], errors="coerce")

    return data


def _add_flows_geometry(data, geography):
    """Add geometric centroids for flow mapping."""
    try:
        import geopandas as gpd

        from .geography import get_geography
    except ImportError:
        warnings.warn("GeoPandas not available. Returning data without geometry.")
        return data

    # Generate centroids for all unique GEOIDs in the data
    all_geoids = set()
    if "GEOID1" in data.columns:
        all_geoids.update(data["GEOID1"].dropna().unique())
    if "GEOID2" in data.columns:
        all_geoids.update(data["GEOID2"].dropna().unique())

    if not all_geoids:
        raise ValueError("No GEOID columns found for geometry processing.")

    # Get geographic boundaries and calculate centroids
    try:
        # For flows, we need to get centroids for all relevant geographies
        centroids_dict = {}

        if geography == "county":
            # Separate GEOIDs by geography type based on length
            county_geoids = set()
            subdivision_geoids = set()

            for geoid in all_geoids:
                geoid_str = str(geoid)
                if len(geoid_str) == 5:
                    county_geoids.add(geoid)
                elif len(geoid_str) == 10:
                    subdivision_geoids.add(geoid)
                # Ignore other formats (e.g., None, international locations)

            try:
                # Get all US counties in one download
                if county_geoids:
                    all_counties = get_geography(
                        geography="county", year=2022  # Use recent year for boundaries
                    )

                    # Reproject to US National Atlas Equal Area (EPSG:2163) for accurate centroids
                    # This projection is designed for the entire US with AK/HI repositioned
                    all_counties_proj = all_counties.to_crs(epsg=2163)

                    # Calculate centroids in projected coordinates
                    all_counties_proj["centroid"] = all_counties_proj.geometry.centroid

                    # Transform centroids back to original CRS (EPSG:4269)
                    centroids_gdf = gpd.GeoDataFrame(
                        all_counties_proj[["GEOID", "centroid"]],
                        geometry="centroid",
                        crs="EPSG:2163",
                    ).to_crs("EPSG:4269")

                    # Create lookup dictionary for all counties we need
                    for _, row in centroids_gdf.iterrows():
                        if row["GEOID"] in county_geoids:
                            centroids_dict[row["GEOID"]] = row["centroid"]

                # Get county subdivisions if present in the data
                if subdivision_geoids:
                    # Group subdivisions by state to download efficiently
                    subdivisions_by_state = {}
                    for geoid in subdivision_geoids:
                        state_fips = str(geoid)[:2]
                        if state_fips not in subdivisions_by_state:
                            subdivisions_by_state[state_fips] = set()
                        subdivisions_by_state[state_fips].add(geoid)

                    # Download subdivisions state by state
                    import pygris

                    for state_fips, state_geoids in subdivisions_by_state.items():
                        try:
                            state_subdivisions = pygris.county_subdivisions(
                                state=state_fips,
                                cb=True,  # Use generalized boundaries for speed
                                year=2022,
                            )

                            # Reproject to US National Atlas Equal Area (EPSG:2163)
                            state_subdivisions_proj = state_subdivisions.to_crs(epsg=2163)

                            # Calculate centroids in projected coordinates
                            state_subdivisions_proj["centroid"] = (
                                state_subdivisions_proj.geometry.centroid
                            )

                            # Transform centroids back to original CRS (EPSG:4269)
                            subdiv_centroids_gdf = gpd.GeoDataFrame(
                                state_subdivisions_proj[["GEOID", "centroid"]],
                                geometry="centroid",
                                crs="EPSG:2163",
                            ).to_crs("EPSG:4269")

                            # Add to lookup dictionary
                            for _, row in subdiv_centroids_gdf.iterrows():
                                if row["GEOID"] in state_geoids:
                                    centroids_dict[row["GEOID"]] = row["centroid"]
                        except Exception as subdiv_error:
                            warnings.warn(
                                f"Could not download county subdivisions for state {state_fips}: "
                                f"{subdiv_error}. Subdivision centroids may be missing."
                            )
                            continue

                # Check for any missing GEOIDs
                expected_geoids = county_geoids | subdivision_geoids
                missing_geoids = expected_geoids - set(centroids_dict.keys())
                if missing_geoids:
                    warnings.warn(
                        f"Could not find centroids for {len(missing_geoids)} GEOIDs: "
                        f"{list(missing_geoids)[:5]}{'...' if len(missing_geoids) > 5 else ''}. "
                        f"These flows will not have geometry data."
                    )

            except Exception as e:
                raise RuntimeError(
                    f"Could not download geography: {e}. "
                    f"Unable to provide geometry for flows data. "
                    f"Try setting geometry=False or check your internet connection."
                ) from e

        elif geography == "county subdivision":
            raise NotImplementedError(
                "Geometry for county subdivision is not yet implemented. "
                "Use geometry=False or try a different geography level."
            )

        elif geography == "metropolitan statistical area":
            raise NotImplementedError(
                "Geometry for metropolitan statistical area is not yet implemented. "
                "Use geometry=False or try a different geography level."
            )

        # Add centroid columns to the data
        data = data.copy()

        if "GEOID1" in data.columns:
            data["centroid1"] = data["GEOID1"].map(centroids_dict)

        if "GEOID2" in data.columns:
            data["centroid2"] = data["GEOID2"].map(centroids_dict)

        # Convert to GeoDataFrame using the first centroid column
        if "centroid1" in data.columns:
            # Remove rows where centroid1 is None
            data = data.dropna(subset=["centroid1"])
            gdf = gpd.GeoDataFrame(data, geometry="centroid1", crs="EPSG:4269")
            return gdf
        else:
            raise ValueError("No valid centroids found for geometry creation.")

    except Exception as e:
        # Let specific geometry errors propagate, but catch other unexpected errors
        if isinstance(e, (RuntimeError, ValueError, NotImplementedError)):
            raise
        else:
            raise RuntimeError(f"Unexpected error adding geometry: {e}") from e
