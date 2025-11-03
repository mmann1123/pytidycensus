"""
pytidycensus: Python interface to US Census Bureau APIs

A Python library that provides an integrated interface to several United States
Census Bureau APIs and geographic boundary files. Allows users to return Census
and ACS data as pandas DataFrames, and optionally returns GeoPandas GeoDataFrames
with feature geometry for mapping and spatial analysis.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("pytidycensus")
except importlib.metadata.PackageNotFoundError:
    # Package is not installed, fallback to a default version
    __version__ = "0.0.0.dev"

__author__ = "Michael Mann"

from .acs import get_acs
from .api import CensusAPI, set_census_api_key
from .decennial import get_decennial
from .estimates import get_estimates
from .flows import get_flows, identify_geoid_type
from .geography import get_geography
from .time_series import compare_time_periods, get_time_series
from .utils import get_credentials
from .variables import get_table_variables, load_variables, search_variables

# Import mapping module (optional dependency)
try:
    from .mapping import flow_brushmap, quick_flow_map

    _MAPPING_AVAILABLE = True
except Exception as e:
    # Catch all exceptions (ImportError, CRSError, etc.) to prevent
    # optional mapping dependencies from breaking the entire package
    import warnings

    _MAPPING_AVAILABLE = False
    flow_brushmap = None
    quick_flow_map = None
    warnings.warn(
        f"Mapping functions unavailable due to import error: {type(e).__name__}. "
        f"To use mapping features, ensure all dependencies are properly installed: "
        f"pip install pytidycensus[map]",
        stacklevel=2,
    )

__all__ = [
    "CensusAPI",
    "set_census_api_key",
    "get_acs",
    "get_decennial",
    "get_estimates",
    "get_flows",
    "identify_geoid_type",
    "get_geography",
    "get_time_series",
    "compare_time_periods",
    "load_variables",
    "search_variables",
    "get_table_variables",
    "get_credentials",
    "flow_brushmap",
    "quick_flow_map",
]
