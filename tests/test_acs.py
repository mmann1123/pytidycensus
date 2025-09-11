"""
Tests for ACS data retrieval functions.
"""

import pytest
import pandas as pd
import geopandas as gpd
from unittest.mock import Mock, patch, MagicMock
from pytidycensus.acs import get_acs, get_acs_variables


class TestGetACS:
    """Test cases for the get_acs function."""
    
    @patch('pytidycensus.acs.CensusAPI')
    @patch('pytidycensus.acs.process_census_data')
    @patch('pytidycensus.acs.add_margin_of_error')
    def test_get_acs_basic(self, mock_add_moe, mock_process, mock_api_class):
        """Test basic ACS data retrieval."""
        # Mock API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "B01001_001E": "5024279", "B01001_001M": "1000", "state": "01"}
        ]
        mock_api_class.return_value = mock_api
        
        # Mock processing functions
        mock_df = pd.DataFrame({
            "NAME": ["Alabama"],
            "B01001_001E": [5024279],
            "state": ["01"],
            "variable": ["B01001_001E"],
            "value": [5024279]
        })
        mock_process.return_value = mock_df
        mock_add_moe.return_value = mock_df
        
        result = get_acs(
            geography="state",
            variables="B01001_001E",
            year=2022,
            api_key="test"
        )
        
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
    
    @patch('pytidycensus.acs.CensusAPI')
    @patch('pytidycensus.variables.load_variables')
    def test_get_acs_with_table(self, mock_load_vars, mock_api_class):
        """Test ACS data retrieval with table parameter."""
        # Mock variables loading
        mock_vars_df = pd.DataFrame({
            'name': ['B19013_001E', 'B19013_002E'],
            'label': ['Median household income', 'Something else']
        })
        mock_load_vars.return_value = mock_vars_df
        
        # Mock API
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api
        
        with patch('pytidycensus.acs.process_census_data') as mock_process, \
             patch('pytidycensus.acs.add_margin_of_error') as mock_add_moe:
            mock_process.return_value = pd.DataFrame()
            mock_add_moe.return_value = pd.DataFrame()
            
            get_acs(
                geography="state",
                table="B19013",
                year=2022,
                api_key="test"
            )
        
        # Should load variables for the table (using cache_table parameter default=False)
        mock_load_vars.assert_called_once_with(2022, "acs", "acs5", cache=False)
        
        # Should call API with table variables
        call_args = mock_api.get.call_args[1]["variables"]
        assert "B19013_001E" in call_args
        assert "B19013_001M" in call_args  # MOE variables
    
    @patch('pytidycensus.acs.CensusAPI')
    @patch('pytidycensus.acs.get_geography')
    def test_get_acs_with_geometry(self, mock_get_geo, mock_api_class):
        """Test ACS data retrieval with geometry."""
        # Mock API response
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "B01001_001E": "5024279", "GEOID": "01", "state": "01"}
        ]
        mock_api_class.return_value = mock_api
        
        # Mock geometry data
        mock_gdf = gpd.GeoDataFrame({
            "GEOID": ["01"],
            "NAME": ["Alabama"],
            "geometry": [None]  # Simplified for test
        })
        mock_get_geo.return_value = mock_gdf
        
        with patch('pytidycensus.acs.process_census_data') as mock_process, \
             patch('pytidycensus.acs.add_margin_of_error') as mock_add_moe:
            
            mock_df = pd.DataFrame({
                "NAME": ["Alabama"],
                "B01001_001E": [5024279],
                "GEOID": ["01"]
            })
            mock_process.return_value = mock_df
            mock_add_moe.return_value = mock_df
            
            result = get_acs(
                geography="state",
                variables="B01001_001E",
                geometry=True,
                api_key="test"
            )
        
        # Should call get_geography
        mock_get_geo.assert_called_once()
        
        # Result should be merged with geometry
        assert "GEOID" in result.columns
    
    def test_get_acs_validation_errors(self):
        """Test validation errors in get_acs."""
        # No variables or table
        with pytest.raises(ValueError, match="Either a vector of variables or an ACS table must be specified"):
            get_acs(geography="state", api_key="test")
        
        # Both variables and table
        with pytest.raises(ValueError, match="Specify variables or a table to retrieve"):
            get_acs(geography="state", variables="B01001_001E", table="B19013", api_key="test")
        
        # Invalid survey
        with pytest.raises(ValueError, match="Survey must be"):
            get_acs(geography="state", variables="B01001_001E", survey="invalid", api_key="test")
    
    @patch('pytidycensus.acs.CensusAPI')
    def test_get_acs_different_surveys(self, mock_api_class):
        """Test get_acs with different survey types."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api
        
        with patch('pytidycensus.acs.process_census_data') as mock_process, \
             patch('pytidycensus.acs.add_margin_of_error') as mock_add_moe:
            mock_process.return_value = pd.DataFrame()
            mock_add_moe.return_value = pd.DataFrame()
            
            # Test ACS5
            get_acs(geography="state", variables="B01001_001E", survey="acs5", api_key="test")
            call_args = mock_api.get.call_args[1]
            assert call_args["survey"] == "acs5"
            
            # Test ACS1
            get_acs(geography="state", variables="B01001_001E", survey="acs1", api_key="test")
            call_args = mock_api.get.call_args[1]
            assert call_args["survey"] == "acs1"
    
    def test_get_acs_multiple_variables(self):
        """Test get_acs with multiple variables."""
        with patch('pytidycensus.acs.CensusAPI') as mock_api_class, \
             patch('pytidycensus.acs.process_census_data') as mock_process, \
             patch('pytidycensus.acs.add_margin_of_error') as mock_add_moe:
            
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
    
    @patch('pytidycensus.acs.CensusAPI')
    @patch('pytidycensus.variables.load_variables')
    def test_get_acs_table_not_found(self, mock_load_vars, mock_api_class):
        """Test get_acs with table that has no variables."""
        # Mock empty variables result
        mock_vars_df = pd.DataFrame({
            'name': ['B01001_001E', 'B01001_002E'], 
            'label': ['Population', 'Something else']
        })
        mock_load_vars.return_value = mock_vars_df
        
        with pytest.raises(ValueError, match="No variables found for table"):
            get_acs(geography="state", table="B99999", api_key="test")
    
    @patch('pytidycensus.acs.CensusAPI')
    def test_get_acs_non_standard_variables(self, mock_api_class):
        """Test get_acs with variables that don't end in E."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api
        
        with patch('pytidycensus.acs.process_census_data') as mock_process, \
             patch('pytidycensus.acs.add_margin_of_error') as mock_add_moe:
            mock_process.return_value = pd.DataFrame()
            mock_add_moe.return_value = pd.DataFrame()
            
            # Test variable that doesn't end in E or M
            get_acs(geography="state", variables="B01001_001", api_key="test")
            
            call_args = mock_api.get.call_args[1]["variables"]
            assert "B01001_001" in call_args
            assert "B01001_001M" in call_args  # MOE should be added
    
    @patch('pytidycensus.acs.CensusAPI')
    @patch('pytidycensus.acs.get_geography')
    def test_get_acs_geometry_merge_warning(self, mock_get_geo, mock_api_class):
        """Test warning when geometry merge fails due to missing GEOID."""
        # Mock API response without GEOID
        mock_api = Mock()
        mock_api.get.return_value = [
            {"NAME": "Alabama", "B01001_001E": "5024279", "state": "01"}
        ]
        mock_api_class.return_value = mock_api
        
        # Mock geometry data with GEOID
        mock_gdf = gpd.GeoDataFrame({
            "GEOID": ["01"],
            "NAME": ["Alabama"],
            "geometry": [None]
        })
        mock_get_geo.return_value = mock_gdf
        
        with patch('pytidycensus.acs.process_census_data') as mock_process, \
             patch('pytidycensus.acs.add_margin_of_error') as mock_add_moe:
            
            # Census data without GEOID
            mock_df = pd.DataFrame({
                "NAME": ["Alabama"],
                "B01001_001E": [5024279],
                "state": ["01"]
            })
            mock_process.return_value = mock_df
            mock_add_moe.return_value = mock_df
            
            # Should return census data without geometry merge
            result = get_acs(
                geography="state",
                variables="B01001_001E", 
                geometry=True,
                api_key="test"
            )
            
            # Should be the original DataFrame, not merged
            assert "geometry" not in result.columns
    
    @patch('pytidycensus.acs.CensusAPI')
    def test_get_acs_api_error(self, mock_api_class):
        """Test get_acs handles API errors properly."""
        mock_api = Mock()
        mock_api.get.side_effect = Exception("API request failed")
        mock_api_class.return_value = mock_api
        
        with pytest.raises(Exception, match="Failed to retrieve ACS data: API request failed"):
            get_acs(geography="state", variables="B01001_001E", api_key="test")


class TestGetACSVariables:
    """Test cases for the get_acs_variables function."""
    
    @patch('pytidycensus.variables.load_variables')
    def test_get_acs_variables_default(self, mock_load_vars):
        """Test getting ACS variables with default parameters."""
        mock_df = pd.DataFrame({'name': ['B01001_001E'], 'label': ['Total population']})
        mock_load_vars.return_value = mock_df
        
        result = get_acs_variables()
        
        mock_load_vars.assert_called_once_with(2022, "acs", "acs5")
        assert isinstance(result, pd.DataFrame)
    
    @patch('pytidycensus.variables.load_variables')
    def test_get_acs_variables_custom(self, mock_load_vars):
        """Test getting ACS variables with custom parameters."""
        mock_df = pd.DataFrame({'name': ['B01001_001E'], 'label': ['Total population']})
        mock_load_vars.return_value = mock_df
        
        result = get_acs_variables(year=2020, survey="acs1")
        
        mock_load_vars.assert_called_once_with(2020, "acs", "acs1")
        assert isinstance(result, pd.DataFrame)