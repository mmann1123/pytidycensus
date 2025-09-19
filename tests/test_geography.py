"""Tests for geography module functionality."""

import os
import tempfile
from unittest.mock import Mock, mock_open, patch

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from pytidycensus.geography import (
    TigerDownloader,
    get_block_group_boundaries,
    get_county_boundaries,
    get_geography,
    get_state_boundaries,
    get_tract_boundaries,
)


@pytest.fixture
def mock_tiger_downloader():
    """Mock TigerDownloader instance."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield TigerDownloader(cache_dir=tmp_dir)


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


class TestTigerDownloader:
    """Test cases for TigerDownloader class."""

    def test_init_default_cache_dir(self):
        """Test initialization with default cache directory."""
        downloader = TigerDownloader()
        assert downloader.cache_dir == tempfile.gettempdir()

    def test_init_custom_cache_dir(self, tmp_path):
        """Test initialization with custom cache directory."""
        cache_dir = str(tmp_path / "custom_cache")
        downloader = TigerDownloader(cache_dir=cache_dir)
        assert downloader.cache_dir == cache_dir
        assert os.path.exists(cache_dir)

    def test_build_url_state(self, mock_tiger_downloader):
        """Test URL building for state geography."""
        url = mock_tiger_downloader._build_url(2022, "state")
        expected = "https://www2.census.gov/geo/tiger/TIGER2022/STATE/tl_2022_us_state.zip"
        assert url == expected

    def test_build_url_county(self, mock_tiger_downloader):
        """Test URL building for county geography."""
        url = mock_tiger_downloader._build_url(2022, "county")
        expected = "https://www2.census.gov/geo/tiger/TIGER2022/COUNTY/tl_2022_us_county.zip"
        assert url == expected

    def test_build_url_tract(self, mock_tiger_downloader):
        """Test URL building for tract geography."""
        url = mock_tiger_downloader._build_url(2022, "tract", state_fips="48")
        expected = "https://www2.census.gov/geo/tiger/TIGER2022/TRACT/tl_2022_48_tract.zip"
        assert url == expected

    def test_build_url_tract_no_state(self, mock_tiger_downloader):
        """Test URL building for tract geography without state FIPS."""
        with pytest.raises(ValueError, match="State FIPS code required for tract geography"):
            mock_tiger_downloader._build_url(2022, "tract")

    def test_build_url_block_group(self, mock_tiger_downloader):
        """Test URL building for block group geography."""
        url = mock_tiger_downloader._build_url(2022, "block group", state_fips="48")
        expected = "https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_48_bg.zip"
        assert url == expected

    def test_build_url_block_group_no_state(self, mock_tiger_downloader):
        """Test URL building for block group geography without state FIPS."""
        with pytest.raises(ValueError, match="State FIPS code required for block group geography"):
            mock_tiger_downloader._build_url(2022, "block group")

    def test_build_url_zcta(self, mock_tiger_downloader):
        """Test URL building for ZCTA geography."""
        # Test 2020+ uses ZCTA520 (2020 boundaries)
        url_2022 = mock_tiger_downloader._build_url(2022, "zcta")
        expected_2022 = "https://www2.census.gov/geo/tiger/TIGER2022/ZCTA520/tl_2022_us_zcta520.zip"
        assert url_2022 == expected_2022

        # Test pre-2020 uses ZCTA510 (2010 boundaries)
        url_2019 = mock_tiger_downloader._build_url(2019, "zcta")
        expected_2019 = "https://www2.census.gov/geo/tiger/TIGER2019/ZCTA5/tl_2019_us_zcta510.zip"
        assert url_2019 == expected_2019

        # Test both aliases work
        url_full = mock_tiger_downloader._build_url(2022, "zip code tabulation area")
        assert url_full == expected_2022

    def test_build_url_place(self, mock_tiger_downloader):
        """Test URL building for place geography."""
        url = mock_tiger_downloader._build_url(2022, "place", state_fips="48")
        expected = "https://www2.census.gov/geo/tiger/TIGER2022/PLACE/tl_2022_48_place.zip"
        assert url == expected

    def test_build_url_place_no_state(self, mock_tiger_downloader):
        """Test URL building for place geography without state FIPS."""
        with pytest.raises(ValueError, match="State FIPS code required for place geography"):
            mock_tiger_downloader._build_url(2022, "place")

    def test_build_url_cbsa(self, mock_tiger_downloader):
        """Test URL building for CBSA geography."""
        url = mock_tiger_downloader._build_url(
            2022, "metropolitan statistical area/micropolitan statistical area"
        )
        expected = "https://www2.census.gov/geo/tiger/TIGER2022/CBSA/tl_2022_us_cbsa.zip"
        assert url == expected

    def test_build_url_unsupported_geography(self, mock_tiger_downloader):
        """Test URL building for unsupported geography."""
        with pytest.raises(ValueError, match="Geography 'unsupported' not yet supported"):
            mock_tiger_downloader._build_url(2022, "unsupported")

    def test_download_and_extract_already_exists(self, mock_tiger_downloader, tmp_path):
        """Test download when files already exist."""
        # Create extraction directory
        extract_dir = os.path.join(mock_tiger_downloader.cache_dir, "test_file")
        os.makedirs(extract_dir)

        result = mock_tiger_downloader.download_and_extract(
            "http://example.com/test_file.zip", "test_file.zip"
        )
        assert result == extract_dir

    @patch("pytidycensus.geography.requests.get")
    @patch("pytidycensus.geography.zipfile.ZipFile")
    def test_download_and_extract_success(
        self, mock_zipfile, mock_requests_get, mock_tiger_downloader
    ):
        """Test successful download and extraction."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        # Mock zipfile extraction
        mock_zip = Mock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        with patch("builtins.open", mock_open()) as mock_file, patch("os.remove") as mock_remove:
            result = mock_tiger_downloader.download_and_extract(
                "http://example.com/test.zip", "test.zip"
            )

            expected_path = os.path.join(mock_tiger_downloader.cache_dir, "test")
            assert result == expected_path

            # Verify file operations
            mock_file.assert_called()
            mock_zip.extractall.assert_called_once_with(expected_path)
            mock_remove.assert_called_once()

    # def test_download_and_extract_real_file(tmp_path):
    #     """Actually download and extract a TIGER shapefile zip."""
    #     cache_dir = str(tmp_path)
    #     downloader = TigerDownloader(cache_dir=cache_dir)
    #     url = (
    #         "https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_division_20m.zip"
    #     )
    #     filename = "cb_2018_us_division_20m.zip"

    #     # Download and extract
    #     extract_dir = downloader.download_and_extract(url, filename)

    #     # Check that extraction directory exists and contains a .shp file
    #     assert os.path.exists(extract_dir)
    #     shp_files = [f for f in os.listdir(extract_dir) if f.endswith(".shp")]
    #     assert len(shp_files) > 0

    @patch("pytidycensus.geography.requests.get")
    @patch("pytidycensus.geography.TigerDownloader.download_with_wget_or_curl")
    def test_download_fallback_to_wget_curl(
        self, mock_wget_curl, mock_requests_get, mock_tiger_downloader
    ):
        """Test fallback to wget/curl when requests fails."""
        # Mock requests failure
        mock_requests_get.side_effect = Exception("Connection error")

        # Mock successful wget/curl download
        mock_wget_curl.return_value = None

        with patch("pytidycensus.geography.zipfile.ZipFile") as mock_zipfile, patch("os.remove"):
            mock_zip = Mock()
            mock_zipfile.return_value.__enter__.return_value = mock_zip

            result = mock_tiger_downloader.download_and_extract(
                "http://example.com/test.zip", "test.zip"
            )

            # Should call the backup download method
            mock_wget_curl.assert_called_once()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_download_with_wget_available(self, mock_subprocess, mock_which):
        """Test wget download when wget is available."""
        # Mock wget being available
        mock_which.side_effect = lambda cmd: "/usr/bin/wget" if cmd == "wget" else None

        TigerDownloader.download_with_wget_or_curl("http://example.com/test.zip", "/tmp/test.zip")

        # Should call wget
        mock_subprocess.assert_called_once_with(
            [
                "wget",
                "--quiet",
                "--show-progress",
                "--progress=bar:force:noscroll",
                "-O",
                "/tmp/test.zip",
                "http://example.com/test.zip",
            ],
            check=True,
        )

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_download_with_curl_fallback(self, mock_subprocess, mock_which):
        """Test curl download when wget is not available."""

        # Mock wget not available, curl available
        def which_side_effect(cmd):
            if cmd == "wget":
                return None
            elif cmd == "curl":
                return "/usr/bin/curl"
            return None

        mock_which.side_effect = which_side_effect

        TigerDownloader.download_with_wget_or_curl("http://example.com/test.zip", "/tmp/test.zip")

        # Should call curl
        mock_subprocess.assert_called_once_with(
            ["curl", "-L", "-o", "/tmp/test.zip", "http://example.com/test.zip"],
            check=True,
        )

    @patch("shutil.which")
    def test_download_no_wget_curl_available(self, mock_which):
        """Test error when neither wget nor curl is available."""
        # Mock neither wget nor curl available
        mock_which.return_value = None

        with pytest.raises(RuntimeError, match="Neither wget nor curl is available"):
            TigerDownloader.download_with_wget_or_curl(
                "http://example.com/test.zip", "/tmp/test.zip"
            )

    def test_get_shapefile_path_success(self, mock_tiger_downloader, tmp_path):
        """Test finding shapefile in directory."""
        test_dir = tmp_path / "test_extract"
        test_dir.mkdir()
        (test_dir / "test_file.shp").touch()
        (test_dir / "test_file.dbf").touch()

        result = mock_tiger_downloader.get_shapefile_path(str(test_dir))
        assert result == str(test_dir / "test_file.shp")

    def test_get_shapefile_path_not_found(self, mock_tiger_downloader, tmp_path):
        """Test error when no shapefile found."""
        test_dir = tmp_path / "empty_extract"
        test_dir.mkdir()
        (test_dir / "readme.txt").touch()

        with pytest.raises(FileNotFoundError, match="No shapefile found in extracted directory"):
            mock_tiger_downloader.get_shapefile_path(str(test_dir))


