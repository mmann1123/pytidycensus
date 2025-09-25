"""Tests for selective normalization logic.

Ensures that variables that don't need normalization (medians, totals,
etc.) don't get normalization variables suggested, while count variables
do.
"""

from pytidycensus.llm_interface.knowledge_base import (
    VARIABLES_NO_NORMALIZATION,
    get_normalization_variables_for_codes,
    needs_normalization,
)


class TestNormalizationLogic:
    """Test suite for selective normalization logic."""

    def test_median_variables_dont_need_normalization(self):
        """Test that median variables are correctly identified as not needing normalization."""
        median_variables = [
            "B19013_001E",  # Median household income
            "B19301_001E",  # Per capita income
            "B25077_001E",  # Median home value
            "B25064_001E",  # Median rent
            "B01002_001E",  # Median age
            "B08303_001E",  # Mean travel time to work
        ]

        for var in median_variables:
            assert not needs_normalization(
                var
            ), f"Median variable {var} should not need normalization"

    def test_total_variables_dont_need_normalization(self):
        """Test that total/universe variables don't need normalization."""
        total_variables = [
            "B01003_001E",  # Total population
            "B19001_001E",  # Total households for income
            "B17001_001E",  # Total population for poverty status
            "B15003_001E",  # Total population 25+ for education
            "B25001_001E",  # Total housing units
            "B23025_002E",  # Labor force
        ]

        for var in total_variables:
            assert not needs_normalization(
                var
            ), f"Total variable {var} should not need normalization"

    def test_count_variables_need_normalization(self):
        """Test that count variables correctly need normalization."""
        count_variables = [
            "B19001_002E",  # Households with income <$10k
            "B17001_002E",  # Population below poverty line
            "B15003_022E",  # Bachelor's degree
            "B25003_002E",  # Owner occupied housing units
            "B23025_005E",  # Unemployed
            "B02001_002E",  # White alone
        ]

        for var in count_variables:
            assert needs_normalization(var), f"Count variable {var} should need normalization"

    def test_001E_pattern_recognition(self):
        """Test that variables ending in _001E are recognized as totals."""
        # Most _001E variables are totals and don't need normalization
        test_variables = [
            "B12345_001E",  # Generic total
            "B99999_001E",  # Another generic total
        ]

        for var in test_variables:
            assert not needs_normalization(
                var
            ), f"Variable {var} ending in _001E should not need normalization"

    def test_get_normalization_for_median_income(self):
        """Test that median income variables don't get normalization variables."""
        median_income_vars = ["B19013_001E"]  # Median household income
        norm_vars = get_normalization_variables_for_codes(median_income_vars)

        assert (
            len(norm_vars) == 0
        ), f"Median income should not get normalization variables, got: {norm_vars}"

    def test_get_normalization_for_income_counts(self):
        """Test that income count variables DO get normalization variables."""
        income_count_vars = ["B19001_002E"]  # Households with income <$10k
        norm_vars = get_normalization_variables_for_codes(income_count_vars)

        assert len(norm_vars) > 0, "Income count variables should get normalization variables"
        assert (
            "B19001_001E" in norm_vars
        ), "Should include total households for income normalization"

    def test_get_normalization_for_poverty_counts(self):
        """Test that poverty count variables get appropriate normalization."""
        poverty_count_vars = ["B17001_002E"]  # Below poverty line
        norm_vars = get_normalization_variables_for_codes(poverty_count_vars)

        assert len(norm_vars) > 0, "Poverty count variables should get normalization variables"
        assert (
            "B17001_001E" in norm_vars
        ), "Should include total population for poverty normalization"

    def test_get_normalization_for_housing_median_values(self):
        """Test that housing median values don't get normalization."""
        housing_median_vars = ["B25077_001E", "B25064_001E"]  # Median home value, median rent
        norm_vars = get_normalization_variables_for_codes(housing_median_vars)

        assert (
            len(norm_vars) == 0
        ), f"Housing median values should not get normalization variables, got: {norm_vars}"

    def test_get_normalization_for_housing_counts(self):
        """Test that housing count variables get normalization."""
        housing_count_vars = ["B25003_002E"]  # Owner occupied units
        norm_vars = get_normalization_variables_for_codes(housing_count_vars)

        assert len(norm_vars) > 0, "Housing count variables should get normalization variables"
        assert "B25001_001E" in norm_vars, "Should include total housing units for normalization"

    def test_mixed_variable_list(self):
        """Test behavior with a mix of variables that do and don't need normalization."""
        mixed_vars = [
            "B19013_001E",  # Median household income (no normalization needed)
            "B19001_002E",  # Households <$10k (normalization needed)
            "B25077_001E",  # Median home value (no normalization needed)
            "B25003_002E",  # Owner occupied (normalization needed)
        ]

        norm_vars = get_normalization_variables_for_codes(mixed_vars)

        # Should only get normalization for the count variables
        expected_norm_vars = {"B19001_001E", "B25001_001E"}
        actual_norm_vars = set(norm_vars.keys())

        assert (
            actual_norm_vars == expected_norm_vars
        ), f"Expected {expected_norm_vars}, got {actual_norm_vars}"

    def test_no_normalization_constant_completeness(self):
        """Test that the VARIABLES_NO_NORMALIZATION set includes key median variables."""
        required_no_norm_vars = {
            "B19013_001E",  # Median household income
            "B25077_001E",  # Median home value
            "B25064_001E",  # Median rent
            "B01002_001E",  # Median age
            "B01003_001E",  # Total population
        }

        for var in required_no_norm_vars:
            assert (
                var in VARIABLES_NO_NORMALIZATION
            ), f"{var} should be in VARIABLES_NO_NORMALIZATION"

    def test_education_variables(self):
        """Test education variable normalization logic."""
        # Median education variables shouldn't need normalization
        education_total = ["B15003_001E"]  # Total population 25+
        norm_vars = get_normalization_variables_for_codes(education_total)
        assert len(norm_vars) == 0, "Education total should not need normalization"

        # Education count variables should need normalization
        education_counts = ["B15003_022E"]  # Bachelor's degree
        norm_vars = get_normalization_variables_for_codes(education_counts)
        assert len(norm_vars) > 0, "Education counts should need normalization"
        assert "B15003_001E" in norm_vars, "Should include education universe"

    def test_employment_variables(self):
        """Test employment variable normalization logic."""
        # Employment count variables should need normalization
        employment_counts = ["B23025_005E"]  # Unemployed
        norm_vars = get_normalization_variables_for_codes(employment_counts)
        assert len(norm_vars) > 0, "Employment counts should need normalization"
        assert "B23025_002E" in norm_vars, "Should include labor force total"

        # Labor force total should not need normalization
        labor_force_total = ["B23025_002E"]
        norm_vars = get_normalization_variables_for_codes(labor_force_total)
        assert len(norm_vars) == 0, "Labor force total should not need normalization"


if __name__ == "__main__":
    # Run basic tests
    test = TestNormalizationLogic()

    print("Testing median variables don't get normalization...")
    test.test_median_variables_dont_need_normalization()
    print("✅ Median variables correctly excluded from normalization!")

    print("Testing count variables do get normalization...")
    test.test_count_variables_need_normalization()
    print("✅ Count variables correctly identified for normalization!")

    print("Testing specific cases...")
    test.test_get_normalization_for_median_income()
    test.test_get_normalization_for_income_counts()
    test.test_mixed_variable_list()
    print("✅ Specific normalization cases work correctly!")

    print("\n🎉 All normalization logic tests passed!")
