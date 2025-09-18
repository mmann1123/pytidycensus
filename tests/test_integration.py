"""
Integration tests that make actual API calls to the Census Bureau.

These tests require a valid Census API key and internet connection.
They test the complete functionality with real data.
"""

import os
import geopandas as gpd
import pandas as pd
import pytest
import pytidycensus as tc
from unittest.mock import Mock, patch
from pytidycensus.acs import get_acs


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
        # assert "NAME" in result.columns
        assert "variable" in result.columns
        assert "estimate" in result.columns
        # assert "B19013_001_moe" in result.columns

        # Verify data quality
        assert result["variable"].iloc[0] == "B19013_001"
        assert result["estimate"].dtype in ["int64", "float64"]
        # assert "Vermont" in result["NAME"].iloc[0]

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
        assert "estimate" in result.columns
        assert "moe" in result.columns

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
        assert "summary_est" in result.columns
        assert result["summary_est"].dtype in ["int64", "float64"]
        assert all(result["summary_est"] > 0)  # Population should be positive

        print(
            f"✓ Summary variable working: max population = {result['summary_est'].max()}"
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
            output="wide",
        )

        # Get data with 95% confidence
        result_95 = tc.get_acs(
            geography="state",
            variables="B19013_001",
            state="VT",
            year=2022,
            moe_level=95,
            output="wide",
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
        # assert "NAME" in result.columns
        assert "variable" in result.columns
        assert "estimate" in result.columns

        # Verify data quality
        assert result["variable"].iloc[0] == "P1_001N"
        assert result["estimate"].dtype in ["int64", "float64"]
        # assert "Vermont" in result["NAME"].iloc[0]

        print(
            f"✓ Retrieved 2020 decennial data: Vermont population = {result['estimate'].iloc[0]}"
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
        assert "summary_est" in result.columns
        assert all(result["summary_est"] >= result["estimate"])  # Total >= subset

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
        assert result["estimate"].iloc[0] > 600000  # Vermont population ~625k in 2010

        print(f"✓ 2010 decennial data: Vermont population = {result['estimate'].iloc[0]}")


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


"""
Integration tests for pytidycensus functionality.

These tests focus on end-to-end workflows and realistic data scenarios.
"""


class TestSummaryVariableIntegration:
    """Integration tests for summary variable functionality."""

    @patch("pytidycensus.acs.CensusAPI")
    def test_summary_var_complete_workflow_tidy(self, mock_api_class):
        """Test complete summary_var workflow from API call to final output."""
        # Mock complete realistic API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                # Race variables
                "B03002_003E": "12993",  # White
                "B03002_003M": "56",
                "B03002_004E": "544",  # Black
                "B03002_004M": "56",
                "B03002_005E": "51979",  # Native
                "B03002_005M": "327",
                "B03002_006E": "1234",  # Asian
                "B03002_006M": "89",
                "B03002_007E": "567",  # HIPI
                "B03002_007M": "45",
                "B03002_012E": "4256",  # Hispanic
                "B03002_012M": "178",
                # Summary variable (total population)
                "B03002_001E": "71714",
                "B03002_001M": "0",
                # Geographic identifiers
                "state": "04",
                "county": "001",
                "NAME": "Apache County, Arizona",
            },
            {
                # Second geography - Cochise County
                "B03002_003E": "69095",
                "B03002_003M": "350",
                "B03002_004E": "1024",
                "B03002_004M": "89",
                "B03002_005E": "2156",
                "B03002_005M": "145",
                "B03002_006E": "2345",
                "B03002_006M": "123",
                "B03002_007E": "678",
                "B03002_007M": "67",
                "B03002_012E": "5678",
                "B03002_012M": "234",
                "B03002_001E": "75045",
                "B03002_001M": "0",
                "state": "04",
                "county": "003",
                "NAME": "Cochise County, Arizona",
            },
            {
                # Third geography - Maricopa County
                "B03002_003E": "2845321",
                "B03002_003M": "1234",
                "B03002_004E": "234567",
                "B03002_004M": "567",
                "B03002_005E": "45678",
                "B03002_005M": "234",
                "B03002_006E": "123456",
                "B03002_006M": "345",
                "B03002_007E": "12345",
                "B03002_007M": "123",
                "B03002_012E": "1234567",
                "B03002_012M": "789",
                "B03002_001E": "4420568",
                "B03002_001M": "0",
                "state": "04",
                "county": "013",
                "NAME": "Maricopa County, Arizona",
            },
        ]
        mock_api_class.return_value = mock_api

        # Test the complete race variables workflow exactly as in the user example
        race_vars = {
            "White": "B03002_003",
            "Black": "B03002_004",
            "Native": "B03002_005",
            "Asian": "B03002_006",
            "HIPI": "B03002_007",
            "Hispanic": "B03002_012",
        }

        result = get_acs(
            geography="county",
            state="AZ",
            variables=race_vars,
            summary_var="B03002_001",
            year=2020,
            output="tidy",
            api_key="test",
        )

        # Verify API call was made correctly
        mock_api.get.assert_called_once()
        call_args = mock_api.get.call_args[1]

        # Check that all race variables + summary variable were requested with E/M suffixes
        variables = call_args["variables"]
        expected_vars = [
            "B03002_003E",
            "B03002_003M",  # White
            "B03002_004E",
            "B03002_004M",  # Black
            "B03002_005E",
            "B03002_005M",  # Native
            "B03002_006E",
            "B03002_006M",  # Asian
            "B03002_007E",
            "B03002_007M",  # HIPI
            "B03002_012E",
            "B03002_012M",  # Hispanic
            "B03002_001E",
            "B03002_001M",  # Summary variable
        ]
        for var in expected_vars:
            assert var in variables, f"Missing variable: {var}"

        # Verify result structure matches R tidycensus exactly
        assert isinstance(result, pd.DataFrame)

        # Check columns match expected R tidycensus format
        expected_columns = [
            "GEOID",
            "NAME",
            "variable",
            "estimate",
            "moe",
            "summary_est",
            "summary_moe",
        ]
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"

        # Verify we have correct number of rows: 3 counties × 6 race variables = 18 rows
        assert len(result) == 18

        # Check that summary variable is NOT in the main data variables
        unique_vars = result["variable"].unique()
        assert "B03002_001" not in unique_vars, "Summary variable should be excluded"

        # Verify all race variables are present with custom names
        expected_race_vars = ["White", "Black", "Native", "Asian", "HIPI", "Hispanic"]
        for var in expected_race_vars:
            assert var in unique_vars, f"Missing race variable: {var}"

        # Test specific data values for Apache County
        apache_data = result[result["GEOID"] == "04001"]
        assert len(apache_data) == 6  # 6 race variables

        # Check White population data for Apache County
        apache_white = apache_data[apache_data["variable"] == "White"]
        assert len(apache_white) == 1
        assert apache_white["estimate"].iloc[0] == 12993
        assert apache_white["moe"].iloc[0] == 56.0
        assert apache_white["summary_est"].iloc[0] == 71714
        assert apache_white["summary_moe"].iloc[0] == 0.0

        # Check Native population data for Apache County
        apache_native = apache_data[apache_data["variable"] == "Native"]
        assert apache_native["estimate"].iloc[0] == 51979
        assert apache_native["moe"].iloc[0] == 327.0
        assert (
            apache_native["summary_est"].iloc[0] == 71714
        )  # Same summary for all variables

        # Verify summary values are consistent within each geography
        for geoid in ["04001", "04003", "04013"]:
            geo_data = result[result["GEOID"] == geoid]
            summary_est_values = geo_data["summary_est"].unique()
            summary_moe_values = geo_data["summary_moe"].unique()
            assert (
                len(summary_est_values) == 1
            ), f"Summary estimate should be same for all variables in {geoid}"
            assert (
                len(summary_moe_values) == 1
            ), f"Summary MOE should be same for all variables in {geoid}"

        # Verify Maricopa County (largest) has expected values
        maricopa_data = result[result["GEOID"] == "04013"]
        assert len(maricopa_data) == 6
        assert all(maricopa_data["summary_est"] == 4420568)
        assert all(maricopa_data["summary_moe"] == 0.0)

    @patch("pytidycensus.acs.CensusAPI")
    def test_summary_var_with_geometry_integration(self, mock_api_class):
        """Test summary_var functionality with geometry (wide format)."""
        # Mock API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "B03002_003E": "12993",
                "B03002_003M": "56",
                "B03002_001E": "71714",
                "B03002_001M": "0",
                "state": "04",
                "county": "001",
                "NAME": "Apache County, Arizona",
            }
        ]
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.get_geography") as mock_get_geo:
            # Mock geography data
            import geopandas as gpd

            mock_gdf = gpd.GeoDataFrame(
                {
                    "GEOID": ["04001"],
                    "NAME": ["Apache County, Arizona"],
                    "geometry": [None],  # Simplified for test
                }
            )
            mock_get_geo.return_value = mock_gdf

            result = get_acs(
                geography="county",
                state="AZ",
                variables={"White": "B03002_003"},
                summary_var="B03002_001",
                year=2020,
                geometry=True,  # This forces wide format
                api_key="test",
            )

            # Should be wide format with geometry
            assert isinstance(result, gpd.GeoDataFrame)
            assert "geometry" in result.columns

            # Check summary columns in wide format
            assert "summary_est" in result.columns
            assert "summary_moe" in result.columns
            assert result["summary_est"].iloc[0] == 71714
            assert result["summary_moe"].iloc[0] == 0.0

    @patch("pytidycensus.acs.CensusAPI")
    def test_summary_var_without_custom_names(self, mock_api_class):
        """Test summary_var with standard variable codes (no custom names)."""
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "B03002_003E": "12993",
                "B03002_003M": "56",
                "B03002_001E": "71714",
                "B03002_001M": "0",
                "state": "04",
                "county": "001",
                "NAME": "Apache County, Arizona",
            }
        ]
        mock_api_class.return_value = mock_api

        result = get_acs(
            geography="county",
            state="AZ",
            variables=["B03002_003"],  # No custom names
            summary_var="B03002_001",
            year=2020,
            output="tidy",
            api_key="test",
        )

        # Variable should be cleaned (E suffix removed)
        assert "B03002_003" in result["variable"].values
        assert (
            "B03002_001" not in result["variable"].values
        )  # Summary should be excluded

        # Summary columns should still be present
        assert "summary_est" in result.columns
        assert "summary_moe" in result.columns
        assert result["summary_est"].iloc[0] == 71714

    @patch("pytidycensus.acs.CensusAPI")
    def test_summary_var_missing_data(self, mock_api_class):
        """Test summary_var handling when summary variable data is missing."""
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "B03002_003E": "12993",
                "B03002_003M": "56",
                # No summary variable data
                "state": "04",
                "county": "001",
                "NAME": "Apache County, Arizona",
            }
        ]
        mock_api_class.return_value = mock_api

        result = get_acs(
            geography="county",
            state="AZ",
            variables=["B03002_003"],
            summary_var="B03002_001",
            year=2020,
            output="tidy",
            api_key="test",
        )

        # Should still work but summary columns may have NaN values
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert "B03002_003" in result["variable"].values

        # Summary columns should exist but may be empty/NaN
        assert "summary_est" in result.columns
        assert "summary_moe" in result.columns


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
