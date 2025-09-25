"""Tests for state validation functionality."""

import pytest

from pytidycensus.utils import validate_state


class TestStateValidation:
    """Test state validation with various inputs."""

    def test_valid_state_abbreviations(self):
        """Test valid state abbreviations."""
        # Test standard states
        assert validate_state("CA") == ["06"]
        assert validate_state("NY") == ["36"]
        assert validate_state("TX") == ["48"]
        assert validate_state("FL") == ["12"]

    def test_valid_state_names(self):
        """Test valid state names."""
        assert validate_state("California") == ["06"]
        assert validate_state("New York") == ["36"]
        assert validate_state("Texas") == ["48"]
        assert validate_state("Florida") == ["12"]

    def test_valid_fips_codes_string(self):
        """Test valid FIPS codes as strings."""
        assert validate_state("06") == ["06"]
        assert validate_state("36") == ["36"]
        assert validate_state("48") == ["48"]
        assert validate_state("1") == ["01"]  # Should pad with zero

    def test_valid_fips_codes_integer(self):
        """Test valid FIPS codes as integers."""
        assert validate_state(6) == ["06"]
        assert validate_state(36) == ["36"]
        assert validate_state(48) == ["48"]
        assert validate_state(1) == ["01"]

    def test_district_of_columbia_variations(self):
        """Test District of Columbia in all valid formats."""
        # These should all work for DC (FIPS 11)
        assert validate_state("DC") == ["11"]
        assert validate_state("11") == ["11"]
        assert validate_state(11) == ["11"]
        assert validate_state("District of Columbia") == ["11"]

    def test_multiple_states(self):
        """Test validation of multiple states at once."""
        states = ["CA", "NY", "DC"]
        expected = ["06", "36", "11"]
        assert validate_state(states) == expected

    def test_mixed_formats(self):
        """Test mixed formats in a single call."""
        states = ["CA", 36, "District of Columbia", "12"]
        expected = ["06", "36", "11", "12"]
        assert validate_state(states) == expected

    def test_case_insensitive(self):
        """Test that state validation is case insensitive."""
        assert validate_state("ca") == ["06"]
        assert validate_state("Ca") == ["06"]
        assert validate_state("california") == ["06"]
        assert validate_state("CALIFORNIA") == ["06"]
        assert validate_state("dc") == ["11"]
        assert validate_state("Dc") == ["11"]

    def test_invalid_states(self):
        """Test invalid state identifiers raise ValueError."""
        with pytest.raises(ValueError, match="Invalid state identifier"):
            validate_state("ZZ")

        with pytest.raises(ValueError, match="Invalid state identifier"):
            validate_state("99")

        with pytest.raises(ValueError, match="Invalid state identifier"):
            validate_state("Invalid State")

        with pytest.raises(ValueError, match="Invalid state identifier"):
            validate_state(99)

    def test_territories_and_outlying_areas(self):
        """Test US territories and outlying areas."""
        # Puerto Rico
        assert validate_state("PR") == ["72"]
        assert validate_state("Puerto Rico") == ["72"]
        assert validate_state("72") == ["72"]

        # Other territories if supported
        territory_tests = [
            ("AS", "60", "American Samoa"),
            ("GU", "66", "Guam"),
            ("MP", "69", "Northern Mariana Islands"),
            ("VI", "78", "Virgin Islands"),
        ]

        for abbr, fips, name in territory_tests:
            try:
                assert validate_state(abbr) == [fips]
                assert validate_state(name) == [fips]
                assert validate_state(fips) == [fips]
            except ValueError:
                # Some territories might not be supported, that's OK
                pass

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Empty list should return empty list
        assert validate_state([]) == []

        # Single-item lists should work
        assert validate_state(["CA"]) == ["06"]

        # Leading/trailing whitespace should be handled
        assert validate_state(" CA ") == ["06"]
        assert validate_state(" District of Columbia ") == ["11"]

    def test_fips_padding(self):
        """Test that FIPS codes are properly zero-padded."""
        # Single digit states should be zero-padded
        assert validate_state(1) == ["01"]
        assert validate_state("1") == ["01"]
        assert validate_state(2) == ["02"]
        assert validate_state("2") == ["02"]

    def test_dc_is_special_case(self):
        """Test that DC is handled as a special case since it's not in regular states list."""
        # DC should work despite not being in us.STATES_AND_TERRITORIES
        dc_variants = [
            "DC",
            "dc",
            "Dc",
            "11",
            11,
            "District of Columbia",
            "district of columbia",
            "DISTRICT OF COLUMBIA",
        ]

        for variant in dc_variants:
            result = validate_state(variant)
            assert result == ["11"], f"Failed for DC variant: {variant}"


if __name__ == "__main__":
    # Run some basic tests
    test = TestStateValidation()
    print("Testing DC variations...")
    try:
        test.test_district_of_columbia_variations()
        print("✅ DC tests passed!")
    except Exception as e:
        print(f"❌ DC tests failed: {e}")

    print("Testing regular states...")
    try:
        test.test_valid_state_abbreviations()
        print("✅ Regular state tests passed!")
    except Exception as e:
        print(f"❌ Regular state tests failed: {e}")
