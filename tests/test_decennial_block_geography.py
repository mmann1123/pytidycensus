"""Tests for block geography in Decennial Census."""

from unittest.mock import Mock, patch

import pytest

from pytidycensus.decennial import get_decennial
from pytidycensus.utils import build_geography_params, validate_geography


class TestDecennialBlockGeography:
    """Test that block geography works correctly in Decennial Census."""

    def test_validate_geography_allows_block_for_decennial(self):
        """Test that validate_geography allows block for decennial dataset."""
        result = validate_geography("block", dataset="decennial")
        assert result == "block"

    def test_build_geography_params_handles_block_geography(self):
        """Test that build_geography_params correctly handles block geography."""
        # Test basic block geography
        params = build_geography_params("block")
        assert params["for"] == "block:*"
        assert "in" not in params

        # Test block geography with state
        params = build_geography_params("block", state="OK")
        assert params["for"] == "block:*"
        assert params["in"] == "state:40"

        # Test block geography with state and county
        params = build_geography_params("block", state="OK", county="025")
        assert params["for"] == "block:*"
        assert params["in"] == "state:40 county:025"

    @patch("pytidycensus.decennial.CensusAPI")
    def test_get_decennial_accepts_block_geography(self, mock_api_class):
        """Test that get_decennial accepts block geography without errors."""
        mock_api = Mock()
        mock_api.get.return_value = [
            {"H1_001N": "4", "state": "40", "county": "025", "tract": "000100", "block": "1000"}
        ]
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.decennial.process_census_data") as mock_process:
            import pandas as pd

            mock_process.return_value = pd.DataFrame(
                {
                    "H1_001N": ["4"],
                    "state": ["40"],
                    "county": ["025"],
                    "tract": ["000100"],
                    "block": ["1000"],
                    "GEOID": ["40025000100001000"],
                }
            )

            # This should not raise any NotImplementedError
            result = get_decennial(
                geography="block",
                variables="H1_001N",
                state="OK",
                county="025",
                year=2020,
                sumfile="pl",
                api_key="test",
            )

        # Verify the API call was made correctly
        mock_api.get.assert_called_once()
        call_kwargs = mock_api.get.call_args[1]
        assert call_kwargs["geography"]["for"] == "block:*"
        assert call_kwargs["geography"]["in"] == "state:40 county:025"

    def test_validate_geography_rejects_block_for_acs(self):
        """Test that validate_geography rejects block for ACS dataset."""
        with pytest.raises(NotImplementedError, match="not available in ACS data"):
            validate_geography("block", dataset="acs")

    def test_validate_geography_allows_block_for_estimates(self):
        """Test behavior with estimates dataset (should reject since blocks not in estimates)."""
        with pytest.raises(NotImplementedError, match="not available in estimates data"):
            validate_geography("block", dataset="estimates")

    def test_validate_geography_backwards_compatibility(self):
        """Test that block works when no dataset is specified (backwards compatibility)."""
        result = validate_geography("block")
        assert result == "block"
