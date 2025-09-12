"""
Tests for population estimates data retrieval functions.
"""

from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd
import pandas as pd
import pytest

from pytidycensus.estimates import (
    _add_breakdown_labels,
    get_estimates,
    get_estimates_variables,
)


class TestGetEstimates:
    """Test cases for the get_estimates function."""

    @patch("pytidycensus.estimates.CensusAPI")
    @patch("pytidycensus.estimates.process_census_data")
    def test_get_estimates_basic(self, mock_process, mock_api_class):
        """Test basic population estimates data retrieval."""
        # Mock API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "POP": "5024279", "state": "01"}
        ]
        mock_api_class.return_value = mock_api

        # Mock processing function
        mock_df = pd.DataFrame(
            {
                "NAME": ["Alabama"],
                "POP": [5024279],
                "state": ["01"],
                "variable": ["POP"],
                "value": [5024279],
            }
        )
        mock_process.return_value = mock_df

        result = get_estimates(
            geography="state", variables="POP", year=2022, api_key="test"
        )

        # Verify API was called correctly
        mock_api.get.assert_called_once()
        call_args = mock_api.get.call_args
        assert call_args[1]["year"] == 2022
        assert call_args[1]["dataset"] == "pep/population"
        assert "POP" in call_args[1]["variables"]

        # Verify processing was called
        mock_process.assert_called_once()

        assert isinstance(result, pd.DataFrame)

    @patch("pytidycensus.estimates.CensusAPI")
    @patch("pytidycensus.estimates.get_geography")
    def test_get_estimates_with_geometry(self, mock_get_geo, mock_api_class):
        """Test population estimates data retrieval with geometry."""
        # Mock API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "POP": "5024279", "GEOID": "01", "state": "01"}
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

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_df = pd.DataFrame(
                {"NAME": ["Alabama"], "POP": [5024279], "GEOID": ["01"]}
            )
            mock_process.return_value = mock_df

            result = get_estimates(
                geography="state", variables="POP", geometry=True, api_key="test"
            )

        # Should call get_geography
        mock_get_geo.assert_called_once()

        # Result should be merged with geometry
        assert "GEOID" in result.columns

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_validation_errors(self, mock_api_class):
        """Test validation errors in get_estimates."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test invalid year
            with pytest.raises(ValueError):
                get_estimates(
                    geography="state", variables="POP", year=1999, api_key="test"
                )

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_multiple_variables(self, mock_api_class):
        """Test get_estimates with multiple variables."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            variables = ["POP", "BIRTHS", "DEATHS"]
            get_estimates(geography="state", variables=variables, api_key="test")

            # Should include all variables
            call_args = mock_api.get.call_args[1]["variables"]
            assert "POP" in call_args
            assert "BIRTHS" in call_args
            assert "DEATHS" in call_args

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_with_breakdown(self, mock_api_class):
        """Test get_estimates with breakdown variables."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test with breakdown (should use charagegroups dataset)
            get_estimates(
                geography="state",
                variables="POP",
                breakdown=["SEX", "AGEGROUP"],
                api_key="test",
            )

            call_args = mock_api.get.call_args
            # Should use charagegroups dataset
            assert call_args[1]["dataset"] == "pep/charagegroups"

            # Should include breakdown variables
            variables = call_args[1]["variables"]
            assert "SEX" in variables
            assert "AGEGROUP" in variables
            assert "POP" in variables

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_string_variable(self, mock_api_class):
        """Test get_estimates with single string variable."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test single string variable (should be converted to list)
            get_estimates(geography="state", variables="POP", api_key="test")

            call_args = mock_api.get.call_args[1]["variables"]
            assert isinstance(call_args, list)
            assert "POP" in call_args

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_time_series(self, mock_api_class):
        """Test get_estimates with time series data."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test time series (should use components dataset)
            get_estimates(
                geography="state", variables="POP", time_series=True, api_key="test"
            )

            call_args = mock_api.get.call_args
            # Should use components dataset for time series
            assert call_args[1]["dataset"] == "pep/components"

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_different_years(self, mock_api_class):
        """Test get_estimates with different years."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test different years
            for year in [2020, 2021, 2022]:
                get_estimates(
                    geography="state", variables="POP", year=year, api_key="test"
                )
                call_args = mock_api.get.call_args[1]
                assert call_args["year"] == year

    @patch("pytidycensus.estimates.CensusAPI")
    @patch("pytidycensus.estimates.get_geography")
    def test_get_estimates_geometry_merge_warning(self, mock_get_geo, mock_api_class):
        """Test warning when geometry merge fails due to missing GEOID."""
        # Mock API response without GEOID
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "POP": "5024279", "state": "01"}
        ]
        mock_api_class.return_value = mock_api

        # Mock geometry data with GEOID
        mock_gdf = gpd.GeoDataFrame(
            {"GEOID": ["01"], "NAME": ["Alabama"], "geometry": [None]}
        )
        mock_get_geo.return_value = mock_gdf

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            # Census data without GEOID
            mock_df = pd.DataFrame(
                {"NAME": ["Alabama"], "POP": [5024279], "state": ["01"]}
            )
            mock_process.return_value = mock_df

            # Should return census data without geometry merge
            result = get_estimates(
                geography="state", variables="POP", geometry=True, api_key="test"
            )

            # Should be the original DataFrame, not merged
            assert "geometry" not in result.columns

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_api_error(self, mock_api_class):
        """Test get_estimates handles API errors properly."""
        mock_api = Mock()
        mock_api.get.side_effect = Exception("API request failed")
        mock_api_class.return_value = mock_api

        with pytest.raises(
            Exception,
            match="Failed to retrieve population estimates: API request failed",
        ):
            get_estimates(geography="state", variables="POP", api_key="test")

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_different_outputs(self, mock_api_class):
        """Test get_estimates with different output formats."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test tidy output
            get_estimates(
                geography="state", variables="POP", output="tidy", api_key="test"
            )
            call_args = mock_process.call_args[0]
            assert "tidy" in call_args

            # Test wide output
            get_estimates(
                geography="state", variables="POP", output="wide", api_key="test"
            )
            call_args = mock_process.call_args[0]
            assert "wide" in call_args

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_default_variables(self, mock_api_class):
        """Test get_estimates with default variables when none provided."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test with no variables (should use default)
            get_estimates(geography="state", api_key="test")

            call_args = mock_api.get.call_args[1]["variables"]
            # Should have some default variable
            assert len(call_args) > 0

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_breakdown_labels(self, mock_api_class):
        """Test get_estimates with breakdown labels."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.estimates.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame()

            # Test with breakdown labels
            get_estimates(
                geography="state",
                variables="POP",
                breakdown=["SEX"],
                breakdown_labels=True,
                api_key="test",
            )

            # Should still work
            mock_api.get.assert_called_once()

    @patch("pytidycensus.estimates.CensusAPI")
    def test_get_estimates_breakdown_labels_processing(self, mock_api_class):
        """Test get_estimates with breakdown labels processing."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        # Create a mock DataFrame with breakdown variables
        mock_df = pd.DataFrame(
            {"SEX": ["1", "2"], "AGEGROUP": ["1", "2"], "POP": [100, 200]}
        )

        with patch("pytidycensus.estimates.process_census_data") as mock_process, patch(
            "pytidycensus.estimates._add_breakdown_labels"
        ) as mock_add_labels:
            mock_process.return_value = mock_df
            mock_add_labels.return_value = mock_df

            # Test with breakdown labels
            get_estimates(
                geography="state",
                variables="POP",
                breakdown=["SEX", "AGEGROUP"],
                breakdown_labels=True,
                api_key="test",
            )

            # Should call _add_breakdown_labels
            mock_add_labels.assert_called_once_with(mock_df, ["SEX", "AGEGROUP"])


