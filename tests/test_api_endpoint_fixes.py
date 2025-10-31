"""Tests for API endpoint fixes and dataset normalization.

These tests verify that user-friendly dataset names work correctly and
that the API builds proper URLs for different years and datasets.
"""

from unittest.mock import Mock, patch

import pytest

from pytidycensus.api import CensusAPI
from pytidycensus.variables import load_variables, search_variables


class TestAPIEndpointFixes:
    """Test fixes for API endpoint construction and dataset normalization."""

    @patch.dict("os.environ", {"CENSUS_API_KEY": "test_key"})
    def test_dataset_normalization(self):
        """Test that dataset names are normalized correctly."""
        api = CensusAPI()

        # Test decennial normalization
        assert api._normalize_dataset("decennial") == "dec"
        assert api._normalize_dataset("DECENNIAL") == "dec"
        assert api._normalize_dataset("dec") == "dec"

        # Test ACS normalization
        assert api._normalize_dataset("american_community_survey") == "acs"
        assert api._normalize_dataset("acs") == "acs"

        # Test unknown dataset (should pass through)
        assert api._normalize_dataset("unknown") == "unknown"

    @patch.dict("os.environ", {"CENSUS_API_KEY": "test_key"})
    def test_build_url_with_dataset_normalization(self):
        """Test URL building with dataset normalization."""
        api = CensusAPI()

        # Test decennial URL building
        url_2010 = api._build_url(2010, "decennial", "sf1")
        assert url_2010 == "https://api.census.gov/data/2010/dec/sf1"

        url_2020 = api._build_url(2020, "decennial", "pl")
        assert url_2020 == "https://api.census.gov/data/2020/dec/pl"

        # Test ACS URL building
        url_acs = api._build_url(2022, "acs", "acs5")
        assert url_acs == "https://api.census.gov/data/2022/acs/acs5"

        # Test user-friendly names
        url_friendly = api._build_url(2020, "american_community_survey", "acs5")
        assert url_friendly == "https://api.census.gov/data/2020/acs/acs5"

    @patch.dict("os.environ", {"CENSUS_API_KEY": "test_key"})
    def test_variables_url_construction(self):
        """Test that variables URLs are constructed correctly."""
        api = CensusAPI()

        with patch.object(api, "session") as mock_session:
            mock_response = Mock()
            mock_response.json.return_value = {"variables": {}}
            mock_session.get.return_value = mock_response

            # Test 2010 decennial variables URL
            api.get_variables(2010, "decennial", "sf1")
            expected_url = "https://api.census.gov/data/2010/dec/sf1/variables.json"
            mock_session.get.assert_called_with(expected_url, timeout=30)

            # Test 2020 decennial variables URL
            api.get_variables(2020, "decennial", "pl")
            expected_url = "https://api.census.gov/data/2020/dec/pl/variables.json"
            mock_session.get.assert_called_with(expected_url, timeout=30)

    def test_search_variables_with_user_friendly_names(self):
        """Test that search_variables works with user-friendly dataset names."""
        import pandas as pd

        # Mock load_variables to return test data
        mock_df = pd.DataFrame(
            {
                "name": ["P001001", "P001002"],
                "label": ["Total", "Male"],
                "concept": ["TOTAL POPULATION", "TOTAL POPULATION"],
            }
        )

        with patch("pytidycensus.variables.load_variables") as mock_load:
            mock_load.return_value = mock_df

            result = search_variables(
                pattern="total", year=2010, dataset="decennial", field="label"  # User-friendly name
            )

            # Verify load_variables was called with normalized parameters
            mock_load.assert_called_once_with(2010, "decennial", None)

            # Verify result is correct
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1  # Should find "Total" but not "Male"
            assert result.iloc[0]["name"] == "P001001"

    def test_default_survey_selection(self):
        """Test automatic survey selection for decennial data."""
        from pytidycensus.variables import _get_default_survey

        # Test 2010 defaults to sf1
        assert _get_default_survey(2010, "decennial") == "sf1"
        assert _get_default_survey(2010, "dec") == "sf1"

        # Test 2020 defaults to pl
        assert _get_default_survey(2020, "decennial") == "pl"
        assert _get_default_survey(2020, "dec") == "pl"

        # Test 2000 defaults to sf1
        assert _get_default_survey(2000, "decennial") == "sf1"

        # Test ACS has no default
        assert _get_default_survey(2020, "acs") is None

    @patch("pytidycensus.variables.CensusAPI")
    @patch("pytidycensus.variables.os.path.exists", return_value=False)  # Disable cache
    def test_load_variables_with_automatic_survey(self, mock_exists, mock_api_class):
        """Test that load_variables automatically selects survey when none provided."""
        mock_api = Mock()
        mock_api.get_variables.return_value = {"variables": {}}
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.variables._parse_variables") as mock_parse:
            import pandas as pd

            mock_parse.return_value = pd.DataFrame()

            # Test 2010 decennial without survey - should auto-select sf1
            load_variables(2010, "decennial", cache=False)
            mock_api.get_variables.assert_called_with(2010, "decennial", "sf1")

            # Test 2020 decennial without survey - should auto-select pl
            load_variables(2020, "decennial", cache=False)
            mock_api.get_variables.assert_called_with(2020, "decennial", "pl")

    @patch.dict("os.environ", {"CENSUS_API_KEY": "test_key"})
    def test_census_api_error_handling(self):
        """Test that proper error messages are shown for API failures."""
        import requests

        api = CensusAPI()

        with patch.object(api, "session") as mock_session:
            # Mock 404 error
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.RequestException(
                "404 Client Error"
            )
            mock_session.get.return_value = mock_response

            with pytest.raises(requests.RequestException, match="Failed to fetch variables"):
                api.get_variables(2010, "invalid_dataset", "invalid_survey")

    @pytest.mark.integration
    def test_real_api_endpoints_work(self):
        """Integration test to verify real API endpoints work."""
        # Skip if no API key available
        import os

        api_key = os.environ.get("CENSUS_API_KEY")
        if not api_key:
            pytest.skip("Census API key not available")

        # Test that the real endpoints work
        try:
            # Test user-friendly search
            result_2010 = search_variables("total", 2010, "decennial", field="label")
            assert len(result_2010) > 0, "Should find 2010 variables"

            result_2020 = search_variables("total", 2020, "decennial", field="label")
            assert len(result_2020) > 0, "Should find 2020 variables"

            # Verify key variables exist
            p001_found = any(result_2010["name"] == "P001001")
            p1_found = any(result_2020["name"] == "P1_001N")

            assert p001_found, "Should find P001001 in 2010 data"
            assert p1_found, "Should find P1_001N in 2020 data"

        except Exception as e:
            pytest.fail(f"Real API endpoints failed: {e}")


