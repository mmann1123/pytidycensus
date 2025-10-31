"""Census variable loading and caching functionality."""

import os
import pickle
from typing import Any, Dict, Optional

import appdirs
import pandas as pd

from .api import CensusAPI


def _get_default_survey(year: int, dataset: str) -> Optional[str]:
    """Get default survey for a given year and dataset.

    Parameters
    ----------
    year : int
        Census year
    dataset : str
        Dataset name

    Returns
    -------
    str or None
        Default survey name, or None if no default
    """
    # Normalize dataset name for comparison
    if dataset.lower() in ["decennial", "dec"]:
        if year >= 2020:
            return "pl"  # PL 94-171 Redistricting Data
        else:
            return "sf1"  # Summary File 1

    # For ACS, no automatic default since acs1/acs3/acs5 are all valid
    return None


def load_variables(
    year: int,
    dataset: Optional[str] = None,
    survey: Optional[str] = None,
    cache: bool = True,
    cache_dir: Optional[str] = None,
) -> pd.DataFrame:
    """Load Census variables for a given dataset and year.

    Parameters
    ----------
    year : int
        Census year
    dataset : str, optional
        Dataset name ('acs', 'dec', 'pep', etc.). Provide either `dataset` or `survey`.
    survey : str, optional
        Survey type (e.g., 'acs5', 'acs1', 'sf1', 'pl'). If provided, the dataset will be
        inferred from the survey. Provide either `dataset` or `survey`, not both.
    cache : bool, default True
        Whether to cache variables for faster future access
    cache_dir : str, optional
        Directory for caching. Defaults to user cache directory.

    Returns
    -------
    pd.DataFrame
        Variables with columns: name, label, concept, predicateType, group, limit

    Examples
    --------
    >>> # Load ACS 5-year variables for 2022
    >>> acs_vars = load_variables(2022, "acs", "acs5")
    >>>
    >>> # Search for income-related variables
    >>> income_vars = acs_vars[acs_vars['label'].str.contains('income', case=False)]
    >>>
    >>> # Load decennial census variables for 2020
    >>> dec_vars = load_variables(2020, "dec", "pl")
    """

    if cache_dir is None:
        cache_dir = appdirs.user_cache_dir("pytidycensus", "variables")

    os.makedirs(cache_dir, exist_ok=True)

    # Create cache filename
    cache_filename = f"{dataset}_{year}"
    if survey:
        cache_filename += f"_{survey}"
    cache_filename += "_variables.pkl"
    cache_path = os.path.join(cache_dir, cache_filename)

    # Try to load from cache first
    if cache and os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                df = pickle.load(f)
            print(
                f"Loaded cached variables for {year} {dataset}" + (f" {survey}" if survey else "")
            )
            return df
        except (pickle.PickleError, EOFError):
            # Cache file corrupted, will re-download
            pass

    # Use default survey if none provided
    if survey is None:
        survey = _get_default_survey(year, dataset)

    # Download variables from API
    print(f"Downloading variables for {year} {dataset}" + (f" {survey}" if survey else ""))

    try:
        api = CensusAPI()
        variables_data = api.get_variables(year, dataset, survey)

        # Parse variables into DataFrame
        df = _parse_variables(variables_data)

        # Cache the results
        if cache:
            with open(cache_path, "wb") as f:
                pickle.dump(df, f)
            print(f"Cached variables to {cache_path}")

        return df

    except Exception as e:
        raise Exception(f"Failed to load variables: {str(e)}")


def _parse_variables(variables_data: Dict[str, Any]) -> pd.DataFrame:
    """Parse raw variables JSON into a structured DataFrame.

    Parameters
    ----------
    variables_data : Dict[str, Any]
        Raw variables JSON from Census API

    Returns
    -------
    pd.DataFrame
        Parsed variables data
    """
    if "variables" not in variables_data:
        raise ValueError("Invalid variables data format")

    variables = variables_data["variables"]

    # Convert to list of dictionaries
    var_list = []
    for var_code, var_info in variables.items():
        if isinstance(var_info, dict):
            record = {
                "name": var_code,
                "label": var_info.get("label", ""),
                "concept": var_info.get("concept", ""),
                "predicateType": var_info.get("predicateType", ""),
                "group": var_info.get("group", ""),
                "limit": var_info.get("limit", 0),
            }
            var_list.append(record)

    df = pd.DataFrame(var_list)

    # Handle empty DataFrame
    if len(df) == 0:
        return pd.DataFrame(
            columns=[
                "name",
                "label",
                "concept",
                "predicateType",
                "group",
                "limit",
                "table",
            ]
        )

    # Clean up and enhance the data
    df["label"] = df["label"].fillna("")
    df["concept"] = df["concept"].fillna("")

    # Add table name extraction
    df["table"] = df["name"].str.extract(r"^([A-Z]+\d+[A-Z]*)")[0]

    # Sort by name
    df = df.sort_values("name").reset_index(drop=True)

    return df


