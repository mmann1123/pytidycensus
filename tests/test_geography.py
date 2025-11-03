"""Tests for geography module functionality."""

from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from pytidycensus.geography import (
    get_block_group_boundaries,
    get_county_boundaries,
    get_geography,
    get_state_boundaries,
    get_tract_boundaries,
)


@pytest.fixture
def mock_geodataframe():
    """Mock GeoDataFrame with typical TIGER columns."""
    return gpd.GeoDataFrame(
        {
            "STATEFP": ["48", "48", "06"],
            "COUNTYFP": ["201", "113", "037"],
            "TRACTCE": ["001000", "001001", "001002"],
            "BLKGRPCE": ["1", "2", "1"],
            "GEOID": ["48201001000", "48113001001", "06037001002"],
            "NAME": ["Census Tract 10", "Census Tract 10.01", "Census Tract 10.02"],
            "NAMELSAD": ["Census Tract 10", "Census Tract 10.01", "Census Tract 10.02"],
            "STUSPS": ["TX", "TX", "CA"],
            "geometry": [
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
                Polygon([(2, 0), (3, 0), (3, 1), (2, 1)]),
            ],
        }
    )


class TestGetGeography:
    """Test cases for get_geography function using pygris."""

    @patch("pytidycensus.geography.pygris.counties")
    def test_get_geography_county_basic(self, mock_counties, mock_geodataframe):
        """Test basic county geography retrieval."""
        mock_counties.return_value = mock_geodataframe.copy()

        result = get_geography("county", year=2022)

        assert isinstance(result, gpd.GeoDataFrame)
        mock_counties.assert_called_once_with(state=None, cb=True, year=2022)

    @patch("pytidycensus.geography.pygris.states")
    @patch("pytidycensus.geography.validate_state")
    def test_get_geography_state_with_filter(self, mock_validate_state, mock_states):
        """Test state geography with filtering."""
        mock_validate_state.return_value = ["48"]

        test_gdf = gpd.GeoDataFrame(
            {
                "STATEFP": ["48", "06"],
                "NAME": ["Texas", "California"],
                "STUSPS": ["TX", "CA"],
                "geometry": [Point(0, 0), Point(1, 1)],
            }
        )
        mock_states.return_value = test_gdf

        result = get_geography("state", year=2022, state="TX")

        # Should filter to only Texas
        assert len(result) == 1
        assert result.iloc[0]["STATEFP"] == "48"

    @patch("pytidycensus.geography.pygris.counties")
    @patch("pytidycensus.geography.validate_state")
    def test_get_geography_county_single_state(
        self, mock_validate_state, mock_counties, mock_geodataframe
    ):
        """Test county geography with single state filter."""
        mock_validate_state.return_value = ["48"]
        mock_counties.return_value = mock_geodataframe.copy()

        result = get_geography("county", year=2022, state="TX")

        # pygris should be called with state filter
        mock_counties.assert_called_once_with(state="48", cb=True, year=2022)

    @patch("pytidycensus.geography.pygris.tracts")
    @patch("pytidycensus.geography.validate_state")
    def test_get_geography_tract_requires_state(self, mock_validate_state, mock_tracts):
        """Test that tract geography requires state."""
        with pytest.raises(ValueError, match="State must be specified"):
            get_geography("tract", year=2022)

    @patch("pytidycensus.geography.pygris.tracts")
    @patch("pytidycensus.geography.validate_state")
    def test_get_geography_tract_with_state(
        self, mock_validate_state, mock_tracts, mock_geodataframe
    ):
        """Test tract geography with state."""
        mock_validate_state.return_value = ["48"]
        mock_tracts.return_value = mock_geodataframe.copy()

        result = get_geography("tract", state="TX", year=2022)

        mock_tracts.assert_called_once_with(state="48", county=None, cb=True, year=2022)
        assert isinstance(result, gpd.GeoDataFrame)

    @patch("pytidycensus.geography.pygris.tracts")
    @patch("pytidycensus.geography.validate_state")
    @patch("pytidycensus.geography.validate_county")
    def test_get_geography_tract_with_county(
        self, mock_validate_county, mock_validate_state, mock_tracts, mock_geodataframe
    ):
        """Test tract geography with county filter."""
        mock_validate_state.return_value = ["48"]
        mock_validate_county.return_value = ["201"]
        mock_tracts.return_value = mock_geodataframe.copy()

        result = get_geography("tract", state="TX", county="201", year=2022)

        mock_tracts.assert_called_once_with(state="48", county="201", cb=True, year=2022)

    @patch("pytidycensus.geography.pygris.block_groups")
    @patch("pytidycensus.geography.validate_state")
    def test_get_geography_block_group_requires_state(self, mock_validate_state, mock_block_groups):
        """Test that block group geography requires state."""
        with pytest.raises(ValueError, match="State must be specified"):
            get_geography("block group", year=2022)

    @patch("pytidycensus.geography.pygris.block_groups")
    @patch("pytidycensus.geography.validate_state")
    def test_get_geography_block_group_with_state(
        self, mock_validate_state, mock_block_groups, mock_geodataframe
    ):
        """Test block group geography with state."""
        mock_validate_state.return_value = ["48"]
        mock_block_groups.return_value = mock_geodataframe.copy()

        result = get_geography("block group", state="TX", year=2022)

        mock_block_groups.assert_called_once_with(state="48", county=None, cb=True, year=2022)
        assert isinstance(result, gpd.GeoDataFrame)

    @patch("pytidycensus.geography.pygris.zctas")
    def test_get_geography_zcta(self, mock_zctas):
        """Test ZCTA geography."""
        test_gdf = gpd.GeoDataFrame(
            {
                "ZCTA5CE20": ["75001", "75002"],
                "NAME": ["ZCTA5 75001", "ZCTA5 75002"],
                "geometry": [Point(0, 0), Point(1, 1)],
            }
        )
        mock_zctas.return_value = test_gdf

        result = get_geography("zcta", year=2022)

        mock_zctas.assert_called_once_with(cb=True, year=2022)
        assert "GEOID" in result.columns
        assert result["GEOID"].tolist() == ["75001", "75002"]

    @patch("pytidycensus.geography.pygris.places")
    @patch("pytidycensus.geography.validate_state")
    def test_get_geography_place_requires_state(self, mock_validate_state, mock_places):
        """Test that place geography requires state."""
        with pytest.raises(ValueError, match="State must be specified"):
            get_geography("place", year=2022)

    @patch("pytidycensus.geography.pygris.places")
    @patch("pytidycensus.geography.validate_state")
    def test_get_geography_place_with_state(self, mock_validate_state, mock_places):
        """Test place geography with state."""
        mock_validate_state.return_value = ["48"]
        test_gdf = gpd.GeoDataFrame(
            {"NAME": ["Houston", "Dallas"], "geometry": [Point(0, 0), Point(1, 1)]}
        )
        mock_places.return_value = test_gdf

        result = get_geography("place", state="TX", year=2022)

        mock_places.assert_called_once_with(state="48", cb=True, year=2022)

    @patch("pytidycensus.geography.pygris.core_based_statistical_areas")
    def test_get_geography_cbsa(self, mock_cbsas):
        """Test CBSA geography."""
        test_gdf = gpd.GeoDataFrame(
            {
                "CBSAFP": ["12345", "67890"],
                "NAME": ["Houston-The Woodlands-Sugar Land", "Dallas-Fort Worth-Arlington"],
                "geometry": [Point(0, 0), Point(1, 1)],
            }
        )
        mock_cbsas.return_value = test_gdf

        result = get_geography(
            "metropolitan statistical area/micropolitan statistical area", year=2022
        )

        mock_cbsas.assert_called_once_with(cb=True, year=2022)
        assert "GEOID" in result.columns
        assert result["GEOID"].tolist() == ["12345", "67890"]

    @patch("pytidycensus.geography.pygris.counties")
    def test_get_geography_unsupported(self, mock_counties):
        """Test error for unsupported geography."""
        with pytest.raises(ValueError, match="Geography 'unsupported' not supported"):
            get_geography("unsupported", year=2022)

    @patch("pytidycensus.geography.pygris.counties")
    def test_get_geography_cb_parameter(self, mock_counties, mock_geodataframe):
        """Test that cb parameter is passed correctly."""
        mock_counties.return_value = mock_geodataframe.copy()

        # Test with cb=False (detailed TIGER/Line files)
        result = get_geography("county", year=2022, cb=False)

        mock_counties.assert_called_with(state=None, cb=False, year=2022)

    @patch("pytidycensus.geography.pygris.counties")
    def test_get_geography_keep_geo_vars(self, mock_counties, mock_geodataframe):
        """Test keeping all geographic variables."""
        # Add extra columns to test data
        test_gdf = mock_geodataframe.copy()
        test_gdf["EXTRA_COL"] = ["A", "B", "C"]
        mock_counties.return_value = test_gdf

        result = get_geography("county", year=2022, keep_geo_vars=True)

        # Should keep all columns
        assert "EXTRA_COL" in result.columns
        assert len(result.columns) == len(test_gdf.columns)

    @patch("pytidycensus.geography.pygris.counties")
    def test_get_geography_filter_columns(self, mock_counties, mock_geodataframe):
        """Test column filtering."""
        mock_counties.return_value = mock_geodataframe.copy()

        result = get_geography("county", year=2022, keep_geo_vars=False)

        # Should keep essential columns for county
        expected_cols = ["GEOID", "NAME", "STATEFP", "COUNTYFP", "NAMELSAD"]
        for col in expected_cols:
            if col in mock_geodataframe.columns:
                assert col in result.columns

        # Should filter out block group column
        assert "BLKGRPCE" not in result.columns

    @patch("pytidycensus.geography.pygris.states")
    def test_get_geography_set_crs(self, mock_states):
        """Test CRS setting when missing."""
        # Create test data without CRS
        test_gdf = gpd.GeoDataFrame(
            {
                "STATEFP": ["48"],
                "NAME": ["Texas"],
                "STUSPS": ["TX"],
                "geometry": [Point(0, 0)],
            }
        )
        test_gdf.crs = None
        mock_states.return_value = test_gdf

        result = get_geography("state", year=2022)

        assert result.crs is not None
        assert result.crs.to_string() == "EPSG:4269"


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    @patch("pytidycensus.geography.get_geography")
    def test_get_state_boundaries(self, mock_get_geography):
        """Test get_state_boundaries function."""
        mock_get_geography.return_value = gpd.GeoDataFrame()

        result = get_state_boundaries(year=2020, cb=True)

        mock_get_geography.assert_called_once_with("state", year=2020, cb=True)
        assert isinstance(result, gpd.GeoDataFrame)

    @patch("pytidycensus.geography.get_geography")
    def test_get_county_boundaries(self, mock_get_geography):
        """Test get_county_boundaries function."""
        mock_get_geography.return_value = gpd.GeoDataFrame()

        result = get_county_boundaries(state="TX", year=2020, cb=False)

        mock_get_geography.assert_called_once_with("county", year=2020, state="TX", cb=False)
        assert isinstance(result, gpd.GeoDataFrame)

    @patch("pytidycensus.geography.get_geography")
    def test_get_tract_boundaries(self, mock_get_geography):
        """Test get_tract_boundaries function."""
        mock_get_geography.return_value = gpd.GeoDataFrame()

        result = get_tract_boundaries(state="TX", county="201", year=2020, cb=True)

        mock_get_geography.assert_called_once_with(
            "tract", year=2020, state="TX", county="201", cb=True
        )
        assert isinstance(result, gpd.GeoDataFrame)

    @patch("pytidycensus.geography.get_geography")
    def test_get_block_group_boundaries(self, mock_get_geography):
        """Test get_block_group_boundaries function."""
        mock_get_geography.return_value = gpd.GeoDataFrame()

        result = get_block_group_boundaries(state="TX", county="201", year=2020, cb=True)

        mock_get_geography.assert_called_once_with(
            "block group", year=2020, state="TX", county="201", cb=True
        )
        assert isinstance(result, gpd.GeoDataFrame)


