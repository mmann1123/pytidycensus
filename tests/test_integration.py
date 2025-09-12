"""
Integration tests that make actual API calls to the Census Bureau.

These tests require a valid Census API key and internet connection.
They test the complete functionality with real data.
"""

import os
import sys
from getpass import getpass

import geopandas as gpd
import pandas as pd
import pytest

import pytidycensus as tc


def get_api_key():
    """Get Census API key from environment or user input."""
    api_key = os.environ.get("CENSUS_API_KEY")

    # Check for debug mode
    debug_mode = os.environ.get("INTEGRATION_DEBUG", "").lower() == "true"

    if not api_key:
        print("\n" + "=" * 60)
        print("CENSUS API KEY REQUIRED FOR INTEGRATION TESTS")
        print("=" * 60)
        print("These tests require a valid Census API key to make real API calls.")
        print(
            "You can get a free API key at: https://api.census.gov/data/key_signup.html"
        )
        print()

        if debug_mode:
            print("DEBUG MODE: Using placeholder API key for structural testing")
            api_key = "debug_placeholder_key"
        else:
            try:
                api_key = input(
                    "Please enter your Census API key (or 'skip' to skip tests): "
                ).strip()
                if api_key.lower() == "skip":
                    pytest.skip("Integration tests skipped by user")
                if not api_key:
                    pytest.skip("No API key provided")

            except (KeyboardInterrupt, EOFError):
                pytest.skip("API key input cancelled")

        # Set for the session
        os.environ["CENSUS_API_KEY"] = api_key
        tc.set_census_api_key(api_key)
        print(f"✓ API key set successfully")

    else:
        print(f"✓ Using Census API key from CENSUS_API_KEY environment variable")

    return api_key


@pytest.fixture(scope="session", autouse=True)
def setup_api_key():
    """Setup API key for all integration tests."""
    return get_api_key()


class TestACSIntegration:
    """Integration tests for get_acs with real API calls."""

    def test_basic_acs_call(self, setup_api_key):
        """Test basic ACS data retrieval."""
        result = tc.get_acs(
            geography="state",
            variables="B19013_001",  # Median household income
            state="VT",  # Vermont (small state, fast)
            year=2022,
        )

        # Verify structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "GEOID" in result.columns
        assert "NAME" in result.columns
        assert "variable" in result.columns
        assert "value" in result.columns
        assert "B19013_001_moe" in result.columns

        # Verify data quality
        assert result["variable"].iloc[0] == "B19013_001"
        assert result["value"].dtype in ["int64", "float64"]
        assert "Vermont" in result["NAME"].iloc[0]

        print(f"✓ Retrieved ACS data for {len(result)} Vermont counties")

    def test_acs_named_variables(self, setup_api_key):
        """Test ACS with named variables (dictionary support)."""
        result = tc.get_acs(
            geography="county",
            variables={"median_income": "B19013_001", "total_population": "B01003_001"},
            state="VT",
            year=2022,
            output="tidy",
        )

        # Verify named variables work
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "median_income" in result["variable"].values
        assert "total_population" in result["variable"].values
        assert "B19013_001" not in result["variable"].values  # Should be replaced

        # Verify MOE columns use custom names
        assert "median_income_moe" in result.columns
        assert "total_population_moe" in result.columns

        print(f"✓ Named variables working: {result['variable'].unique()}")

    def test_acs_wide_format(self, setup_api_key):
        """Test ACS with wide output format."""
        result = tc.get_acs(
            geography="county",
            variables={"median_income": "B19013_001", "total_pop": "B01003_001"},
            state="VT",
            year=2022,
            output="wide",
        )

        # Verify wide format structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "median_income" in result.columns
        assert "total_pop" in result.columns
        assert "median_income_moe" in result.columns
        assert "total_pop_moe" in result.columns
        assert "variable" not in result.columns  # Should not exist in wide format

        print(f"✓ Wide format working with columns: {list(result.columns)}")

    def test_acs_summary_variable(self, setup_api_key):
        """Test ACS with summary variable."""
        result = tc.get_acs(
            geography="county",
            variables="B19013_001",  # Median income
            summary_var="B01003_001",  # Total population
            state="VT",
            year=2022,
        )

        # Verify summary variable
        assert isinstance(result, pd.DataFrame)
        assert "summary_value" in result.columns
        assert result["summary_value"].dtype in ["int64", "float64"]
        assert all(result["summary_value"] > 0)  # Population should be positive

        print(
            f"✓ Summary variable working: max population = {result['summary_value'].max()}"
        )

    def test_acs_moe_levels(self, setup_api_key):
        """Test different MOE confidence levels."""
        # Get data with 90% confidence (default)
        result_90 = tc.get_acs(
            geography="state",
            variables="B19013_001",
            state="VT",
            year=2022,
            moe_level=90,
        )

        # Get data with 95% confidence
        result_95 = tc.get_acs(
            geography="state",
            variables="B19013_001",
            state="VT",
            year=2022,
            moe_level=95,
        )

        # 95% MOE should be larger than 90% MOE
        moe_90 = result_90["B19013_001_moe"].iloc[0]
        moe_95 = result_95["B19013_001_moe"].iloc[0]

        assert moe_95 > moe_90
        print(f"✓ MOE levels working: 90% = {moe_90:.0f}, 95% = {moe_95:.0f}")

    def test_acs_table_parameter(self, setup_api_key):
        """Test ACS table parameter."""
        result = tc.get_acs(
            geography="state",
            table="B01003",  # Total population table
            state="VT",
            year=2022,
        )

        # Should get all variables from the table
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert all(var.startswith("B01003_") for var in result["variable"].unique())

        print(
            f"✓ Table parameter working: {len(result['variable'].unique())} variables from B01003"
        )

    @pytest.mark.skipif(
        os.environ.get("SKIP_GEOMETRY_TESTS") == "1",
        reason="Geometry tests skipped (set SKIP_GEOMETRY_TESTS=1)",
    )
    def test_acs_with_geometry(self, setup_api_key):
        """Test ACS with geometry (may take longer)."""
        result = tc.get_acs(
            geography="county",
            variables="B19013_001",
            state="VT",
            year=2022,
            geometry=True,
        )

        # Should return GeoDataFrame
        assert isinstance(result, gpd.GeoDataFrame)
        assert "geometry" in result.columns
        assert len(result) > 0
        assert result.crs is not None

        print(f"✓ Geometry working: {len(result)} counties with {result.crs}")