def search_variables(
    pattern: str,
    year: int,
    dataset: str,
    survey: Optional[str] = None,
    field: str = "concept",
) -> pd.DataFrame:
    """Search for variables by pattern in labels, concepts, or names.

    Parameters
    ----------
    pattern : str
        Search pattern (case-insensitive)
    year : int
        Census year
    dataset : str, optional
        Dataset name ('acs', 'dec', 'pep', etc.). Provide either `dataset` or `survey`.
    survey : str, optional
        Survey type (e.g., 'acs5', 'acs1', 'sf1', 'pl'). If provided, the dataset will be
        inferred from the survey. Provide either `dataset` or `survey`, not both.
    field : str, default "label"
        Field to search in ('label', 'concept', 'name', or 'all')

    Returns
    -------
    pd.DataFrame
        Matching variables

    Examples
    --------
    >>> # Search for income variables in ACS
    >>> income_vars = search_variables("income", 2022, "acs", "acs5")
    >>>
    >>> # Search for population in concepts
    >>> pop_vars = search_variables("population", 2020, "dec", "pl", field="concept")
    """
    df = load_variables(year, dataset, survey)

    pattern = pattern.lower()

    if field == "label":
        mask = df["label"].str.lower().str.contains(pattern, na=False)
    elif field == "concept":
        mask = df["concept"].str.lower().str.contains(pattern, na=False)
    elif field == "name":
        mask = df["name"].str.lower().str.contains(pattern, na=False)
    elif field == "all":
        mask = (
            df["label"].str.lower().str.contains(pattern, na=False)
            | df["concept"].str.lower().str.contains(pattern, na=False)
            | df["name"].str.lower().str.contains(pattern, na=False)
        )
    else:
        raise ValueError("Field must be 'label', 'concept', 'name', or 'all'")

    return df[mask].reset_index(drop=True)


def get_table_variables(
    table: str, year: int, dataset: str, survey: Optional[str] = None
) -> pd.DataFrame:
    """Get all variables for a specific table.

    Parameters
    ----------
    table : str
        Table code (e.g., 'B19013', 'P1')
    year : int
        Census year
    dataset : str
        Dataset name
    survey : str, optional
        Survey type

    Returns
    -------
    pd.DataFrame
        Variables for the specified table

    Examples
    --------
    >>> # Get all variables for median household income table
    >>> b19013_vars = get_table_variables("B19013", 2022, "acs", "acs5")
    >>>
    >>> # Get all variables for race table in 2020 Census
    >>> p1_vars = get_table_variables("P1", 2020, "dec", "pl")
    """
    df = load_variables(year, dataset, survey)

    # Match table prefix
    mask = df["name"].str.startswith(table.upper() + "_")

    return df[mask].reset_index(drop=True)


def clear_cache(cache_dir: Optional[str] = None) -> None:
    """Clear the variables cache.

    Parameters
    ----------
    cache_dir : str, optional
        Cache directory to clear. Defaults to user cache directory.
    """
    if cache_dir is None:
        cache_dir = appdirs.user_cache_dir("pytidycensus", "variables")

    if os.path.exists(cache_dir):
        import shutil

        shutil.rmtree(cache_dir)
        print(f"Cleared variables cache at {cache_dir}")
    else:
        print("No cache directory found")


def list_available_datasets(year: int) -> Dict[str, list]:
    """List available datasets for a given year.

    Parameters
    ----------
    year : int
        Census year

    Returns
    -------
    Dict[str, list]
        Available datasets and their surveys
    """
    # This is a simplified version - would need to query Census API for complete list
    datasets = {
        "acs": ["acs1", "acs5"] if year >= 2005 else [],
        "dec": (
            ["sf1", "sf2", "sf3", "sf4"]
            if year <= 2000
            else ["sf1"] if year == 2010 else ["pl"] if year == 2020 else []
        ),
        "pep": ["population", "components", "charagegroups"] if year >= 2000 else [],
    }

    # Filter based on year availability
    available = {}
    for dataset, surveys in datasets.items():
        if surveys:  # Only include if surveys are available
            available[dataset] = surveys

    return available
