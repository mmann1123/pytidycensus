"""
Simple Time Series Analysis Example
===================================

A working example of time series analysis using pytidycensus that focuses on
geographic levels that don't change over time (states, counties).

This example demonstrates:
1. Decennial census comparison (2010 vs 2020)
2. ACS 5-year comparison (2012 vs 2020)
3. Multi-geography analysis
4. Basic visualization

Requirements: pytidycensus, pandas, matplotlib
"""

import matplotlib.pyplot as plt
import pandas as pd

import pytidycensus as tc


def setup_demo():
    """Setup for demo - uses built-in example data if no API key."""
    print("Simple Time Series Analysis with pytidycensus")
    print("=" * 50)
    print("Note: This example uses geographic levels that don't change over time")
    print("(states, counties) to avoid boundary interpolation complexity.\n")


def compare_state_populations():
    """Compare state population changes between 2010 and 2020 decennial census."""
    print("=== State Population Changes (2010-2020 Decennial) ===")

    # Focus on DC metro area
    states = ["DC", "MD", "VA"]
    results = []

    for state in states:
        try:
            # Get 2010 decennial data (state level - no boundary changes)
            pop_2010 = tc.get_decennial(
                geography="state", variables={"total_pop": "P001001"}, state=state, year=2010
            )

            # Get 2020 decennial data
            pop_2020 = tc.get_decennial(
                geography="state", variables={"total_pop": "P1_001N"}, state=state, year=2020
            )

            # Calculate change
            pop_2010_val = pop_2010.iloc[0]["total_pop"]
            pop_2020_val = pop_2020.iloc[0]["total_pop"]
            change = pop_2020_val - pop_2010_val
            pct_change = (change / pop_2010_val) * 100

            results.append(
                {
                    "State": pop_2010.iloc[0]["NAME"],
                    "Pop_2010": pop_2010_val,
                    "Pop_2020": pop_2020_val,
                    "Change": change,
                    "Pct_Change": pct_change,
                }
            )

            print(f"{state}: {pop_2010_val:,} → {pop_2020_val:,} ({pct_change:+.1f}%)")

        except Exception as e:
            print(f"Error processing {state}: {e}")

    return pd.DataFrame(results)


def compare_county_income():
    """Compare county median income using ACS 5-year data."""
    print("\n=== County Income Changes (ACS 5-year: 2012 vs 2020) ===")

    # Focus on DC metro counties
    counties_data = [
        {"state": "MD", "county": "Montgomery County"},
        {"state": "VA", "county": "Arlington County"},
        {"state": "DC", "county": "District of Columbia"},  # DC is county-equivalent
    ]

    results = []

    for county_info in counties_data:
        try:
            # Get 2012 ACS 5-year data (2008-2012)
            income_2012 = tc.get_acs(
                geography="county",
                variables={"median_income": "B19013_001E"},
                state=county_info["state"],
                county=county_info["county"] if county_info["state"] != "DC" else None,
                year=2012,
                survey="acs5",
                output="wide",  # Use wide format for easier access
            )

            # Get 2020 ACS 5-year data (2016-2020)
            income_2020 = tc.get_acs(
                geography="county",
                variables={"median_income": "B19013_001E"},
                state=county_info["state"],
                county=county_info["county"] if county_info["state"] != "DC" else None,
                year=2020,
                survey="acs5",
                output="wide",  # Use wide format for easier access
            )

            # Calculate change (wide format uses variable names as columns)
            income_2012_val = income_2012.iloc[0]["median_income"]
            income_2020_val = income_2020.iloc[0]["median_income"]
            change = income_2020_val - income_2012_val
            pct_change = (change / income_2012_val) * 100

            results.append(
                {
                    "County": income_2012.iloc[0]["NAME"],
                    "Income_2012": income_2012_val,
                    "Income_2020": income_2020_val,
                    "Change": change,
                    "Pct_Change": pct_change,
                }
            )

            print(
                f"{county_info['county'] if county_info['state'] != 'DC' else 'Washington DC'}: ${income_2012_val:,} → ${income_2020_val:,} ({pct_change:+.1f}%)"
            )

        except Exception as e:
            print(f"Error processing {county_info}: {e}")

    return pd.DataFrame(results)


