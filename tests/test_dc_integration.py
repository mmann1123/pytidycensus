"""Integration tests for DC state parameter handling."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pytidycensus import get_acs, get_decennial


class TestDCIntegration:
    """Test that DC works as a state parameter in main functions."""

    @patch("pytidycensus.acs.CensusAPI")
    def test_get_acs_with_dc_variations(self, mock_api_class):
        """Test that get_acs accepts all DC variations."""
        # Mock the API response
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get.return_value = [
            {"B01003_001E": "705749", "state": "11", "NAME": "District of Columbia"}
        ]

        dc_variations = ["DC", "11", "District of Columbia"]

        for dc_var in dc_variations:
            # This should not raise any validation errors
            try:
                result = get_acs(
                    geography="state",
                    variables=["B01003_001E"],
                    state=dc_var,
                    year=2020,
                    output="tidy",
                    api_key="test_key",
                )

                # Verify the result is a DataFrame
                assert isinstance(result, pd.DataFrame)

                # Verify the API was called with the correct parameters
                mock_api.get.assert_called()
                call_args = mock_api.get.call_args

                # Should have converted DC to FIPS 11
                geography_param = call_args[1]["geography"]
                assert "11" in str(geography_param), f"Failed for {dc_var}: {geography_param}"

            except Exception as e:
                pytest.fail(f"get_acs failed for DC variation '{dc_var}': {e}")

    @patch("pytidycensus.decennial.CensusAPI")
    def test_get_decennial_with_dc_variations(self, mock_api_class):
        """Test that get_decennial accepts all DC variations."""
        # Mock the API response
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get.return_value = [
            {"P1_001N": "689545", "state": "11", "NAME": "District of Columbia"}
        ]

        dc_variations = ["DC", "11", "District of Columbia"]

        for dc_var in dc_variations:
            try:
                result = get_decennial(
                    geography="state",
                    variables=["P1_001N"],
                    state=dc_var,
                    year=2020,
                    api_key="test_key",
                )

                assert isinstance(result, pd.DataFrame)

                # Verify the API was called
                mock_api.get.assert_called()
                call_args = mock_api.get.call_args
                geography_param = call_args[1]["geography"]
                assert "11" in str(geography_param), f"Failed for {dc_var}: {geography_param}"

            except Exception as e:
                pytest.fail(f"get_decennial failed for DC variation '{dc_var}': {e}")

    @patch("pytidycensus.acs.CensusAPI")
    def test_mixed_states_including_dc(self, mock_api_class):
        """Test multiple states including DC."""
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get.return_value = [
            {"B01003_001E": "39538223", "state": "06", "NAME": "California"},
            {"B01003_001E": "705749", "state": "11", "NAME": "District of Columbia"},
            {"B01003_001E": "19453561", "state": "36", "NAME": "New York"},
        ]

        try:
            result = get_acs(
                geography="state",
                variables=["B01003_001E"],
                state=["CA", "DC", "New York"],  # Mixed formats with DC
                year=2020,
                api_key="test_key",
                output="tidy",
            )

            assert isinstance(result, pd.DataFrame)
            mock_api.get.assert_called()

        except Exception as e:
            pytest.fail(f"Mixed states with DC failed: {e}")

    def test_dc_edge_cases(self):
        """Test DC edge cases in validation."""
        from pytidycensus.utils import validate_state

        # Test case insensitive
        assert validate_state("dc") == ["11"]
        assert validate_state("DC") == ["11"]
        assert validate_state("Dc") == ["11"]

        # Test with whitespace
        assert validate_state(" DC ") == ["11"]
        assert validate_state(" District of Columbia ") == ["11"]

        # Test alternative formats
        assert validate_state("D.C.") == ["11"]

        # Test in lists with other states
        result = validate_state(["CA", "DC", "NY"])
        assert result == ["06", "11", "36"]


if __name__ == "__main__":
    # Run a simple test
    test = TestDCIntegration()
    test.test_dc_edge_cases()
    print("✅ DC edge case tests passed!")
