"""
Tests for utility functions.
"""

import pandas as pd
import pytest

from pytidycensus.utils import (
    add_margin_of_error,
    build_geography_params,
    process_census_data,
    validate_county,
    validate_geography,
    validate_state,
    validate_year,
)


class TestValidateState:
    """Test cases for state validation."""

    def test_validate_state_name(self):
        """Test validation with state name."""
        result = validate_state("Texas")
        assert result == ["48"]

    def test_validate_state_abbreviation(self):
        """Test validation with state abbreviation."""
        result = validate_state("TX")
        assert result == ["48"]

    def test_validate_state_fips(self):
        """Test validation with FIPS code."""
        result = validate_state("48")
        assert result == ["48"]

        result = validate_state(48)
        assert result == ["48"]

    def test_validate_multiple_states(self):
        """Test validation with multiple states."""
        result = validate_state(["TX", "CA", "NY"])
        assert set(result) == {"48", "06", "36"}

    def test_validate_invalid_state(self):
        """Test validation with invalid state."""
        with pytest.raises(ValueError, match="Invalid state identifier"):
            validate_state("INVALID")

    def test_validate_state_single_digit_fips(self):
        """Test validation with single-digit FIPS code."""
        result = validate_state("1")  # Alabama
        assert result == ["01"]

        result = validate_state(1)
        assert result == ["01"]

    def test_validate_state_two_digit_fips(self):
        """Test validation with two-digit FIPS code."""
        result = validate_state("48")
        assert result == ["48"]

    def test_validate_state_invalid_fips(self):
        """Test validation with invalid FIPS code."""
        with pytest.raises(ValueError, match="Invalid state identifier"):
            validate_state("99")


class TestValidateCounty:
    """Test cases for county validation."""

    def test_validate_county_fips(self):
        """Test validation with FIPS code."""
        result = validate_county("201", "48")  # Harris County, TX
        assert result == ["201"]

        result = validate_county(201, "48")
        assert result == ["201"]

    def test_validate_multiple_counties(self):
        """Test validation with multiple counties."""
        result = validate_county(["201", "157"], "48")
        assert result == ["201", "157"]


class TestValidateYear:
    """Test cases for year validation."""

    def test_validate_acs_year(self):
        """Test ACS year validation."""
        assert validate_year(2022, "acs") == 2022
        assert validate_year(2009, "acs") == 2009

        with pytest.raises(ValueError, match="ACS data not available"):
            validate_year(2004, "acs")

        with pytest.raises(ValueError, match="ACS data not available"):
            validate_year(2030, "acs")

    def test_validate_decennial_year(self):
        """Test decennial census year validation."""
        assert validate_year(2020, "dec") == 2020
        assert validate_year(2010, "dec") == 2010

        with pytest.raises(ValueError, match="Decennial census data not available"):
            validate_year(2015, "dec")

    def test_validate_estimates_year(self):
        """Test population estimates year validation."""
        assert validate_year(2022, "estimates") == 2022

        with pytest.raises(ValueError, match="Population estimates not available"):
            validate_year(1999, "estimates")


class TestValidateGeography:
    """Test cases for geography validation."""

    def test_validate_common_geographies(self):
        """Test validation of common geography types."""
        assert validate_geography("state") == "state"
        assert validate_geography("county") == "county"
        assert validate_geography("tract") == "tract"
        assert validate_geography("block group") == "block group"

    def test_validate_cbg_alias(self):
        """Test that 'cbg' is converted to 'block group'."""
        assert validate_geography("cbg") == "block group"

    def test_validate_case_insensitive(self):
        """Test case-insensitive validation."""
        assert validate_geography("STATE") == "state"
        assert validate_geography("County") == "county"

    def test_validate_invalid_geography(self):
        """Test validation with invalid geography."""
        with pytest.raises(ValueError, match="Geography 'invalid' not supported"):
            validate_geography("invalid")


