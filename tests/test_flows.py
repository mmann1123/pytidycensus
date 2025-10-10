"""Tests for Migration Flows API functionality."""

from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from pytidycensus.flows import (
    _add_flows_geometry,
    _build_geography_clauses,
    _load_migration_recodes,
    _prepare_variables,
    _process_breakdown_variables,
    _transform_flows_output,
    _validate_flows_parameters,
    get_flows,
)


@pytest.fixture
def sample_flows_response():
    """Sample Migration Flows API response for testing."""
    return [
        [
            "GEOID1",
            "GEOID2",
            "FULL1_NAME",
            "FULL2_NAME",
            "MOVEDIN",
            "MOVEDIN_M",
            "MOVEDOUT",
            "MOVEDOUT_M",
        ],
        [
            "48001",
            "48003",
            "Anderson County, Texas",
            "Angelina County, Texas",
            "125",
            "15",
            "98",
            "12",
        ],
        ["48001", "48005", "Anderson County, Texas", "Archer County, Texas", "45", "8", "67", "9"],
        [
            "48003",
            "48001",
            "Angelina County, Texas",
            "Anderson County, Texas",
            "87",
            "11",
            "134",
            "16",
        ],
    ]


@pytest.fixture
def sample_flows_with_breakdown_response():
    """Sample flows response with breakdown variables."""
    return [
        ["GEOID1", "GEOID2", "FULL1_NAME", "FULL2_NAME", "MOVEDIN", "MOVEDIN_M", "AGE", "SEX"],
        [
            "48001",
            "48003",
            "Anderson County, Texas",
            "Angelina County, Texas",
            "125",
            "15",
            "01",
            "1",
        ],
        [
            "48001",
            "48003",
            "Anderson County, Texas",
            "Angelina County, Texas",
            "89",
            "12",
            "02",
            "1",
        ],
        ["48001", "48005", "Anderson County, Texas", "Archer County, Texas", "45", "8", "01", "2"],
    ]


@pytest.fixture
def mock_census_api_key():
    """Provide a mock Census API key for testing."""
    with patch.dict("os.environ", {"CENSUS_API_KEY": "test_api_key_123"}):
        yield "test_api_key_123"


class TestFlowsValidation:
    """Test input validation for get_flows function."""

    def test_invalid_geography(self):
        """Test that invalid geography raises ValueError."""
        with pytest.raises(ValueError, match="Geography must be one of"):
            _validate_flows_parameters("invalid_geo", 2018, None, 90, "tidy")

    def test_year_too_early(self):
        """Test that year before 2010 raises ValueError."""
        with pytest.raises(ValueError, match="Migration flows are available beginning in 2010"):
            _validate_flows_parameters("county", 2009, None, 90, "tidy")

    def test_msa_year_too_early(self):
        """Test that MSA data before 2013 raises ValueError."""
        with pytest.raises(ValueError, match="MSA-level data is only available beginning"):
            _validate_flows_parameters("metropolitan statistical area", 2012, None, 90, "tidy")

    def test_breakdown_after_2015(self):
        """Test that breakdown variables after 2015 raise ValueError."""
        with pytest.raises(ValueError, match="Breakdown characteristics are only available"):
            _validate_flows_parameters("county", 2016, ["AGE"], 90, "tidy")

    def test_invalid_moe_level(self):
        """Test that invalid MOE level raises ValueError."""
        with pytest.raises(ValueError, match="moe_level must be 90, 95, or 99"):
            _validate_flows_parameters("county", 2018, None, 85, "tidy")

    def test_invalid_output(self):
        """Test that invalid output format raises ValueError."""
        with pytest.raises(ValueError, match='output must be "tidy" or "wide"'):
            _validate_flows_parameters("county", 2018, None, 90, "invalid")

    def test_valid_parameters(self):
        """Test that valid parameters pass validation."""
        # Should not raise any exception
        _validate_flows_parameters("county", 2018, None, 90, "tidy")
        _validate_flows_parameters("metropolitan statistical area", 2015, ["AGE"], 95, "wide")


class TestMigrationRecodes:
    """Test migration recode data loading and processing."""

    def test_load_migration_recodes(self):
        """Test loading migration recode CSV file."""
        recodes = _load_migration_recodes()

        assert isinstance(recodes, pd.DataFrame)
        assert len(recodes) > 0
        assert "characteristic" in recodes.columns
        assert "code" in recodes.columns
        assert "desc" in recodes.columns
        assert "ordered" in recodes.columns

        # Test specific characteristics exist
        expected_chars = ["AGE", "SEX", "RACE", "HSGP", "REL"]
        assert all(char in recodes["characteristic"].values for char in expected_chars)

    def test_prepare_variables(self):
        """Test variable preparation logic."""
        recodes = _load_migration_recodes()

        # Test with no additional variables
        vars_list = _prepare_variables(None, None, recodes)
        expected_core = [
            "GEOID1",
            "GEOID2",
            "FULL1_NAME",
            "FULL2_NAME",
            "MOVEDIN",
            "MOVEDIN_M",
            "MOVEDOUT",
            "MOVEDOUT_M",
            "MOVEDNET",
            "MOVEDNET_M",
        ]
        assert all(var in vars_list for var in expected_core)

        # Test with breakdown variables
        vars_list = _prepare_variables(None, ["AGE", "SEX"], recodes)
        assert "AGE" in vars_list
        assert "SEX" in vars_list

        # Test with custom variables
        vars_list = _prepare_variables(["CUSTOM_VAR"], None, recodes)
        assert "CUSTOM_VAR" in vars_list