class TestGetEstimatesVariables:
    """Test cases for the get_estimates_variables function."""

    @patch("pytidycensus.variables.load_variables")
    def test_get_estimates_variables_default(self, mock_load_vars):
        """Test getting estimates variables with default parameters."""
        mock_df = pd.DataFrame({"name": ["POP"], "label": ["Total population"]})
        mock_load_vars.return_value = mock_df

        result = get_estimates_variables()

        mock_load_vars.assert_called_once_with(2022, "pep", "population")
        assert isinstance(result, pd.DataFrame)

    @patch("pytidycensus.variables.load_variables")
    def test_get_estimates_variables_custom_year(self, mock_load_vars):
        """Test getting estimates variables with custom year."""
        mock_df = pd.DataFrame({"name": ["POP"], "label": ["Total population"]})
        mock_load_vars.return_value = mock_df

        result = get_estimates_variables(year=2020)

        mock_load_vars.assert_called_once_with(2020, "pep", "population")
        assert isinstance(result, pd.DataFrame)

    def test_get_estimates_variables_different_year(self):
        """Test getting estimates variables with different year."""
        with patch("pytidycensus.variables.load_variables") as mock_load_vars:
            mock_df = pd.DataFrame({"name": ["POP"], "label": ["Total population"]})
            mock_load_vars.return_value = mock_df

            result = get_estimates_variables(year=2021)

            mock_load_vars.assert_called_once_with(2021, "pep", "population")
            assert isinstance(result, pd.DataFrame)