class TestDatasetCompatibility:
    """Test backward compatibility with existing dataset names."""

    @patch.dict("os.environ", {"CENSUS_API_KEY": "test_key"})
    def test_existing_tests_still_work(self):
        """Test that existing code using 'dec' still works."""
        api = CensusAPI()

        # Existing code using 'dec' should continue to work
        url = api._build_url(2020, "dec", "pl")
        assert url == "https://api.census.gov/data/2020/dec/pl"

    @patch.dict("os.environ", {"CENSUS_API_KEY": "test_key"})
    def test_mixed_case_handling(self):
        """Test that mixed case dataset names are handled."""
        api = CensusAPI()

        # Test various cases
        assert api._normalize_dataset("Decennial") == "dec"
        assert api._normalize_dataset("DECENNIAL") == "dec"
        assert api._normalize_dataset("decennial") == "dec"
        assert api._normalize_dataset("Dec") == "dec"
        assert api._normalize_dataset("DEC") == "dec"

    @patch("pytidycensus.variables.CensusAPI")
    @patch("pytidycensus.variables.os.path.exists", return_value=False)  # Disable cache
    def test_backward_compatibility_with_explicit_survey(self, mock_exists, mock_api_class):
        """Test that explicit survey parameters override defaults."""
        mock_api = Mock()
        mock_api.get_variables.return_value = {"variables": {}}
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.variables._parse_variables") as mock_parse:
            import pandas as pd

            mock_parse.return_value = pd.DataFrame()

            # Test that explicit survey is used even when default exists
            load_variables(2020, "decennial", survey="dhc", cache=False)
            mock_api.get_variables.assert_called_with(2020, "decennial", "dhc")

            # Verify default is NOT used when survey is explicitly provided
            assert mock_api.get_variables.call_args[0][2] == "dhc"
