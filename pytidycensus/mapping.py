"""Interactive mapping functions for pytidycensus data.

This module provides functions to create interactive maps from Census data,
particularly for visualizing migration flows with lonboard's BrushingExtension.

See the complete tutorial at:
https://mmann1123.github.io/pytidycensus/examples/09_flow_brushmap_api.html

For the Jupyter notebook example:
https://github.com/mmann1123/pytidycensus/blob/main/examples/09_flow_brushmap_api.ipynb
"""

import warnings
from typing import Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import shapely

# Try to import lonboard components
try:
    from lonboard import Map, ScatterplotLayer
    from lonboard._geoarrow.geopandas_interop import geopandas_to_geoarrow
    from lonboard.experimental import ArcLayer
    from lonboard.layer_extension import BrushingExtension

    LONBOARD_AVAILABLE = True
except ImportError:
    LONBOARD_AVAILABLE = False


def _check_lonboard_available():
    """Check if lonboard is installed and raise helpful error if not."""
    if not LONBOARD_AVAILABLE:
        raise ImportError(
            "lonboard is required for mapping functions. "
            "Install it with: pip install pytidycensus[map]"
        )


def flow_brushmap(
    flows_data: Union[pd.DataFrame, gpd.GeoDataFrame],
    flow_threshold: int = 50,
    brushing_radius: float = 100000,
    source_color: Tuple[int, int, int] = (166, 3, 3),
    target_color: Tuple[int, int, int] = (35, 181, 184),
    arc_opacity: float = 0.4,
    arc_width: float = 1,
    point_radius_scale: float = 3000,
    picking_radius: int = 10,
    return_layers: bool = False,
) -> Union[Map, Tuple[Map, dict]]:
    """Create an interactive brush map from migration flows data.

    This function takes data from `get_flows(geometry=True)` and creates an
    interactive lonboard map with arcs showing migration flows between locations.
    The map uses the BrushingExtension to show only flows near the cursor.

    Parameters
    ----------
    flows_data : pd.DataFrame or gpd.GeoDataFrame
        Flow data from `get_flows()` with `geometry=True`. Must contain columns:
        - GEOID1, GEOID2: origin and destination GEOIDs
        - FULL1_NAME, FULL2_NAME: origin and destination names
        - MOVEDNET: net migration value
        - centroid1, centroid2: Point geometries for origin/destination
    flow_threshold : int, optional
        Minimum absolute flow value to display (default: 50)
    brushing_radius : float, optional
        Radius in meters for brushing effect (default: 100000 = 100km)
    source_color : tuple of int, optional
        RGB color for outward migration (default: red)
    target_color : tuple of int, optional
        RGB color for inward migration (default: blue)
    arc_opacity : float, optional
        Opacity of arc lines, 0-1 (default: 0.4)
    arc_width : float, optional
        Width of arc lines (default: 1)
    point_radius_scale : float, optional
        Scale factor for point radii (default: 3000)
    picking_radius : int, optional
        Picking radius for mouse interactions (default: 10)
    return_layers : bool, optional
        If True, return tuple of (map, layers_dict) (default: False)

    Returns
    -------
    Map or tuple
        lonboard Map object, or tuple of (Map, dict of layers) if return_layers=True

    Examples
    --------
    >>> import pytidycensus as tc
    >>> from pytidycensus.mapping import flow_brushmap
    >>> flows = tc.get_flows(geography="county", state="TX", year=2018, geometry=True)
    >>> map_ = flow_brushmap(flows, flow_threshold=100, brushing_radius=150000)
    >>> map_  # Display in Jupyter

    Notes
    -----
    - Requires lonboard: `pip install pytidycensus[map]`
    - Best used in Jupyter notebooks for interactive visualization
    - Red colors indicate outward migration (people leaving)
    - Blue colors indicate inward migration (people arriving)
    - Hover over the map to see flows near your cursor
    """
    _check_lonboard_available()

    # Validate input data
    required_cols = ["GEOID1", "GEOID2", "FULL1_NAME", "FULL2_NAME", "centroid1", "centroid2"]
    missing_cols = [col for col in required_cols if col not in flows_data.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required columns: {missing_cols}. "
            "Did you call get_flows() with geometry=True?"
        )

    # Filter to valid flows with geometry
    valid_flows = flows_data[
        (flows_data["GEOID2"].notna())
        & (flows_data["centroid1"].notna())
        & (flows_data["centroid2"].notna())
    ].copy()

    print(f"Processing {len(valid_flows)} flow records...")

    # Build county lookup
    county_lookup = _build_county_lookup(valid_flows)

    # Build arcs, sources, and targets
    arcs, sources, targets = _build_flow_geometry(valid_flows, county_lookup, flow_threshold)

    if len(arcs) == 0:
        warnings.warn(f"No arcs found with threshold={flow_threshold}. Try lowering the threshold.")
        return Map([])

    print(f"Created {len(arcs)} arcs, {len(sources)} sources, and {len(targets)} targets")

    # Create color arrays
    colors = np.vstack(
        [np.array(source_color, dtype=np.uint8), np.array(target_color, dtype=np.uint8)]
    )
    source_lookup, target_lookup = 0, 1

    # Create brushing extension
    brushing_ext = BrushingExtension()

    # Create source layer
    source_layer = _create_source_layer(
        sources,
        colors,
        source_lookup,
        target_lookup,
        point_radius_scale,
        brushing_ext,
        brushing_radius,
    )

    # Create target layer
    target_layer = _create_target_layer(
        targets,
        colors,
        source_lookup,
        target_lookup,
        point_radius_scale,
        brushing_ext,
        brushing_radius,
    )

    # Create arc layer
    arc_layer = _create_arc_layer(
        arcs, source_color, target_color, arc_width, arc_opacity, brushing_ext, brushing_radius
    )

    # Combine layers
    layers = [layer for layer in [source_layer, target_layer, arc_layer] if layer is not None]

    if len(layers) == 0:
        warnings.warn("No layers created. Check your data.")
        return Map([])

    # Create map
    map_ = Map(layers, picking_radius=picking_radius)

    if return_layers:
        layers_dict = {"source": source_layer, "target": target_layer, "arc": arc_layer}
        return map_, layers_dict

    return map_