class TestBuildGeographyParams:
    """Test cases for building geography parameters."""

    def test_build_us_params(self):
        """Test building parameters for US geography."""
        params = build_geography_params("us")
        assert params == {"for": "us:*"}

    def test_build_state_params(self):
        """Test building parameters for state geography."""
        params = build_geography_params("state")
        assert params == {"for": "state:*"}

        params = build_geography_params("state", state="TX")
        assert params == {"for": "state:48"}

    def test_build_county_params(self):
        """Test building parameters for county geography."""
        params = build_geography_params("county", state="TX")
        assert params == {"for": "county:*", "in": "state:48"}

        params = build_geography_params("county", state="TX", county="201")
        assert params == {"for": "county:201", "in": "state:48"}

    def test_build_tract_params(self):
        """Test building parameters for tract geography."""
        params = build_geography_params("tract", state="TX")
        assert params == {"for": "tract:*", "in": "state:48"}

        params = build_geography_params("tract", state="TX", county="201")
        assert params == {"for": "tract:*", "in": "state:48 county:201"}

    def test_build_region_params(self):
        """Test building parameters for region geography."""
        params = build_geography_params("region")
        assert params == {"for": "region:*"}

    def test_build_division_params(self):
        """Test building parameters for division geography."""
        params = build_geography_params("division")
        assert params == {"for": "division:*"}

    def test_build_block_group_params(self):
        """Test building parameters for block group geography."""
        params = build_geography_params("block group", state="TX")
        assert params == {"for": "block group:*", "in": "state:48"}

        params = build_geography_params("block group", state="TX", county="201")
        assert params == {"for": "block group:*", "in": "state:48 county:201"}

    def test_build_other_geography_params(self):
        """Test building parameters for other geography types."""
        params = build_geography_params("place", state="TX")
        assert params == {"for": "place:*", "in": "state:48"}

    def test_build_state_params_multiple(self):
        """Test building parameters for multiple states."""
        params = build_geography_params("state", state=["TX", "CA"])
        assert params == {"for": "state:48,06"}

    def test_build_county_params_no_state(self):
        """Test building county parameters without state."""
        params = build_geography_params("county")
        assert params == {"for": "county:*"}


