"""Tests for the Census API client."""

import json
import os
from unittest.mock import Mock, patch

import pytest
import requests

from pytidycensus.api import CensusAPI, set_census_api_key


class TestCensusAPI:
    """Test cases for the CensusAPI class."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        api = CensusAPI(api_key="test_key")
        assert api.api_key == "test_key"

    def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        with patch.dict(os.environ, {"CENSUS_API_KEY": "env_key"}):
            api = CensusAPI()
            assert api.api_key == "env_key"

    def test_init_without_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Census API key is required"):
                CensusAPI()

    def test_build_url(self):
        """Test URL building for different datasets."""
        api = CensusAPI(api_key="test")

        # Test ACS URL
        url = api._build_url(2022, "acs", "acs5")
        assert url == "https://api.census.gov/data/2022/acs/acs5"

        # Test decennial URL
        url = api._build_url(2020, "dec", "pl")
        assert url == "https://api.census.gov/data/2020/dec/pl"

        # Test without survey
        url = api._build_url(2022, "pep")
        assert url == "https://api.census.gov/data/2022/pep"

    @patch("pytidycensus.api.requests.Session.get")
    def test_successful_api_call(self, mock_get):
        """Test successful API call."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = [
            ["NAME", "B01001_001E", "state"],
            ["Alabama", "5024279", "01"],
            ["Alaska", "733391", "02"],
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")

        result = api.get(
            year=2022,
            dataset="acs",
            variables=["B01001_001E"],
            geography={"for": "state:*"},
            survey="acs5",
        )

        expected = [
            {"NAME": "Alabama", "B01001_001E": "5024279", "state": "01"},
            {"NAME": "Alaska", "B01001_001E": "733391", "state": "02"},
        ]

        assert result == expected

    @patch("pytidycensus.api.requests.Session.get")
    def test_api_error_response(self, mock_get):
        """Test handling of API error responses."""
        # Mock error response
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid variable code"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")

        with pytest.raises(ValueError, match="Census API error"):
            api.get(
                year=2022,
                dataset="acs",
                variables=["INVALID"],
                geography={"for": "state:*"},
                survey="acs5",
            )

    @patch("pytidycensus.api.requests.Session.get")
    def test_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = requests.RequestException("Network error")

        api = CensusAPI(api_key="test")

        with pytest.raises(requests.RequestException, match="Failed to fetch data"):
            api.get(
                year=2022,
                dataset="acs",
                variables=["B01001_001E"],
                geography={"for": "state:*"},
                survey="acs5",
            )

    @patch("pytidycensus.api.requests.Session.get")
    def test_show_call_parameter(self, mock_get, capsys):
        """Test that show_call parameter prints the URL."""
        mock_response = Mock()
        mock_response.json.return_value = [["test"], ["data"]]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")

        api.get(
            year=2022,
            dataset="acs",
            variables=["B01001_001E"],
            geography={"for": "state:*"},
            survey="acs5",
            show_call=True,
        )

        captured = capsys.readouterr()
        assert "Census API call:" in captured.out
        assert "https://api.census.gov/data/2022/acs/acs5" in captured.out

    @patch("pytidycensus.api.requests.Session.get")
    def test_get_variables(self, mock_get):
        """Test fetching variables metadata."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "variables": {"B01001_001E": {"label": "Total population", "concept": "Sex by Age"}}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")
        result = api.get_variables(2022, "acs", "acs5")

        assert "variables" in result
        assert "B01001_001E" in result["variables"]

    def test_rate_limiting(self):
        """Test that rate limiting is enforced."""
        api = CensusAPI(api_key="test")

        # Mock time.time to control timing
        with patch("pytidycensus.api.time.time") as mock_time, patch(
            "pytidycensus.api.time.sleep"
        ) as mock_sleep:
            # Simulate rapid successive calls - first call at 0, second at 0.05 (too soon), then 0.15
            mock_time.side_effect = [0, 0.05, 0.15, 0.25]  # Added more time values

            api._rate_limit()  # First call
            api._rate_limit()  # Second call should trigger sleep

            # Should have called sleep at least once
            assert mock_sleep.call_count >= 1

    @patch("requests.Session.get")
    def test_api_request_exception(self, mock_get):
        """Test API request exception handling."""
        mock_get.side_effect = requests.RequestException("Network error")

        api = CensusAPI(api_key="test")

        with pytest.raises(requests.RequestException, match="Failed to fetch data from Census API"):
            api.get(2022, "acs", ["B01001_001E"], {"for": "state:*"}, "acs5")

    @patch("requests.Session.get")
    def test_get_geography_codes_success(self, mock_get):
        """Test successful geography codes retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {"fips": "Alabama"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")
        result = api.get_geography_codes(2022, "acs", "acs5")

        assert result == {"fips": "Alabama"}
        mock_get.assert_called_once()
        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "geography.json" in call_args

    @patch("requests.Session.get")
    def test_get_geography_codes_error(self, mock_get):
        """Test geography codes retrieval error handling."""
        mock_get.side_effect = requests.RequestException("API error")

        api = CensusAPI(api_key="test")

        with pytest.raises(requests.RequestException, match="Failed to fetch geography codes"):
            api.get_geography_codes(2022, "acs", "acs5")

    @patch("requests.Session.get")
    def test_get_variables_success(self, mock_get):
        """Test successful variables retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "variables": {"B01001_001E": {"label": "Total population"}}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")
        result = api.get_variables(2022, "acs", "acs5")

        assert "variables" in result
        assert "B01001_001E" in result["variables"]
        mock_get.assert_called_once()
        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "variables.json" in call_args

    @patch("requests.Session.get")
    def test_get_variables_error(self, mock_get):
        """Test variables retrieval error handling."""
        mock_get.side_effect = requests.RequestException("API error")

        api = CensusAPI(api_key="test")

        with pytest.raises(requests.RequestException, match="Failed to fetch variables"):
            api.get_variables(2022, "acs", "acs5")

    @patch("requests.Session.get")
    def test_api_response_not_list_format(self, mock_get):
        """Test API response that's not in list format."""
        mock_response = Mock()
        # Response that's not a list - should return as-is
        mock_response.json.return_value = {"some": "data"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")
        result = api.get(2022, "acs", ["B01001_001E"], {"for": "state:*"}, "acs5")

        # Should return the data as-is since it's not a list
        assert result == {"some": "data"}

    @patch("requests.Session.get")
    def test_json_decode_error_handling(self, mock_get):
        """Test handling of non-JSON responses from API."""
        mock_response = Mock()
        mock_response.text = "<html><title>Invalid Key</title><body>Invalid API key</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")

        with pytest.raises(ValueError, match="Census API returned invalid response"):
            api.get(2022, "acs", ["B01001_001E"], {"for": "state:*"}, "acs5")

    @patch("requests.Session.get")
    def test_json_decode_error_handling_variables(self, mock_get):
        """Test handling of non-JSON responses for variables endpoint."""
        mock_response = Mock()
        mock_response.text = "<html><title>Invalid Key</title><body>Invalid API key</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")

        with pytest.raises(ValueError, match="Census API returned invalid response for variables"):
            api.get_variables(2022, "acs", "acs5")

    @patch("requests.Session.get")
    def test_json_decode_error_handling_geography_codes(self, mock_get):
        """Test handling of non-JSON responses for geography codes endpoint."""
        mock_response = Mock()
        mock_response.text = "<html><title>Invalid Key</title><body>Invalid API key</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")

        with pytest.raises(
            ValueError, match="Census API returned invalid response for geography codes"
        ):
            api.get_geography_codes(2022, "acs", "acs5")

    @patch("requests.Session.get")
    def test_api_response_single_item_list(self, mock_get):
        """Test API response with single item list."""
        mock_response = Mock()
        # Single-item list should return as-is
        mock_response.json.return_value = ["single_item"]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api = CensusAPI(api_key="test")
        result = api.get(2022, "acs", ["B01001_001E"], {"for": "state:*"}, "acs5")

        # Should return the data as-is since it has only one item
        assert result == ["single_item"]


class TestSetCensusAPIKey:
    """Test cases for the set_census_api_key function."""

    def test_set_api_key(self, capsys):
        """Test setting API key as environment variable."""
        set_census_api_key("r" * 40)

        assert os.environ["CENSUS_API_KEY"] == "r" * 40

        captured = capsys.readouterr()
        assert "Census API key has been set" in captured.out


@pytest.fixture(autouse=True)
def cleanup_env():
    """Clean up environment variables after each test."""
    yield
    # Clean up after test
    if "CENSUS_API_KEY" in os.environ:
        del os.environ["CENSUS_API_KEY"]
