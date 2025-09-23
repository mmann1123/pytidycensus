"""Tests for unimplemented geography error handling."""

import pytest

from pytidycensus.acs import get_acs
from pytidycensus.utils import build_geography_params, validate_geography


class TestUnimplementedGeographyErrors:
    """Test that unimplemented geographies properly raise NotImplementedError."""

    def test_validate_geography_raises_not_implemented_for_county_subdivision(self):
        """Test that county subdivision raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="recognized but not yet implemented"):
            validate_geography("county subdivision")

    def test_validate_geography_raises_not_implemented_for_consolidated_city(self):
        """Test that consolidated city raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="recognized but not yet implemented"):
            validate_geography("consolidated city")

    def test_validate_geography_raises_not_implemented_for_tribal_areas(self):
        """Test that tribal areas raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="recognized but not yet implemented"):
            validate_geography("american indian area/alaska native area/hawaiian home land")

    def test_validate_geography_raises_not_implemented_for_combined_statistical_area(self):
        """Test that combined statistical area raises NotImplementedError."""
        with pytest.raises(
            NotImplementedError, match="combined statistical area.*not yet implemented"
        ):
            validate_geography("csa")

    def test_validate_geography_raises_not_implemented_for_urban_area(self):
        """Test that urban area raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="recognized but not yet implemented"):
            validate_geography("urban area")

    def test_validate_geography_raises_not_implemented_for_block_in_acs(self):
        """Test that block geography raises specific NotImplementedError for ACS."""
        with pytest.raises(NotImplementedError, match="not available in ACS data"):
            validate_geography("block", dataset="acs")

    def test_validate_geography_allows_block_in_decennial(self):
        """Test that block geography is allowed for Decennial Census."""
        # Should not raise any error
        result = validate_geography("block", dataset="decennial")
        assert result == "block"

    def test_validate_geography_allows_block_when_no_dataset_specified(self):
        """Test that block geography is allowed when no dataset is specified."""
        # Should not raise any error (backwards compatibility)
        result = validate_geography("block")
        assert result == "block"

    def test_validate_geography_raises_not_implemented_for_necta(self):
        """Test that NECTA raises NotImplementedError."""
        with pytest.raises(
            NotImplementedError, match="New England city and town area.*not yet implemented"
        ):
            validate_geography("necta")

    def test_build_geography_params_raises_not_implemented_for_county_subdivision(self):
        """Test that build_geography_params raises NotImplementedError for county subdivision."""
        with pytest.raises(NotImplementedError, match="recognized but not yet implemented"):
            build_geography_params("county subdivision", state="06")

    def test_build_geography_params_raises_not_implemented_for_metropolitan_division(self):
        """Test that build_geography_params raises NotImplementedError for metropolitan division."""
        with pytest.raises(NotImplementedError, match="recognized but not yet implemented"):
            build_geography_params("metropolitan division")

    def test_get_acs_raises_not_implemented_for_unimplemented_geography(self):
        """Test that get_acs raises NotImplementedError for unimplemented geographies."""
        with pytest.raises(NotImplementedError, match="recognized but not yet implemented"):
            get_acs(
                geography="county subdivision",
                variables="B01001_001E",
                state="06",
                year=2020,
                api_key="test",
            )

    def test_get_acs_raises_not_implemented_for_block_geography(self):
        """Test that get_acs raises NotImplementedError for block geography."""
        with pytest.raises(NotImplementedError, match="not available in ACS data"):
            get_acs(
                geography="block",
                variables="B01001_001E",
                state="06",
                year=2020,
                api_key="test",
            )

    def test_validate_geography_raises_value_error_for_unknown_geography(self):
        """Test that completely unknown geography raises ValueError."""
        with pytest.raises(ValueError, match="not recognized"):
            validate_geography("completely_unknown_geography")

    def test_implemented_geographies_work(self):
        """Test that implemented geographies work correctly."""
        # These should not raise any errors
        assert validate_geography("us") == "us"
        assert validate_geography("state") == "state"
        assert validate_geography("county") == "county"
        assert validate_geography("tract") == "tract"
        assert validate_geography("block group") == "block group"
        assert validate_geography("place") == "place"
        assert validate_geography("zip code tabulation area") == "zip code tabulation area"
        assert (
            validate_geography("metropolitan statistical area/micropolitan statistical area")
            == "metropolitan statistical area/micropolitan statistical area"
        )
        assert validate_geography("congressional district") == "congressional district"
        assert validate_geography("public use microdata area") == "public use microdata area"
        # Block should work for decennial or when no dataset specified
        assert validate_geography("block", dataset="decennial") == "block"
        assert validate_geography("block") == "block"

    def test_legacy_aliases_work(self):
        """Test that legacy aliases work correctly."""
        assert validate_geography("cbg") == "block group"
        assert (
            validate_geography("msa")
            == "metropolitan statistical area/micropolitan statistical area"
        )
        assert validate_geography("zcta") == "zip code tabulation area"

    def test_build_geography_params_handles_redirects(self):
        """Test that build_geography_params handles legacy alias redirects."""
        # MSA should redirect to full name
        params1 = build_geography_params("msa")
        params2 = build_geography_params(
            "metropolitan statistical area/micropolitan statistical area"
        )
        assert params1 == params2

        # ZCTA should redirect to full name
        params3 = build_geography_params("zcta")
        params4 = build_geography_params("zip code tabulation area")
        assert params3 == params4

    def test_unimplemented_but_recognized_geographies_list(self):
        """Test specific unimplemented geographies from the Census API documentation."""
        unimplemented_geographies = [
            "county subdivision",
            "subminor civil division",
            "place/remainder (or part)",
            "county (or part)",
            "consolidated city",
            "alaska native regional corporation",
            "american indian area/alaska native area/hawaiian home land",
            "tribal subdivision/remainder",
            "tribal census tract",
            "tribal block group",
            "combined statistical area",
            "urban area",
            "metropolitan division",
            "principal city (or part)",
        ]

        for geography in unimplemented_geographies:
            with pytest.raises(NotImplementedError):
                validate_geography(geography)