class TestProcessCensusData:
    """Test cases for processing Census API responses."""

    def test_process_tidy_format(self):
        """Test processing data in tidy format."""
        data = [
            {
                "NAME": "Alabama",
                "B01001_001E": "5024279",
                "B01001_002E": "2449981",
                "state": "01",
            },
            {
                "NAME": "Alaska",
                "B01001_001E": "733391",
                "B01001_002E": "379169",
                "state": "02",
            },
        ]
        variables = ["B01001_001E", "B01001_002E"]

        result = process_census_data(data, variables, output="tidy")

        assert len(result) == 4  # 2 states × 2 variables
        assert "variable" in result.columns
        assert "estimate" in result.columns  # Updated to new column name
        assert result["variable"].nunique() == 2

    def test_process_wide_format(self):
        """Test processing data in wide format."""
        data = [
            {"NAME": "Alabama", "B01001_001E": "5024279", "state": "01"},
            {"NAME": "Alaska", "B01001_001E": "733391", "state": "02"},
        ]
        variables = ["B01001_001E"]

        result = process_census_data(data, variables, output="wide")

        assert len(result) == 2
        assert "B01001_001E" in result.columns
        assert result["B01001_001E"].dtype in [
            "float64",
            "int64",
        ]  # Allow both numeric types

    def test_process_with_geoid_creation(self):
        """Test GEOID creation from geography columns."""
        data = [
            {
                "NAME": "Harris County",
                "B01001_001E": "4000000",
                "state": "48",
                "county": "201",
            },
            {
                "NAME": "Dallas County",
                "B01001_001E": "2600000",
                "state": "48",
                "county": "113",
            },
        ]
        variables = ["B01001_001E"]

        result = process_census_data(data, variables, output="wide")

        assert "GEOID" in result.columns
        assert result["GEOID"].tolist() == ["48201", "48113"]

    def test_process_with_name_column_creation(self):
        """Test NAME column creation from name fields."""
        data = [
            {"state_name": "Texas", "B01001_001E": "5000000", "state": "48"},
            {"state_name": "California", "B01001_001E": "6000000", "state": "06"},
        ]
        variables = ["B01001_001E"]

        result = process_census_data(data, variables, output="wide")

        # Should create NAME column from the first available name field
        assert "NAME" in result.columns
        assert result["NAME"].iloc[0] == "Texas"
        assert result["NAME"].iloc[1] == "California"

    def test_process_realistic_census_api_data_tidy(self):
        """Test processing realistic Census API data in tidy format."""
        # Realistic data matching actual Census Bureau API response format
        data = [
            {
                'B01003_001E': '3269', 
                'B01003_001M': '452', 
                'B19013_001E': '234236', 
                'B19013_001M': '42845', 
                'state': '06', 
                'county': '001', 
                'tract': '400100',
                'NAME': 'Census Tract 4001, Alameda County, California'
            },
            {
                'B01003_001E': '2147', 
                'B01003_001M': '201', 
                'B19013_001E': '225500', 
                'B19013_001M': '29169', 
                'state': '06', 
                'county': '001', 
                'tract': '400200',
                'NAME': 'Census Tract 4002, Alameda County, California'
            },
            {
                'B01003_001E': '5619', 
                'B01003_001M': '571', 
                'B19013_001E': '164000', 
                'B19013_001M': '44675', 
                'state': '06', 
                'county': '001', 
                'tract': '400300',
                'NAME': 'Census Tract 4003, Alameda County, California'
            }
        ]
        variables = ['B01003_001E', 'B01003_001M', 'B19013_001E', 'B19013_001M']

        result = process_census_data(data, variables, output="tidy")

        # Verify basic structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 12  # 3 tracts × 4 variables = 12 rows
        
        # Verify columns (updated for new format with 'estimate' instead of 'value')
        expected_columns = ['state', 'county', 'tract', 'NAME', 'GEOID', 'variable', 'estimate']
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"
        
        # Verify GEOID creation
        expected_geoids = ['06001400100', '06001400200', '06001400300']
        actual_geoids = result['GEOID'].unique()
        for geoid in expected_geoids:
            assert geoid in actual_geoids, f"Missing GEOID: {geoid}"
        
        # Verify variable melting
        expected_variables = ['B01003_001E', 'B01003_001M', 'B19013_001E', 'B19013_001M']
        actual_variables = result['variable'].unique()
        for var in expected_variables:
            assert var in actual_variables, f"Missing variable: {var}"
        
        # Verify data types - estimates should be numeric after processing
        assert result['estimate'].dtype in ['int64', 'float64', 'object']  # Can be string from API
        
        # Verify specific data values
        tract_4001_pop = result[
            (result['GEOID'] == '06001400100') & 
            (result['variable'] == 'B01003_001E')
        ]['estimate'].iloc[0]
        assert tract_4001_pop == 3269  # Should be converted to numeric
        
        tract_4002_income = result[
            (result['GEOID'] == '06001400200') & 
            (result['variable'] == 'B19013_001E')
        ]['estimate'].iloc[0]
        assert tract_4002_income == 225500

    def test_process_realistic_census_api_data_wide(self):
        """Test processing realistic Census API data in wide format."""
        # Same realistic data
        data = [
            {
                'B01003_001E': '3269', 
                'B01003_001M': '452', 
                'B19013_001E': '234236', 
                'B19013_001M': '42845', 
                'state': '06', 
                'county': '001', 
                'tract': '400100',
                'NAME': 'Census Tract 4001, Alameda County, California'
            },
            {
                'B01003_001E': '2147', 
                'B01003_001M': '201', 
                'B19013_001E': '225500', 
                'B19013_001M': '29169', 
                'state': '06', 
                'county': '001', 
                'tract': '400200',
                'NAME': 'Census Tract 4002, Alameda County, California'
            }
        ]
        variables = ['B01003_001E', 'B01003_001M', 'B19013_001E', 'B19013_001M']

        result = process_census_data(data, variables, output="wide")

        # Verify basic structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # 2 tracts
        
        # Verify geographic columns are present and data columns follow
        all_cols = list(result.columns)
        assert 'state' in all_cols
        assert 'county' in all_cols
        assert 'tract' in all_cols
        assert 'GEOID' in all_cols
        assert 'NAME' in all_cols
        
        # Verify all variable columns are present
        for var in variables:
            assert var in result.columns, f"Missing variable column: {var}"
        
        # Verify GEOID creation from geographic parts
        assert result['GEOID'].tolist() == ['06001400100', '06001400200']
        
        # Verify data values are numeric
        assert result['B01003_001E'].iloc[0] == 3269
        assert result['B19013_001E'].iloc[1] == 225500
        assert result['B01003_001M'].iloc[0] == 452


