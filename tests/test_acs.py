"""Tests for ACS data retrieval functions."""

from unittest.mock import Mock, patch

import geopandas as gpd
import pandas as pd
import pytest

from pytidycensus.acs import get_acs, get_acs_variables


class TestGetACS:
    """Test cases for the get_acs function."""

    @patch("pytidycensus.acs.CensusAPI")
    @patch("pytidycensus.acs.process_census_data")
    @patch("pytidycensus.acs.add_margin_of_error")
    def test_get_acs_basic(self, mock_add_moe, mock_process, mock_api_class):
        """Test basic ACS data retrieval."""
        # Mock API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "NAME": "Alabama",
                "B01001_001E": "5024279",
                "B01001_001M": "1000",
                "state": "01",
            }
        ]
        mock_api_class.return_value = mock_api

        # Mock processing functions
        mock_df_tidy = pd.DataFrame(
            {
                "NAME": ["Alabama"],
                "GEOID": ["01"],
                "state": ["01"],
                "variable": ["B01001_001"],  # E suffix removed
                "estimate": [5024279],
                "moe": [1000.0],
            }
        )
        mock_process.return_value = mock_df_tidy
        mock_add_moe.return_value = mock_df_tidy

        result = get_acs(geography="state", variables="B01001_001E", year=2022, api_key="test")

        # Verify API was called correctly
        mock_api.get.assert_called_once()
        call_args = mock_api.get.call_args
        assert call_args[1]["year"] == 2022
        assert call_args[1]["dataset"] == "acs"
        assert call_args[1]["survey"] == "acs5"
        assert "B01001_001E" in call_args[1]["variables"]
        assert "B01001_001M" in call_args[1]["variables"]  # MOE variable added

        # Verify processing was called
        mock_process.assert_called_once()
        mock_add_moe.assert_called_once()

        assert isinstance(result, pd.DataFrame)

    @patch("pytidycensus.acs.CensusAPI")
    @patch("pytidycensus.variables.load_variables")
    def test_get_acs_with_table(self, mock_load_vars, mock_api_class):
        """Test ACS data retrieval with table parameter."""
        # Mock variables loading
        mock_vars_df = pd.DataFrame(
            {
                "name": ["B19013_001E", "B19013_002E"],
                "label": ["Median household income", "Something else"],
            }
        )
        mock_load_vars.return_value = mock_vars_df

        # Mock API
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = pd.DataFrame()
            mock_add_moe.return_value = pd.DataFrame()

            get_acs(geography="state", table="B19013", year=2022, api_key="test")

        # Should load variables for the table (using cache_table parameter default=False)
        mock_load_vars.assert_called_once_with(2022, "acs", "acs5", cache=False)

        # Should call API with table variables
        call_args = mock_api.get.call_args[1]["variables"]
        assert "B19013_001E" in call_args
        assert "B19013_001M" in call_args  # MOE variables

    @patch("pytidycensus.acs.CensusAPI")
    @patch("pytidycensus.variables.load_variables")
    def test_get_acs_table_b01001_returns_expected_values(self, mock_load_vars, mock_api_class):
        """Test that table B01001 returns expected values matching R tidycensus output."""
        # Mock variables loading for B01001 (first 4 variables from the R output)
        mock_vars_df = pd.DataFrame(
            {
                "name": ["B01001_001E", "B01001_002E", "B01001_003E", "B01001_004E"],
                "label": ["Total", "Male", "Male under 5 years", "Male 5 to 9 years"],
                "concept": ["SEX BY AGE", "SEX BY AGE", "SEX BY AGE", "SEX BY AGE"],
                "predicateType": ["int", "int", "int", "int"],
                "group": ["B01001", "B01001", "B01001", "B01001"],
                "limit": [0, 0, 0, 0],
                "table": ["B01001", "B01001", "B01001", "B01001"],
            }
        )
        mock_load_vars.return_value = mock_vars_df

        # Mock API response with the exact values from R output
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "state": "01",
                "NAME": "Alabama",
                "B01001_001E": "4893186",  # Total population
                "B01001_001M": "-222222222",  # No MOE for total (will be converted to NA)
                "B01001_002E": "2365734",  # Male
                "B01001_002M": "1090",  # MOE for male
                "B01001_003E": "149579",  # Male under 5
                "B01001_003M": "672",  # MOE for male under 5
                "B01001_004E": "150937",  # Male 5 to 9
                "B01001_004M": "2202",  # MOE for male 5 to 9
            }
        ]
        mock_api_class.return_value = mock_api

        # Execute the function
        result = get_acs(
            geography="state", table="B01001", year=2020, api_key="test", output="tidy"
        )

        # Verify the result structure and values
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4  # 4 variables for Alabama

        # Check that all expected columns are present
        expected_columns = {"GEOID", "NAME", "variable", "estimate", "moe"}
        assert expected_columns.issubset(set(result.columns))

        # Verify specific values match R output
        # Convert to dict for easier lookup
        result_dict = {}
        for _, row in result.iterrows():
            result_dict[row["variable"]] = {"estimate": row["estimate"], "moe": row["moe"]}

        # Check estimates match R output
        assert result_dict["B01001_001"]["estimate"] == 4893186
        assert result_dict["B01001_002"]["estimate"] == 2365734
        assert result_dict["B01001_003"]["estimate"] == 149579
        assert result_dict["B01001_004"]["estimate"] == 150937

        # Check MOE values (first should be NA/null, others should match)
        assert pd.isna(result_dict["B01001_001"]["moe"])  # Total population has no MOE in R
        assert result_dict["B01001_002"]["moe"] == 1090
        assert result_dict["B01001_003"]["moe"] == 672
        assert result_dict["B01001_004"]["moe"] == 2202

        # Verify GEOID and NAME are correct
        assert all(result["GEOID"] == "01")
        assert all(result["NAME"] == "Alabama")

        # Verify that load_variables was called correctly
        mock_load_vars.assert_called_once_with(2020, "acs", "acs5", cache=False)

    @patch("pytidycensus.acs.CensusAPI")
    @patch("pytidycensus.acs.get_geography")
    def test_get_acs_with_geometry(self, mock_get_geo, mock_api_class):
        """Test ACS data retrieval with geometry."""
        # Mock API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "B01001_001E": "5024279", "GEOID": "01", "state": "01"}
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

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_df = pd.DataFrame({"NAME": ["Alabama"], "B01001_001E": [5024279], "GEOID": ["01"]})
            mock_process.return_value = mock_df
            mock_add_moe.return_value = mock_df

            result = get_acs(
                geography="state",
                variables="B01001_001E",
                geometry=True,
                api_key="test",
            )

        # Should call get_geography
        mock_get_geo.assert_called_once()

        # Result should be merged with geometry
        assert "GEOID" in result.columns

    def test_get_acs_validation_errors(self):
        """Test validation errors in get_acs."""
        # No variables or table
        with pytest.raises(
            ValueError,
            match="Either a vector of variables or an ACS table must be specified",
        ):
            get_acs(geography="state", api_key="test")

        # Both variables and table
        with pytest.raises(ValueError, match="Specify variables or a table to retrieve"):
            get_acs(
                geography="state",
                variables="B01001_001E",
                table="B19013",
                api_key="test",
            )

        # Invalid survey
        with pytest.raises(ValueError, match="Survey must be"):
            get_acs(
                geography="state",
                variables="B01001_001E",
                survey="invalid",
                api_key="test",
            )

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_different_surveys(self, mock_api_class):
        """Test get_acs with different survey types."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = pd.DataFrame()
            mock_add_moe.return_value = pd.DataFrame()

            # Test ACS5
            get_acs(
                geography="state",
                variables="B01001_001E",
                survey="acs5",
                api_key="test",
            )
            call_args = mock_api.get.call_args[1]
            assert call_args["survey"] == "acs5"

            # Test ACS1
            get_acs(
                geography="state",
                variables="B01001_001E",
                survey="acs1",
                api_key="test",
            )
            call_args = mock_api.get.call_args[1]
            assert call_args["survey"] == "acs1"

    def test_get_acs_multiple_variables(self):
        """Test get_acs with multiple variables."""
        with patch("pytidycensus.acs.CensusAPI") as mock_api_class, patch(
            "pytidycensus.acs.process_census_data"
        ) as mock_process, patch("pytidycensus.acs.add_margin_of_error") as mock_add_moe:
            mock_api = Mock()
            mock_api.get.return_value = []
            mock_api_class.return_value = mock_api
            mock_process.return_value = pd.DataFrame()
            mock_add_moe.return_value = pd.DataFrame()

            variables = ["B01001_001E", "B19013_001E"]
            get_acs(geography="state", variables=variables, api_key="test")

            # Should include all variables plus MOE variables
            call_args = mock_api.get.call_args[1]["variables"]
            assert "B01001_001E" in call_args
            assert "B01001_001M" in call_args
            assert "B19013_001E" in call_args
            assert "B19013_001M" in call_args

    @patch("pytidycensus.acs.CensusAPI")
    @patch("pytidycensus.variables.load_variables")
    def test_get_acs_table_not_found(self, mock_load_vars, mock_api_class):
        """Test get_acs with table that has no variables."""
        # Mock empty variables result
        mock_vars_df = pd.DataFrame(
            {
                "name": ["B01001_001E", "B01001_002E"],
                "label": ["Population", "Something else"],
            }
        )
        mock_load_vars.return_value = mock_vars_df

        with pytest.raises(ValueError, match="No variables found for table"):
            get_acs(geography="state", table="B99999", api_key="test")

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_non_standard_variables(self, mock_api_class):
        """Test get_acs with variables that don't end in E."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = pd.DataFrame()
            mock_add_moe.return_value = pd.DataFrame()

            # Test variable that doesn't end in E or M
            get_acs(geography="state", variables="B01001_001", api_key="test")

            call_args = mock_api.get.call_args[1]["variables"]
            assert "B01001_001E" in call_args
            assert "B01001_001M" in call_args  # MOE should be added

    @patch("pytidycensus.acs.CensusAPI")
    @patch("pytidycensus.acs.get_geography")
    def test_get_acs_geometry_merge_warning(self, mock_get_geo, mock_api_class):
        """Test warning when geometry merge fails due to missing GEOID."""
        # Mock API response without GEOID
        mock_api = Mock()
        mock_api.get.return_value = [{"NAME": "Alabama", "B01001_001E": "5024279", "state": "01"}]
        mock_api_class.return_value = mock_api

        # Mock geometry data with GEOID
        mock_gdf = gpd.GeoDataFrame({"GEOID": ["01"], "NAME": ["Alabama"], "geometry": [None]})
        mock_get_geo.return_value = mock_gdf

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            # Census data without GEOID
            mock_df = pd.DataFrame({"NAME": ["Alabama"], "B01001_001E": [5024279], "state": ["01"]})
            mock_process.return_value = mock_df
            mock_add_moe.return_value = mock_df

            # Should return census data without geometry merge
            result = get_acs(
                geography="state",
                variables="B01001_001E",
                geometry=True,
                api_key="test",
            )

            # Should be the original DataFrame, not merged
            assert "geometry" not in result.columns

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_api_error(self, mock_api_class):
        """Test get_acs handles API errors properly."""
        mock_api = Mock()
        mock_api.get.side_effect = Exception("API request failed")
        mock_api_class.return_value = mock_api

        with pytest.raises(Exception, match="Failed to retrieve ACS data: API request failed"):
            get_acs(geography="state", variables="B01001_001E", api_key="test")

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_named_variables_tidy(self, mock_api_class):
        """Test get_acs with named variables in tidy format."""
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "NAME": "Alabama",
                "B01001_001E": "5024279",
                "B01001_001M": "1000",
                "state": "01",
            }
        ]
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            # Mock tidy format data with new structure
            mock_df = pd.DataFrame(
                {
                    "NAME": ["Alabama"],
                    "variable": ["B01001_001"],  # E suffix removed
                    "estimate": [5024279],
                    "moe": [1000.0],
                    "GEOID": ["01"],
                }
            )
            mock_process.return_value = mock_df
            mock_add_moe.return_value = mock_df

            # Test named variables
            variables_dict = {"total_pop": "B01001_001"}
            result = get_acs(
                geography="state",
                variables=variables_dict,
                output="tidy",
                api_key="test",
            )

            # Verify that the variable names were processed for API call
            call_args = mock_api.get.call_args[1]["variables"]
            assert "B01001_001E" in call_args
            assert "B01001_001M" in call_args

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_moe_confidence_levels(self, mock_api_class):
        """Test get_acs with different MOE confidence levels."""
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "NAME": "Alabama",
                "B01001_001E": "5024279",
                "B01001_001M": "1000",
                "state": "01",
            }
        ]
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = pd.DataFrame()
            mock_add_moe.return_value = pd.DataFrame()

            # Test different MOE levels
            for moe_level in [90, 95, 99]:
                get_acs(
                    geography="state",
                    variables="B01001_001E",
                    moe_level=moe_level,
                    api_key="test",
                )
                # Check that add_margin_of_error was called with correct moe_level
                call_args = mock_add_moe.call_args[1]
                assert call_args["moe_level"] == moe_level

    def test_get_acs_invalid_moe_level(self):
        """Test get_acs with invalid MOE level."""
        with pytest.raises(ValueError, match="moe_level must be 90, 95, or 99"):
            get_acs(geography="state", variables="B01001_001E", moe_level=85, api_key="test")

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_geometry_forces_wide_output(self, mock_api_class):
        """Test that requesting geometry forces wide output format."""
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "B01001_001E": "5024279", "GEOID": "01", "state": "01"}
        ]
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.get_geography") as mock_get_geo, patch(
            "pytidycensus.acs.process_census_data"
        ) as mock_process, patch("pytidycensus.acs.add_margin_of_error") as mock_add_moe:
            mock_gdf = gpd.GeoDataFrame({"GEOID": ["01"], "NAME": ["Alabama"], "geometry": [None]})
            mock_get_geo.return_value = mock_gdf

            mock_df = pd.DataFrame({"NAME": ["Alabama"], "B01001_001E": [5024279], "GEOID": ["01"]})
            mock_process.return_value = mock_df
            mock_add_moe.return_value = mock_df

            result = get_acs(
                geography="state",
                variables="B01001_001E",
                geometry=True,
                output="tidy",  # Request tidy but should be forced to wide
                api_key="test",
            )

            # Should call process_census_data with "wide" output regardless of request
            call_args = mock_process.call_args
            assert call_args[0][2] == "wide"  # Third argument should be "wide"

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_tidy_format_new_structure(self, mock_api_class):
        """Test get_acs tidy format with new estimate/moe structure and API call."""
        # Mock realistic API response matching actual Census Bureau format
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "B01003_001E": "3269",
                "B01003_001M": "452",
                "B19013_001E": "234236",
                "B19013_001M": "42845",
                "state": "06",
                "county": "001",
                "tract": "400100",
                "NAME": "Census Tract 4001, Alameda County, California",
            },
            {
                "B01003_001E": "2147",
                "B01003_001M": "201",
                "B19013_001E": "225500",
                "B19013_001M": "29169",
                "state": "06",
                "county": "001",
                "tract": "400200",
                "NAME": "Census Tract 4002, Alameda County, California",
            },
        ]
        mock_api_class.return_value = mock_api

        # Test the actual function without mocking internal processing
        result = get_acs(
            geography="tract",
            variables=["B01003_001", "B19013_001"],  # Variables without E suffix
            state="CA",
            county="001",
            output="tidy",
            api_key="test",
        )

        # Verify API call structure
        mock_api.get.assert_called_once()
        call_args = mock_api.get.call_args[1]

        # Check the API call parameters match the current structure
        assert call_args["year"] == 2022  # Default year
        assert call_args["dataset"] == "acs"
        assert call_args["survey"] == "acs5"  # Default survey
        assert call_args["show_call"] == False  # Default

        # Verify geography parameter structure
        assert "geography" in call_args
        geography_params = call_args["geography"]
        assert "for" in geography_params
        assert "in" in geography_params

        # Verify variables include both estimate and MOE variables
        variables = call_args["variables"]
        assert "B01003_001E" in variables  # Population estimate
        assert "B01003_001M" in variables  # Population MOE
        assert "B19013_001E" in variables  # Income estimate
        assert "B19013_001M" in variables  # Income MOE

        # Verify tidy format output structure
        assert isinstance(result, pd.DataFrame)
        expected_columns = [
            "state",
            "county",
            "tract",
            "NAME",
            "GEOID",
            "variable",
            "estimate",
            "moe",
        ]
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"

        # Verify data format
        assert len(result) == 4  # 2 geographies × 2 variables = 4 rows

        # Check that variable names have E suffix removed
        unique_vars = result["variable"].unique()
        assert "B01003_001" in unique_vars  # No E suffix
        assert "B19013_001" in unique_vars  # No E suffix
        assert not any(var.endswith("E") for var in unique_vars)  # No E suffixes

        # Verify estimate and moe columns contain numeric data
        assert result["estimate"].dtype in [
            "int64",
            "float64",
            # "object",
        ]  # Can be string from API
        assert result["moe"].dtype in [
            "int64",
            "float64",
        ]  # "object"]

        # Verify GEOID format (state + county + tract)
        geoids = result["GEOID"].unique()
        assert "06001400100" in geoids
        assert "06001400200" in geoids

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_api_call_parameters(self, mock_api_class):
        """Test that get_acs calls the API with correct parameters."""
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "B01003_001E": "1000",
                "B01003_001M": "100",
                "state": "01",
                "NAME": "Alabama",
            }
        ]
        mock_api_class.return_value = mock_api

        # Test with various parameters
        get_acs(
            geography="state",
            variables="B01003_001",
            year=2021,
            survey="acs1",
            api_key="test_key",
            show_call=True,
        )

        # Verify API was called with correct structure
        mock_api.get.assert_called_once()
        call_kwargs = mock_api.get.call_args[1]

        # Verify all expected parameters are present
        expected_params = [
            "year",
            "dataset",
            "variables",
            "geography",
            "survey",
            "show_call",
        ]
        for param in expected_params:
            assert param in call_kwargs, f"Missing API parameter: {param}"

        # Verify parameter values
        assert call_kwargs["year"] == 2021
        assert call_kwargs["dataset"] == "acs"
        assert call_kwargs["survey"] == "acs1"
        assert call_kwargs["show_call"] == True

        # Verify variables include both E and M suffixes
        variables = call_kwargs["variables"]
        assert "B01003_001E" in variables
        assert "B01003_001M" in variables

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_summary_var_tidy_format(self, mock_api_class):
        """Test summary_var functionality in tidy format with realistic race data."""
        # Mock realistic API response with race variables and summary var
        mock_api = Mock()
        mock_api.get.return_value = [
            {
                "B03002_003E": "12993",  # White
                "B03002_003M": "56",  # White MOE
                "B03002_004E": "544",  # Black
                "B03002_004M": "56",  # Black MOE
                "B03002_005E": "51979",  # Native
                "B03002_005M": "327",  # Native MOE
                "B03002_001E": "71714",  # Total (summary var)
                "B03002_001M": "0",  # Total MOE
                "state": "04",
                "county": "001",
                "NAME": "Apache County, Arizona",
            },
            {
                "B03002_003E": "69095",  # White
                "B03002_003M": "350",  # White MOE
                "B03002_004E": "1024",  # Black
                "B03002_004M": "89",  # Black MOE
                "B03002_005E": "2156",  # Native
                "B03002_005M": "145",  # Native MOE
                "B03002_001E": "75045",  # Total (summary var)
                "B03002_001M": "0",  # Total MOE
                "state": "04",
                "county": "003",
                "NAME": "Cochise County, Arizona",
            },
        ]
        mock_api_class.return_value = mock_api

        # Test race variables with summary var
        race_vars = {
            "White": "B03002_003",
            "Black": "B03002_004",
            "Native": "B03002_005",
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

        # Verify result structure
        assert isinstance(result, pd.DataFrame)

        # Check expected columns for R tidycensus format
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

        # Verify we have 6 rows (2 counties × 3 race variables)
        assert len(result) == 6

        # Check that summary variable is NOT in the main data
        unique_vars = result["variable"].unique()
        assert "B03002_001" not in unique_vars, "Summary variable should be excluded from main data"
        assert "White" in unique_vars  # Custom variable names should be preserved
        assert "Black" in unique_vars
        assert "Native" in unique_vars

        # Verify summary values are correctly joined
        apache_white = result[(result["GEOID"] == "04001") & (result["variable"] == "White")]
        assert len(apache_white) == 1
        assert apache_white["estimate"].iloc[0] == 12993
        assert apache_white["moe"].iloc[0] == 56.0
        assert apache_white["summary_est"].iloc[0] == 71714
        assert apache_white["summary_moe"].iloc[0] == 0.0

        # Verify summary values are the same for all variables in same geography
        apache_rows = result[result["GEOID"] == "04001"]
        summary_est_values = apache_rows["summary_est"].unique()
        summary_moe_values = apache_rows["summary_moe"].unique()
        assert len(summary_est_values) == 1 and summary_est_values[0] == 71714
        assert len(summary_moe_values) == 1 and summary_moe_values[0] == 0.0

        # Verify summary columns are numeric types
        assert result["summary_est"].dtype in [
            "int64",
            "float64",
        ], f"summary_est dtype is {result['summary_est'].dtype}"
        assert result["summary_moe"].dtype in [
            "int64",
            "float64",
        ], f"summary_moe dtype is {result['summary_moe'].dtype}"


class TestGetACSVariables:
    """Test cases for the get_acs_variables function."""

    @patch("pytidycensus.variables.load_variables")
    def test_get_acs_variables_default(self, mock_load_vars):
        """Test getting ACS variables with default parameters."""
        mock_df = pd.DataFrame({"name": ["B01001_001E"], "label": ["Total population"]})
        mock_load_vars.return_value = mock_df

        result = get_acs_variables()

        mock_load_vars.assert_called_once_with(2022, "acs", "acs5")
        assert isinstance(result, pd.DataFrame)

    @patch("pytidycensus.variables.load_variables")
    def test_get_acs_variables_custom(self, mock_load_vars):
        """Test getting ACS variables with custom parameters."""
        mock_df = pd.DataFrame({"name": ["B01001_001E"], "label": ["Total population"]})
        mock_load_vars.return_value = mock_df

        result = get_acs_variables(year=2020, survey="acs1")

        mock_load_vars.assert_called_once_with(2020, "acs", "acs1")
        assert isinstance(result, pd.DataFrame)
