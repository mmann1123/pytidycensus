"""Time series analysis functions for Census data.

This module provides functions for collecting and analyzing time series
data from the US Census Bureau, with support for handling changing
geographic boundaries through area interpolation.
"""

import warnings
from typing import Dict, List, Optional, Union

import pandas as pd

from .acs import get_acs
from .decennial import get_decennial
from .utils import check_overlapping_acs_periods

# Optional dependency for area interpolation
try:
    import geopandas as gpd
    from tobler.area_weighted import area_interpolate

    TOBLER_AVAILABLE = True
except ImportError:
    TOBLER_AVAILABLE = False
    gpd = None
    area_interpolate = None


def get_time_series(
    geography: str,
    variables: Union[str, List[str], Dict[str, str]],
    years: List[int],
    dataset: str = "acs5",
    base_year: Optional[int] = None,
    extensive_variables: Optional[List[str]] = None,
    intensive_variables: Optional[List[str]] = None,
    geometry: bool = True,
    output: str = "wide",
    crs="EPSG:3857",
    **kwargs,
) -> pd.DataFrame:
    """Collect time series data from Census APIs with area interpolation support.

    This function automatically handles boundary changes by interpolating data
    to a consistent set of geographic boundaries (base year). It supports both
    ACS and Decennial Census data.

    Parameters
    ----------
    geography : str
        Geographic level (e.g., 'tract', 'county', 'state').
    variables : str, list, or dict
        Variable codes to retrieve. Can be:
        - Single variable code as string
        - List of variable codes
        - Dictionary mapping custom names to variable codes
    years : list of int
        Years to retrieve data for.
    dataset : str, default "acs5"
        Dataset type. Options:
        - "acs5": ACS 5-year estimates
        - "acs1": ACS 1-year estimates
        - "decennial": Decennial Census
    base_year : int, optional
        Year to use for base geography boundaries. If None, uses the most recent year.
        All other years will be interpolated to these boundaries.
    extensive_variables : list of str, optional
        Variables representing counts/totals that should be redistributed proportionally
        by area during interpolation (e.g., population, housing units).
        REQUIRED when area interpolation is needed (changing tract/block group boundaries).
    intensive_variables : list of str, optional
        Variables representing rates/densities that should be area-weighted during
        interpolation (e.g., median income, poverty rate, percentages).
        REQUIRED when area interpolation is needed (changing tract/block group boundaries).
    geometry : bool, default True
        Whether to include geographic boundaries. Required for area interpolation.
    output : str, default "wide"
        Output format:
        - "wide": Variables as columns, years as separate DataFrames or multi-index
        - "tidy": Long format with separate rows for each variable-year combination
    crs : str or dict, default "EPSG:3857"
        Coordinate reference system to use for area calculations during interpolation.
    **kwargs
        Additional arguments passed to get_acs() or get_decennial().

    Returns
    -------
    pd.DataFrame
        Time series data with consistent geographic boundaries.
        - If output="wide": Multi-index DataFrame with years and variables as columns
        - If output="tidy": Long format with 'year', 'variable', 'estimate' columns

    Examples
    --------
    >>> # ACS 5-year time series with area interpolation
    >>> data = get_time_series(
    ...     geography="tract",
    ...     variables={"total_pop": "B01003_001E", "median_income": "B19013_001E"},
    ...     years=[2015, 2020],
    ...     dataset="acs5",
    ...     state="CA",
    ...     county="037",
    ...     base_year=2020,
    ...     extensive_variables=["total_pop"],
    ...     intensive_variables=["median_income"]
    ... )

    >>> # Decennial census time series
    >>> data = get_time_series(
    ...     geography="tract",
    ...     variables={"total_pop": {"2010": "P001001", "2020": "P1_001N"}},
    ...     years=[2010, 2020],
    ...     dataset="decennial",
    ...     state="DC",
    ...     base_year=2020
    ... )

    Notes
    -----
    - Area interpolation requires the `tobler` package: `pip install tobler`
    - For geographies that don't change (state, county), interpolation is skipped
    - Decennial census variables may differ between years - use a dict to specify
    - When base_year is None, the most recent year is used as the base
    - **IMPORTANT**: When area interpolation is needed, ALL variables must be classified
      as either extensive or intensive. This ensures proper redistribution of values
      across changing boundaries.
        - Extensive: counts/totals (population, housing units) - redistributed by area
        - Intensive: rates/medians/percentages (median income, poverty rate) - area-weighted
    """
    if not years:
        raise ValueError("At least one year must be specified")

    if len(years) == 1 and base_year is None:
        # No interpolation needed for single year
        return _get_single_year_data(
            geography, variables, years[0], dataset, geometry, output, **kwargs
        )

    # Set default base year to most recent
    if base_year is None:
        base_year = max(years)

    if base_year not in years:
        raise ValueError(f"Base year {base_year} must be included in years list")

    # Check for overlapping ACS periods
    if dataset in ["acs1", "acs3", "acs5"]:
        check_overlapping_acs_periods(years, dataset)

    # Check if area interpolation is available and needed
    needs_interpolation = _needs_area_interpolation(geography, years)
    if needs_interpolation and not TOBLER_AVAILABLE:
        raise ImportError(
            "Area interpolation requires the 'tobler' package, which is not installed. "
            "Install it with: pip install tobler\n\n"
            f"Time series analysis for '{geography}' geography across years {years} "
            "requires area interpolation to handle boundary changes. "
            "The tobler package provides the necessary spatial interpolation functionality."
        )

    # When interpolation is needed, require explicit variable classification
    if needs_interpolation and geometry:
        # Get variable names to check
        if isinstance(variables, dict):
            # Handle year-specific variables or named variables
            if all(isinstance(k, int) for k in variables.keys()):
                # Year-specific: {2010: {...}, 2020: {...}}
                all_var_names = set()
                for year_vars in variables.values():
                    if isinstance(year_vars, dict):
                        all_var_names.update(year_vars.keys())
                    elif isinstance(year_vars, list):
                        all_var_names.update(year_vars)
                    elif isinstance(year_vars, str):
                        all_var_names.add(year_vars)
            else:
                # Named variables: {"total_pop": "B01003_001E", ...}
                all_var_names = set(variables.keys())
        elif isinstance(variables, list):
            all_var_names = set(variables)
        else:
            all_var_names = {variables}

        # Check if all variables are classified
        ext_set = set(extensive_variables) if extensive_variables else set()
        int_set = set(intensive_variables) if intensive_variables else set()
        classified = ext_set | int_set
        unclassified = all_var_names - classified

        if unclassified:
            raise ValueError(
                f"When using area interpolation, all variables must be explicitly classified "
                f"as either 'extensive' or 'intensive'.\n\n"
                f"Unclassified variables: {sorted(unclassified)}\n\n"
                f"Use extensive_variables=[...] for counts/totals (e.g., population, housing units)\n"
                f"Use intensive_variables=[...] for rates/ratios/medians (e.g., median income, density)\n\n"
                f"Example:\n"
                f"  get_time_series(\n"
                f"      ...,\n"
                f"      extensive_variables=['total_pop'],\n"
                f"      intensive_variables=['median_income']\n"
                f"  )"
            )

    # Collect data for all years
    yearly_data = {}
    for year in years:
        print(f"Collecting data for {year}...")
        data = _get_single_year_data(
            geography, variables, year, dataset, geometry, output="wide", **kwargs
        )
        yearly_data[year] = data
        # DEBUG: Log data type
        import geopandas as gpd

        print(
            f"DEBUG: Year {year} data type: {type(data).__name__}, "
            f"is GeoDataFrame: {isinstance(data, gpd.GeoDataFrame)}, shape: {data.shape}"
        )

    # Get base year data for reference
    base_data = yearly_data[base_year]

    # If no interpolation needed or available, just concatenate
    if not needs_interpolation or not TOBLER_AVAILABLE or not geometry:
        print(
            f"DEBUG: Skipping interpolation - needs_interpolation: {needs_interpolation}, "
            f"TOBLER_AVAILABLE: {TOBLER_AVAILABLE}, geometry: {geometry}"
        )
        return _concatenate_yearly_data(yearly_data, output)

    # Verify all data are GeoDataFrames before attempting area interpolation
    import geopandas as gpd

    print(f"DEBUG: Checking if data are GeoDataFrames before interpolation...")
    for year, data in yearly_data.items():
        if not isinstance(data, gpd.GeoDataFrame):
            warnings.warn(
                f"Cannot perform area interpolation - data for year {year} "
                f"is a {type(data).__name__}, not a GeoDataFrame. "
                f"This usually means geometry=False or the geometry merge failed. "
                f"For changing boundaries like tracts, interpolation is required to avoid NaN values. "
                f"Check that geometry=True and that the geography data is available for your area. "
                f"Returning data without interpolation.",
                UserWarning,
            )
            return _concatenate_yearly_data(yearly_data, output)

    print(f"DEBUG: All data are GeoDataFrames. Proceeding with interpolation.")

    # Perform area interpolation
    interpolated_data = {}
    interpolated_data[base_year] = base_data  # Base year doesn't need interpolation

    # Project to consistent CRS for area calculations
    print(f"DEBUG: Projecting base year ({base_year}) data to CRS: {crs}")
    base_data_proj = base_data.to_crs(crs)

    for year in years:
        if year == base_year:
            continue

        print(f"Performing area interpolation for {year} to {base_year} boundaries...")

        source_data = yearly_data[year].to_crs(crs)

        # Determine variable classification
        data_columns = _get_data_columns(source_data)
        dropped_vars = set(source_data.columns) - set(data_columns)

        ext_vars, int_vars = _classify_variables(
            data_columns, extensive_variables, intensive_variables
        )

        # Convert data columns to numeric before interpolation
        # Census API returns strings, but tobler needs numeric types
        print(f"DEBUG: Converting data columns to numeric types...")
        all_data_vars = ext_vars + int_vars
        for col in all_data_vars:
            if col in source_data.columns:
                source_data[col] = pd.to_numeric(source_data[col], errors="coerce")
            if col in base_data_proj.columns:
                base_data_proj[col] = pd.to_numeric(base_data_proj[col], errors="coerce")

        try:
            interpolated = area_interpolate(
                source_df=source_data,
                target_df=base_data_proj,
                extensive_variables=ext_vars,
                intensive_variables=int_vars,
            )

            # Convert back to geographic CRS
            interpolated = interpolated.to_crs(crs)

            # Ensure GEOID and geometry come from target (base year), not source
            # area_interpolate returns data with target's geometry but may not have GEOID
            if "GEOID" in base_data_proj.columns:
                interpolated["GEOID"] = base_data_proj["GEOID"].values

            interpolated_data[year] = interpolated

            # Validate interpolation
            _validate_interpolation(source_data, interpolated, ext_vars)

            # add back any dropped non-data columns from base_data (not source_data)
            # These should come from the target year boundaries, not the source
            for col in dropped_vars:
                if col in base_data_proj.columns and col not in interpolated.columns:
                    interpolated_data[year][col] = base_data_proj[col].values

        except Exception as e:
            warnings.warn(
                f"Area interpolation failed for {year}: {e}. " f"Using original boundaries.",
                UserWarning,
            )
            interpolated_data[year] = yearly_data[year]

    return _concatenate_yearly_data(interpolated_data, output)