def _build_county_lookup(flows_data: pd.DataFrame) -> dict:
    """Build lookup dictionary for county information by GEOID."""
    county_lookup = {}

    for idx, row in flows_data.iterrows():
        # Add origin
        if row["GEOID1"] not in county_lookup and row["centroid1"] is not None:
            county_lookup[row["GEOID1"]] = {
                "name": row["FULL1_NAME"],
                "centroid": [row["centroid1"].x, row["centroid1"].y, 0],
                "geoid": row["GEOID1"],
            }

        # Add destination
        if row["GEOID2"] not in county_lookup and row["centroid2"] is not None:
            county_lookup[row["GEOID2"]] = {
                "name": row["FULL2_NAME"],
                "centroid": [row["centroid2"].x, row["centroid2"].y, 0],
                "geoid": row["GEOID2"],
            }

    return county_lookup


def _build_flow_geometry(
    flows_data: pd.DataFrame, county_lookup: dict, flow_threshold: int
) -> Tuple[list, list, list]:
    """Build arcs, sources, and targets from flow data."""
    arcs = []
    targets = []
    sources = []
    pairs = {}

    # Group by origin to calculate flows
    for geoid1, group in flows_data.groupby("GEOID1"):
        if geoid1 not in county_lookup:
            continue

        origin_county = county_lookup[geoid1]
        origin_centroid = origin_county["centroid"]

        total_value = {"gain": 0, "loss": 0}

        # Process each destination
        for idx, row in group.iterrows():
            geoid2 = row["GEOID2"]

            if geoid2 not in county_lookup or geoid2 == geoid1:
                continue

            destination_county = county_lookup[geoid2]
            destination_centroid = destination_county["centroid"]

            # Get migration value
            if pd.notna(row.get("MOVEDNET")):
                value = row["MOVEDNET"]
            else:
                movedin = row.get("MOVEDIN", 0) if pd.notna(row.get("MOVEDIN")) else 0
                movedout = row.get("MOVEDOUT", 0) if pd.notna(row.get("MOVEDOUT")) else 0
                value = movedin - movedout

            if value > 0:
                total_value["gain"] += value
            else:
                total_value["loss"] += value

            # Filter small flows
            if abs(value) < flow_threshold:
                continue

            # Create unique pair key
            pair_key = "-".join(sorted([geoid1, geoid2]))
            gain = np.sign(value)

            # Add source point
            sources.append(
                {
                    "position": destination_centroid,
                    "target": origin_centroid,
                    "name": destination_county["name"],
                    "radius": 3,
                    "gain": -gain,
                }
            )

            # Eliminate duplicate arcs
            if pair_key in pairs:
                continue

            pairs[pair_key] = True

            # Add arc based on direction
            if gain > 0:
                arcs.append(
                    {
                        "target": origin_centroid,
                        "source": destination_centroid,
                        "value": value,
                    }
                )
            else:
                arcs.append(
                    {
                        "target": destination_centroid,
                        "source": origin_centroid,
                        "value": value,
                    }
                )

        # Add target point
        targets.append(
            {
                "gain": total_value["gain"],
                "loss": total_value["loss"],
                "position": [origin_centroid[0], origin_centroid[1], 10],
                "net": total_value["gain"] + total_value["loss"],
                "name": origin_county["name"],
            }
        )

    # Sort targets by net migration
    targets = sorted(targets, key=lambda d: abs(d["net"]), reverse=True)

    return arcs, sources, targets


