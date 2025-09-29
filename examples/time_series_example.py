"""
Time Series Analysis Example with pytidycensus
==============================================

This example demonstrates how to conduct time series analysis with Census data,
including handling boundary changes with area interpolation.

Key concepts:
- Comparing like survey types (ACS5 ↔ ACS5, Decennial ↔ Decennial)
- Using area_interpolate to handle changing tract boundaries
- Distinguishing extensive vs intensive variables

Requirements:
- pytidycensus
- tobler (for area interpolation)
- geopandas
- matplotlib

Install tobler with: pip install tobler
"""

import warnings

import matplotlib.pyplot as plt

import pytidycensus as tc

warnings.filterwarnings("ignore")

# Check for tobler availability
try:
    from tobler.area_weighted import area_interpolate

    TOBLER_AVAILABLE = True
except ImportError:
    TOBLER_AVAILABLE = False
    print("⚠️  Warning: tobler not available. Install with: pip install tobler")
    print("    Continuing with simplified analysis without area interpolation.")


def setup_api_key():
    """Set up Census API key."""
    # Uncomment and add your API key
    # tc.set_census_api_key("YOUR_API_KEY_HERE")


def compare_decennial_population(state="DC"):
    """Compare decennial census population between 2010 and 2020, accounting for tract boundary
    changes using area interpolation."""
    print(f"=== Decennial Population Comparison: {state} ===\n")

    # Get 2010 decennial data
    print("Fetching 2010 decennial data...")
    data_2010 = tc.get_decennial(
        geography="tract",
        variables={"total_pop": "P001001"},
        state=state,
        year=2010,
        geometry=True,
        output="wide",
    )

    # Get 2020 decennial data
    print("Fetching 2020 decennial data...")
    data_2020 = tc.get_decennial(
        geography="tract",
        variables={"total_pop": "P1_001N"},
        state=state,
        year=2020,
        geometry=True,
        output="wide",
    )

    print(f"2010 tracts: {len(data_2010)}")
    print(f"2020 tracts: {len(data_2020)}")
    print(f"2010 total population: {data_2010['total_pop'].sum():,}")
    print(f"2020 total population: {data_2020['total_pop'].sum():,}")

    # Project to consistent CRS for area calculations
    data_2010_proj = data_2010.to_crs("EPSG:3857")
    data_2020_proj = data_2020.to_crs("EPSG:3857")

    # Interpolate 2010 data to 2020 boundaries
    if TOBLER_AVAILABLE:
        print("\nPerforming area interpolation...")
        data_2010_interpolated = area_interpolate(
            source_df=data_2010_proj,
            target_df=data_2020_proj,
            extensive_variables=["total_pop"],
            intensive_variables=[],
        )
    else:
        print("\nSkipping area interpolation (tobler not available)")
        print("Note: This simplified analysis may not account for boundary changes")
        # For demonstration, use a simple approach (not recommended for real analysis)
        common_geoids = set(data_2010["GEOID"]) & set(data_2020["GEOID"])
        data_2010_interpolated = data_2010_proj[data_2010_proj["GEOID"].isin(common_geoids)]
        data_2020_proj = data_2020_proj[data_2020_proj["GEOID"].isin(common_geoids)]
        print(f"Using {len(common_geoids)} tracts with consistent boundaries")

    # Calculate change
    change_data = data_2020_proj.copy()
    change_data["pop_2010"] = data_2010_interpolated["total_pop"]
    change_data["pop_2020"] = data_2020_proj["total_pop"]
    change_data["pop_change"] = change_data["pop_2020"] - change_data["pop_2010"]
    change_data["pop_change_pct"] = change_data["pop_change"] / change_data["pop_2010"] * 100

    # Summary statistics
    print(f"\nResults after interpolation:")
    print(f"Total population change: {change_data['pop_change'].sum():,.0f}")
    print(
        f"Percent change: {(change_data['pop_change'].sum() / change_data['pop_2010'].sum() * 100):.1f}%"
    )
    print(f"Growing tracts: {(change_data['pop_change'] > 0).sum()}")
    print(f"Declining tracts: {(change_data['pop_change'] < 0).sum()}")

    return change_data


