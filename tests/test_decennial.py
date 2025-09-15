"""
Tests for decennial Census data retrieval functions.
"""

from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd
import pandas as pd
import pytest

from pytidycensus.decennial import get_decennial, get_decennial_variables


class TestGetDecennial:
    """Test cases for the get_decennial function."""

    @patch("pytidycensus.decennial.CensusAPI")
    @patch("pytidycensus.decennial.process_census_data")
    def test_get_decennial_basic(self, mock_process, mock_api_class):
        """Test basic decennial Census data retrieval."""
        # Mock API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "P1_001N": "5024279", "state": "01"}
        ]
        mock_api_class.return_value = mock_api

        # Mock processing function
        mock_df = pd.DataFrame(
            {
                "NAME": ["Alabama"],
                "P1_001N": [5024279],
                "state": ["01"],
                "variable": ["P1_001N"],
                "value": [5024279],
            }
        )
        mock_process.return_value = mock_df

        result = get_decennial(
            geography="state", variables="P1_001N", year=2020, api_key="test"
        )

        # Verify API was called correctly
        mock_api.get.assert_called_once()
        call_args = mock_api.get.call_args
        assert call_args[1]["year"] == 2020
        assert call_args[1]["dataset"] == "dec"
        assert call_args[1]["survey"] == "pl"  # Default for 2020
        assert "P1_001N" in call_args[1]["variables"]

        # Verify processing was called
        mock_process.assert_called_once()

        assert isinstance(result, pd.DataFrame)

    @patch("pytidycensus.decennial.CensusAPI")
    @patch("pytidycensus.variables.load_variables")
    def test_get_decennial_with_table(self, mock_load_vars, mock_api_class):
        """Test decennial Census data retrieval with table parameter."""
        # Mock variables loading
        mock_vars_df = pd.DataFrame(
            {
                "name": ["P1_001N", "P1_002N"],
                "label": ["Total population", "Population of one race"],
            }
        )
        mock_load_vars.return_value = mock_vars_df

        # Mock API
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            get_decennial(geography="state", table="P1", year=2020, api_key="test")

        # Should load variables for the table
        mock_load_vars.assert_called_once_with(2020, "dec", "pl", cache=False)

        # Should call API with table variables
        call_args = mock_api.get.call_args[1]["variables"]
        assert "P1_001N" in call_args
        assert "P1_002N" in call_args

    @patch("pytidycensus.decennial.CensusAPI")
    @patch("pytidycensus.decennial.get_geography")
    def test_get_decennial_with_geometry(self, mock_get_geo, mock_api_class):
        """Test decennial Census data retrieval with geometry."""
        # Mock API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "P1_001N": "5024279", "GEOID": "01", "state": "01"}
        ]
        mock_api_class.return_value = mock_api

        # Mock geometry data
        mock_gdf = gpd.GeoDataFrame(
            {
                "GEOID": ["01"],
                "NAME": ["Alabama"],
                "geometry": [None],  # Simplified for test
            }
        )
        mock_get_geo.return_value = mock_gdf

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            mock_df = pd.DataFrame(
                {"NAME": ["Alabama"], "P1_001N": [5024279], "GEOID": ["01"]}
            )
            mock_process.return_value = mock_df

            result = get_decennial(
                geography="state", variables="P1_001N", geometry=True, api_key="test"
            )

        # Should call get_geography
        mock_get_geo.assert_called_once()

        # Result should be merged with geometry
        assert "GEOID" in result.columns

    def test_get_decennial_validation_errors(self):
        """Test validation errors in get_decennial."""
        # No variables or table
        with pytest.raises(
            ValueError,
            match="Either a vector of variables or a table must be specified",
        ):
            get_decennial(geography="state", api_key="test")

        # Both variables and table
        with pytest.raises(
            ValueError, match="Specify variables or a table to retrieve"
        ):
            get_decennial(
                geography="state", variables="P1_001N", table="P1", api_key="test"
            )

        # Invalid year
        with pytest.raises(ValueError, match="Decennial census data not available"):
            get_decennial(
                geography="state", variables="P1_001N", year=2019, api_key="test"
            )

    @patch("pytidycensus.decennial.CensusAPI")
    def test_get_decennial_different_years(self, mock_api_class):
        """Test get_decennial with different years and default sumfiles."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test 2020 (should use 'pl')
            get_decennial(
                geography="state", variables="P1_001N", year=2020, api_key="test"
            )
            call_args = mock_api.get.call_args[1]
            assert call_args["survey"] == "pl"

            # Test 2010 (should use 'sf1')
            get_decennial(
                geography="state", variables="P001001", year=2010, api_key="test"
            )
            call_args = mock_api.get.call_args[1]
            assert call_args["survey"] == "sf1"

            # Test 2000 (should use 'sf1')
            get_decennial(
                geography="state", variables="P001001", year=2000, api_key="test"
            )
            call_args = mock_api.get.call_args[1]
            assert call_args["survey"] == "sf1"

    @patch("pytidycensus.decennial.CensusAPI")
    def test_get_decennial_custom_sumfile(self, mock_api_class):
        """Test get_decennial with custom sumfile."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test custom sumfile
            get_decennial(
                geography="state",
                variables="P1_001N",
                year=2020,
                sumfile="dhc",
                api_key="test",
            )
            call_args = mock_api.get.call_args[1]
            assert call_args["survey"] == "dhc"

    def test_get_decennial_multiple_variables(self):
        """Test get_decennial with multiple variables."""
        with patch("pytidycensus.decennial.CensusAPI") as mock_api_class, patch(
            "pytidycensus.decennial.process_census_data"
        ) as mock_process:
            mock_api = Mock()
            mock_api.get.return_value = []
            mock_api_class.return_value = mock_api
            mock_process.return_value = pd.DataFrame()

            variables = ["P1_001N", "P1_002N"]
            get_decennial(geography="state", variables=variables, api_key="test")

            # Should include all variables
            call_args = mock_api.get.call_args[1]["variables"]
            assert "P1_001N" in call_args
            assert "P1_002N" in call_args

    @patch("pytidycensus.decennial.CensusAPI")
    @patch("pytidycensus.variables.load_variables")
    def test_get_decennial_table_not_found(self, mock_load_vars, mock_api_class):
        """Test get_decennial with table that has no variables."""
        # Mock empty variables result
        mock_vars_df = pd.DataFrame(
            {"name": ["P1_001N", "P1_002N"], "label": ["Population", "Something else"]}
        )
        mock_load_vars.return_value = mock_vars_df

        with pytest.raises(ValueError, match="No variables found for table"):
            get_decennial(geography="state", table="P99", api_key="test")

    @patch("pytidycensus.decennial.CensusAPI")
    def test_get_decennial_string_variable(self, mock_api_class):
        """Test get_decennial with single string variable."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test single string variable (should be converted to list)
            get_decennial(geography="state", variables="P1_001N", api_key="test")

            call_args = mock_api.get.call_args[1]["variables"]
            assert isinstance(call_args, list)
            assert "P1_001N" in call_args

    @patch("pytidycensus.decennial.CensusAPI")
    @patch("pytidycensus.decennial.get_geography")
    def test_get_decennial_geometry_merge_warning(self, mock_get_geo, mock_api_class):
        """Test warning when geometry merge fails due to missing GEOID."""
        # Mock API response without GEOID
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "P1_001N": "5024279", "state": "01"}
        ]
        mock_api_class.return_value = mock_api

        # Mock geometry data with GEOID
        mock_gdf = gpd.GeoDataFrame(
            {"GEOID": ["01"], "NAME": ["Alabama"], "geometry": [None]}
        )
        mock_get_geo.return_value = mock_gdf

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            # Census data without GEOID
            mock_df = pd.DataFrame(
                {"NAME": ["Alabama"], "P1_001N": [5024279], "state": ["01"]}
            )
            mock_process.return_value = mock_df

            # Should return census data without geometry merge
            result = get_decennial(
                geography="state", variables="P1_001N", geometry=True, api_key="test"
            )

            # Should be the original DataFrame, not merged
            assert "geometry" not in result.columns

    @patch("pytidycensus.decennial.CensusAPI")
    def test_get_decennial_api_error(self, mock_api_class):
        """Test get_decennial handles API errors properly."""
        mock_api = Mock()
        mock_api.get.side_effect = Exception("API request failed")
        mock_api_class.return_value = mock_api

        with pytest.raises(
            Exception,
            match="Failed to retrieve decennial Census data: API request failed",
        ):
            get_decennial(geography="state", variables="P1_001N", api_key="test")

    @patch("pytidycensus.decennial.CensusAPI")
    def test_get_decennial_different_outputs(self, mock_api_class):
        """Test get_decennial with different output formats."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test tidy output
            get_decennial(
                geography="state", variables="P1_001N", output="tidy", api_key="test"
            )
            call_args = mock_process.call_args[0]
            assert "tidy" in call_args

            # Test wide output
            get_decennial(
                geography="state", variables="P1_001N", output="wide", api_key="test"
            )
            call_args = mock_process.call_args[0]
            assert "wide" in call_args


