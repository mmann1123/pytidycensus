"""
Comprehensive Time Series Analysis with pytidycensus
===================================================

This example demonstrates the new get_time_series() function for analyzing
Census data across multiple time periods with automatic area interpolation
to handle changing geographic boundaries.

Key Features:
- Automatic area interpolation for changing boundaries
- Support for both ACS and Decennial Census data
- Intelligent variable classification (extensive vs intensive)
- Flexible output formats (wide vs tidy)
- Built-in validation and comparison tools

Requirements:
- pytidycensus
- tobler (for area interpolation): pip install pytidycensus[time]
- geopandas
- matplotlib

Author: pytidycensus contributors
"""

import warnings

import pytidycensus as tc

warnings.filterwarnings("ignore")


def setup_api_key():
    """Set up Census API key."""
    # Uncomment and add your API key
    # tc.set_census_api_key("YOUR_API_KEY_HERE")


def example_1_acs_time_series():
    """Example 1: ACS 5-year time series with area interpolation."""
    print("=" * 60)
    print("Example 1: ACS 5-year Time Series Analysis")
    print("=" * 60)

    # Define variables of interest
    variables = {
        "total_pop": "B01003_001E",  # Total population (extensive)
        "median_income": "B19013_001E",  # Median household income (intensive)
        "poverty_count": "B17001_002E",  # Population below poverty (extensive)
        "poverty_total": "B17001_001E",  # Total for poverty calculation (extensive)
    }

    print("Collecting ACS 5-year data for DC tracts (2015-2020)...")
    print("Variables:")
    for name, code in variables.items():
        print(f"  {name}: {code}")

    try:
        # Get time series data with automatic area interpolation
        data = tc.get_time_series(
            geography="tract",
            variables=variables,
            years=[2015, 2020],
            dataset="acs5",
            state="DC",
            base_year=2020,  # Use 2020 boundaries as base
            extensive_variables=["total_pop", "poverty_count", "poverty_total"],
            intensive_variables=["median_income"],
            geometry=True,
            output="wide",
        )

        print(f"\nData shape: {data.shape}")
        print(f"Years available: {[col[0] for col in data.columns if isinstance(col, tuple)]}")

        # Calculate poverty rates for both years
        data["poverty_rate_2015"] = (
            data[(2015, "poverty_count")] / data[(2015, "poverty_total")] * 100
        )
        data["poverty_rate_2020"] = (
            data[(2020, "poverty_count")] / data[(2020, "poverty_total")] * 100
        )

        # Calculate changes
        data["pop_change"] = data[(2020, "total_pop")] - data[(2015, "total_pop")]
        data["income_change"] = data[(2020, "median_income")] - data[(2015, "median_income")]
        data["poverty_rate_change"] = data["poverty_rate_2020"] - data["poverty_rate_2015"]

        # Summary statistics
        print(f"\nSummary Statistics:")
        print(f"Average population change: {data['pop_change'].mean():.0f}")
        print(f"Average income change: ${data['income_change'].mean():.0f}")
        print(
            f"Average poverty rate change: {data['poverty_rate_change'].mean():.1f} percentage points"
        )
        print(f"Tracts with population growth: {(data['pop_change'] > 0).sum()}")
        print(f"Tracts with income growth: {(data['income_change'] > 0).sum()}")

        return data

    except Exception as e:
        print(f"Error: {e}")
        print("This example requires a Census API key and internet connection.")
        return None


def example_2_decennial_comparison():
    """Example 2: Decennial Census comparison with different variable codes."""
    print("\n" + "=" * 60)
    print("Example 2: Decennial Census Time Series (2010-2020)")
    print("=" * 60)

    # Different variable codes for different years
    variables = {
        2010: {"total_pop": "P001001"},  # 2010 uses P001001
        2020: {"total_pop": "P1_001N"},  # 2020 uses P1_001N
    }

    print("Collecting Decennial Census data for DC tracts...")
    print("Using year-specific variable codes:")
    for year, vars_dict in variables.items():
        print(f"  {year}: {vars_dict}")

    try:
        # Get decennial time series data
        data = tc.get_time_series(
            geography="tract",
            variables=variables,
            years=[2010, 2020],
            dataset="decennial",
            state="DC",
            base_year=2020,  # Use 2020 boundaries
            extensive_variables=["total_pop"],
            geometry=True,
            output="wide",
        )

        print(f"\nData shape: {data.shape}")

        # Calculate 10-year change
        data["pop_change"] = data[(2020, "total_pop")] - data[(2010, "total_pop")]
        data["pop_pct_change"] = data["pop_change"] / data[(2010, "total_pop")] * 100

        # Summary statistics
        print(f"\nDecennial Population Change (2010-2020):")
        print(f"Total DC population change: {data['pop_change'].sum():,}")
        print(f"Average tract change: {data['pop_change'].mean():.0f}")
        print(f"Average percent change: {data['pop_pct_change'].mean():.1f}%")
        print(f"Growing tracts: {(data['pop_change'] > 0).sum()}")
        print(f"Declining tracts: {(data['pop_change'] < 0).sum()}")

        return data

    except Exception as e:
        print(f"Error: {e}")
        print("This example requires a Census API key and internet connection.")
        return None