def _get_single_year_data(
    geography: str,
    variables: Union[str, List[str], Dict[str, str]],
    year: int,
    dataset: str,
    geometry: bool,
    output: str,
    **kwargs,
) -> pd.DataFrame:
    """Get data for a single year."""
    # Handle variable specification for different years
    if isinstance(variables, dict) and all(isinstance(k, int) for k in variables.keys()):
        # Year-specific variable mapping
        if year not in variables:
            raise ValueError(f"No variables specified for year {year}")
        year_variables = variables[year]
    else:
        year_variables = variables

    # Get data using appropriate function
    if dataset == "decennial":
        # Determine appropriate survey for decennial
        survey = "pl" if year >= 2020 else "sf1"
        return get_decennial(
            geography=geography,
            variables=year_variables,
            year=year,
            sumfile=survey,
            geometry=geometry,
            output=output,
            **kwargs,
        )
    else:
        return get_acs(
            geography=geography,
            variables=year_variables,
            year=year,
            survey=dataset,
            geometry=geometry,
            output=output,
            **kwargs,
        )


def _needs_area_interpolation(geography: str, years: List[int]) -> bool:
    """Check if area interpolation is needed for the given geography and years."""
    # Stable geographies that don't change boundaries
    stable_geographies = {"state", "region", "division"}

    if geography.lower() in stable_geographies:
        return False

    # County boundaries rarely change, but can
    if geography.lower() == "county" and max(years) - min(years) < 20:
        return False

    # Tract, block group, and block boundaries frequently change
    return True


