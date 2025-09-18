"""
pytidycensus: Python interface to US Census Bureau APIs

A Python library that provides an integrated interface to several United States
Census Bureau APIs and geographic boundary files. Allows users to return Census
and ACS data as pandas DataFrames, and optionally returns GeoPandas GeoDataFrames
with feature geometry for mapping and spatial analysis.
"""

__version__ = "0.1.0"
__author__ = "pytidycensus contributors"

from .acs import get_acs
from .api import CensusAPI, set_census_api_key
from .decennial import get_decennial
from .estimates import get_estimates
from .geography import get_geography
from .utils import get_credentials
from .variables import get_table_variables, load_variables, search_variables

__all__ = [
    "CensusAPI",
    "set_census_api_key",
    "get_acs",
    "get_decennial",
    "get_estimates",
    "get_geography",
    "load_variables",
    "search_variables",
    "get_table_variables",
    "get_credentials",
]
