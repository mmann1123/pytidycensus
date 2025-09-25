"""Practical examples demonstrating selective normalization logic.

Shows real-world scenarios where normalization should and shouldn't be
applied.
"""

from pytidycensus.llm_interface.knowledge_base import (
    get_normalization_variables_for_codes,
    needs_normalization,
)


def test_median_income_example():
    """Example: Median income doesn't need normalization."""
    print("\n📊 Example: Median household income analysis")

    # Median income variables
    median_vars = ["B19013_001E"]  # Median household income

    print(f"Variables: {median_vars}")
    print(f"Description: Median household income")

    # Check if normalization is needed
    needs_norm = needs_normalization(median_vars[0])
    print(f"Needs normalization: {needs_norm}")

    # Get normalization variables
    norm_vars = get_normalization_variables_for_codes(median_vars)
    print(f"Normalization variables added: {list(norm_vars.keys()) if norm_vars else 'None'}")

    print("✅ Result: Median income correctly identified as NOT needing normalization")
    assert not needs_norm
    assert len(norm_vars) == 0


def test_poverty_count_example():
    """Example: Poverty counts need normalization."""
    print("\n📊 Example: Poverty rate calculation")

    # Poverty count variables
    poverty_vars = ["B17001_002E"]  # Below poverty line

    print(f"Variables: {poverty_vars}")
    print(f"Description: Population below poverty line")

    # Check if normalization is needed
    needs_norm = needs_normalization(poverty_vars[0])
    print(f"Needs normalization: {needs_norm}")

    # Get normalization variables
    norm_vars = get_normalization_variables_for_codes(poverty_vars)
    print(f"Normalization variables added: {list(norm_vars.keys())}")

    print("✅ Result: Poverty counts correctly get total population for rate calculation")
    assert needs_norm
    assert "B17001_001E" in norm_vars  # Total population for poverty status


def test_income_distribution_example():
    """Example: Income distribution counts need normalization."""
    print("\n📊 Example: Income distribution analysis")

    # Income count variables
    income_vars = ["B19001_002E", "B19001_014E"]  # <$10k, $150k-$200k

    print(f"Variables: {income_vars}")
    print(f"Description: Households with income <$10k and $150k-$200k")

    # Check normalization for each
    for var in income_vars:
        needs_norm = needs_normalization(var)
        print(f"{var} needs normalization: {needs_norm}")
        assert needs_norm

    # Get normalization variables
    norm_vars = get_normalization_variables_for_codes(income_vars)
    print(f"Normalization variables added: {list(norm_vars.keys())}")

    print("✅ Result: Income distribution counts get total households for percentage calculation")
    assert "B19001_001E" in norm_vars  # Total households


def test_mixed_analysis_example():
    """Example: Mixed analysis with medians and counts."""
    print("\n📊 Example: Comprehensive income analysis")

    # Mixed variables - medians and counts
    mixed_vars = [
        "B19013_001E",  # Median household income (no normalization)
        "B19001_002E",  # Households <$10k (needs normalization)
        "B25077_001E",  # Median home value (no normalization)
        "B25003_002E",  # Owner occupied units (needs normalization)
    ]

    print(f"Variables: {mixed_vars}")
    print(
        "Description: Median income, low-income households, median home value, owner-occupied housing"
    )

    # Check each variable individually
    for var in mixed_vars:
        needs_norm = needs_normalization(var)
        var_type = "COUNT" if needs_norm else "MEDIAN/TOTAL"
        print(f"  {var}: {var_type}")

    # Get normalization variables for the entire set
    norm_vars = get_normalization_variables_for_codes(mixed_vars)
    print(f"Normalization variables added: {list(norm_vars.keys())}")

    expected_norms = {"B19001_001E", "B25001_001E"}  # Total households, total housing units
    actual_norms = set(norm_vars.keys())

    print("✅ Result: Only count variables get normalization, medians are left alone")
    assert expected_norms == actual_norms


def test_housing_example():
    """Example: Housing analysis with medians vs counts."""
    print("\n📊 Example: Housing market analysis")

    # Housing variables - mix of medians and counts
    housing_vars = [
        "B25077_001E",  # Median home value (no normalization)
        "B25064_001E",  # Median rent (no normalization)
        "B25003_002E",  # Owner occupied (needs normalization)
        "B25003_003E",  # Renter occupied (needs normalization)
    ]

    print(f"Variables: {housing_vars}")
    print(
        "Description: Median home value, median rent, owner-occupied units, renter-occupied units"
    )

    # Separate medians from counts
    medians = ["B25077_001E", "B25064_001E"]
    counts = ["B25003_002E", "B25003_003E"]

    # Test medians don't need normalization
    median_norms = get_normalization_variables_for_codes(medians)
    print(f"Normalization for medians: {list(median_norms.keys()) if median_norms else 'None'}")
    assert len(median_norms) == 0

    # Test counts do need normalization
    count_norms = get_normalization_variables_for_codes(counts)
    print(f"Normalization for counts: {list(count_norms.keys())}")
    assert "B25001_001E" in count_norms  # Total housing units

    print("✅ Result: Housing medians need no normalization, counts get total housing units")


def test_employment_example():
    """Example: Employment analysis."""
    print("\n📊 Example: Employment analysis")

    # Employment variables
    employment_vars = [
        "B23025_005E",  # Unemployed (needs normalization)
        "B23025_004E",  # Employed (needs normalization)
        "B23025_002E",  # Total labor force (is the denominator)
    ]

    print(f"Variables: {employment_vars}")
    print("Description: Unemployed, employed, total labor force")

    # Check each variable
    for var in employment_vars:
        needs_norm = needs_normalization(var)
        var_type = "COUNT" if needs_norm else "TOTAL"
        print(f"  {var}: {var_type}")

    # Total labor force shouldn't need normalization (it IS the denominator)
    assert not needs_normalization("B23025_002E")

    # Individual employment counts should need normalization
    assert needs_normalization("B23025_005E")  # Unemployed
    assert needs_normalization("B23025_004E")  # Employed

    # Get normalization for unemployment
    unemployed_norms = get_normalization_variables_for_codes(["B23025_005E"])
    print(f"Normalization for unemployed: {list(unemployed_norms.keys())}")
    assert "B23025_002E" in unemployed_norms  # Total labor force

    print(
        "✅ Result: Employment counts get labor force total, labor force total needs no normalization"
    )


if __name__ == "__main__":
    print("🧪 Demonstrating Selective Normalization Logic")
    print("=" * 60)

    test_median_income_example()
    test_poverty_count_example()
    test_income_distribution_example()
    test_mixed_analysis_example()
    test_housing_example()
    test_employment_example()

    print("\n" + "=" * 60)
    print("🎉 All examples demonstrate correct selective normalization!")
    print("\nKey principles:")
    print("✅ Median values (B19013_001E, B25077_001E) → NO normalization")
    print("✅ Count values (B19001_002E, B17001_002E) → GET normalization")
    print(
        "✅ Total/universe values (B19001_001E, B17001_001E) → NO normalization (they ARE denominators)"
    )
    print("✅ Mixed lists → Only counts get normalization, medians left alone")