def _get_data_columns(df: pd.DataFrame) -> List[str]:
    """Get columns that contain actual data (not geographic identifiers)."""
    # Exclude standard geographic and metadata columns
    exclude_cols = {
        "GEOID",
        "NAME",
        "geometry",
        "state",
        "county",
        "tract",
        "block group",
        "variable",
        "estimate",
        "moe",
        "summary_var",
        "summary_est",
        "summary_moe",
    }

    # Also exclude MOE columns (ending with _moe or _m)
    return [
        col
        for col in df.columns
        if col not in exclude_cols and not str(col).endswith("_moe") and not str(col).endswith("_m")
    ]


def _classify_variables(
    data_columns: List[str],
    extensive_variables: Optional[List[str]] = None,
    intensive_variables: Optional[List[str]] = None,
) -> tuple:
    """Classify variables as extensive or intensive for interpolation."""
    if extensive_variables is None and intensive_variables is None:
        # Default: assume all variables are extensive (counts/totals)
        return data_columns, []

    if extensive_variables is None:
        extensive_variables = []
    if intensive_variables is None:
        intensive_variables = []

    # Validate that all specified variables exist
    all_specified = set(extensive_variables + intensive_variables)
    available = set(data_columns)
    missing = all_specified - available
    if missing:
        warnings.warn(
            f"Some specified variables not found in data: {missing}. " f"Available: {available}",
            UserWarning,
        )

    # Filter to only include available variables
    ext_vars = [v for v in extensive_variables if v in available]
    int_vars = [v for v in intensive_variables if v in available]

    # Add unspecified variables to extensive by default
    unspecified = available - set(ext_vars + int_vars)
    ext_vars.extend(list(unspecified))

    return ext_vars, int_vars


