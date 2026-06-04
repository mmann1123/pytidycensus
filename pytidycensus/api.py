"""Core Census API client for making requests to the US Census Bureau APIs."""

import json
import os
import re
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

    @staticmethod
    def _redact_key(text: str, api_key: Optional[str]) -> str:
        """Remove the API key from a string before showing it to the user."""
        if not text:
            return text
        if api_key:
            text = text.replace(api_key, "<your-api-key>")
        # Also redact a ``key=`` query parameter in case the key came from elsewhere.
        return re.sub(r"(key=)[^&\s]+", r"\1<your-api-key>", text)

    def _interpret_http_error(
        self,
        response: "requests.Response",
        url: str,
        year: int,
        dataset: str,
        survey: Optional[str],
        variables: Optional[List[str]] = None,
        context: str = "data",
    ) -> Exception:
        """Translate an HTTP error response into a specific, actionable exception.

        The Census API usually returns a short plain-text description of what went
        wrong (e.g. ``error: error: unknown variable 'B19013_001EXX'``). We surface
        that text and add a targeted tip based on the HTTP status code instead of
        always blaming the API key.

        Parameters
        ----------
        context : str
            What was being fetched, used to phrase messages (e.g. ``"data"``,
            ``"variable metadata"``, ``"geography codes"``).
        variables : list of str, optional
            Requested variable codes, when applicable (data endpoint only).
        """
        status = getattr(response, "status_code", None)
        body = self._redact_key((getattr(response, "text", "") or "").strip(), self.api_key)
        detail = body[:500] + ("..." if len(body) > 500 else "") if body else ""
        api_response = f"\nCensus API said: {detail}" if detail else ""
        endpoint = self._redact_key(url, self.api_key)
        combo = f"{dataset} {survey or ''} {year}".strip()
        requested = f" Requested: {', '.join(variables)}." if variables else ""
        low = body.lower()

        if status in (401, 403):
            return ValueError(
                f"Census API rejected the request as unauthorized (HTTP {status}). "
                "Your API key is likely invalid or not yet activated (activation can "
                "take a few minutes after signup). Check the CENSUS_API_KEY environment "
                "variable or the api_key argument, or request a key at "
                "https://api.census.gov/data/key_signup.html." + api_response
            )

        if status == 400:
            tips = []
            if "unknown variable" in low or "not a variable" in low:
                tips.append(
                    "One or more variables are not valid for this dataset/year "
                    f"({combo}).{requested} Verify codes with "
                    "pytidycensus.load_variables() or search_variables()."
                )
            if "geography" in low or "fips" in low:
                tips.append(
                    "The geography request may be unsupported for this dataset/year. "
                    "Check that the geography level and any state/county filters are valid."
                )
            if not tips:
                tips.append(
                    "The request was malformed. Common causes are an invalid variable "
                    "code, an unsupported geography, or a variable/geography that does "
                    f"not exist for this year ({combo})." + requested
                )
            return ValueError(
                "Census API rejected the request (HTTP 400 Bad Request). "
                + " ".join(tips)
                + api_response
            )

        if status == 404:
            return ValueError(
                f"Census API endpoint not found (HTTP 404) while fetching {context}. "
                "This usually means the dataset/year/survey combination does not "
                f"exist: {combo}. Endpoint: {endpoint}." + api_response
            )

        if status == 204:
            return ValueError(
                f"Census API returned no {context} (HTTP 204) for this request. The "
                "request is valid but no values are available for "
                f"{combo} at the requested geography."
            )

        if status is not None and 500 <= status < 600:
            return requests.RequestException(
                f"Census API server error (HTTP {status}) while fetching {context}. "
                "This is a problem on the Census Bureau's side, not your request. "
                "Try again in a few minutes." + api_response
            )

        return requests.RequestException(
            f"Failed to fetch {context} from Census API (HTTP {status}). Endpoint: "
            f"{endpoint}." + api_response
        )

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

    @staticmethod
    def _detect_table_type(variables: List[str]) -> str:
        """Detect ACS table type from variable prefixes.

        Based on R tidycensus implementation.

        Parameters
        ----------
        variables : List[str]
            List of variable codes

        Returns
        -------
        str
            Table type: 'profile', 'subject', 'cprofile', or None for detailed tables
        """
        if not variables:
            return None

        # Check first variable to determine table type
        # All variables in a single request should be from the same table type
        first_var = variables[0]

        if first_var.startswith("DP"):
            return "profile"
        elif first_var.startswith("S"):
            return "subject"
        elif first_var.startswith("CP"):
            return "cprofile"
        else:
            # B or C tables (detailed tables) - no suffix needed
            return None

    def _build_url(
        self,
        year: int,
        dataset: str,
        survey: Optional[str] = None,
        table_type: Optional[str] = None,
    ) -> str:
        """Build Census API URL for given parameters.

        Parameters
        ----------
        year : int
            Census year
        dataset : str
            Dataset name (e.g., 'acs', 'dec', 'decennial')
        survey : str, optional
            Survey type (e.g., 'acs5', 'acs1', 'sf1', 'pl')
        table_type : str, optional
            ACS table type ('profile', 'subject', 'cprofile') for Data Profile,
            Subject Tables, or Comparison Profile

        Returns
        -------
        str
            Complete API URL
        """
        # Normalize dataset name
        normalized_dataset = self._normalize_dataset(dataset)

        if survey:
            base_url = f"{self.BASE_URL}/{year}/{normalized_dataset}/{survey}"
            # Append table type suffix if specified (for ACS only)
            if table_type and normalized_dataset == "acs":
                base_url = f"{base_url}/{table_type}"
            return base_url
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

        # Detect table type for ACS datasets
        table_type = None
        if dataset == "acs" and variables:
            table_type = self._detect_table_type(variables)

        url = self._build_url(year, dataset, survey, table_type)

        # Build query parameters
        params = {"get": ",".join(variables), "key": self.api_key}
        params.update(geography)

        if show_call:
            full_url = f"{url}?{urlencode(params)}"
            print(f"Census API call: {full_url}")

        try:
            response = self.session.get(url, params=params, timeout=30)
        except requests.RequestException as e:
            # No HTTP response was received at all (DNS failure, timeout, no network).
            raise requests.RequestException(
                "Failed to fetch data from Census API: could not reach the server. "
                "Check your internet connection and try again.\n"
                f"Original error: {e}"
            )

        # Inspect the HTTP status before parsing so we can give a specific,
        # actionable message instead of always blaming the API key.
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise self._interpret_http_error(
                response, url, year, dataset, survey, variables=variables, context="data"
            ) from None

        try:
            data = response.json()
        except json.JSONDecodeError:
            # A 200 response with non-JSON content is how the Census API reports an
            # invalid API key (it returns an HTML page rather than a JSON error).
            body = self._redact_key((response.text or "").strip(), self.api_key)
            raise ValueError(
                "Census API returned a non-JSON response. This most often means the "
                "API key is invalid or not yet activated. Verify CENSUS_API_KEY or "
                "request a key at https://api.census.gov/data/key_signup.html.\n"
                f"Response content: {body[:300]}..."
            )

        # Handle structured API error responses
        if isinstance(data, dict) and "error" in data:
            raise ValueError(f"Census API error: {data['error']}")

        # Convert to list of dictionaries with header as keys
        if isinstance(data, list) and len(data) > 1:
            headers = data[0]
            rows = data[1:]
            return [dict(zip(headers, row)) for row in rows]

        return data

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
        except requests.RequestException as e:
            raise requests.RequestException(
                "Failed to fetch geography codes: could not reach the Census API "
                f"server. Check your internet connection.\nOriginal error: {e}"
            )

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise self._interpret_http_error(
                response, url, year, dataset, survey, context="geography codes"
            ) from None

        try:
            return response.json()
        except json.JSONDecodeError:
            body = self._redact_key((response.text or "").strip(), self.api_key)
            raise ValueError(
                "Census API returned invalid response for geography codes. "
                "This usually indicates an invalid API key. "
                f"Response content: {body[:200]}..."
            )

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
        except requests.RequestException as e:
            raise requests.RequestException(
                "Failed to fetch variables: could not reach the Census API server. "
                f"Check your internet connection.\nOriginal error: {e}"
            )

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise self._interpret_http_error(
                response, url, year, dataset, survey, context="variable metadata"
            ) from None

        try:
            return response.json()
        except json.JSONDecodeError:
            body = self._redact_key((response.text or "").strip(), self.api_key)
            raise ValueError(
                "Census API returned invalid response for variables. "
                "This usually indicates an invalid API key. "
                f"Response content: {body[:200]}..."
            )


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
