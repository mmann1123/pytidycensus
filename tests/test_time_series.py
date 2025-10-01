"""Tests for time series analysis functions."""

from unittest.mock import patch

import pandas as pd
import pytest

from pytidycensus.time_series import (
    _classify_variables,
    _concatenate_yearly_data,
    _get_data_columns,
    _needs_area_interpolation,
    compare_time_periods,
    get_time_series,
)


class TestTimeSeries:
    """Test time series functionality."""

    def test_needs_area_interpolation_stable_geographies(self):
        """Test that stable geographies don't need interpolation."""
        # Stable geographies
        assert not _needs_area_interpolation("state", [2010, 2020])
        assert not _needs_area_interpolation("region", [2015, 2020])
        assert not _needs_area_interpolation("division", [2010, 2020])

        # County is stable for short periods
        assert not _needs_area_interpolation("county", [2018, 2022])

    def test_needs_area_interpolation_changing_geographies(self):
        """Test that tract/block geographies need interpolation."""
        # Tract boundaries change frequently
        assert _needs_area_interpolation("tract", [2010, 2020])
        assert _needs_area_interpolation("block group", [2015, 2020])
        assert _needs_area_interpolation("block", [2010, 2020])

        # County over long periods might change
        assert _needs_area_interpolation("county", [2000, 2020])

    def test_get_data_columns(self):
        """Test identification of data columns."""
        df = pd.DataFrame(
            {
                "GEOID": ["123", "456"],
                "NAME": ["Place A", "Place B"],
                "total_pop": [1000, 2000],
                "median_income": [50000, 60000],
                "geometry": [None, None],
                "state": ["01", "01"],
            }
        )

        data_cols = _get_data_columns(df)
        expected = ["total_pop", "median_income"]
        assert set(data_cols) == set(expected)

    def test_classify_variables_default(self):
        """Test default variable classification."""
        data_cols = ["total_pop", "median_income", "poverty_count"]

        ext_vars, int_vars = _classify_variables(data_cols)

        # By default, all should be extensive
        assert set(ext_vars) == set(data_cols)
        assert int_vars == []

    def test_classify_variables_specified(self):
        """Test variable classification with specification."""
        data_cols = ["total_pop", "median_income", "poverty_count"]

        ext_vars, int_vars = _classify_variables(
            data_cols,
            extensive_variables=["total_pop", "poverty_count"],
            intensive_variables=["median_income"],
        )

        assert set(ext_vars) == {"total_pop", "poverty_count"}
        assert set(int_vars) == {"median_income"}

    def test_classify_variables_unspecified(self):
        """Test handling of unspecified variables."""
        data_cols = ["total_pop", "median_income", "other_var"]

        ext_vars, int_vars = _classify_variables(
            data_cols, extensive_variables=["total_pop"], intensive_variables=["median_income"]
        )

        # Unspecified variables should go to extensive
        assert "other_var" in ext_vars
        assert "total_pop" in ext_vars
        assert "median_income" in int_vars

    def test_concatenate_yearly_data_wide(self):
        """Test concatenating yearly data in wide format."""
        # Create sample yearly data
        yearly_data = {
            2010: pd.DataFrame(
                {"GEOID": ["123", "456"], "NAME": ["Place A", "Place B"], "total_pop": [1000, 2000]}
            ),
            2020: pd.DataFrame(
                {"GEOID": ["123", "456"], "NAME": ["Place A", "Place B"], "total_pop": [1100, 2100]}
            ),
        }

        result = _concatenate_yearly_data(yearly_data, "wide")

        # Should have multi-index columns
        assert isinstance(result.columns, pd.MultiIndex)
        assert (2010, "total_pop") in result.columns
        assert (2020, "total_pop") in result.columns

        # Should have same number of rows
        assert len(result) == 2

    def test_concatenate_yearly_data_tidy(self):
        """Test concatenating yearly data in tidy format."""
        yearly_data = {
            2010: pd.DataFrame(
                {"GEOID": ["123", "456"], "NAME": ["Place A", "Place B"], "total_pop": [1000, 2000]}
            ),
            2020: pd.DataFrame(
                {"GEOID": ["123", "456"], "NAME": ["Place A", "Place B"], "total_pop": [1100, 2100]}
            ),
        }

        result = _concatenate_yearly_data(yearly_data, "tidy")

        # Should have year column
        assert "year" in result.columns
        assert "variable" in result.columns
        assert "estimate" in result.columns

        # Should have 4 rows (2 places × 2 years)
        assert len(result) == 4

        # Check year values
        assert set(result["year"].unique()) == {2010, 2020}

    @patch("pytidycensus.time_series.get_acs")
    def test_get_time_series_single_year(self, mock_get_acs):
        """Test time series with single year (no interpolation needed)."""
        # Mock return data
        mock_data = pd.DataFrame(
            {"GEOID": ["123", "456"], "NAME": ["Place A", "Place B"], "total_pop": [1000, 2000]}
        )
        mock_get_acs.return_value = mock_data

        result = get_time_series(
            geography="county",
            variables={"total_pop": "B01003_001E"},
            years=[2020],
            dataset="acs5",
            state="CA",
        )

        # Should call get_acs once
        mock_get_acs.assert_called_once()

        # Should return the mocked data
        pd.testing.assert_frame_equal(result, mock_data)

    @patch("pytidycensus.time_series.get_acs")
    @patch("pytidycensus.time_series.TOBLER_AVAILABLE", False)
    def test_get_time_series_no_tobler(self, mock_get_acs):
        """Test time series without tobler available."""
        # Mock return data for multiple years
        mock_data_2018 = pd.DataFrame(
            {"GEOID": ["123", "456"], "NAME": ["Tract A", "Tract B"], "total_pop": [1000, 2000]}
        )
        mock_data_2020 = pd.DataFrame(
            {"GEOID": ["123", "456"], "NAME": ["Tract A", "Tract B"], "total_pop": [1100, 2100]}
        )

        mock_get_acs.side_effect = [mock_data_2018, mock_data_2020]

        with pytest.warns(UserWarning, match="Area interpolation requires"):
            result = get_time_series(
                geography="tract",  # Needs interpolation
                variables={"total_pop": "B01003_001E"},
                years=[2018, 2020],
                dataset="acs5",
                state="CA",
            )

        # Should still return concatenated data
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # Same number of tracts

    @patch("pytidycensus.time_series.get_decennial")
    def test_get_time_series_decennial(self, mock_get_decennial):
        """Test time series with decennial data."""
        # Mock return data
        mock_data = pd.DataFrame({"GEOID": ["123"], "NAME": ["Place A"], "total_pop": [1000]})
        mock_get_decennial.return_value = mock_data

        result = get_time_series(
            geography="state",
            variables={"total_pop": "P1_001N"},
            years=[2020],
            dataset="decennial",
            state="DC",
        )

        # Should call get_decennial with correct survey
        mock_get_decennial.assert_called_once()
        call_args = mock_get_decennial.call_args[1]
        assert call_args["survey"] == "pl"  # 2020 should use 'pl'

    def test_get_time_series_validation_errors(self):
        """Test validation errors in get_time_series."""
        # No years provided
        with pytest.raises(ValueError, match="At least one year must be specified"):
            get_time_series(
                geography="state", variables={"total_pop": "B01003_001E"}, years=[], dataset="acs5"
            )

        # Base year not in years list
        with pytest.raises(ValueError, match="Base year .* must be included in years list"):
            get_time_series(
                geography="state",
                variables={"total_pop": "B01003_001E"},
                years=[2018, 2020],
                base_year=2019,
                dataset="acs5",
            )

    def test_compare_time_periods_basic(self):
        """Test basic time period comparison."""
        # Create test data with multi-index columns
        data = pd.DataFrame(
            {
                ("", "GEOID"): ["123", "456"],
                ("", "NAME"): ["Place A", "Place B"],
                (2018, "total_pop"): [1000, 2000],
                (2020, "total_pop"): [1100, 2100],
                (2018, "median_income"): [50000, 60000],
                (2020, "median_income"): [52000, 61000],
            }
        )
        data.columns = pd.MultiIndex.from_tuples(data.columns, names=["year", "variable"])

        result = compare_time_periods(
            data=data,
            base_period=2018,
            comparison_period=2020,
            variables=["total_pop", "median_income"],
        )

        # Should have comparison columns
        assert "total_pop_2018" in result.columns
        assert "total_pop_2020" in result.columns
        assert "total_pop_change" in result.columns
        assert "total_pop_pct_change" in result.columns

        # Check calculated values
        assert result["total_pop_change"].iloc[0] == 100  # 1100 - 1000
        assert result["total_pop_pct_change"].iloc[0] == 10.0  # 10% increase

    def test_compare_time_periods_validation(self):
        """Test validation in compare_time_periods."""
        # Non-multi-index data
        data = pd.DataFrame({"GEOID": ["123"], "total_pop": [1000]})

        with pytest.raises(ValueError, match="Data must have multi-index columns"):
            compare_time_periods(data=data, base_period=2018, comparison_period=2020)

    def test_compare_time_periods_missing_periods(self):
        """Test error handling for missing time periods."""
        data = pd.DataFrame({(2018, "total_pop"): [1000], (2020, "total_pop"): [1100]})
        data.columns = pd.MultiIndex.from_tuples(data.columns, names=["year", "variable"])

        # Base period not found
        with pytest.raises(ValueError, match="Base period .* not found"):
            compare_time_periods(data=data, base_period=2015, comparison_period=2020)

        # Comparison period not found
        with pytest.raises(ValueError, match="Comparison period .* not found"):
            compare_time_periods(data=data, base_period=2018, comparison_period=2025)