def _validate_interpolation(
    source_df: pd.DataFrame, interpolated_df: pd.DataFrame, extensive_variables: List[str]
) -> None:
    """Validate that interpolation preserved data totals for extensive variables."""
    for var in extensive_variables:
        if var in source_df.columns and var in interpolated_df.columns:
            source_total = source_df[var].sum()
            interpolated_total = interpolated_df[var].sum()

            if source_total > 0:  # Avoid division by zero
                pct_diff = abs(interpolated_total - source_total) / source_total * 100
                if pct_diff > 5:  # More than 5% difference
                    warnings.warn(
                        f"Large difference in total for {var}: "
                        f"{source_total:.0f} → {interpolated_total:.0f} "
                        f"({pct_diff:.1f}% change)",
                        UserWarning,
                    )


def _concatenate_yearly_data(yearly_data: Dict[int, pd.DataFrame], output: str) -> pd.DataFrame:
    """Concatenate data from multiple years into desired output format."""
    # Debug: Print information about the input data
    print(f"DEBUG: Processing {len(yearly_data)} years of data")
    for year, df in yearly_data.items():
        print(f"  Year {year}: shape={df.shape}, columns={list(df.columns)}")
    if output == "tidy":
        # Long format with year column
        tidy_dfs = []
        for year, df in yearly_data.items():
            if "geometry" in df.columns:
                # Handle geometry separately for tidy format
                geom_df = df[["GEOID", "geometry"]].copy()
                df_no_geom = df.drop("geometry", axis=1)
            else:
                df_no_geom = df
                geom_df = None

            # Build id_vars list based on what's actually available
            id_vars = []

            # Check for primary ID column
            if "GEOID" in df_no_geom.columns:
                id_vars.append("GEOID")
                primary_id = "GEOID"
            else:
                # Look for other ID columns
                id_candidates = [col for col in df_no_geom.columns if col.upper().endswith("ID")]
                if id_candidates:
                    id_vars.append(id_candidates[0])
                    primary_id = id_candidates[0]
                else:
                    raise ValueError(
                        f"No suitable ID column found in data. Available columns: {list(df_no_geom.columns)}"
                    )

            # Add other identifier columns if present
            for col in ["NAME", "state", "county"]:
                if col in df_no_geom.columns:
                    id_vars.append(col)

            melted = pd.melt(
                df_no_geom, id_vars=id_vars, var_name="variable", value_name="estimate"
            )
            melted["year"] = year

            # Add geometry back if available
            if geom_df is not None:
                if primary_id in geom_df.columns:
                    melted = melted.merge(geom_df, on=primary_id, how="left")
                else:
                    print(
                        f"Warning: Cannot merge geometry - {primary_id} not found in geometry DataFrame"
                    )

            tidy_dfs.append(melted)

        result = pd.concat(tidy_dfs, ignore_index=True)

        # Convert to GeoDataFrame if geometry present
        if "geometry" in result.columns:
            result = gpd.GeoDataFrame(result)

        return result

    else:
        # Wide format with multi-index columns (year, variable)
        wide_dfs = []
        base_geo_cols = None
        geometry_col = None

        for year, df in yearly_data.items():
            # Identify geographic/metadata columns to preserve
            geo_metadata_cols = [
                "GEOID",
                "NAME",
                "state",
                "county",
                "tract",
                "block group",
                "geometry",
            ]

            # Keep track of base geography columns from first year
            if base_geo_cols is None:
                base_geo_cols = [col for col in geo_metadata_cols if col in df.columns]
                if "geometry" in df.columns:
                    geometry_col = df["geometry"].copy()

            # Get data columns (exclude geographic/metadata columns)
            data_cols = _get_data_columns(df)

            # Create renamed dataframe with only data columns + GEOID for merging
            rename_dict = {col: (year, col) for col in data_cols}

            # Start with GEOID for merging
            if "GEOID" in df.columns:
                df_renamed = df[["GEOID"]].copy()
            else:
                # Fallback to other ID columns
                id_candidates = [col for col in df.columns if col.upper().endswith("ID")]
                if id_candidates:
                    df_renamed = df[[id_candidates[0]]].copy()
                else:
                    raise ValueError("No suitable ID column found for merging")

            # Add renamed data columns
            for old_col, new_col in rename_dict.items():
                df_renamed[new_col] = df[old_col]

            wide_dfs.append(df_renamed)

        # Merge all years on GEOID (or other ID column)
        result = wide_dfs[0]
        merge_key = "GEOID" if "GEOID" in result.columns else result.columns[0]

        for df in wide_dfs[1:]:
            result = result.merge(df, on=merge_key, how="outer", suffixes=("", "_dup"))

            # Remove any duplicate columns that were created
            dup_cols = [col for col in result.columns if str(col).endswith("_dup")]
            if dup_cols:
                result = result.drop(columns=dup_cols)

        # Add back the base geographic/metadata columns from first year
        # Keep geometry as a regular column (not part of MultiIndex)
        if base_geo_cols:
            first_year_data = yearly_data[min(yearly_data.keys())]

            # Separate geometry from other metadata columns
            geometry_cols = [
                col
                for col in ["geometry"]
                if col in base_geo_cols and col in first_year_data.columns
            ]
            other_geo_cols = [
                col
                for col in base_geo_cols
                if col not in result.columns
                and col in first_year_data.columns
                and col != merge_key
                and col not in geometry_cols
            ]

            if other_geo_cols:
                # Create a temporary dataframe with just the merge key and columns to add
                temp_df = first_year_data[[merge_key] + other_geo_cols].copy()

                # Only merge if we have valid merge keys in both dataframes
                if merge_key in result.columns and merge_key in temp_df.columns:
                    # Verify merge key is not duplicated
                    if (
                        not result[merge_key].duplicated().any()
                        and not temp_df[merge_key].duplicated().any()
                    ):
                        result = result.merge(temp_df, on=merge_key, how="left")
                    else:
                        warnings.warn(
                            f"Skipping merge to add geographic columns due to duplicate {merge_key} values",
                            UserWarning,
                        )

        # Create proper multi-index for data columns
        # Note: geometry will be part of MultiIndex as ('geometry', '') but GeoDataFrame
        # will still work correctly with it
        data_columns = [col for col in result.columns if isinstance(col, tuple)]
        if data_columns:
            # Set up multi-index
            result.columns = pd.MultiIndex.from_tuples(
                [col if isinstance(col, tuple) else ("", col) for col in result.columns],
                names=["year", "variable"],
            )

        # Convert to GeoDataFrame if geometry is available
        # Note: GeoDataFrame handles geometry columns with tuple names correctly
        if geometry_col is not None and gpd is not None:
            # Make sure geometry aligns with result
            if data_columns:
                # With MultiIndex, geometry will be ('', 'geometry')
                result[("", "geometry")] = geometry_col
                result = gpd.GeoDataFrame(result, geometry=("", "geometry"))
            else:
                # Without MultiIndex, geometry is just 'geometry'
                result["geometry"] = geometry_col
                result = gpd.GeoDataFrame(result, geometry="geometry")

        return result