class TestGetGeography:
    """Test cases for get_geography function."""

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_get_geography_basic(self, mock_read_file, mock_downloader_class, mock_geodataframe):
        """Test basic geography retrieval."""
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        # Mock geopandas
        mock_read_file.return_value = mock_geodataframe.copy()

        result = get_geography("county", year=2022)

        assert isinstance(result, gpd.GeoDataFrame)
        mock_downloader_class.assert_called_once()
        mock_read_file.assert_called_once()

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    @patch("pytidycensus.geography.validate_state")
    def test_get_geography_with_state_filter(
        self,
        mock_validate_state,
        mock_read_file,
        mock_downloader_class,
        mock_geodataframe,
    ):
        """Test geography retrieval with state filtering."""
        mock_validate_state.return_value = ["48"]

        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        # Mock geopandas - return data with multiple states
        test_gdf = mock_geodataframe.copy()
        mock_read_file.return_value = test_gdf

        result = get_geography("county", year=2022, state="TX")

        # Should filter to only Texas counties (STATEFP == '48')
        assert len(result) == 2  # Only TX counties
        assert all(statefp == "48" for statefp in result["STATEFP"])

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    @patch("pytidycensus.geography.validate_state")
    @patch("pytidycensus.geography.validate_county")
    def test_get_geography_with_county_filter(
        self,
        mock_validate_county,
        mock_validate_state,
        mock_read_file,
        mock_downloader_class,
        mock_geodataframe,
    ):
        """Test geography retrieval with county filtering."""
        mock_validate_state.return_value = ["48"]
        mock_validate_county.return_value = ["201"]

        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        test_gdf = mock_geodataframe.copy()
        mock_read_file.return_value = test_gdf

        result = get_geography("tract", year=2022, state="TX", county="201")

        # Should filter to only Harris County (201)
        assert len(result) == 1
        assert result.iloc[0]["COUNTYFP"] == "201"

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_get_geography_multiple_states_warning(
        self, mock_read_file, mock_downloader_class, mock_geodataframe, capsys
    ):
        """Test warning when multiple states specified."""
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        mock_read_file.return_value = mock_geodataframe.copy()

        with patch("pytidycensus.geography.validate_state") as mock_validate_state:
            mock_validate_state.return_value = ["48", "06"]  # Multiple states

            get_geography("county", year=2022, state=["TX", "CA"])

            captured = capsys.readouterr()
            assert "Multiple states specified" in captured.out

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_get_geography_geoid_creation_state(self, mock_read_file, mock_downloader_class):
        """Test GEOID creation for state geography."""
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        # Create test data without GEOID
        test_gdf = gpd.GeoDataFrame(
            {
                "STATEFP": ["48", "06"],
                "NAME": ["Texas", "California"],
                "geometry": [Point(0, 0), Point(1, 1)],
            }
        )
        mock_read_file.return_value = test_gdf

        result = get_geography("state", year=2022)

        assert "GEOID" in result.columns
        assert result["GEOID"].tolist() == ["48", "06"]

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_get_geography_geoid_creation_county(self, mock_read_file, mock_downloader_class):
        """Test GEOID creation for county geography."""
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        # Create test data without GEOID
        test_gdf = gpd.GeoDataFrame(
            {
                "STATEFP": ["48", "48"],
                "COUNTYFP": ["201", "113"],
                "NAME": ["Harris County", "Dallas County"],
                "geometry": [Point(0, 0), Point(1, 1)],
            }
        )
        mock_read_file.return_value = test_gdf

        result = get_geography("county", year=2022)

        assert "GEOID" in result.columns
        assert result["GEOID"].tolist() == ["48201", "48113"]

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_get_geography_geoid_creation_tract(self, mock_read_file, mock_downloader_class):
        """Test GEOID creation for tract geography."""
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        # Create test data without GEOID
        test_gdf = gpd.GeoDataFrame(
            {
                "STATEFP": ["48"],
                "COUNTYFP": ["201"],
                "TRACTCE": ["001000"],
                "NAME": ["Census Tract 10"],
                "geometry": [Point(0, 0)],
            }
        )
        mock_read_file.return_value = test_gdf

        result = get_geography("tract", year=2022)

        assert "GEOID" in result.columns
        assert result["GEOID"].tolist() == ["48201001000"]

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_get_geography_geoid_creation_block_group(self, mock_read_file, mock_downloader_class):
        """Test GEOID creation for block group geography."""
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        # Create test data without GEOID
        test_gdf = gpd.GeoDataFrame(
            {
                "STATEFP": ["48"],
                "COUNTYFP": ["201"],
                "TRACTCE": ["001000"],
                "BLKGRPCE": ["1"],
                "NAME": ["Block Group 1"],
                "geometry": [Point(0, 0)],
            }
        )
        mock_read_file.return_value = test_gdf

        result = get_geography("block group", year=2022)

        assert "GEOID" in result.columns
        assert result["GEOID"].tolist() == ["482010010001"]

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_get_geography_keep_geo_vars(
        self, mock_read_file, mock_downloader_class, mock_geodataframe
    ):
        """Test keeping all geographic variables."""
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        # Add extra columns to test data
        test_gdf = mock_geodataframe.copy()
        test_gdf["EXTRA_COL"] = ["A", "B", "C"]
        mock_read_file.return_value = test_gdf

        result = get_geography("county", year=2022, keep_geo_vars=True)

        # Should keep all columns
        assert "EXTRA_COL" in result.columns
        assert len(result.columns) == len(test_gdf.columns)

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_get_geography_filter_columns_county(
        self, mock_read_file, mock_downloader_class, mock_geodataframe
    ):
        """Test column filtering for county geography."""
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        mock_read_file.return_value = mock_geodataframe.copy()

        result = get_geography("county", year=2022, keep_geo_vars=False)

        # Should keep essential columns for county
        expected_cols = ["GEOID", "NAME", "geometry", "STATEFP", "COUNTYFP", "NAMELSAD"]
        assert all(
            col in result.columns for col in expected_cols if col in mock_geodataframe.columns
        )
        assert "BLKGRPCE" not in result.columns  # Should be filtered out

    @patch("pytidycensus.geography.TigerDownloader")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_get_geography_set_crs(self, mock_read_file, mock_downloader_class, mock_geodataframe):
        """Test CRS setting when missing."""
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_and_extract.return_value = "/path/to/extract"
        mock_downloader.get_shapefile_path.return_value = "/path/to/extract/file.shp"
        mock_downloader._build_url.return_value = "http://example.com/file.zip"
        mock_downloader_class.return_value = mock_downloader

        # Create test data without CRS
        test_gdf = mock_geodataframe.copy()
        test_gdf.crs = None
        mock_read_file.return_value = test_gdf

        result = get_geography("county", year=2022)

        assert result.crs is not None
        assert result.crs.to_string() == "EPSG:4269"


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    @patch("pytidycensus.geography.get_geography")
    def test_get_state_boundaries(self, mock_get_geography):
        """Test get_state_boundaries function."""
        mock_get_geography.return_value = gpd.GeoDataFrame()

        result = get_state_boundaries(year=2020)

        mock_get_geography.assert_called_once_with("state", year=2020)
        assert isinstance(result, gpd.GeoDataFrame)

    @patch("pytidycensus.geography.get_geography")
    def test_get_county_boundaries(self, mock_get_geography):
        """Test get_county_boundaries function."""
        mock_get_geography.return_value = gpd.GeoDataFrame()

        result = get_county_boundaries(state="TX", year=2020)

        mock_get_geography.assert_called_once_with("county", year=2020, state="TX")
        assert isinstance(result, gpd.GeoDataFrame)

    @patch("pytidycensus.geography.get_geography")
    def test_get_tract_boundaries(self, mock_get_geography):
        """Test get_tract_boundaries function."""
        mock_get_geography.return_value = gpd.GeoDataFrame()

        result = get_tract_boundaries(state="TX", county="201", year=2020)

        mock_get_geography.assert_called_once_with("tract", year=2020, state="TX", county="201")
        assert isinstance(result, gpd.GeoDataFrame)

    @patch("pytidycensus.geography.get_geography")
    def test_get_block_group_boundaries(self, mock_get_geography):
        """Test get_block_group_boundaries function."""
        mock_get_geography.return_value = gpd.GeoDataFrame()

        result = get_block_group_boundaries(state="TX", county="201", year=2020)

        mock_get_geography.assert_called_once_with(
            "block group", year=2020, state="TX", county="201"
        )
        assert isinstance(result, gpd.GeoDataFrame)