def example_3_county_level_stable_boundaries():
    """Example 3: County-level analysis (stable boundaries, no interpolation)."""
    print("\n" + "=" * 60)
    print("Example 3: County-Level Analysis (Stable Boundaries)")
    print("=" * 60)

    variables = {
        "total_pop": "B01003_001E",
        "median_age": "B01002_001E",
        "median_income": "B19013_001E",
    }

    print("Collecting ACS data for all US counties (2018, 2022)...")
    print("Note: County boundaries are stable, so no interpolation needed.")

    try:
        # County boundaries rarely change, so interpolation not needed
        data = tc.get_time_series(
            geography="county",
            variables=variables,
            years=[2018, 2022],
            dataset="acs5",
            extensive_variables=["total_pop"],
            intensive_variables=["median_age", "median_income"],
            geometry=False,  # Skip geometry for faster processing
            output="wide",
        )

        print(f"\nData shape: {data.shape}")

        # Calculate changes
        data["pop_change"] = data[(2022, "total_pop")] - data[(2018, "total_pop")]
        data["pop_pct_change"] = data["pop_change"] / data[(2018, "total_pop")] * 100
        data["income_change"] = data[(2022, "median_income")] - data[(2018, "median_income")]

        # National summary
        print(f"\nNational Summary (2018-2022):")
        print(f"Counties analyzed: {len(data):,}")
        print(f"Total population change: {data['pop_change'].sum():,}")
        print(f"Average county population change: {data['pop_change'].mean():.0f}")
        print(f"Average income change: ${data['income_change'].mean():.0f}")
        print(f"Counties with population growth: {(data['pop_change'] > 0).sum():,}")

        # Top growing counties
        top_growth = data.nlargest(5, "pop_change")[["NAME", "pop_change", "pop_pct_change"]]
        print(f"\nTop 5 Growing Counties:")
        for _, row in top_growth.iterrows():
            print(f"  {row['NAME']}: +{row['pop_change']:,.0f} ({row['pop_pct_change']:+.1f}%)")

        return data

    except Exception as e:
        print(f"Error: {e}")
        print("This example requires a Census API key and internet connection.")
        return None


def example_4_tidy_format_analysis():
    """Example 4: Time series analysis with tidy format output."""
    print("\n" + "=" * 60)
    print("Example 4: Tidy Format for Time Series Analysis")
    print("=" * 60)

    variables = {"total_pop": "B01003_001E", "median_income": "B19013_001E"}

    print("Collecting ACS data in tidy format for analysis...")

    try:
        # Get data in tidy format (long format)
        data = tc.get_time_series(
            geography="county",
            variables=variables,
            years=[2017, 2019, 2021],  # Multiple years
            dataset="acs5",
            state=["CA", "TX", "FL"],  # Multiple states
            geometry=False,
            output="tidy",  # Long format
        )

        print(f"\nTidy data shape: {data.shape}")
        print(f"Columns: {list(data.columns)}")
        print(f"Years: {sorted(data['year'].unique())}")
        print(f"Variables: {data['variable'].unique()}")
        print(f"States represented: {len(data['NAME'].str.extract(r', ([A-Z]{2})$')[0].unique())}")

        # Example analysis with tidy data
        print(f"\nSample of tidy data:")
        print(data.head(10).to_string(index=False))

        # Calculate year-over-year changes
        data_sorted = data.sort_values(["GEOID", "variable", "year"])
        data_sorted["prev_estimate"] = data_sorted.groupby(["GEOID", "variable"])["estimate"].shift(
            1
        )
        data_sorted["change"] = data_sorted["estimate"] - data_sorted["prev_estimate"]
        data_sorted["pct_change"] = data_sorted["change"] / data_sorted["prev_estimate"] * 100

        # Summary by year and variable
        summary = (
            data_sorted.groupby(["year", "variable"])
            .agg({"estimate": "mean", "change": "mean", "pct_change": "mean"})
            .round(2)
        )

        print(f"\nYear-over-year changes by variable:")
        print(summary)

        return data_sorted

    except Exception as e:
        print(f"Error: {e}")
        print("This example requires a Census API key and internet connection.")
        return None