class TestAddMarginOfError:
    """Test cases for adding margin of error columns."""

    def test_add_moe_columns(self):
        """Test adding margin of error columns for ACS data."""
        df = pd.DataFrame(
            {
                "NAME": ["Alabama", "Alaska"],
                "B01001_001E": [5024279, 733391],
                "B01001_001M": [1000, 500],
                "B01001_002E": [2449981, 379169],
                "B01001_002M": [800, 400],
                "state": ["01", "02"],
            }
        )
        variables = ["B01001_001E", "B01001_001M", "B01001_002E", "B01001_002M"]

        result = add_margin_of_error(df, variables, output="wide")

        assert "B01001_001_moe" in result.columns
        assert "B01001_002_moe" in result.columns
        assert "B01001_001M" not in result.columns
        assert "B01001_002M" not in result.columns
        assert result["B01001_001_moe"].tolist() == [1000, 500]

    def test_no_moe_columns(self):
        """Test handling when no MOE columns are present."""
        df = pd.DataFrame(
            {
                "NAME": ["Alabama", "Alaska"],
                "B01001_001E": [5024279, 733391],
                "state": ["01", "02"],
            }
        )
        variables = ["B01001_001E"]

        result = add_margin_of_error(df, variables, output="wide")

        # Should return unchanged if no MOE columns found
        assert len(result.columns) == len(df.columns)
        assert "B01001_001E_moe" not in result.columns

    def test_add_moe_tidy_format(self):
        """Test adding margin of error in tidy format with new structure."""
        df = pd.DataFrame(
            {
                "NAME": ["Alabama", "Alabama", "Alaska", "Alaska"],
                "variable": [
                    "B01001_001E",
                    "B01001_001M",
                    "B01001_001E",
                    "B01001_001M",
                ],
                "estimate": [5024279, 1000, 733391, 500],
                "GEOID": ["01", "01", "02", "02"],
            }
        )
        variables = ["B01001_001E", "B01001_001M"]

        result = add_margin_of_error(df, variables, output="tidy")

        # Should have estimate and moe columns, with variable names cleaned (E suffix removed)
        assert "estimate" in result.columns
        assert "moe" in result.columns
        assert len(result) == 2  # 2 geographies, estimate and MOE combined into one row each
        
        # Check variable names have E suffix removed
        assert "B01001_001" in result["variable"].values
        assert not any(var.endswith("E") for var in result["variable"].values)
        
        # Verify data values
        alabama_row = result[result["GEOID"] == "01"]
        assert alabama_row["estimate"].iloc[0] == 5024279
        assert alabama_row["moe"].iloc[0] == 1000.0  # MOE value

    def test_add_moe_confidence_levels(self):
        """Test MOE confidence level adjustments."""
        df = pd.DataFrame(
            {
                "NAME": ["Alabama"],
                "B01001_001E": [5024279],
                "B01001_001M": [1000],
                "state": ["01"],
            }
        )
        variables = ["B01001_001E", "B01001_001M"]

        # Test 90% (default - no adjustment)
        result_90 = add_margin_of_error(df, variables, moe_level=90, output="wide")
        assert result_90["B01001_001_moe"].iloc[0] == 1000

        # Test 95% (should be adjusted)
        result_95 = add_margin_of_error(df, variables, moe_level=95, output="wide")
        expected_95 = 1000 * (1.96 / 1.645)
        assert abs(result_95["B01001_001_moe"].iloc[0] - expected_95) < 0.01

        # Test 99% (should be adjusted)
        result_99 = add_margin_of_error(df, variables, moe_level=99, output="wide")
        expected_99 = 1000 * (2.576 / 1.645)
        assert abs(result_99["B01001_001_moe"].iloc[0] - expected_99) < 0.01

    def test_add_moe_invalid_confidence_level(self):
        """Test invalid MOE confidence level."""
        df = pd.DataFrame({"NAME": ["Alabama"], "B01001_001E": [5024279]})
        variables = ["B01001_001E"]

        with pytest.raises(ValueError, match="moe_level must be 90, 95, or 99"):
            add_margin_of_error(df, variables, moe_level=85)
