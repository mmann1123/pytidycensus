"""Core Census API client for making requests to the US Census Bureau APIs."""

import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import appdirs
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class CensusAPI:
    """Core client for interacting with US Census Bureau APIs.

    Handles authentication, rate limiting, caching, and error handling
    for Census API requests.
    """

    BASE_URL = "https://api.census.gov/data"

    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        """Initialize Census API client.

        Parameters
        ----------
        api_key : str, optional
            Census API key. If not provided, will look for CENSUS_API_KEY environment variable.
        cache_dir : str, optional
            Directory for caching API responses. Defaults to user cache directory.
        """
        self.api_key = api_key or os.getenv("CENSUS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Census API key is required. Get one at: "
                "https://api.census.gov/data/key_signup.html"
            )

        self.cache_dir = cache_dir or appdirs.user_cache_dir("pytidycensus")
        os.makedirs(self.cache_dir, exist_ok=True)

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def _normalize_dataset(self, dataset: str) -> str:
        """Normalize dataset name to Census API format.

        Parameters
        ----------
        dataset : str
            Dataset name (user-friendly or API format)

        Returns
        -------
        str
            Normalized dataset name for API
        """
        dataset_mapping = {
            "decennial": "dec",
            "american_community_survey": "acs",
            "population_estimates": "pep",
        }
        return dataset_mapping.get(dataset.lower(), dataset.lower())

    def _build_url(self, year: int, dataset: str, survey: Optional[str] = None) -> str:
        """Build Census API URL for given parameters.

        Parameters
        ----------
        year : int
            Census year
        dataset : str
            Dataset name (e.g., 'acs', 'dec', 'decennial')
        survey : str, optional
            Survey type (e.g., 'acs5', 'acs1', 'sf1', 'pl')

        Returns
        -------
        str
            Complete API URL
        """
        # Normalize dataset name
        normalized_dataset = self._normalize_dataset(dataset)

        if survey:
            return f"{self.BASE_URL}/{year}/{normalized_dataset}/{survey}"
        else:
            return f"{self.BASE_URL}/{year}/{normalized_dataset}"

    def get(
        self,
        year: int,
        dataset: str,
        variables: List[str],
        geography: Dict[str, str],
        survey: Optional[str] = None,
        show_call: bool = False,
    ) -> List[Dict[str, Any]]:
        """Make a request to the Census API.

        Parameters
        ----------
        year : int
            Census year
        dataset : str
            Dataset name (e.g., 'acs', 'dec')
        variables : List[str]
            List of variable codes to retrieve
        geography : Dict[str, str]
            Geography specification (e.g., {'for': 'county:*', 'in': 'state:06'})
        survey : str, optional
            Survey type (e.g., 'acs5', 'acs1')
        show_call : bool, default False
            Whether to print the API call URL

        Returns
        -------
        List[Dict[str, Any]]
            Parsed JSON response from API

        Raises
        ------
        requests.RequestException
            If API request fails
        ValueError
            If API returns error response
        """
        self._rate_limit()

        url = self._build_url(year, dataset, survey)

        # Build query parameters
        params = {"get": ",".join(variables), "key": self.api_key}
        params.update(geography)

        if show_call:
            full_url = f"{url}?{urlencode(params)}"
            print(f"Census API call: {full_url}")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError:
                # API returned non-JSON content (likely HTML error page)
                raise ValueError(
                    f"Census API returned invalid response. "
                    f"This usually indicates an invalid API key or malformed request. "
                    f"Response content: {response.text[:200]}..."
                )

            # Handle API error responses
            if isinstance(data, dict) and "error" in data:
                raise ValueError(f"Census API error: {data['error']}")

            # Convert to list of dictionaries with header as keys
            if isinstance(data, list) and len(data) > 1:
                headers = data[0]
                rows = data[1:]
                return [dict(zip(headers, row)) for row in rows]

            return data

        except requests.RequestException as e:
            raise requests.RequestException(
                f"""
                Failed to fetch data from Census API  
                =======================================
                Please make sure you get a valid API key set
                ========================================
                {e}
                """
            )

    def get_geography_codes(
        self, year: int, dataset: str, survey: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get available geography codes for a dataset.

        Parameters
        ----------
        year : int
            Census year
        dataset : str
            Dataset name
        survey : str, optional
            Survey type

        Returns
        -------
        Dict[str, Any]
            Available geography codes
        """
        url = self._build_url(year, dataset, survey) + "/geography.json"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            try:
                return response.json()
            except json.JSONDecodeError:
                raise ValueError(
                    f"Census API returned invalid response for geography codes. "
                    f"This usually indicates an invalid API key. "
                    f"Response content: {response.text[:200]}..."
                )
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch geography codes: {e}")

    def get_variables(
        self, year: int, dataset: str, survey: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get available variables for a dataset.

        Parameters
        ----------
        year : int
            Census year
        dataset : str
            Dataset name
        survey : str, optional
            Survey type

        Returns
        -------
        Dict[str, Any]
            Available variables with metadata
        """
        url = self._build_url(year, dataset, survey) + "/variables.json"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            try:
                return response.json()
            except json.JSONDecodeError:
                raise ValueError(
                    f"Census API returned invalid response for variables. "
                    f"This usually indicates an invalid API key. "
                    f"Response content: {response.text[:200]}..."
                )
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch variables: {e}")


def set_census_api_key(api_key: str) -> None:
    """Set Census API key as environment variable.

    Parameters
    ----------
    api_key : str
        Census API key obtained from https://api.census.gov/data/key_signup.html

    Raises
    ------
    ValueError
        If the API key is not a string of exactly 40 characters
    """
    if not isinstance(api_key, str):
        raise ValueError("Census API key must be a string")

    if len(api_key) != 40:
        raise ValueError("Census API key must be exactly 40 characters long")

    os.environ["CENSUS_API_KEY"] = api_key
    print("Census API key has been set for this session.")
