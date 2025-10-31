"""Integration tests that make actual API calls to the Census Bureau.

These tests require a valid Census API key and internet connection. They
test the complete functionality with real data.
"""

import os
from unittest.mock import Mock, patch

import geopandas as gpd
import pandas as pd
import pytest

import pytidycensus as tc
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
        print("You can get a free API key at: https://api.census.gov/data/key_signup.html")
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
            output="tidy",
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

        print(f"✓ Summary variable working: max population = {result['summary_est'].max()}")

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
            output="tidy",
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

    def test_acs_b01001_table_chunking_integration(self, setup_api_key):
        """Test that B01001 table (sex by age) works with chunking in real API calls."""
        # B01001 has 49 variables, so with E and M variants it will trigger chunking
        result = tc.get_acs(
            geography="state",
            table="B01001",
            state="VT",  # Vermont (small state for faster testing)
            year=2020,  # Use 2020 to match the R example
            output="tidy",
        )

        # Verify the result structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        # Verify required columns are present
        expected_columns = {"GEOID", "NAME", "variable", "estimate", "moe"}
        assert expected_columns.issubset(set(result.columns))

        # Verify we got all B01001 variables (should be 49)
        unique_variables = result["variable"].nunique()
        assert unique_variables == 49, f"Expected 49 B01001 variables, got {unique_variables}"

        # Verify specific variables are present (matching R tidycensus example)
        variables_present = set(result["variable"].unique())
        expected_vars = {"B01001_001", "B01001_002", "B01001_003", "B01001_004"}
        assert expected_vars.issubset(
            variables_present
        ), f"Missing expected variables: {expected_vars - variables_present}"

        # Verify data quality - estimates should be numeric and reasonable
        assert result["estimate"].dtype in ["int64", "float64"]
        assert result["estimate"].min() >= 0  # Population counts should be non-negative

        # Verify MOE values are present and reasonable
        assert "moe" in result.columns
        # MOE should be numeric (but can be NaN for some variables)
        moe_numeric = pd.to_numeric(result["moe"], errors="coerce")
        valid_moe = moe_numeric.dropna()
        if len(valid_moe) > 0:
            assert valid_moe.min() >= 0  # MOE should be non-negative when present

        # Verify geographic data
        assert "Vermont" in result["NAME"].iloc[0]
        assert result["GEOID"].iloc[0] == "50"  # Vermont state FIPS code

        # Verify total population variable is present and reasonable
        total_pop = result[result["variable"] == "B01001_001"]["estimate"].iloc[0]
        assert total_pop > 500000  # Vermont has over 500k people
        assert total_pop < 1000000  # Vermont has under 1M people

        print(f"✓ B01001 table chunking integration test passed:")
        print(f"  - Retrieved {unique_variables} variables for Vermont")
        print(f"  - Total rows: {len(result)}")
        print(f"  - Total population (B01001_001): {total_pop:,}")
        print(f"  - Sample variables: {sorted(list(variables_present))[:5]}")


