"""Tests for variables module functionality."""

import pickle
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from pytidycensus.variables import (
    _parse_variables,
    clear_cache,
    get_table_variables,
    list_available_datasets,
    load_variables,
    search_variables,
)


@pytest.fixture
def mock_variables_data():
    """Mock Census API variables response."""
    return {
        "variables": {
            "B19013_001E": {
                "label": "Estimate!!Median household income in the past 12 months (in 2022 inflation-adjusted dollars)",
                "concept": "MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)",
                "predicateType": "int",
                "group": "B19013",
                "limit": 0,
            },
            "B19013_001M": {
                "label": "Margin of Error!!Median household income in the past 12 months (in 2022 inflation-adjusted dollars)",
                "concept": "MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)",
                "predicateType": "int",
                "group": "B19013",
                "limit": 0,
            },
            "B25001_001E": {
                "label": "Estimate!!Total housing units",
                "concept": "HOUSING UNITS",
                "predicateType": "int",
                "group": "B25001",
                "limit": 0,
            },
            "P1_001N": {
                "label": "Total population",
                "concept": "RACE",
                "predicateType": "int",
                "group": "P1",
                "limit": 0,
            },
        }
    }


@pytest.fixture
def mock_variables_df():
    """Expected DataFrame from parsed variables."""
    return pd.DataFrame(
        [
            {
                "name": "B19013_001E",
                "label": "Estimate!!Median household income in the past 12 months (in 2022 inflation-adjusted dollars)",
                "concept": "MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)",
                "predicateType": "int",
                "group": "B19013",
                "limit": 0,
                "table": "B19013",
            },
            {
                "name": "B19013_001M",
                "label": "Margin of Error!!Median household income in the past 12 months (in 2022 inflation-adjusted dollars)",
                "concept": "MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)",
                "predicateType": "int",
                "group": "B19013",
                "limit": 0,
                "table": "B19013",
            },
            {
                "name": "B25001_001E",
                "label": "Estimate!!Total housing units",
                "concept": "HOUSING UNITS",
                "predicateType": "int",
                "group": "B25001",
                "limit": 0,
                "table": "B25001",
            },
            {
                "name": "P1_001N",
                "label": "Total population",
                "concept": "RACE",
                "predicateType": "int",
                "group": "P1",
                "limit": 0,
                "table": "P1",
            },
        ]
    )


class TestParseVariables:
    """Test _parse_variables function."""

    def test_parse_variables_success(self, mock_variables_data, mock_variables_df):
        """Test successful parsing of variables data."""
        result = _parse_variables(mock_variables_data)

        # Check structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4
        assert list(result.columns) == [
            "name",
            "label",
            "concept",
            "predicateType",
            "group",
            "limit",
            "table",
        ]

        # Check data is sorted by name
        assert result["name"].tolist() == [
            "B19013_001E",
            "B19013_001M",
            "B25001_001E",
            "P1_001N",
        ]

        # Check table extraction
        assert result["table"].tolist() == ["B19013", "B19013", "B25001", "P1"]

    def test_parse_variables_invalid_format(self):
        """Test parsing with invalid data format."""
        with pytest.raises(ValueError, match="Invalid variables data format"):
            _parse_variables({"invalid": "data"})

    def test_parse_variables_empty(self):
        """Test parsing with empty variables."""
        result = _parse_variables({"variables": {}})
        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)