def compare_time_periods(
    data: pd.DataFrame,
    base_period: Union[int, str],
    comparison_period: Union[int, str],
    variables: Optional[List[str]] = None,
    calculate_change: bool = True,
    calculate_percent_change: bool = True,
) -> pd.DataFrame:
    """Compare data between two time periods.

    Parameters
    ----------
    data : pd.DataFrame
        Time series data from get_time_series() with wide format.
    base_period : int or str
        Base time period for comparison.
    comparison_period : int or str
        Comparison time period.
    variables : list of str, optional
        Variables to compare. If None, uses all available variables.
    calculate_change : bool, default True
        Whether to calculate absolute change.
    calculate_percent_change : bool, default True
        Whether to calculate percent change.

    Returns
    -------
    pd.DataFrame
        DataFrame with comparison results.
    """
    if not isinstance(data.columns, pd.MultiIndex):
        raise ValueError("Data must have multi-index columns from get_time_series()")

    # Get available years and variables
    years = data.columns.get_level_values("year").unique()
    if base_period not in years:
        raise ValueError(f"Base period {base_period} not found in data")
    if comparison_period not in years:
        raise ValueError(f"Comparison period {comparison_period} not found in data")

    if variables is None:
        variables = data.columns.get_level_values("variable").unique().tolist()

    # Create comparison DataFrame
    geo_cols = [col for col in data.columns if not isinstance(col[0], (int, str)) or col[0] == ""]
    result = data[geo_cols].copy()

    for var in variables:
        if (base_period, var) in data.columns and (comparison_period, var) in data.columns:
            base_values = data[(base_period, var)]
            comparison_values = data[(comparison_period, var)]

            # Add base and comparison values
            result[f"{var}_{base_period}"] = base_values
            result[f"{var}_{comparison_period}"] = comparison_values

            if calculate_change:
                result[f"{var}_change"] = comparison_values - base_values

            if calculate_percent_change:
                pct_change = (comparison_values - base_values) / base_values * 100
                result[f"{var}_pct_change"] = pct_change.replace(
                    [float("inf"), float("-inf")], None
                )

    return result