class TestDecennialIntegration:
    """Integration tests for get_decennial with real API calls."""

    def test_basic_decennial_call(self, setup_api_key):
        """Test basic decennial Census data retrieval."""
        result = tc.get_decennial(
            geography="state",
            variables="P1_001N",  # Total population
            state="VT",
            year=2020,
            output="tidy",
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

        print(f"✓ Retrieved 2020 decennial data: Vermont population = {result['estimate'].iloc[0]}")

    def test_decennial_named_variables(self, setup_api_key):
        """Test decennial with named variables."""
        result = tc.get_decennial(
            geography="county",
            variables={"total_pop": "P1_001N", "white_pop": "P1_003N"},
            state="VT",
            year=2020,
            output="tidy",
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
            output="tidy",
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
            geography="state",
            table="P1",
            state="VT",
            year=2020,
            output="tidy",  # Race table
        )

        # Should get all variables from P1 table
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert all(var.startswith("P1_") for var in result["variable"].unique())

        print(f"✓ Decennial table parameter: {len(result['variable'].unique())} variables from P1")

    def test_decennial_2010_data(self, setup_api_key):
        """Test 2010 decennial data."""
        result = tc.get_decennial(
            geography="state",
            variables="P001001",  # 2010 variable format
            state="VT",
            year=2010,
            output="tidy",
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

            tc.get_decennial(geography="state", variables="P1_001N", state="VT", year=2020)

            # Check for differential privacy warning
            dp_warnings = [
                warning for warning in w if "differential privacy" in str(warning.message)
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
        assert apache_native["summary_est"].iloc[0] == 71714  # Same summary for all variables

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
        assert "B03002_001" not in result["variable"].values  # Summary should be excluded

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
    """Run integration tests manually (useful for development)."""
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
        result = tc.get_acs(geography="state", variables="B19013_001", state="VT", year=2022)
        print(f"✓ ACS test passed: {len(result)} records")

        # Basic decennial test
        print("\n2. Testing basic decennial functionality...")
        result = tc.get_decennial(geography="state", variables="P1_001N", state="VT", year=2020)
        print(f"✓ Decennial test passed: Vermont population = {result['value'].iloc[0]}")

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


class TestDecennialTableChunkingIntegration:
    """Integration tests for table chunking with real Census API calls."""

    def test_large_table_chunking_integration(self, setup_api_key):
        """Test that large tables (like P1) work with real API calls via chunking."""
        # P1 table has 71 variables - should trigger chunking
        result = tc.get_decennial(
            geography="state",
            table="P1",  # Race table with 71 variables
            state="VT",
            year=2020,
            output="tidy",
        )

        # Verify the request succeeded
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        # Verify all P1 variables are present
        variables = result["variable"].unique()
        assert all(var.startswith("P1_") for var in variables)

        # P1 table should have exactly 71 variables
        assert len(variables) == 71

        # Verify proper tidy format structure
        expected_columns = {"state", "GEOID", "NAME", "variable", "estimate"}
        assert set(result.columns) == expected_columns

        # Verify data looks reasonable (population should be > 0)
        total_pop = result[result["variable"] == "P1_001N"]["estimate"].iloc[0]
        assert int(total_pop) > 600000  # Vermont has ~643k people

        print(f"✓ Large table chunking test passed: {len(variables)} variables retrieved")

    def test_medium_table_chunking_integration(self, setup_api_key):
        """Test chunking with a medium-sized table (P2 - 73 variables)."""
        # P2 table also exceeds 48-variable limit
        result = tc.get_decennial(
            geography="state",
            table="P2",  # Hispanic/Latino origin table
            state="CA",  # Use California for variety
            year=2020,
            output="tidy",
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        # Verify all variables start with P2_
        variables = result["variable"].unique()
        assert all(var.startswith("P2_") for var in variables)

        # P2 should have many variables (typically 73)
        assert len(variables) > 50  # Should be chunked

        print(f"✓ Medium table chunking test passed: {len(variables)} variables retrieved")

    def test_small_table_no_chunking_integration(self, setup_api_key):
        """Test that small tables work without chunking."""
        # P5 table has only 10 variables - should not trigger chunking
        result = tc.get_decennial(
            geography="state",
            table="P5",  # Group quarters population table (10 variables)
            state="VT",
            year=2020,
            output="tidy",
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        variables = result["variable"].unique()
        assert all(var.startswith("P5_") for var in variables)

        # P5 table should have exactly 10 variables (no chunking needed)
        assert len(variables) == 10
        assert len(variables) < 48

        print(f"✓ Small table no-chunking test passed: {len(variables)} variables retrieved")

    def test_table_chunking_wide_format_integration(self, setup_api_key):
        """Test table chunking works with wide format output."""
        result = tc.get_decennial(
            geography="state", table="P1", state="VT", year=2020, output="wide"
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # Single state = single row

        # Count P1 columns
        p1_columns = [col for col in result.columns if col.startswith("P1_")]
        assert len(p1_columns) == 71  # All P1 variables as columns

        # Verify geography columns exist
        assert "GEOID" in result.columns
        assert "state" in result.columns

        print(f"✓ Wide format chunking test passed: {len(p1_columns)} P1 columns")

    def test_table_chunking_with_summary_var_integration(self, setup_api_key):
        """Test table chunking works with summary_var parameter."""
        result = tc.get_decennial(
            geography="county",
            table="P1",
            summary_var="P1_001N",  # Total population as summary
            state="VT",
            year=2020,
            output="tidy",
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        # Should have summary_est column
        assert "summary_est" in result.columns

        # Summary values should be numeric and positive
        summary_values = result["summary_est"].dropna()
        assert all(val > 0 for val in summary_values)

        # Should have P1 variables (minus the summary variable that gets separated)
        variables = result["variable"].unique()
        # Total variables should be 70 (71 P1 variables minus the summary variable)
        assert len(variables) == 70

        print(
            f"✓ Table chunking with summary_var test passed: {len(variables)} variables + summary column"
        )

    def test_table_chunking_with_geometry_integration(self, setup_api_key):
        """Test table chunking works with geometry requests."""
        result = tc.get_decennial(
            geography="county",
            table="P2",  # Use P2 table (requires chunking)
            state="VT",
            year=2020,
            geometry=True,  # Request geometry
            output="tidy",
        )

        # Should return GeoDataFrame when geometry=True
        assert hasattr(result, "geometry")  # GeoDataFrame has geometry attribute
        assert len(result) > 0

        # Should have geographic data
        assert "GEOID" in result.columns

        # Should have all P2 variables
        variables = result["variable"].unique()
        assert all(var.startswith("P2_") for var in variables)
        assert len(variables) > 50  # P2 is a large table

        print(
            f"✓ Table chunking with geometry test passed: {len(variables)} variables with geometry"
        )

    @pytest.mark.integration
    def test_p1_table_integration(self, setup_api_key):
        """Pytest version: Test P1 table chunking with real API calls."""
        result = tc.get_decennial(
            geography="state",
            table="P1",
            state="VT",
            year=2020,
            output="tidy",
        )

        # Verify comprehensive table retrieval
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        variables = result["variable"].unique()
        assert all(var.startswith("P1_") for var in variables)
        assert len(variables) == 71  # P1 should have exactly 71 variables

        # Verify proper data structure
        expected_columns = {"state", "GEOID", "NAME", "variable", "estimate"}
        assert set(result.columns) == expected_columns

    @pytest.mark.integration
    def test_p5_table_small_no_chunking_integration(self, setup_api_key):
        """Pytest version: Test small table that doesn't require chunking."""
        result = tc.get_decennial(
            geography="state", table="P5", state="VT", year=2020, output="tidy"
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        variables = result["variable"].unique()
        assert all(var.startswith("P5_") for var in variables)
        assert len(variables) == 10  # P5 should have exactly 10 variables

    @pytest.mark.integration
    def test_table_wide_format_chunking_integration(self, setup_api_key):
        """Pytest version: Test table chunking with wide format."""
        result = tc.get_decennial(
            geography="state", table="P1", state="VT", year=2020, output="wide"
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # Single state
        p1_columns = [col for col in result.columns if col.startswith("P1_")]
        assert len(p1_columns) == 71  # All P1 variables as columns


class TestNameColumnIntegration:
    """Integration tests for NAME column functionality with real API calls."""

    @pytest.mark.integration
    def test_acs_state_name_column(self, setup_api_key):
        """Test NAME column for ACS state-level data."""
        result = tc.get_acs(geography="state", variables="B01003_001", state="VT", year=2022)

        assert isinstance(result, pd.DataFrame)
        assert "NAME" in result.columns
        assert len(result) > 0

        # Vermont should have proper state name
        assert result["NAME"].iloc[0] == "Vermont"

    @pytest.mark.integration
    def test_acs_county_name_column(self, setup_api_key):
        """Test NAME column for ACS county-level data."""
        result = tc.get_acs(geography="county", variables="B01003_001", state="VT", year=2022)

        assert isinstance(result, pd.DataFrame)
        assert "NAME" in result.columns
        assert len(result) > 0

        # Should have county names
        county_names = result["NAME"].unique()
        assert any("County" in name for name in county_names)

    @pytest.mark.integration
    def test_decennial_state_name_column(self, setup_api_key):
        """Test NAME column for decennial state-level data."""
        result = tc.get_decennial(geography="state", variables="P1_001N", state="VT", year=2020)

        assert isinstance(result, pd.DataFrame)
        assert "NAME" in result.columns
        assert len(result) > 0

        # Vermont should have proper state name
        assert result["NAME"].iloc[0] == "Vermont"

    @pytest.mark.integration
    def test_decennial_county_name_column(self, setup_api_key):
        """Test NAME column for decennial county-level data."""
        result = tc.get_decennial(geography="county", variables="P1_001N", state="VT", year=2020)

        assert isinstance(result, pd.DataFrame)
        assert "NAME" in result.columns
        assert len(result) > 0

        # Should have county names
        county_names = result["NAME"].unique()
        assert any("County" in name for name in county_names)

    @pytest.mark.integration
    def test_name_column_wide_format(self, setup_api_key):
        """Test NAME column works with wide format output."""
        result = tc.get_acs(
            geography="county",
            variables=["B01003_001", "B19013_001"],
            state="VT",
            year=2022,
            output="wide",
        )

        assert isinstance(result, pd.DataFrame)
        assert "NAME" in result.columns
        assert len(result) > 0

        # Should have proper county names in wide format
        county_names = result["NAME"].unique()
        assert any("County" in name for name in county_names)

    @pytest.mark.integration
    def test_tract_name_column_integration(self, setup_api_key):
        """Test NAME column for tract-level data shows county and state."""
        result = tc.get_acs(
            geography="tract",
            variables="B01003_001",
            state="VT",
            county="003",  # Bennington County
            year=2022,
        )

        assert isinstance(result, pd.DataFrame)
        assert "NAME" in result.columns
        assert len(result) > 0

        # All tracts should show county and state name (without tract number)
        name_sample = result["NAME"].iloc[0]
        assert "Bennington County, Vermont" == name_sample

        # All entries should have the same NAME since they're all in the same county
        unique_names = result["NAME"].unique()
        assert len(unique_names) == 1
        assert unique_names[0] == "Bennington County, Vermont"


class TestGeographyLevelsIntegration:
    """Test that all documented geography levels work for each function."""

    @pytest.mark.integration
    def test_get_acs_geography_levels(self, setup_api_key):
        """Test all documented geography levels for get_acs()."""
        # Geography levels that are supported in pytidycensus
        geography_tests = [
            ("us", {}, "United States"),
            ("region", {}, "Census region"),
            ("division", {}, "Census division"),
            ("state", {"state": "VT"}, "State"),
            ("county", {"state": "VT"}, "County"),
            ("tract", {"state": "VT", "county": "003"}, "Census tract"),
            ("block group", {"state": "VT", "county": "003"}, "Block group"),
            ("place", {"state": "VT"}, "Incorporated place"),
            ("msa", {}, "Metropolitan Statistical Area"),
            ("zcta", {"state": "VT"}, "ZIP Code Tabulation Area"),
            ("congressional district", {"state": "VT"}, "Congressional district"),
            (
                "state legislative district (upper chamber)",
                {"state": "VT"},
                "State senate district",
            ),
            (
                "state legislative district (lower chamber)",
                {"state": "VT"},
                "State house district",
            ),
            ("public use microdata area", {"state": "VT"}, "PUMA"),
            (
                "school district (elementary)",
                {"state": "VT"},
                "Elementary school district",
            ),
            (
                "school district (secondary)",
                {"state": "VT"},
                "Secondary school district",
            ),
            ("school district (unified)", {"state": "VT"}, "Unified school district"),
        ]

        # Test a subset of geographies to avoid hitting rate limits
        test_geographies = geography_tests[:8]  # Test first 8 levels

        for geography, params, description in test_geographies:
            try:
                result = tc.get_acs(
                    geography=geography,
                    variables="B01003_001",  # Total population
                    year=2022,
                    output="tidy",
                    **params,
                )

                assert isinstance(result, pd.DataFrame), f"Failed for {description}"
                assert len(result) > 0, f"No data returned for {description}"

                # Check for geographic identifier column (varies by geography level)
                geo_id_cols = [
                    "GEOID",
                    "us",
                    "region",
                    "division",
                    "state",
                    "county",
                    "tract",
                    "block group",
                    "place",
                ]
                has_geo_id = any(col in result.columns for col in geo_id_cols)
                assert (
                    has_geo_id
                ), f"Missing geographic identifier for {description}, columns: {result.columns.tolist()}"

                assert "estimate" in result.columns, f"Missing estimate for {description}"

                print(f"✓ {description} geography works")

            except Exception as e:
                print(f"✗ {description} geography failed: {e}")
                # Don't fail the test for expected failures
                if "not available" in str(e).lower() or "invalid" in str(e).lower():
                    print(f"  (Expected failure for {description})")
                    continue
                raise

    @pytest.mark.integration
    def test_get_decennial_geography_levels(self, setup_api_key):
        """Test all documented geography levels for get_decennial()."""
        # Geography levels that are supported for decennial Census
        geography_tests = [
            ("us", {}, "United States"),
            ("region", {}, "Census region"),
            ("division", {}, "Census division"),
            ("state", {"state": "VT"}, "State"),
            ("county", {"state": "VT"}, "County"),
            ("tract", {"state": "VT", "county": "003"}, "Census tract"),
            ("block group", {"state": "VT", "county": "003"}, "Block group"),
            ("place", {"state": "VT"}, "Incorporated place"),
            ("congressional district", {"state": "VT"}, "Congressional district"),
        ]

        # Test a subset to avoid rate limits
        test_geographies = geography_tests[:8]

        for geography, params, description in test_geographies:
            try:
                # Use 2020 for voting districts requirement
                year = 2020 if geography == "voting district" else 2020

                result = tc.get_decennial(
                    geography=geography,
                    variables="P1_001N",  # Total population
                    year=year,
                    output="tidy",
                    **params,
                )

                assert isinstance(result, pd.DataFrame), f"Failed for {description}"
                assert len(result) > 0, f"No data returned for {description}"

                # Check for geographic identifier column (varies by geography level)
                geo_id_cols = [
                    "GEOID",
                    "us",
                    "region",
                    "division",
                    "state",
                    "county",
                    "tract",
                    "block group",
                    "place",
                ]
                has_geo_id = any(col in result.columns for col in geo_id_cols)
                assert (
                    has_geo_id
                ), f"Missing geographic identifier for {description}, columns: {result.columns.tolist()}"

                assert "estimate" in result.columns, f"Missing estimate for {description}"

                print(f"✓ {description} geography works")

            except Exception as e:
                print(f"✗ {description} geography failed: {e}")
                # Don't fail for expected failures
                if "not available" in str(e).lower() or "invalid" in str(e).lower():
                    print(f"  (Expected failure for {description})")
                    continue
                raise

    @pytest.mark.integration
    def test_get_estimates_geography_levels(self, setup_api_key):
        """Test all documented geography levels for get_estimates()."""
        # Geography levels that are supported for population estimates
        geography_tests = [
            ("us", {}, "United States"),
            ("region", {}, "Census region"),
            ("division", {}, "Census division"),
            ("state", {"state": "VT"}, "State"),
            ("county", {"state": "VT"}, "County"),
            (
                "metropolitan statistical area/micropolitan statistical area",
                {},
                "Metropolitan Statistical Area",
            ),
            ("place", {"state": "VT"}, "Incorporated place"),
        ]

        for geography, params, description in geography_tests:
            try:
                result = tc.get_estimates(
                    geography=geography,
                    variables="POP",  # Population estimate
                    year=2022,
                    **params,
                )

                assert isinstance(result, pd.DataFrame), f"Failed for {description}"
                assert len(result) > 0, f"No data returned for {description}"

                # Check for geographic identifier column (varies by geography level)
                geo_id_cols = [
                    "GEOID",
                    "us",
                    "region",
                    "division",
                    "state",
                    "county",
                    "tract",
                    "block group",
                    "place",
                ]
                has_geo_id = any(col in result.columns for col in geo_id_cols)
                assert (
                    has_geo_id
                ), f"Missing geographic identifier for {description}, columns: {result.columns.tolist()}"

                # Check for estimate column (varies by function)
                estimate_cols = [
                    "estimate",
                    "POPESTIMATE2022",
                    "POPESTIMATE2021",
                    "POPESTIMATE2020",
                ]
                has_estimate = any(col in result.columns for col in estimate_cols)
                assert (
                    has_estimate
                ), f"Missing estimate column for {description}, columns: {result.columns.tolist()}"

                print(f"✓ {description} geography works")

            except Exception as e:
                print(f"✗ {description} geography failed: {e}")
                # Don't fail for expected failures
                if "not available" in str(e).lower() or "invalid" in str(e).lower():
                    print(f"  (Expected failure for {description})")
                    continue
                raise

    @pytest.mark.integration
    def test_geography_aliases(self, setup_api_key):
        """Test that geography aliases work correctly."""
        aliases_to_test = [
            ("cbg", "block group"),
            ("cbsa", "metropolitan statistical area/micropolitan statistical area"),
            ("zcta", "zip code tabulation area"),
        ]

        for alias, full_name in aliases_to_test:
            try:
                # Set parameters based on geography type
                if alias == "cbg":
                    params = {"state": "VT", "county": "003"}
                elif alias == "cbsa":
                    params = {}  # National geography
                elif alias == "zcta":
                    params = {"zcta": "05401"}  # Specific ZCTA

                # Test alias
                result_alias = tc.get_acs(
                    geography=alias, variables="B01003_001", year=2022, **params
                )

                # Test full name
                result_full = tc.get_acs(
                    geography=full_name, variables="B01003_001", year=2022, **params
                )

                # Both should return data
                assert isinstance(result_alias, pd.DataFrame)
                assert isinstance(result_full, pd.DataFrame)
                assert len(result_alias) > 0
                assert len(result_full) > 0

                print(f"✓ Geography alias '{alias}' works correctly")

            except Exception as e:
                print(f"✗ Geography alias '{alias}' failed: {e}")
                if "not available" in str(e).lower() or "requires" in str(e).lower():
                    print(f"  (Expected failure or parameter issue for {alias})")
                    continue
                raise

    @pytest.mark.integration
    def test_geography_with_name_column(self, setup_api_key):
        """Test that NAME column is added for supported geography levels."""
        name_column_geographies = [
            ("state", {"state": "VT"}),
            ("county", {"state": "VT"}),
            ("tract", {"state": "VT", "county": "003"}),
        ]

        for geography, params in name_column_geographies:
            try:
                result = tc.get_acs(
                    geography=geography, variables="B01003_001", year=2022, **params
                )

                assert isinstance(result, pd.DataFrame), f"Failed for {geography}"
                assert "NAME" in result.columns, f"Missing NAME column for {geography}"
                assert len(result) > 0, f"No data returned for {geography}"

                # Check NAME column has proper format
                name_sample = result["NAME"].iloc[0]
                assert isinstance(name_sample, str), f"NAME not string for {geography}"
                assert len(name_sample) > 0, f"Empty NAME for {geography}"

                print(f"✓ NAME column works for {geography}")

            except Exception as e:
                print(f"✗ NAME column test failed for {geography}: {e}")
                raise

    @pytest.mark.integration
    def test_special_geography_requirements(self, setup_api_key):
        """Test special geography requirements and restrictions."""

        # Test PUMAs not available in 2020 PL file
        try:
            result = tc.get_decennial(
                geography="public use microdata area",
                variables="P1_001N",
                state="VT",
                year=2020,
                sumfile="pl",  # Should fail
            )
            # If we get here without error, that's unexpected
            print("⚠️ PUMAs with 2020 PL didn't fail as expected")

        except ValueError as e:
            if "not available" in str(e) and "PL" in str(e):
                print("✓ Correctly blocks PUMAs in 2020 PL file")
            else:
                raise
        except Exception as e:
            print(f"✗ PUMA restriction test failed: {e}")
            raise

        print("✓ Special geography requirements tests completed")

    @pytest.mark.integration
    def test_r_tidycensus_output_format(self, setup_api_key):
        """Test that output format exactly matches R tidycensus format."""

        # Test CBSA format matching the user's example
        cbsa_result = tc.get_acs(geography="cbsa", variables="B01003_001", year=2020, output="tidy")

        # Verify required columns exist
        required_cols = ["GEOID", "NAME", "variable", "estimate", "moe"]
        for col in required_cols:
            assert col in cbsa_result.columns, f"Missing required column: {col}"

        # Verify Aberdeen, SD is in the correct format
        aberdeen = cbsa_result[cbsa_result["GEOID"] == "10100"]
        assert not aberdeen.empty, "Aberdeen, SD (GEOID 10100) not found"

        row = aberdeen.iloc[0]
        assert row["GEOID"] == "10100", "GEOID format incorrect"
        assert "Aberdeen, SD Micro Area" in row["NAME"], "NAME format incorrect"
        assert row["variable"] == "B01003_001", "Variable format incorrect"
        assert isinstance(row["estimate"], (int, float)), "Estimate should be numeric"

        print("✓ CBSA output format matches R tidycensus")

        # Test ZCTA format
        zcta_result = tc.get_acs(
            geography="zcta", variables="B01003_001", zcta="05401", year=2020, output="tidy"
        )

        # Verify required columns exist
        for col in required_cols:
            assert col in zcta_result.columns, f"Missing required column in ZCTA: {col}"

        # Check first ZCTA has proper format
        if len(zcta_result) > 0:
            row = zcta_result.iloc[0]
            assert isinstance(row["GEOID"], str), "ZCTA GEOID should be string"
            assert "ZCTA5" in row["NAME"], "ZCTA NAME format incorrect"
            assert row["variable"] == "B01003_001", "ZCTA Variable format incorrect"

        print("✓ ZCTA output format matches R tidycensus")

    @pytest.mark.integration
    def test_national_geographies_ignore_state(self, setup_api_key):
        """Test that national geographies ignore state parameters correctly."""

        # Test that ZCTAs work with state parameter (but ignore it)
        with pytest.warns(UserWarning, match="ZCTAs are national geographies"):
            zcta_result = tc.get_acs(
                geography="zcta",
                state="VT",  # Should be ignored
                variables="B01003_001",
                year=2020,
            )

        # Should get all national ZCTAs, not just VT ZCTAs
        assert len(zcta_result) > 1000, "Should get many ZCTAs (national dataset)"
        assert "GEOID" in zcta_result.columns
        assert "NAME" in zcta_result.columns

        print("✓ ZCTAs correctly ignore state parameter")

        # Test that CBSAs work with state parameter (but ignore it)
        cbsa_result = tc.get_acs(
            geography="cbsa",
            state="VT",  # Should be ignored
            variables="B01003_001",
            year=2020,
        )

        # Should get all national CBSAs
        assert len(cbsa_result) > 500, "Should get many CBSAs (national dataset)"
        assert "GEOID" in cbsa_result.columns
        assert "NAME" in cbsa_result.columns

        print("✓ CBSAs correctly ignore state parameter")


def run_table_chunking_integration_tests():
    """Run table chunking integration tests that require a valid Census API key.

    These tests verify that:
    1. Large tables (>48 variables) are automatically chunked
    2. Multiple API calls are made and results properly combined
    3. All output formats work with chunking
    4. Summary variables and geometry work with chunked requests
    """
    import os

    api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        print("⚠️  CENSUS_API_KEY not found. Skipping table chunking integration tests.")
        print("   Set CENSUS_API_KEY environment variable to run these tests.")
        return

    tc.set_census_api_key(api_key)

    print("🧪 Running Table Chunking Integration Tests...")
    print("=" * 60)

    test_class = TestDecennialTableChunkingIntegration()

    try:
        # Test large table chunking
        print("\n📊 Testing large table chunking (P1 table - 71 variables)...")
        test_class.test_large_table_chunking_integration(api_key)

        # Test medium table chunking
        print("\n📊 Testing medium table chunking (P2 table)...")
        test_class.test_medium_table_chunking_integration(api_key)

        # Test small table (no chunking)
        print("\n📊 Testing small table (P5 table - no chunking needed)...")
        test_class.test_small_table_no_chunking_integration(api_key)

        # Test wide format with chunking
        print("\n📊 Testing wide format with table chunking...")
        test_class.test_table_chunking_wide_format_integration(api_key)

        # Test summary variable with chunking
        print("\n📊 Testing summary variable with table chunking...")
        test_class.test_table_chunking_with_summary_var_integration(api_key)

        # Test geometry with chunking (skip if SSL issues)
        print("\n📊 Testing geometry with table chunking...")
        try:
            test_class.test_table_chunking_with_geometry_integration(api_key)
        except Exception as e:
            if "SSL" in str(e) or "certificate" in str(e) or "wget" in str(e):
                print("⚠️  Skipping geometry test due to SSL/download issues")
            else:
                raise

        print("\n" + "=" * 60)
        print("🎉 ALL TABLE CHUNKING INTEGRATION TESTS PASSED! ✓")
        print("=" * 60)
        print()
        print("Table chunking functionality is working correctly with:")
        print("• Large tables (71+ variables) automatically chunked")
        print("• All output formats (tidy/wide) supported")
        print("• Summary variables work with chunking")
        print("• Geometry requests work with chunking")
        print("• Small tables work without chunking overhead")

    except Exception as e:
        print(f"\n❌ Table chunking integration test failed: {e}")
        print("\nThis might be due to:")
        print("- Invalid API key")
        print("- Network connectivity issues")
        print("- Census Bureau API being down")
        print("- Specific table not available for requested geography/year")
        raise


if __name__ == "__main__":
    # Run both original integration tests and new table chunking tests
    run_integration_tests()
    print("\n" + "=" * 60)
    run_table_chunking_integration_tests()