class TestDecennialIntegration:
    """Integration tests for get_decennial with real API calls."""

    def test_basic_decennial_call(self, setup_api_key):
        """Test basic decennial Census data retrieval."""
        result = tc.get_decennial(
            geography="state",
            variables="P1_001N",  # Total population
            state="VT",
            year=2020,
        )

        # Verify structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "GEOID" in result.columns
        assert "NAME" in result.columns
        assert "variable" in result.columns
        assert "value" in result.columns

        # Verify data quality
        assert result["variable"].iloc[0] == "P1_001N"
        assert result["value"].dtype in ["int64", "float64"]
        assert "Vermont" in result["NAME"].iloc[0]

        print(
            f"✓ Retrieved 2020 decennial data: Vermont population = {result['value'].iloc[0]}"
        )

    def test_decennial_named_variables(self, setup_api_key):
        """Test decennial with named variables."""
        result = tc.get_decennial(
            geography="county",
            variables={"total_pop": "P1_001N", "white_pop": "P1_003N"},
            state="VT",
            year=2020,
        )

        # Verify named variables work
        assert isinstance(result, pd.DataFrame)
        assert "total_pop" in result["variable"].values
        assert "white_pop" in result["variable"].values
        assert "P1_001N" not in result["variable"].values

        print(f"✓ Named variables in decennial: {result['variable'].unique()}")

    def test_decennial_summary_variable(self, setup_api_key):
        """Test decennial with summary variable."""
        result = tc.get_decennial(
            geography="county",
            variables="P1_003N",  # White population
            summary_var="P1_001N",  # Total population
            state="VT",
            year=2020,
        )

        # Verify summary variable
        assert isinstance(result, pd.DataFrame)
        assert "summary_value" in result.columns
        assert all(result["summary_value"] >= result["value"])  # Total >= subset

        print(f"✓ Summary variable in decennial working")

    def test_decennial_wide_format(self, setup_api_key):
        """Test decennial wide format."""
        result = tc.get_decennial(
            geography="county",
            variables={"total": "P1_001N", "white": "P1_003N"},
            state="VT",
            year=2020,
            output="wide",
        )

        # Verify wide format
        assert isinstance(result, pd.DataFrame)
        assert "total" in result.columns
        assert "white" in result.columns
        assert "variable" not in result.columns

        print(f"✓ Decennial wide format working")

    def test_decennial_table_parameter(self, setup_api_key):
        """Test decennial table parameter."""
        result = tc.get_decennial(
            geography="state", table="P1", state="VT", year=2020  # Race table
        )

        # Should get all variables from P1 table
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert all(var.startswith("P1_") for var in result["variable"].unique())

        print(
            f"✓ Decennial table parameter: {len(result['variable'].unique())} variables from P1"
        )

    def test_decennial_2010_data(self, setup_api_key):
        """Test 2010 decennial data."""
        result = tc.get_decennial(
            geography="state",
            variables="P001001",  # 2010 variable format
            state="VT",
            year=2010,
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert result["value"].iloc[0] > 600000  # Vermont population ~625k in 2010

        print(f"✓ 2010 decennial data: Vermont population = {result['value'].iloc[0]}")


class TestEnhancedFeaturesIntegration:
    """Test enhanced features that mirror R tidycensus."""

    def test_survey_messages(self, setup_api_key, capsys):
        """Test that survey-specific messages are displayed."""
        # Test ACS5 message
        tc.get_acs(
            geography="state",
            variables="B19013_001",
            state="VT",
            survey="acs5",
            year=2022,
        )

        captured = capsys.readouterr()
        assert "2018-2022 5-year ACS" in captured.out

        print("✓ Survey messages working")

    def test_geography_aliases(self, setup_api_key):
        """Test geography aliases (cbg, cbsa, zcta)."""
        # Test block group alias
        result = tc.get_acs(
            geography="cbg",  # Should be converted to "block group"
            variables="B19013_001",
            state="VT",
            county="007",  # Chittenden County
            year=2022,
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        print("✓ Geography aliases working (cbg → block group)")

    def test_differential_privacy_warning(self, setup_api_key):
        """Test 2020 differential privacy warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            tc.get_decennial(
                geography="state", variables="P1_001N", state="VT", year=2020
            )

            # Check for differential privacy warning
            dp_warnings = [
                warning
                for warning in w
                if "differential privacy" in str(warning.message)
            ]
            assert len(dp_warnings) > 0

        print("✓ 2020 differential privacy warning working")


# Utility function to run integration tests manually
def run_integration_tests():
    """
    Run integration tests manually (useful for development).
    """
    print("Running pytidycensus integration tests...")
    print("These tests make real API calls to the Census Bureau.")
    print()

    # Get API key
    try:
        get_api_key()
    except Exception as e:
        print(f"Error setting up API key: {e}")
        return

    # Run a few key tests
    print("\n" + "=" * 50)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 50)

    try:
        # Basic ACS test
        print("\n1. Testing basic ACS functionality...")
        result = tc.get_acs(
            geography="state", variables="B19013_001", state="VT", year=2022
        )
        print(f"✓ ACS test passed: {len(result)} records")

        # Basic decennial test
        print("\n2. Testing basic decennial functionality...")
        result = tc.get_decennial(
            geography="state", variables="P1_001N", state="VT", year=2020
        )
        print(
            f"✓ Decennial test passed: Vermont population = {result['value'].iloc[0]}"
        )

        # Named variables test
        print("\n3. Testing named variables...")
        result = tc.get_acs(
            geography="county",
            variables={"income": "B19013_001", "population": "B01003_001"},
            state="VT",
            year=2022,
        )
        print(f"✓ Named variables test passed: {result['variable'].unique()}")

        print("\n" + "=" * 50)
        print("ALL INTEGRATION TESTS PASSED! ✓")
        print("=" * 50)
        print()
        print("The enhanced pytidycensus functions are working correctly")
        print("with real Census Bureau data!")

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        print("\nThis might be due to:")
        print("- Invalid API key")
        print("- Network connectivity issues")
        print("- Census Bureau API being down")
        print("- Rate limiting")


if __name__ == "__main__":
    run_integration_tests()
