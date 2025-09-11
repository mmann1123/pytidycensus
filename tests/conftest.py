"""
Pytest configuration and fixtures for pytidycensus tests.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for testing cache functionality."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_census_api_key():
    """Provide a mock Census API key for testing."""
    with patch.dict(os.environ, {'CENSUS_API_KEY': 'test_api_key_123'}):
        yield 'test_api_key_123'


@pytest.fixture
def sample_acs_response():
    """Sample ACS API response for testing."""
    return [
        ["NAME", "B01001_001E", "B01001_001M", "state"],
        ["Alabama", "5024279", "1000", "01"],
        ["Alaska", "733391", "500", "02"],
        ["Arizona", "7151502", "1200", "04"]
    ]


@pytest.fixture
def sample_decennial_response():
    """Sample decennial Census API response for testing."""
    return [
        ["NAME", "P1_001N", "state"],
        ["Alabama", "5024279", "01"],
        ["Alaska", "733391", "02"],
        ["Arizona", "7151502", "04"]
    ]


@pytest.fixture
def sample_variables_response():
    """Sample variables API response for testing."""
    return {
        "variables": {
            "B01001_001E": {
                "label": "Estimate!!Total:",
                "concept": "SEX BY AGE",
                "predicateType": "int",
                "group": "B01001",
                "limit": 0
            },
            "B01001_001M": {
                "label": "Margin of Error!!Total:",
                "concept": "SEX BY AGE", 
                "predicateType": "int",
                "group": "B01001",
                "limit": 0
            },
            "B19013_001E": {
                "label": "Estimate!!Median household income in the past 12 months",
                "concept": "MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS",
                "predicateType": "int",
                "group": "B19013",
                "limit": 0
            }
        }
    }


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean up environment variables and cache after each test."""
    # Store original environment
    original_env = os.environ.copy()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class MockGeometry:
    """Mock geometry object for testing."""
    def __init__(self, geom_type="Polygon"):
        self.geom_type = geom_type
    
    def __str__(self):
        return f"MOCK_{self.geom_type}"


@pytest.fixture
def sample_geodataframe():
    """Sample GeoDataFrame for testing geometry functionality."""
    import pandas as pd
    import geopandas as gpd
    from shapely.geometry import Point
    
    # Create sample data with mock geometry
    data = {
        'GEOID': ['01', '02', '04'],
        'NAME': ['Alabama', 'Alaska', 'Arizona'],
        'geometry': [Point(-86.8, 32.8), Point(-152.0, 64.0), Point(-111.9, 34.0)]
    }
    
    return gpd.GeoDataFrame(data, crs='EPSG:4269')


@pytest.fixture
def mock_tiger_response():
    """Mock TIGER shapefile download response."""
    return b'mock_shapefile_content'