def _create_source_layer(
    sources: list,
    colors: np.ndarray,
    source_lookup: int,
    target_lookup: int,
    radius_scale: float,
    brushing_ext: BrushingExtension,
    brushing_radius: float,
) -> Optional[ScatterplotLayer]:
    """Create ScatterplotLayer for source points."""
    if len(sources) == 0:
        return None

    source_positions_list = [source["position"] for source in sources]
    source_arr = np.array(source_positions_list)
    source_positions = shapely.points(source_arr[:, 0], source_arr[:, 1])

    source_gdf = gpd.GeoDataFrame(
        pd.DataFrame.from_records(sources)[["name", "radius", "gain"]],
        geometry=source_positions,
        crs="EPSG:4326",
    )

    source_colors_lookup = np.where(source_gdf["gain"] > 0, target_lookup, source_lookup)
    source_fill_colors = colors[source_colors_lookup]

    return ScatterplotLayer.from_geopandas(
        source_gdf,
        get_fill_color=source_fill_colors,
        radius_scale=radius_scale,
        pickable=False,
        extensions=[brushing_ext],
        brushing_radius=brushing_radius,
    )


def _create_target_layer(
    targets: list,
    colors: np.ndarray,
    source_lookup: int,
    target_lookup: int,
    radius_scale: float,
    brushing_ext: BrushingExtension,
    brushing_radius: float,
) -> Optional[ScatterplotLayer]:
    """Create ScatterplotLayer for target points (rings)."""
    if len(targets) == 0:
        return None

    targets_positions_list = [target["position"] for target in targets]
    targets_arr = np.array(targets_positions_list)
    target_positions = shapely.points(targets_arr[:, 0], targets_arr[:, 1])

    target_gdf = gpd.GeoDataFrame(
        pd.DataFrame.from_records(targets)[["name", "gain", "loss", "net"]],
        geometry=target_positions,
        crs="EPSG:4326",
    )

    target_line_colors_lookup = np.where(target_gdf["net"] > 0, target_lookup, source_lookup)
    target_line_colors = colors[target_line_colors_lookup]

    return ScatterplotLayer.from_geopandas(
        target_gdf,
        get_line_color=target_line_colors,
        radius_scale=radius_scale * 1.33,  # Slightly larger than source
        pickable=True,
        stroked=True,
        filled=False,
        line_width_min_pixels=2,
        extensions=[brushing_ext],
        brushing_radius=brushing_radius,
    )


def _create_arc_layer(
    arcs: list,
    source_color: Tuple[int, int, int],
    target_color: Tuple[int, int, int],
    width: float,
    opacity: float,
    brushing_ext: BrushingExtension,
    brushing_radius: float,
) -> Optional[ArcLayer]:
    """Create ArcLayer with BrushingExtension using GeoArrow format."""
    if len(arcs) == 0:
        return None

    # Create GeoDataFrames for source and target positions
    arc_source_points = [shapely.Point(arc["source"][:2]) for arc in arcs]
    arc_target_points = [shapely.Point(arc["target"][:2]) for arc in arcs]

    arc_source_gdf = gpd.GeoDataFrame(
        {"value": [arc["value"] for arc in arcs]},
        geometry=arc_source_points,
        crs="EPSG:4326",
    )

    arc_target_gdf = gpd.GeoDataFrame(
        {"value": [arc["value"] for arc in arcs]},
        geometry=arc_target_points,
        crs="EPSG:4326",
    )

    # Convert to GeoArrow format (required for BrushingExtension)
    arc_source_table = geopandas_to_geoarrow(arc_source_gdf)
    arc_target_table = geopandas_to_geoarrow(arc_target_gdf)

    # Create PyArrow table for attributes
    value_array = np.array([arc["value"] for arc in arcs])
    attr_table = pa.table({"value": value_array})

    # Create ArcLayer with BrushingExtension
    return ArcLayer(
        table=attr_table,
        get_source_position=arc_source_table["geometry"],
        get_target_position=arc_target_table["geometry"],
        get_source_color=list(source_color),
        get_target_color=list(target_color),
        get_width=width,
        opacity=opacity,
        pickable=False,
        extensions=[brushing_ext],
        brushing_radius=brushing_radius,
    )


# Convenience function for quick visualization
def quick_flow_map(
    geography: str = "county",
    state: Optional[str] = None,
    year: int = 2018,
    **kwargs,
) -> Map:
    """Quick wrapper to fetch flows and create brush map in one call.

    Parameters
    ----------
    geography : str, optional
        Geographic level (default: "county")
    state : str, optional
        State abbreviation (e.g., "TX", "CA")
    year : int, optional
        Year for flow data (default: 2018)
    **kwargs
        Additional arguments passed to flow_brushmap()

    Returns
    -------
    Map
        lonboard Map object

    Examples
    --------
    >>> from pytidycensus.mapping import quick_flow_map
    >>> map_ = quick_flow_map(state="TX", year=2018, flow_threshold=100)
    >>> map_
    """
    from .flows import get_flows

    print(f"Fetching {year} {geography}-level migration flows for {state}...")
    flows = get_flows(geography=geography, state=state, year=year, geometry=True, output="wide")

    return flow_brushmap(flows, **kwargs)