class TestBreakdownProcessing:
    """Test breakdown variable processing."""

    def test_process_breakdown_variables_padding(self):
        """Test zero-padding of breakdown variable codes."""
        recodes = _load_migration_recodes()

        data = pd.DataFrame({"GEOID1": ["48001", "48003"], "AGE": ["1", "2"], "SEX": ["1", "2"]})

        result = _process_breakdown_variables(data, ["AGE", "SEX"], recodes, breakdown_labels=False)

        # Check zero-padding
        assert result["AGE"].iloc[0] == "01"
        assert result["AGE"].iloc[1] == "02"

    def test_process_breakdown_variables_labels(self):
        """Test breakdown variable label mapping."""
        recodes = _load_migration_recodes()

        data = pd.DataFrame({"GEOID1": ["48001", "48003"], "AGE": ["01", "02"], "SEX": ["1", "2"]})

        result = _process_breakdown_variables(data, ["AGE", "SEX"], recodes, breakdown_labels=True)

        # Check labels are added
        assert "AGE_label" in result.columns
        assert "SEX_label" in result.columns

        # Check specific label mappings
        age_labels = result["AGE_label"].values
        assert "1 to 4 years" in age_labels or "5 to 17 years" in age_labels


class TestDataTransformation:
    """Test data output format transformations."""

    def test_transform_wide_output(self):
        """Test wide format output with MOE adjustment."""
        data = pd.DataFrame(
            {
                "GEOID1": ["48001", "48003"],
                "GEOID2": ["48005", "48007"],
                "MOVEDIN": [100, 200],
                "MOVEDIN_M": [10, 20],
                "MOVEDOUT": [80, 150],
                "MOVEDOUT_M": [8, 15],
            }
        )

        result = _transform_flows_output(data, "wide", 95, ["MOVEDIN", "MOVEDOUT"])

        # Check MOE factor applied (95% confidence = 1.96/1.645)
        expected_factor = 1.96 / 1.645
        assert abs(result["MOVEDIN_M"].iloc[0] - (10 * expected_factor)) < 0.01
        assert abs(result["MOVEDOUT_M"].iloc[0] - (8 * expected_factor)) < 0.01

    def test_transform_tidy_output(self):
        """Test tidy format output transformation."""
        data = pd.DataFrame(
            {
                "GEOID1": ["48001", "48003"],
                "GEOID2": ["48005", "48007"],
                "FULL1_NAME": ["County A", "County B"],
                "MOVEDIN": [100, 200],
                "MOVEDIN_M": [10, 20],
                "MOVEDOUT": [80, 150],
                "MOVEDOUT_M": [8, 15],
            }
        )

        result = _transform_flows_output(data, "tidy", 90, ["MOVEDIN", "MOVEDOUT"])

        # Check structure
        assert "variable" in result.columns
        assert "estimate" in result.columns
        assert "moe" in result.columns

        # Check variables present
        variables = result["variable"].unique()
        assert "MOVEDIN" in variables
        assert "MOVEDOUT" in variables

        # Check that we have the expected number of rows (2 rows * 2 variables = 4 rows)
        assert len(result) == 4

        # Check that breakdown columns are preserved
        assert "GEOID1" in result.columns
        assert "GEOID2" in result.columns
        assert "FULL1_NAME" in result.columns


class TestGeographyClauses:
    """Test geography clause building for API requests."""

    def test_county_geography_clauses(self):
        """Test county geography clause building."""
        # No filtering
        for_clause, in_clause = _build_geography_clauses("county", 2018, None, None, None)
        assert for_clause == "county:*"
        assert in_clause is None

        # State filtering
        for_clause, in_clause = _build_geography_clauses("county", 2018, "TX", None, None)
        assert "state:" in in_clause

        # County and state filtering
        with patch("pytidycensus.flows.validate_county") as mock_validate_county:
            mock_validate_county.return_value = "001"
            for_clause, in_clause = _build_geography_clauses("county", 2018, "TX", "Anderson", None)
            assert "county:" in for_clause

    def test_msa_geography_clauses(self):
        """Test MSA geography clause building."""
        # Test year <= 2015 (different API geography name)
        for_clause, in_clause = _build_geography_clauses(
            "metropolitan statistical area", 2015, None, None, None
        )
        assert "metropolitan statistical areas" in for_clause

        # Test year > 2015
        for_clause, in_clause = _build_geography_clauses(
            "metropolitan statistical area", 2018, None, None, None
        )
        assert "metropolitan statistical area/micropolitan statistical area" in for_clause


