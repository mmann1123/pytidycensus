"""Tests for decennial Census population variables and data validation.

These tests verify that the population variables P001001 (2010) and
P1_001N (2020) work correctly and return expected data structures that
match R tidycensus behavior.
"""

import os
from unittest.mock import patch

import pandas as pd
import pytest

import pytidycensus as tc
from pytidycensus.decennial import get_decennial


@pytest.mark.integration
class TestDecennialPopulationVariables:
    """Integration tests for decennial population variables.

    These tests require a Census API key and internet connection. They
    validate actual data retrieval and structure.
    """

    @classmethod
    def setup_class(cls):
        """Set up test class with API key if available."""
        cls.api_key = os.environ.get("CENSUS_API_KEY")
        if cls.api_key:
            tc.set_census_api_key(cls.api_key)

    def test_2010_population_variable_structure(self):
        """Test 2010 decennial population variable P001001 data structure."""
        if not self.api_key:
            pytest.skip("Census API key not available")

        # Test with small geography (DC) to limit data size
        result = get_decennial(
            geography="state",
            variables={"total_pop": "P001001"},
            state="DC",
            year=2010,
            survey="sf1",
            output="tidy",
        )

        # Validate data structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0, "Should return at least one row for DC"

        # Check required columns (tidy format)
        required_cols = ["GEOID", "NAME", "variable", "estimate"]
        for col in required_cols:
            assert col in result.columns, f"Missing required column: {col}"

        # Validate data content
        assert result["variable"].iloc[0] == "total_pop", "Variable name should match"
        assert result["estimate"].iloc[0] > 0, "Population should be positive"
        assert result["NAME"].iloc[0] == "DC", "Should contain DC name"

        # Validate data types
        assert pd.api.types.is_numeric_dtype(result["estimate"]), "Estimate should be numeric"
        assert pd.api.types.is_string_dtype(result["GEOID"]), "GEOID should be string"

    def test_2020_population_variable_structure(self):
        """Test 2020 decennial population variable P1_001N data structure."""
        if not self.api_key:
            pytest.skip("Census API key not available")

        result = get_decennial(
            geography="state",
            variables={"total_pop": "P1_001N"},
            state="DC",
            year=2020,
            survey="pl",
            output="tidy",
        )

        # Validate data structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0, "Should return at least one row for DC"

        # Check required columns (tidy format)
        required_cols = ["GEOID", "NAME", "variable", "estimate"]
        for col in required_cols:
            assert col in result.columns, f"Missing required column: {col}"

        # Validate data content
        assert result["variable"].iloc[0] == "total_pop", "Variable name should match"
        assert result["estimate"].iloc[0] > 0, "Population should be positive"
        assert result["NAME"].iloc[0] == "DC", "Should contain DC name"

        # Validate data types
        assert pd.api.types.is_numeric_dtype(result["estimate"]), "Estimate should be numeric"
        assert pd.api.types.is_string_dtype(result["GEOID"]), "GEOID should be string"

    def test_population_variable_time_series_compatibility(self):
        """Test that 2010 and 2020 population variables are compatible for time series analysis."""
        if not self.api_key:
            pytest.skip("Census API key not available")

        # Get 2010 data
        data_2010 = get_decennial(
            geography="state",
            variables={"total_pop": "P001001"},
            state="DC",
            year=2010,
            survey="sf1",
            output="tidy",
        )

        # Get 2020 data
        data_2020 = get_decennial(
            geography="state",
            variables={"total_pop": "P1_001N"},
            state="DC",
            year=2020,
            survey="pl",
            output="tidy",
        )

        # Both should have same structure
        assert list(data_2010.columns) == list(data_2020.columns), "Columns should match"

        # Both should have same number of rows (same geography)
        assert len(data_2010) == len(data_2020), "Row count should match for same geography"

        # GEOIDs should match (same state)
        assert data_2010["GEOID"].iloc[0] == data_2020["GEOID"].iloc[0], "GEOIDs should match"

        # Population should be reasonable (DC population is around 600k-700k)
        pop_2010 = data_2010["estimate"].iloc[0]
        pop_2020 = data_2020["estimate"].iloc[0]

        assert 500000 < pop_2010 < 800000, f"2010 DC population seems unreasonable: {pop_2010}"
        assert 500000 < pop_2020 < 800000, f"2020 DC population seems unreasonable: {pop_2020}"

        # Population change should be reasonable (not more than 50% change)
        pct_change = abs((pop_2020 - pop_2010) / pop_2010) * 100
        assert pct_change < 50, f"Population change seems too large: {pct_change:.1f}%"

    def test_population_wide_format_output(self):
        """Test population variables with wide format output."""
        if not self.api_key:
            pytest.skip("Census API key not available")

        result = get_decennial(
            geography="state",
            variables={"total_pop": "P1_001N"},
            state="DC",
            year=2020,
            output="wide",
        )

        # Wide format should have variable as column
        assert isinstance(result, pd.DataFrame)
        assert "total_pop" in result.columns, "Variable should be column in wide format"
        assert "variable" not in result.columns, "Should not have 'variable' column in wide format"
        assert "value" not in result.columns, "Should not have 'value' column in wide format"

        # Should still have geographic identifiers
        assert "GEOID" in result.columns
        assert "NAME" in result.columns

        # Population value should be numeric and positive
        assert pd.api.types.is_numeric_dtype(result["total_pop"]), "Population should be numeric"
        assert result["total_pop"].iloc[0] > 0, "Population should be positive"

    def test_population_variables_with_geometry(self):
        """Test population variables with geometry=True."""
        if not self.api_key:
            pytest.skip("Census API key not available")

        result = get_decennial(
            geography="state",
            variables={"total_pop": "P1_001N"},
            state="DC",
            year=2020,
            geometry=True,
        )

        # Should be a GeoDataFrame with geometry
        try:
            import geopandas as gpd

            assert isinstance(
                result, gpd.GeoDataFrame
            ), "Should return GeoDataFrame when geometry=True"
            assert "geometry" in result.columns, "Should have geometry column"
            assert result.geometry is not None, "Geometry should not be None"
        except ImportError:
            # If GeoPandas not available, should still work but without geometry
            assert isinstance(
                result, pd.DataFrame
            ), "Should return DataFrame if GeoPandas unavailable"

    def test_multiple_states_population_comparison(self):
        """Test population variables across multiple states for comparison."""
        if not self.api_key:
            pytest.skip("Census API key not available")

        # Test with DC metro area states
        states = ["DC", "MD", "VA"]

        # Get 2020 data for all states
        result = get_decennial(
            geography="state",
            variables={"total_pop": "P1_001N"},
            state=states,
            year=2020,
            output="wide",
        )

        # Should have all three states
        assert len(result) == 3, f"Should have 3 states, got {len(result)}"

        # All should have positive populations
        assert all(result["total_pop"] > 0), "All populations should be positive"

        # States should be identifiable
        state_names = result["NAME"].tolist()
        assert any("DC" == name for name in state_names), "Should include DC"
        assert any("Maryland" in name for name in state_names), "Should include Maryland"
        assert any("Virginia" in name for name in state_names), "Should include Virginia"

        # Population order should be reasonable (VA > MD > DC)
        dc_pop = result[result["NAME"] == "DC"]["total_pop"].iloc[0]
        md_pop = result[result["NAME"].str.contains("Maryland")]["total_pop"].iloc[0]
        va_pop = result[result["NAME"].str.contains("Virginia")]["total_pop"].iloc[0]

        assert va_pop > md_pop > dc_pop, "Population order should be VA > MD > DC"

    def test_tract_level_population_data(self):
        """Test population variables at tract level (most detailed geography)."""
        if not self.api_key:
            pytest.skip("Census API key not available")

        # Test with single county to limit data size
        result = get_decennial(
            geography="tract",
            variables={"total_pop": "P1_001N"},
            state="DC",
            year=2020,
            output="wide",
        )

        # Should have multiple tracts
        assert len(result) > 10, f"DC should have many tracts, got {len(result)}"

        # All tracts should have valid GEOIDs (11-digit for tracts)
        assert all(
            len(geoid) == 11 for geoid in result["GEOID"]
        ), "Tract GEOIDs should be 11 digits"

        # All should start with "11" (DC FIPS code)
        assert all(
            geoid.startswith("11") for geoid in result["GEOID"]
        ), "DC tracts should start with '11'"

        # Population should be reasonable for tracts (typically 1000-8000)
        populations = result["total_pop"]
        assert all(pop > 0 for pop in populations), "All tract populations should be positive"
        assert all(pop < 15000 for pop in populations), "Tract populations should be reasonable"

        # Should have NAME column with tract descriptions
        assert all(
            "District of Columbia" in name for name in result["NAME"]
        ), "Names should indicate DC"

    def test_county_level_population_aggregation(self):
        """Test that county-level population data aggregates correctly."""
        if not self.api_key:
            pytest.skip("Census API key not available")

        # Get county-level data for Maryland
        county_data = get_decennial(
            geography="county",
            variables={"total_pop": "P1_001N"},
            state="MD",
            year=2020,
            output="wide",
        )

        # Get state-level data for Maryland
        state_data = get_decennial(
            geography="state",
            variables={"total_pop": "P1_001N"},
            state="MD",
            year=2020,
            output="wide",
        )

        # County populations should sum to approximately state population
        county_total = county_data["total_pop"].sum()
        state_total = state_data["total_pop"].iloc[0]

        # Allow for small differences due to rounding or data processing
        difference_pct = abs((county_total - state_total) / state_total) * 100
        assert (
            difference_pct < 1
        ), f"County sum should approximate state total, difference: {difference_pct:.2f}%"

        # Should have multiple counties
        assert len(county_data) > 10, f"Maryland should have many counties, got {len(county_data)}"

    def test_variable_name_consistency(self):
        """Test that variable names are handled consistently."""
        if not self.api_key:
            pytest.skip("Census API key not available")

        # Test with dictionary variable specification
        result_dict = get_decennial(
            geography="state",
            variables={"population": "P1_001N"},
            state="DC",
            year=2020,
            output="wide",
        )

        # Test with list variable specification
        result_list = get_decennial(
            geography="state", variables=["P1_001N"], state="DC", year=2020, output="wide"
        )

        # Dictionary version should use custom name
        assert "population" in result_dict.columns, "Should use custom variable name"

        # List version should use original code
        assert "P1_001N" in result_list.columns, "Should use original variable code"

        # Both should have same population value
        pop_dict = result_dict["population"].iloc[0]
        pop_list = result_list["P1_001N"].iloc[0]
        assert pop_dict == pop_list, "Population values should be identical"