def compare_acs_poverty(state="DC"):
    """Compare ACS poverty rates between two time periods, demonstrating proper ACS5 ↔ ACS5
    comparison."""
    print(f"\n=== ACS Poverty Rate Comparison: {state} ===\n")

    # Get early ACS data (2008-2012)
    print("Fetching 2012 ACS 5-year data (2008-2012)...")
    poverty_2012 = tc.get_acs(
        geography="tract",
        variables={"poverty_count": "B17001_002E", "poverty_total": "B17001_001E"},
        state=state,
        year=2012,
        survey="acs5",
        geometry=True,
        output="wide",
    )

    # Get recent ACS data (2016-2020)
    print("Fetching 2020 ACS 5-year data (2016-2020)...")
    poverty_2020 = tc.get_acs(
        geography="tract",
        variables={"poverty_count": "B17001_002E", "poverty_total": "B17001_001E"},
        state=state,
        year=2020,
        survey="acs5",
        geometry=True,
        output="wide",
    )

    # Calculate poverty rates
    poverty_2012["poverty_rate"] = (
        poverty_2012["poverty_count"] / poverty_2012["poverty_total"] * 100
    )
    poverty_2020["poverty_rate"] = (
        poverty_2020["poverty_count"] / poverty_2020["poverty_total"] * 100
    )

    print(f"2012 tracts: {len(poverty_2012)}")
    print(f"2020 tracts: {len(poverty_2020)}")
    print(f"2012 avg poverty rate: {poverty_2012['poverty_rate'].mean():.1f}%")
    print(f"2020 avg poverty rate: {poverty_2020['poverty_rate'].mean():.1f}%")

    # Project for interpolation
    poverty_2012_proj = poverty_2012.to_crs("EPSG:3857")
    poverty_2020_proj = poverty_2020.to_crs("EPSG:3857")

    # Interpolate with both extensive and intensive variables
    if TOBLER_AVAILABLE:
        print("\nPerforming area interpolation...")
        poverty_2012_interpolated = area_interpolate(
            source_df=poverty_2012_proj,
            target_df=poverty_2020_proj,
            extensive_variables=["poverty_count", "poverty_total"],
            intensive_variables=["poverty_rate"],
        )
    else:
        print("\nSkipping area interpolation (tobler not available)")
        # Use common tracts only
        common_geoids = set(poverty_2012["GEOID"]) & set(poverty_2020["GEOID"])
        poverty_2012_interpolated = poverty_2012_proj[
            poverty_2012_proj["GEOID"].isin(common_geoids)
        ]
        poverty_2020_proj = poverty_2020_proj[poverty_2020_proj["GEOID"].isin(common_geoids)]
        print(f"Using {len(common_geoids)} tracts with consistent boundaries")

    # Calculate change
    change_data = poverty_2020_proj.copy()
    change_data["poverty_rate_2012"] = poverty_2012_interpolated["poverty_rate"]
    change_data["poverty_rate_2020"] = poverty_2020_proj["poverty_rate"]
    change_data["poverty_change"] = (
        change_data["poverty_rate_2020"] - change_data["poverty_rate_2012"]
    )

    print(f"\nResults after interpolation:")
    print(
        f"Average poverty rate change: {change_data['poverty_change'].mean():.1f} percentage points"
    )
    print(f"Tracts with poverty reduction: {(change_data['poverty_change'] < 0).sum()}")
    print(f"Tracts with poverty increase: {(change_data['poverty_change'] > 0).sum()}")

    return change_data


def create_visualization(population_data, poverty_data):
    """Create visualizations of the time series analysis."""
    # Convert back to geographic CRS for mapping
    pop_data = population_data.to_crs("EPSG:4326")
    pov_data = poverty_data.to_crs("EPSG:4326")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Population change (absolute)
    pop_data.plot(
        column="pop_change", cmap="RdBu_r", legend=True, ax=ax1, edgecolor="white", linewidth=0.3
    )
    ax1.set_title("Population Change 2010-2020\n(Absolute)", fontweight="bold")
    ax1.axis("off")

    # Population change (percent)
    pop_data.plot(
        column="pop_change_pct",
        cmap="RdBu_r",
        legend=True,
        ax=ax2,
        edgecolor="white",
        linewidth=0.3,
    )
    ax2.set_title("Population Change 2010-2020\n(Percent)", fontweight="bold")
    ax2.axis("off")

    # Poverty rate 2020
    pov_data.plot(
        column="poverty_rate_2020",
        cmap="Reds",
        legend=True,
        ax=ax3,
        edgecolor="white",
        linewidth=0.3,
    )
    ax3.set_title("Poverty Rate 2020\n(2016-2020 ACS 5-year)", fontweight="bold")
    ax3.axis("off")

    # Poverty change
    pov_data.plot(
        column="poverty_change",
        cmap="RdBu_r",
        legend=True,
        ax=ax4,
        edgecolor="white",
        linewidth=0.3,
    )
    ax4.set_title("Poverty Rate Change 2012-2020\n(Percentage Points)", fontweight="bold")
    ax4.axis("off")

    plt.tight_layout()
    plt.suptitle(
        "Time Series Analysis: Washington DC Census Tracts", fontsize=16, fontweight="bold", y=0.98
    )
    plt.show()


def main():
    """Run the complete time series analysis example."""
    print("Time Series Analysis with pytidycensus")
    print("=" * 50)
    print("This example demonstrates:")
    print("1. Comparing decennial census data (2010 vs 2020)")
    print("2. Comparing ACS 5-year data (2012 vs 2020)")
    print("3. Handling boundary changes with area interpolation")
    print("4. Distinguishing extensive vs intensive variables")
    print()

    # Setup
    setup_api_key()

    try:
        # Run population analysis
        population_results = compare_decennial_population("DC")

        # Run poverty analysis
        poverty_results = compare_acs_poverty("DC")

        # Create visualization
        print("\n=== Creating Visualizations ===")
        create_visualization(population_results, poverty_results)

        print("\n=== Key Takeaways ===")
        print("1. ✅ Always compare like survey types (Decennial↔Decennial, ACS5↔ACS5)")
        print("2. ✅ Use area interpolation to handle boundary changes")
        print("3. ✅ Classify variables as extensive (counts) or intensive (rates)")
        print("4. ✅ Check interpolation results for data conservation")
        print("5. ✅ Document assumptions and limitations")

    except Exception as e:
        print(f"Error: {e}")
        print("\nThis example requires:")
        print("- Census API key (set in setup_api_key function)")
        print("- Internet connection")
        print("- Libraries: pytidycensus, tobler, geopandas, matplotlib")
        print("\nTo install missing dependencies:")
        print("pip install tobler geopandas matplotlib")


if __name__ == "__main__":
    main()