class TestLoadVariables:
    """Test load_variables function."""

    @patch("pytidycensus.variables.CensusAPI")
    def test_load_variables_from_api(self, mock_api_class, mock_variables_data, tmp_path):
        """Test loading variables from API."""
        # Setup mocks
        mock_api = Mock()
        mock_api.get_variables.return_value = mock_variables_data
        mock_api_class.return_value = mock_api

        # Test
        result = load_variables(2022, "acs", "acs5", cache_dir=str(tmp_path))

        # Verify API call
        mock_api.get_variables.assert_called_once_with(2022, "acs", "acs5")

        # Verify result
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4
        assert "B19013_001E" in result["name"].values

    def test_load_variables_from_cache(self, mock_variables_df, tmp_path):
        """Test loading variables from cache."""
        # Create cache file
        cache_file = tmp_path / "acs_2022_acs5_variables.pkl"
        with open(cache_file, "wb") as f:
            pickle.dump(mock_variables_df, f)

        # Test
        result = load_variables(2022, "acs", "acs5", cache_dir=str(tmp_path))

        # Verify result from cache
        pd.testing.assert_frame_equal(result, mock_variables_df)

    def test_load_variables_corrupted_cache(self, mock_variables_data, tmp_path):
        """Test handling corrupted cache file."""
        # Create corrupted cache file
        cache_file = tmp_path / "acs_2022_acs5_variables.pkl"
        with open(cache_file, "w") as f:
            f.write("corrupted data")

        with patch("pytidycensus.variables.CensusAPI") as mock_api_class:
            mock_api = Mock()
            mock_api.get_variables.return_value = mock_variables_data
            mock_api_class.return_value = mock_api

            # Should fall back to API
            result = load_variables(2022, "acs", "acs5", cache_dir=str(tmp_path))
            mock_api.get_variables.assert_called_once()

    @patch("pytidycensus.variables.CensusAPI")
    def test_load_variables_api_error(self, mock_api_class, tmp_path):
        """Test handling API errors."""
        mock_api = Mock()
        mock_api.get_variables.side_effect = Exception("API Error")
        mock_api_class.return_value = mock_api

        with pytest.raises(Exception, match="Failed to load variables: API Error"):
            load_variables(2022, "acs", "acs5", cache_dir=str(tmp_path))


class TestSearchVariables:
    """Test search_variables function."""

    @patch("pytidycensus.variables.load_variables")
    def test_search_variables_by_label(self, mock_load_variables, mock_variables_df):
        """Test searching variables by label."""
        mock_load_variables.return_value = mock_variables_df

        result = search_variables("income", 2022, "acs", "acs5", field="label")

        # Should find income-related variables
        assert len(result) == 2  # Both estimate and MOE
        assert all("income" in label.lower() for label in result["label"])
        mock_load_variables.assert_called_once_with(2022, "acs", "acs5")

    @patch("pytidycensus.variables.load_variables")
    def test_search_variables_by_concept(self, mock_load_variables, mock_variables_df):
        """Test searching variables by concept."""
        mock_load_variables.return_value = mock_variables_df

        result = search_variables("housing", 2022, "acs", "acs5", field="concept")

        # Should find housing-related variables
        assert len(result) == 1
        assert "housing" in result.iloc[0]["concept"].lower()

    @patch("pytidycensus.variables.load_variables")
    def test_search_variables_by_name(self, mock_load_variables, mock_variables_df):
        """Test searching variables by name."""
        mock_load_variables.return_value = mock_variables_df

        result = search_variables("B19013", 2022, "acs", "acs5", field="name")

        # Should find variables with B19013 in name
        assert len(result) == 2
        assert all("B19013" in name for name in result["name"])

    @patch("pytidycensus.variables.load_variables")
    def test_search_variables_all_fields(self, mock_load_variables, mock_variables_df):
        """Test searching across all fields."""
        mock_load_variables.return_value = mock_variables_df

        result = search_variables("population", 2022, "dec", "pl", field="all")

        # Should find population in label
        assert len(result) == 1
        assert "population" in result.iloc[0]["label"].lower()

    @patch("pytidycensus.variables.load_variables")
    def test_search_variables_no_results(self, mock_load_variables, mock_variables_df):
        """Test search with no matching results."""
        mock_load_variables.return_value = mock_variables_df

        result = search_variables("nonexistent", 2022, "acs", "acs5")

        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)

    @patch("pytidycensus.variables.load_variables")
    def test_search_variables_invalid_field(self, mock_load_variables):
        """Test search with invalid field parameter."""
        mock_load_variables.return_value = pd.DataFrame()

        with pytest.raises(ValueError, match="Field must be"):
            search_variables("test", 2022, "acs", "acs5", field="invalid")