class TestGetDecennialVariables:
    """Test cases for the get_decennial_variables function."""

    @patch("pytidycensus.variables.load_variables")
    def test_get_decennial_variables_default(self, mock_load_vars):
        """Test getting decennial variables with default parameters."""
        mock_df = pd.DataFrame({"name": ["P1_001N"], "label": ["Total population"]})
        mock_load_vars.return_value = mock_df

        result = get_decennial_variables()

        mock_load_vars.assert_called_once_with(2020, "dec", "pl")
        assert isinstance(result, pd.DataFrame)

    @patch("pytidycensus.variables.load_variables")
    def test_get_decennial_variables_custom_year(self, mock_load_vars):
        """Test getting decennial variables with custom year."""
        mock_df = pd.DataFrame({"name": ["P001001"], "label": ["Total population"]})
        mock_load_vars.return_value = mock_df

        result = get_decennial_variables(year=2010)

        mock_load_vars.assert_called_once_with(2010, "dec", "sf1")
        assert isinstance(result, pd.DataFrame)

    @patch("pytidycensus.variables.load_variables")
    def test_get_decennial_variables_custom_sumfile(self, mock_load_vars):
        """Test getting decennial variables with custom sumfile."""
        mock_df = pd.DataFrame({"name": ["P1_001N"], "label": ["Total population"]})
        mock_load_vars.return_value = mock_df

        result = get_decennial_variables(year=2020, sumfile="dhc")

        mock_load_vars.assert_called_once_with(2020, "dec", "dhc")
        assert isinstance(result, pd.DataFrame)

    @patch("pytidycensus.variables.load_variables")
    def test_get_decennial_variables_year_2000(self, mock_load_vars):
        """Test getting decennial variables for year 2000."""
        mock_df = pd.DataFrame({"name": ["P001001"], "label": ["Total population"]})
        mock_load_vars.return_value = mock_df

        result = get_decennial_variables(year=2000)

        mock_load_vars.assert_called_once_with(2000, "dec", "sf1")
        assert isinstance(result, pd.DataFrame)