class TestIntegration:
    """Integration tests for geography module."""

    @patch("pytidycensus.geography.requests.get")
    @patch("pytidycensus.geography.gpd.read_file")
    def test_full_workflow_state_boundaries(self, mock_read_file, mock_requests_get, tmp_path):
        """Test complete workflow for downloading state boundaries."""
        # Mock HTTP response for download
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"fake_zip_data"]
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        # Mock shapefile reading
        mock_gdf = gpd.GeoDataFrame(
            {
                "STATEFP": ["48"],
                "NAME": ["Texas"],
                "STUSPS": ["TX"],
                "geometry": [Point(0, 0)],
            }
        )
        mock_read_file.return_value = mock_gdf

        # Create fake zip file and extracted directory structure
        cache_dir = str(tmp_path / "cache")
        os.makedirs(cache_dir)

        extract_dir = os.path.join(cache_dir, "tl_2022_us_state")
        os.makedirs(extract_dir)

        # Create fake shapefile
        shapefile_path = os.path.join(extract_dir, "tl_2022_us_state.shp")
        with open(shapefile_path, "w") as f:
            f.write("fake shapefile")

        with patch("pytidycensus.geography.zipfile.ZipFile") as mock_zipfile, patch(
            "os.remove"
        ), patch("builtins.open", mock_open()):
            mock_zip = Mock()
            mock_zipfile.return_value.__enter__.return_value = mock_zip

            result = get_geography("state", year=2022, cache_dir=cache_dir)

            assert isinstance(result, gpd.GeoDataFrame)
            assert "GEOID" in result.columns
            assert result["GEOID"].iloc[0] == "48"