class TestGeometryIntegration:
    """Test geometry integration functionality."""

    def test_add_flows_geometry_basic(self):
        """Test basic geometry addition functionality."""
        data = pd.DataFrame(
            {"GEOID1": ["48001", "48003"], "GEOID2": ["48005", "48007"], "MOVEDIN": [100, 200]}
        )

        # Should raise an error when geometry download fails
        with pytest.raises((RuntimeError, ValueError)):
            _add_flows_geometry(data, "county")

    def test_add_flows_geometry_no_geoids(self):
        """Test geometry addition with no GEOID columns."""
        data = pd.DataFrame({"MOVEDIN": [100, 200], "MOVEDOUT": [80, 150]})

        # Should raise an error when no GEOID columns found
        with pytest.raises(ValueError, match="No GEOID columns found"):
            _add_flows_geometry(data, "county")

    def test_add_flows_geometry_unimplemented(self):
        """Test geometry addition for unimplemented geography types."""
        data = pd.DataFrame({"GEOID1": ["12001"], "GEOID2": ["12003"], "MOVEDIN": [100]})

        # Should raise NotImplementedError for county subdivision
        with pytest.raises(NotImplementedError, match="county subdivision"):
            _add_flows_geometry(data, "county subdivision")

        # Should raise NotImplementedError for MSA
        with pytest.raises(NotImplementedError, match="metropolitan statistical area"):
            _add_flows_geometry(data, "metropolitan statistical area")


@pytest.mark.integration
class TestFlowsAPIIntegration:
    """Integration tests that make actual API calls."""

    def test_get_flows_basic_call(self, mock_census_api_key):
        """Test basic get_flows API call with mocked response."""

        with patch("pytidycensus.flows._load_migration_flows") as mock_api_call:
            # Mock API response
            mock_api_call.return_value = pd.DataFrame(
                {
                    "GEOID1": ["48001", "48003"],
                    "GEOID2": ["48005", "48007"],
                    "FULL1_NAME": ["Anderson County, Texas", "Angelina County, Texas"],
                    "FULL2_NAME": ["Archer County, Texas", "Armstrong County, Texas"],
                    "MOVEDIN": [125, 87],
                    "MOVEDIN_M": [15, 11],
                    "MOVEDOUT": [98, 134],
                    "MOVEDOUT_M": [12, 16],
                    "MOVEDNET": [27, -47],
                    "MOVEDNET_M": [19, 20],
                }
            )

            result = get_flows(geography="county", state="TX", year=2018, output="wide")

            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
            assert "GEOID1" in result.columns
            assert "GEOID2" in result.columns
            assert "MOVEDIN" in result.columns

    def test_get_flows_with_breakdown(self, mock_census_api_key):
        """Test get_flows with breakdown variables."""

        with patch("pytidycensus.flows._load_migration_flows") as mock_api_call:
            # Mock API response with breakdown
            mock_api_call.return_value = pd.DataFrame(
                {
                    "GEOID1": ["48001", "48001"],
                    "GEOID2": ["48003", "48003"],
                    "FULL1_NAME": ["Anderson County, Texas", "Anderson County, Texas"],
                    "FULL2_NAME": ["Angelina County, Texas", "Angelina County, Texas"],
                    "MOVEDIN": [125, 89],
                    "MOVEDIN_M": [15, 12],
                    "AGE": ["1", "2"],
                    "SEX": ["1", "1"],
                }
            )

            result = get_flows(
                geography="county",
                breakdown=["AGE", "SEX"],
                breakdown_labels=True,
                state="TX",
                year=2015,  # Breakdown only available before 2016
                output="tidy",
            )

            assert isinstance(result, pd.DataFrame)
            assert "AGE_label" in result.columns
            assert "SEX_label" in result.columns

    def test_get_flows_with_geometry(self, mock_census_api_key):
        """Test get_flows with geometry=True."""

        with patch("pytidycensus.flows._load_migration_flows") as mock_api_call:
            mock_api_call.return_value = pd.DataFrame(
                {"GEOID1": ["48001"], "GEOID2": ["48003"], "MOVEDIN": [125], "MOVEDIN_M": [15]}
            )

            result = get_flows(geography="county", state="TX", year=2018, geometry=True)

            # Should return a DataFrame (might be GeoDataFrame if geometry works)
            assert isinstance(result, pd.DataFrame)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_missing_api_key(self):
        """Test behavior when no API key is provided."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Census API key is required"):
                get_flows(geography="county", year=2018)

    def test_invalid_state_county_combination(self):
        """Test invalid state/county combinations."""
        # This would be caught during validation or API call
        with patch("pytidycensus.flows._load_migration_flows") as mock_api_call:
            mock_api_call.side_effect = ValueError("Invalid geography combination")

            with pytest.raises(ValueError):
                get_flows(
                    geography="county",
                    state="InvalidState",
                    county="InvalidCounty",
                    year=2018,
                    api_key="test_key",
                )


if __name__ == "__main__":
    pytest.main([__file__])