class TestIntegration:
    """Integration tests for geography module with pygris."""

    @patch("pytidycensus.geography.pygris.states")
    def test_full_workflow_state_boundaries(self, mock_states):
        """Test complete workflow for state boundaries."""
        # Mock pygris response
        mock_gdf = gpd.GeoDataFrame(
            {
                "STATEFP": ["48"],
                "NAME": ["Texas"],
                "STUSPS": ["TX"],
                "geometry": [Point(0, 0)],
            }
        )
        mock_states.return_value = mock_gdf

        result = get_geography("state", year=2022)

        assert isinstance(result, gpd.GeoDataFrame)
        assert "GEOID" in result.columns
        assert result["GEOID"].iloc[0] == "48"

    @patch("pytidycensus.geography.pygris.counties")
    @patch("pytidycensus.geography.validate_state")
    @patch("pytidycensus.geography.validate_county")
    def test_county_filtering(self, mock_validate_county, mock_validate_state, mock_counties):
        """Test county filtering by state and county."""
        mock_validate_state.return_value = ["48"]
        mock_validate_county.return_value = ["201"]

        test_gdf = gpd.GeoDataFrame(
            {
                "STATEFP": ["48", "48", "48"],
                "COUNTYFP": ["201", "113", "085"],
                "NAME": ["Harris", "Dallas", "Collin"],
                "geometry": [Point(0, 0), Point(1, 1), Point(2, 2)],
            }
        )
        mock_counties.return_value = test_gdf

        result = get_geography("county", year=2022, state="TX", county="201")

        # Should filter to only Harris County
        assert len(result) == 1
        assert result.iloc[0]["COUNTYFP"] == "201"