class TestAddBreakdownLabels:
    """Test cases for the _add_breakdown_labels function."""

    def test_add_breakdown_labels_sex(self):
        """Test adding labels for SEX breakdown."""
        df = pd.DataFrame({"SEX": ["1", "2"], "POP": [100, 200]})

        result = _add_breakdown_labels(df, ["SEX"])

        assert "SEX_label" in result.columns
        assert result["SEX_label"].tolist() == ["Male", "Female"]

    def test_add_breakdown_labels_agegroup(self):
        """Test adding labels for AGEGROUP breakdown."""
        df = pd.DataFrame({"AGEGROUP": ["1", "2", "18"], "POP": [100, 200, 50]})

        result = _add_breakdown_labels(df, ["AGEGROUP"])

        assert "AGEGROUP_label" in result.columns
        assert result["AGEGROUP_label"].tolist() == [
            "0-4 years",
            "5-9 years",
            "85+ years",
        ]

    def test_add_breakdown_labels_race(self):
        """Test adding labels for RACE breakdown."""
        df = pd.DataFrame({"RACE": ["1", "2", "6"], "POP": [100, 200, 50]})

        result = _add_breakdown_labels(df, ["RACE"])

        assert "RACE_label" in result.columns
        expected = [
            "White alone",
            "Black or African American alone",
            "Two or More Races",
        ]
        assert result["RACE_label"].tolist() == expected

    def test_add_breakdown_labels_hisp(self):
        """Test adding labels for HISP breakdown."""
        df = pd.DataFrame({"HISP": ["1", "2"], "POP": [100, 200]})

        result = _add_breakdown_labels(df, ["HISP"])

        assert "HISP_label" in result.columns
        assert result["HISP_label"].tolist() == [
            "Not Hispanic or Latino",
            "Hispanic or Latino",
        ]

    def test_add_breakdown_labels_multiple(self):
        """Test adding labels for multiple breakdowns."""
        df = pd.DataFrame({"SEX": ["1", "2"], "RACE": ["1", "2"], "POP": [100, 200]})

        result = _add_breakdown_labels(df, ["SEX", "RACE"])

        assert "SEX_label" in result.columns
        assert "RACE_label" in result.columns
        assert result["SEX_label"].tolist() == ["Male", "Female"]
        assert result["RACE_label"].tolist() == [
            "White alone",
            "Black or African American alone",
        ]

    def test_add_breakdown_labels_no_matching_column(self):
        """Test adding labels when breakdown column doesn't exist."""
        df = pd.DataFrame({"OTHER": ["1", "2"], "POP": [100, 200]})

        result = _add_breakdown_labels(df, ["SEX"])

        # Should not add any label columns since SEX column doesn't exist
        assert "SEX_label" not in result.columns
        assert result.equals(df)