def create_visualization(pop_data, income_data):
    """Create simple visualizations."""
    if pop_data.empty and income_data.empty:
        print("No data available for visualization")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Population change chart
    if not pop_data.empty:
        ax1.bar(
            pop_data["State"],
            pop_data["Pct_Change"],
            color=["red" if x < 0 else "blue" for x in pop_data["Pct_Change"]],
        )
        ax1.set_title("Population Change 2010-2020\n(Decennial Census)", fontweight="bold")
        ax1.set_ylabel("Percent Change (%)")
        ax1.axhline(y=0, color="black", linestyle="-", alpha=0.3)

        # Add value labels
        for i, v in enumerate(pop_data["Pct_Change"]):
            ax1.text(
                i,
                v + (0.1 if v >= 0 else -0.3),
                f"{v:.1f}%",
                ha="center",
                va="bottom" if v >= 0 else "top",
            )

    # Income change chart
    if not income_data.empty:
        # Shorten county names for display
        short_names = [
            name.replace(" County", "").replace(", District of Columbia", "")
            for name in income_data["County"]
        ]

        ax2.bar(
            short_names,
            income_data["Pct_Change"],
            color=["red" if x < 0 else "green" for x in income_data["Pct_Change"]],
        )
        ax2.set_title("Median Income Change 2012-2020\n(ACS 5-year)", fontweight="bold")
        ax2.set_ylabel("Percent Change (%)")
        ax2.axhline(y=0, color="black", linestyle="-", alpha=0.3)
        ax2.tick_params(axis="x", rotation=45)

        # Add value labels
        for i, v in enumerate(income_data["Pct_Change"]):
            ax2.text(
                i,
                v + (0.5 if v >= 0 else -1),
                f"{v:.1f}%",
                ha="center",
                va="bottom" if v >= 0 else "top",
            )

    plt.tight_layout()
    plt.show()


def demonstrate_best_practices():
    """Show key principles for time series analysis."""
    print("\n=== Time Series Analysis Best Practices ===")
    print("1. ✅ SURVEY CONSISTENCY:")
    print("   - Compare Decennial ↔ Decennial (every 10 years)")
    print("   - Compare ACS 5-year ↔ ACS 5-year (most stable)")
    print("   - Compare ACS 1-year ↔ ACS 1-year (large areas only)")
    print("   - ❌ DON'T mix: ACS 1-year vs ACS 5-year")

    print("\n2. ✅ GEOGRAPHIC CONSISTENCY:")
    print("   - Use stable geographies (states, counties)")
    print("   - For tracts: use area interpolation (tobler library)")
    print("   - Document boundary changes")

    print("\n3. ✅ VARIABLE CONSISTENCY:")
    print("   - Check variable definitions across years")
    print("   - 2010 Decennial: P001001 (total pop)")
    print("   - 2020 Decennial: P1_001N (total pop)")
    print("   - ACS variables generally consistent")

    print("\n4. ✅ DATA QUALITY:")
    print("   - Use margins of error for ACS data")
    print("   - Consider sample size differences")
    print("   - Document assumptions and limitations")


def main():
    """Run the complete simple time series analysis."""
    setup_demo()

    # Note about API key
    print("Note: This example requires a Census API key.")
    print("Get one free at: https://api.census.gov/data/key_signup.html")
    print("Set it with: tc.set_census_api_key('your_key_here')")
    print("Or uncomment the setup line in the setup_demo() function\n")

    try:
        # Analyze population changes
        pop_results = compare_state_populations()

        # Analyze income changes
        income_results = compare_county_income()

        # Create visualizations
        print("\n=== Creating Visualizations ===")
        create_visualization(pop_results, income_results)

        # Show best practices
        demonstrate_best_practices()

        print("\n=== Summary ===")
        if not pop_results.empty:
            print(f"Population analysis: {len(pop_results)} states analyzed")
            avg_pop_change = pop_results["Pct_Change"].mean()
            print(f"Average population change: {avg_pop_change:.1f}%")

        if not income_results.empty:
            print(f"Income analysis: {len(income_results)} counties analyzed")
            avg_income_change = income_results["Pct_Change"].mean()
            print(f"Average income change: {avg_income_change:.1f}%")

    except Exception as e:
        print(f"Error during analysis: {e}")
        print("\nThis usually means:")
        print("- Census API key not set")
        print("- Internet connection issue")
        print("- Missing data for requested geography")
        print("\nTry:")
        print("- tc.set_census_api_key('your_key_here')")
        print("- Check internet connection")


if __name__ == "__main__":
    main()