class TestTimeSeriesIntegration:
    """Integration tests for time series functionality."""

    @pytest.mark.integration
    def test_time_series_county_stable_boundaries(self):
        """Test time series with stable county boundaries."""
        import os

        api_key = os.environ.get("CENSUS_API_KEY")
        if not api_key:
            pytest.skip("Census API key not available")

        try:
            # County boundaries are stable, so no interpolation needed
            result = get_time_series(
                geography="county",
                variables={"total_pop": "B01003_001E"},
                years=[2019, 2021],
                dataset="acs5",
                state="DC",
                geometry=False,
                output="wide",
            )

            # Should have multi-index columns
            assert isinstance(result.columns, pd.MultiIndex)
            assert (2019, "total_pop") in result.columns
            assert (2021, "total_pop") in result.columns

            # Should have same geography (DC has 1 county)
            assert len(result) == 1
            assert "District of Columbia" in result[("", "NAME")].iloc[0]

        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")

    @pytest.mark.integration
    def test_compare_time_periods_integration(self):
        """Test time period comparison with real data."""
        import os

        api_key = os.environ.get("CENSUS_API_KEY")
        if not api_key:
            pytest.skip("Census API key not available")

        try:
            # Get time series data
            data = get_time_series(
                geography="state",
                variables={"total_pop": "B01003_001E", "median_income": "B19013_001E"},
                years=[2019, 2021],
                dataset="acs5",
                state="DC",
                geometry=False,
                output="wide",
            )

            # Compare time periods
            comparison = compare_time_periods(
                data=data,
                base_period=2019,
                comparison_period=2021,
                variables=["total_pop", "median_income"],
            )

            # Should have comparison columns
            assert "total_pop_change" in comparison.columns
            assert "total_pop_pct_change" in comparison.columns
            assert "median_income_change" in comparison.columns

            # Values should be reasonable
            pop_change = comparison["total_pop_change"].iloc[0]
            assert abs(pop_change) < 100000  # DC population shouldn't change drastically

        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")
