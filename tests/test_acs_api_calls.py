"""Tests for ACS API call generation against Census Bureau examples.

This test suite verifies that the pytidycensus package generates correct
API URLs for various geography levels as documented in the Census
Bureau's ACS5 examples.
"""

import urllib.parse as urlparse
from unittest.mock import Mock, patch

from pytidycensus.acs import get_acs


class TestACSAPICallGeneration:
    """Test API call generation for various ACS geographies."""

    def parse_url_params(self, url):
        """Helper to parse URL parameters for comparison."""
        parsed = urlparse.urlparse(url)
        params = urlparse.parse_qs(parsed.query)
        # Convert single-item lists to strings for easier comparison
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    @patch("pytidycensus.acs.CensusAPI")
    def test_us_geography_api_call(self, mock_api_class):
        """Test US-level geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            get_acs(geography="us", variables="B01001_001E", year=2023, api_key="test")

        # Verify the API call was made correctly
        mock_api.get.assert_called_once()
        call_kwargs = mock_api.get.call_args[1]

        assert call_kwargs["year"] == 2023
        assert call_kwargs["dataset"] == "acs"
        assert call_kwargs["survey"] == "acs5"
        assert "B01001_001E" in call_kwargs["variables"]
        assert call_kwargs["geography"]["for"] == "us:*"

    @patch("pytidycensus.acs.CensusAPI")
    def test_region_geography_api_call(self, mock_api_class):
        """Test region-level geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            get_acs(geography="region", variables="B01001_001E", year=2023, api_key="test")

        # Verify the API call parameters
        call_kwargs = mock_api.get.call_args[1]
        assert call_kwargs["geography"]["for"] == "region:*"

    @patch("pytidycensus.acs.CensusAPI")
    def test_division_geography_api_call(self, mock_api_class):
        """Test division-level geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            get_acs(geography="division", variables="B01001_001E", year=2023, api_key="test")

        # Verify the API call parameters
        call_kwargs = mock_api.get.call_args[1]
        assert call_kwargs["geography"]["for"] == "division:*"

    @patch("pytidycensus.acs.CensusAPI")
    def test_state_geography_api_call(self, mock_api_class):
        """Test state-level geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test all states
            get_acs(geography="state", variables="B01001_001E", year=2023, api_key="test")
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "state:*"

            # Test specific state
            get_acs(
                geography="state", state="06", variables="B01001_001E", year=2023, api_key="test"
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "state:06"

    @patch("pytidycensus.acs.CensusAPI")
    def test_county_geography_api_call(self, mock_api_class):
        """Test county-level geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test all counties
            get_acs(geography="county", variables="B01001_001E", year=2023, api_key="test")
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "county:*"

            # Test counties in a state
            get_acs(
                geography="county", state="06", variables="B01001_001E", year=2023, api_key="test"
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "county:*"
            assert call_kwargs["geography"]["in"] == "state:06"

            # Test specific county in a state
            get_acs(
                geography="county",
                state="06",
                county="037",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "county:037"
            assert call_kwargs["geography"]["in"] == "state:06"

    @patch("pytidycensus.acs.CensusAPI")
    def test_tract_geography_api_call(self, mock_api_class):
        """Test tract-level geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test tracts in a state
            get_acs(
                geography="tract", state="06", variables="B01001_001E", year=2023, api_key="test"
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "tract:*"
            assert call_kwargs["geography"]["in"] == "state:06"

            # Test tracts in a state and county
            get_acs(
                geography="tract",
                state="06",
                county="073",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "tract:*"
            assert call_kwargs["geography"]["in"] == "state:06 county:073"

    @patch("pytidycensus.acs.CensusAPI")
    def test_block_group_geography_api_call(self, mock_api_class):
        """Test block group-level geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test block groups in a state
            get_acs(
                geography="block group",
                state="06",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "block group:*"
            assert call_kwargs["geography"]["in"] == "state:06"

            # Test block groups in a state and county
            get_acs(
                geography="block group",
                state="06",
                county="073",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "block group:*"
            assert call_kwargs["geography"]["in"] == "state:06 county:073"

    @patch("pytidycensus.acs.CensusAPI")
    def test_place_geography_api_call(self, mock_api_class):
        """Test place-level geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test places in a state (using fallback implementation)
            get_acs(
                geography="place", state="36", variables="B01001_001E", year=2023, api_key="test"
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "place:*"
            assert call_kwargs["geography"]["in"] == "state:36"

    @patch("pytidycensus.acs.CensusAPI")
    def test_zcta_geography_api_call(self, mock_api_class):
        """Test ZIP Code Tabulation Area geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test ZCTAs (national geography)
            get_acs(
                geography="zip code tabulation area",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "zip code tabulation area:*"
            # ZCTAs should not have an 'in' parameter since they're national

    @patch("pytidycensus.acs.CensusAPI")
    def test_msa_geography_api_call(self, mock_api_class):
        """Test MSA/μSA geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test MSAs (national geography)
            get_acs(
                geography="metropolitan statistical area/micropolitan statistical area",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert (
                call_kwargs["geography"]["for"]
                == "metropolitan statistical area/micropolitan statistical area:*"
            )

    @patch("pytidycensus.acs.CensusAPI")
    def test_congressional_district_geography_api_call(self, mock_api_class):
        """Test congressional district geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test congressional districts in a state (using fallback implementation)
            get_acs(
                geography="congressional district",
                state="72",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "congressional district:*"
            assert call_kwargs["geography"]["in"] == "state:72"

    @patch("pytidycensus.acs.CensusAPI")
    def test_state_legislative_district_upper_api_call(self, mock_api_class):
        """Test state legislative district (upper chamber) geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test state legislative districts (upper) in a state
            get_acs(
                geography="state legislative district (upper chamber)",
                state="06",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "state legislative district (upper chamber):*"
            assert call_kwargs["geography"]["in"] == "state:06"

    @patch("pytidycensus.acs.CensusAPI")
    def test_state_legislative_district_lower_api_call(self, mock_api_class):
        """Test state legislative district (lower chamber) geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test state legislative districts (lower) in a state
            get_acs(
                geography="state legislative district (lower chamber)",
                state="06",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "state legislative district (lower chamber):*"
            assert call_kwargs["geography"]["in"] == "state:06"

    @patch("pytidycensus.acs.CensusAPI")
    def test_puma_geography_api_call(self, mock_api_class):
        """Test Public Use Microdata Area geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test PUMAs in a state
            get_acs(
                geography="public use microdata area",
                state="36",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "public use microdata area:*"
            assert call_kwargs["geography"]["in"] == "state:36"

    @patch("pytidycensus.acs.CensusAPI")
    def test_school_district_elementary_api_call(self, mock_api_class):
        """Test school district (elementary) geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test elementary school districts in a state
            get_acs(
                geography="school district (elementary)",
                state="48",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "school district (elementary):*"
            assert call_kwargs["geography"]["in"] == "state:48"

    @patch("pytidycensus.acs.CensusAPI")
    def test_school_district_secondary_api_call(self, mock_api_class):
        """Test school district (secondary) geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test secondary school districts in a state
            get_acs(
                geography="school district (secondary)",
                state="48",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "school district (secondary):*"
            assert call_kwargs["geography"]["in"] == "state:48"

    @patch("pytidycensus.acs.CensusAPI")
    def test_school_district_unified_api_call(self, mock_api_class):
        """Test school district (unified) geography API call generation."""
        mock_api = Mock()
        mock_api.get.return_value = []
        mock_api_class.return_value = mock_api

        with patch("pytidycensus.acs.process_census_data") as mock_process, patch(
            "pytidycensus.acs.add_margin_of_error"
        ) as mock_add_moe:
            mock_process.return_value = []
            mock_add_moe.return_value = []

            # Test unified school districts in a state
            get_acs(
                geography="school district (unified)",
                state="06",
                variables="B01001_001E",
                year=2023,
                api_key="test",
            )
            call_kwargs = mock_api.get.call_args[1]
            assert call_kwargs["geography"]["for"] == "school district (unified):*"
            assert call_kwargs["geography"]["in"] == "state:06"


class TestUnimplementedGeographies:
    """Tests for geographies that are not yet fully implemented.

    These tests are commented out but can be used as a reference for
    future implementation.
    """

    # COMMENTED OUT - These geographies are not yet implemented

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_county_subdivision_api_call(self, mock_api_class):
    #     """Test county subdivision geography API call generation."""
    #     # Expected: for=county%20subdivision:*&in=state:48
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_subminor_civil_division_api_call(self, mock_api_class):
    #     """Test subminor civil division geography API call generation."""
    #     # Expected: for=subminor%20civil%20division:*&in=state:72%20county:127%20county%20subdivision:57247
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_place_remainder_api_call(self, mock_api_class):
    #     """Test place/remainder geography API call generation."""
    #     # Expected: for=place/remainder%20(or%20part):*&in=state:17%20county:031%20county%20subdivision:14000
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_county_or_part_api_call(self, mock_api_class):
    #     """Test county (or part) geography API call generation."""
    #     # Expected: for=county%20(or%20part):*&in=state:06%20place:44000
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_consolidated_city_api_call(self, mock_api_class):
    #     """Test consolidated city geography API call generation."""
    #     # Expected: for=consolidated%20city:*&in=state:18
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_alaska_native_regional_corporation_api_call(self, mock_api_class):
    #     """Test Alaska Native Regional Corporation geography API call generation."""
    #     # Expected: for=alaska%20native%20regional%20corporation:*&in=state:02
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_american_indian_area_api_call(self, mock_api_class):
    #     """Test American Indian Area geography API call generation."""
    #     # Expected: for=american%20indian%20area/alaska%20native%20area/hawaiian%20home%20land:*
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_tribal_subdivision_api_call(self, mock_api_class):
    #     """Test tribal subdivision geography API call generation."""
    #     # Expected: for=tribal%20subdivision/remainder:*&in=american%20indian%20area/alaska%20native%20area/hawaiian%20home%20land:*
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_tribal_census_tract_api_call(self, mock_api_class):
    #     """Test tribal census tract geography API call generation."""
    #     # Expected: for=tribal%20census%20tract:*&in=american%20indian%20area/alaska%20native%20area/hawaiian%20home%20land:3000
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_tribal_block_group_api_call(self, mock_api_class):
    #     """Test tribal block group geography API call generation."""
    #     # Expected: for=tribal%20block%20group:*&in=american%20indian%20area/alaska%20native%20area/hawaiian%20home%20land:2555%20tribal%20census%20tract:T00500
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_combined_statistical_area_api_call(self, mock_api_class):
    #     """Test Combined Statistical Area geography API call generation."""
    #     # Expected: for=combined%20statistical%20area:*
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_urban_area_api_call(self, mock_api_class):
    #     """Test urban area geography API call generation."""
    #     # Expected: for=urban%20area:*
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_metropolitan_division_api_call(self, mock_api_class):
    #     """Test metropolitan division geography API call generation."""
    #     # Expected: for=metropolitan%20division:*&in=metropolitan%20statistical%20area/micropolitan%20statistical%20area:35620
    #     pass

    # @patch("pytidycensus.acs.CensusAPI")
    # def test_principal_city_api_call(self, mock_api_class):
    #     """Test principal city geography API call generation."""
    #     # Expected: for=principal%20city%20(or%20part):*&in=metropolitan%20statistical%20area/micropolitan%20statistical%20area:35620%20state%20(or%20part):36
    #     pass