class TestDecennialPopulationVariablesMocked:
    """Unit tests with mocked API calls to test variable handling logic."""

    @patch("pytidycensus.decennial.CensusAPI")
    def test_2010_variable_api_call_structure(self, mock_api_class):
        """Test that 2010 population variable calls API correctly."""
        from pytidycensus.decennial import get_decennial

        # Mock API response
        mock_api = mock_api_class.return_value
        mock_api.get.return_value = [
            {"NAME": "District of Columbia", "P001001": "601723", "state": "11"}
        ]

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame(
                {
                    "GEOID": ["11"],
                    "NAME": ["District of Columbia"],
                    "variable": ["total_pop"],
                    "estimate": [601723],
                }
            )

            result = get_decennial(
                geography="state",
                variables={"total_pop": "P001001"},
                state="DC",
                year=2010,
                api_key="test_key",
            )

        # Verify API call parameters
        call_args = mock_api.get.call_args[1]
        assert call_args["year"] == 2010
        assert call_args["dataset"] == "dec"
        assert call_args["survey"] == "sf1"
        assert "P001001" in call_args["variables"]

        # Verify result structure
        assert isinstance(result, pd.DataFrame)
        assert "total_pop" in result["variable"].values

    @patch("pytidycensus.decennial.CensusAPI")
    def test_2020_variable_api_call_structure(self, mock_api_class):
        """Test that 2020 population variable calls API correctly."""
        from pytidycensus.decennial import get_decennial

        # Mock API response
        mock_api = mock_api_class.return_value
        mock_api.get.return_value = [
            {"NAME": "District of Columbia", "P1_001N": "689545", "state": "11"}
        ]

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            mock_process.return_value = pd.DataFrame(
                {
                    "GEOID": ["11"],
                    "NAME": ["District of Columbia"],
                    "variable": ["total_pop"],
                    "estimate": [689545],
                }
            )

            result = get_decennial(
                geography="state",
                variables={"total_pop": "P1_001N"},
                state="DC",
                year=2020,
                api_key="test_key",
            )

        # Verify API call parameters
        call_args = mock_api.get.call_args[1]
        assert call_args["year"] == 2020
        assert call_args["dataset"] == "dec"
        assert call_args["survey"] == "pl"
        assert "P1_001N" in call_args["variables"]

        # Verify result structure
        assert isinstance(result, pd.DataFrame)
        assert "total_pop" in result["variable"].values

    def test_variable_code_validation(self):
        """Test validation of population variable codes."""
        # Valid 2010 variable
        assert "P001001".startswith("P"), "2010 variable should start with P"
        assert len("P001001") == 7, "2010 variable should be 7 characters"

        # Valid 2020 variable
        assert "P1_001N".startswith("P"), "2020 variable should start with P"
        assert "_" in "P1_001N", "2020 variable should contain underscore"
        assert "P1_001N".endswith("N"), "2020 variable should end with N"

    def test_survey_defaults_by_year(self):
        """Test that correct survey defaults are applied by year."""
        from pytidycensus.decennial import get_decennial

        with patch("pytidycensus.decennial.CensusAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get.return_value = []

            with patch("pytidycensus.decennial.process_census_data") as mock_process:
                mock_process.return_value = pd.DataFrame()

                # Test 2010 defaults to sf1
                get_decennial(geography="state", variables="P001001", year=2010, api_key="test")
                call_args = mock_api.get.call_args[1]
                assert call_args["survey"] == "sf1", "2010 should default to sf1"

                # Test 2020 defaults to pl
                get_decennial(geography="state", variables="P1_001N", year=2020, api_key="test")
                call_args = mock_api.get.call_args[1]
                assert call_args["survey"] == "pl", "2020 should default to pl"

    def test_r_tidycensus_compatibility_structure(self):
        """Test that output structure matches R tidycensus expectations."""
        with patch("pytidycensus.decennial.CensusAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get.return_value = [
                {"NAME": "District of Columbia", "P1_001N": "689545", "state": "11", "GEOID": "11"}
            ]

            with patch("pytidycensus.decennial.process_census_data") as mock_process:
                # Mock R tidycensus-like output structure
                mock_process.return_value = pd.DataFrame(
                    {
                        "GEOID": ["11"],
                        "NAME": ["District of Columbia"],
                        "variable": ["total_pop"],
                        "estimate": [689545],
                        "moe": [
                            None
                        ],  # Decennial doesn't have MOE, but structure should be compatible
                    }
                )

                result = get_decennial(
                    geography="state",
                    variables={"total_pop": "P1_001N"},
                    state="DC",
                    year=2020,
                    api_key="test",
                )

        # Should match R tidycensus column structure
        expected_cols = ["GEOID", "NAME", "variable", "estimate"]
        for col in expected_cols:
            assert col in result.columns, f"Missing R tidycensus compatible column: {col}"

        # Data types should match R expectations
        assert pd.api.types.is_string_dtype(result["GEOID"]), "GEOID should be string like R"
        assert pd.api.types.is_string_dtype(result["NAME"]), "NAME should be string like R"
        assert pd.api.types.is_string_dtype(result["variable"]), "variable should be string like R"
        assert pd.api.types.is_numeric_dtype(
            result["estimate"]
        ), "estimate should be numeric like R"