class TestGetTableVariables:
    """Test get_table_variables function."""

    @patch("pytidycensus.variables.load_variables")
    def test_get_table_variables_success(self, mock_load_variables, mock_variables_df):
        """Test getting variables for a specific table."""
        mock_load_variables.return_value = mock_variables_df

        result = get_table_variables("B19013", 2022, "acs", "acs5")

        # Should find B19013 variables
        assert len(result) == 2
        assert all(name.startswith("B19013_") for name in result["name"])
        mock_load_variables.assert_called_once_with(2022, "acs", "acs5")

    @patch("pytidycensus.variables.load_variables")
    def test_get_table_variables_case_insensitive(self, mock_load_variables, mock_variables_df):
        """Test table lookup is case insensitive."""
        mock_load_variables.return_value = mock_variables_df

        result = get_table_variables("b19013", 2022, "acs", "acs5")

        # Should still find B19013 variables
        assert len(result) == 2
        assert all(name.startswith("B19013_") for name in result["name"])

    @patch("pytidycensus.variables.load_variables")
    def test_get_table_variables_no_results(self, mock_load_variables, mock_variables_df):
        """Test getting variables for non-existent table."""
        mock_load_variables.return_value = mock_variables_df

        result = get_table_variables("B99999", 2022, "acs", "acs5")

        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)


class TestClearCache:
    """Test clear_cache function."""

    def test_clear_cache_existing_directory(self, tmp_path):
        """Test clearing existing cache directory."""
        # Create cache directory with files
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "test_file.pkl").write_text("test")

        # Clear cache
        clear_cache(str(cache_dir))

        # Directory should be removed
        assert not cache_dir.exists()

    def test_clear_cache_nonexistent_directory(self, tmp_path):
        """Test clearing non-existent cache directory."""
        cache_dir = tmp_path / "nonexistent"

        # Should not raise error
        clear_cache(str(cache_dir))


class TestListAvailableDatasets:
    """Test list_available_datasets function."""

    def test_list_available_datasets_2022(self):
        """Test available datasets for 2022."""
        result = list_available_datasets(2022)

        assert "acs" in result
        assert "pep" in result
        assert result["acs"] == ["acs1", "acs5"]
        assert "components" in result["pep"]

    def test_list_available_datasets_2020(self):
        """Test available datasets for 2020."""
        result = list_available_datasets(2020)

        assert "acs" in result
        assert "dec" in result
        assert "pep" in result
        assert result["dec"] == ["pl"]

    def test_list_available_datasets_2010(self):
        """Test available datasets for 2010."""
        result = list_available_datasets(2010)

        assert "acs" in result
        assert "dec" in result
        assert result["dec"] == ["sf1"]

    def test_list_available_datasets_2000(self):
        """Test available datasets for 2000."""
        result = list_available_datasets(2000)

        assert "acs" not in result  # ACS started in 2005
        assert "dec" in result
        assert "pep" in result
        assert result["dec"] == ["sf1", "sf2", "sf3", "sf4"]


class TestIntegration:
    """Integration tests for variables module."""

    @patch("pytidycensus.variables.load_variables")
    def test_full_workflow(self, mock_load_variables, mock_variables_df):
        """Test complete variables workflow."""
        # Setup mock to return same data for all calls
        mock_load_variables.return_value = mock_variables_df

        # Search for income variables
        income_vars = search_variables("income", 2022, "acs", "acs5")

        # Get table variables
        table_vars = get_table_variables("B19013", 2022, "acs", "acs5")

        # Verify results
        assert len(income_vars) == 2
        assert len(table_vars) == 2
        assert all(var in mock_variables_df["name"].values for var in income_vars["name"])
        assert all(var in mock_variables_df["name"].values for var in table_vars["name"])