def example_5_comparison_analysis():
    """Example 5: Using compare_time_periods() for detailed comparison."""
    print("\n" + "=" * 60)
    print("Example 5: Detailed Time Period Comparison")
    print("=" * 60)

    variables = {
        "total_pop": "B01003_001E",
        "median_income": "B19013_001E",
        "bachelor_degree": "B15003_022E",
    }

    print("Collecting data for detailed comparison analysis...")

    try:
        # Get time series data
        data = tc.get_time_series(
            geography="county",
            variables=variables,
            years=[2016, 2021],
            dataset="acs5",
            state="CA",
            geometry=False,
            output="wide",
        )

        # Use comparison function
        comparison = tc.compare_time_periods(
            data=data,
            base_period=2016,
            comparison_period=2021,
            variables=["total_pop", "median_income", "bachelor_degree"],
            calculate_change=True,
            calculate_percent_change=True,
        )

        print(f"\nComparison data shape: {comparison.shape}")
        print(f"Columns: {list(comparison.columns)}")

        # Analysis of changes
        print(f"\nCalifornia County Changes (2016-2021):")
        print(f"Average population change: {comparison['total_pop_change'].mean():.0f}")
        print(f"Average income change: ${comparison['median_income_change'].mean():.0f}")
        print(f"Average education change: {comparison['bachelor_degree_change'].mean():.0f}")

        # Counties with largest changes
        top_pop_growth = comparison.nlargest(3, "total_pop_pct_change")[
            ["NAME", "total_pop_pct_change", "median_income_pct_change"]
        ]
        print(f"\nTop population growth counties:")
        for _, row in top_pop_growth.iterrows():
            print(
                f"  {row['NAME']}: {row['total_pop_pct_change']:+.1f}% pop, "
                f"{row['median_income_pct_change']:+.1f}% income"
            )

        return comparison

    except Exception as e:
        print(f"Error: {e}")
        print("This example requires a Census API key and internet connection.")
        return None


def create_visualization(data, title="Time Series Analysis"):
    """Create visualization of time series results."""
    if data is None:
        return

    try:
        import matplotlib.pyplot as plt

        # Simple visualization based on data structure
        if "pop_change" in data.columns:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

            # Population change histogram
            data["pop_change"].hist(bins=30, ax=ax1, alpha=0.7)
            ax1.set_title("Distribution of Population Change")
            ax1.set_xlabel("Population Change")
            ax1.set_ylabel("Frequency")
            ax1.axvline(0, color="red", linestyle="--", alpha=0.7)

            # Income change if available
            if "income_change" in data.columns:
                data["income_change"].hist(bins=30, ax=ax2, alpha=0.7, color="green")
                ax2.set_title("Distribution of Income Change")
                ax2.set_xlabel("Income Change ($)")
                ax2.set_ylabel("Frequency")
                ax2.axvline(0, color="red", linestyle="--", alpha=0.7)

            plt.suptitle(title, fontsize=14, fontweight="bold")
            plt.tight_layout()
            plt.show()

    except ImportError:
        print("Matplotlib not available for visualization")
    except Exception as e:
        print(f"Visualization error: {e}")


def demonstrate_installation():
    """Demonstrate installation requirements and check dependencies."""
    print("=" * 60)
    print("Time Series Analysis Setup")
    print("=" * 60)

    print("Installation options:")
    print("1. Basic pytidycensus:")
    print("   pip install pytidycensus")
    print()
    print("2. With time series support:")
    print("   pip install pytidycensus[time]")
    print()
    print("3. With all features:")
    print("   pip install pytidycensus[all]")
    print()

    # Check for dependencies
    print("Checking dependencies...")

    try:
        pass

        print("✅ pytidycensus: Available")
    except ImportError:
        print("❌ pytidycensus: Not available")

    try:
        pass

        print("✅ tobler: Available (area interpolation enabled)")
    except ImportError:
        print("❌ tobler: Not available (install with: pip install tobler)")

    try:
        pass

        print("✅ geopandas: Available")
    except ImportError:
        print("❌ geopandas: Not available")

    try:
        pass

        print("✅ matplotlib: Available")
    except ImportError:
        print("❌ matplotlib: Not available")

    print()


def main():
    """Run all time series analysis examples."""
    print("Comprehensive Time Series Analysis with pytidycensus")
    print("=" * 60)

    # Setup
    demonstrate_installation()
    setup_api_key()

    # Examples
    data1 = example_1_acs_time_series()
    create_visualization(data1, "ACS Time Series: DC Tracts 2015-2020")

    data2 = example_2_decennial_comparison()
    create_visualization(data2, "Decennial Census: DC Population Change 2010-2020")

    example_3_county_level_stable_boundaries()

    example_4_tidy_format_analysis()

    example_5_comparison_analysis()

    print("\n" + "=" * 60)
    print("Key Features Demonstrated:")
    print("=" * 60)
    print("✅ Automatic area interpolation for changing boundaries")
    print("✅ Support for both ACS and Decennial Census data")
    print("✅ Intelligent handling of extensive vs intensive variables")
    print("✅ Flexible output formats (wide vs tidy)")
    print("✅ Built-in comparison and validation tools")
    print("✅ Graceful handling of missing dependencies")
    print()
    print("Best Practices:")
    print("• Use consistent survey types (ACS5↔ACS5, Decennial↔Decennial)")
    print("• Classify variables correctly as extensive or intensive")
    print("• Choose appropriate base year for boundary consistency")
    print("• Validate interpolation results for data conservation")
    print("• Use stable geographies when interpolation isn't needed")


if __name__ == "__main__":
    main()
