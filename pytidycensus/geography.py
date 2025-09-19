"""Geographic boundary data retrieval and processing using TIGER shapefiles."""

import os
import tempfile
import zipfile
from typing import List, Optional, Union

import certifi
import geopandas as gpd
import requests

from .utils import validate_county, validate_state


class TigerDownloader:
    """Downloads and processes TIGER/Line shapefiles from the US Census Bureau."""

    BASE_URL = "https://www2.census.gov/geo/tiger"

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize TIGER downloader.

        Parameters
        ----------
        cache_dir : str, optional
            Directory for caching downloaded files
        """
        self.cache_dir = cache_dir or tempfile.gettempdir()
        os.makedirs(self.cache_dir, exist_ok=True)

    def _build_url(self, year: int, geography: str, **kwargs) -> str:
        """Build URL for TIGER shapefile download.

        Parameters
        ----------
        year : int
            Census year
        geography : str
            Geography type
        **kwargs
            Additional parameters (state, county, etc.)

        Returns
        -------
        str
            Download URL
        """
        if geography == "state":
            return f"{self.BASE_URL}/TIGER{year}/STATE/tl_{year}_us_state.zip"
        elif geography == "county":
            return f"{self.BASE_URL}/TIGER{year}/COUNTY/tl_{year}_us_county.zip"
        elif geography == "tract":
            state_fips = kwargs.get("state_fips")
            if not state_fips:
                raise ValueError("State FIPS code required for tract geography")
            return f"{self.BASE_URL}/TIGER{year}/TRACT/tl_{year}_{state_fips}_tract.zip"
        elif geography == "block group":
            state_fips = kwargs.get("state_fips")
            if not state_fips:
                raise ValueError("State FIPS code required for block group geography")
            return f"{self.BASE_URL}/TIGER{year}/BG/tl_{year}_{state_fips}_bg.zip"
        elif geography in ["zcta", "zip code tabulation area"]:
            # Use 2020 ZCTA boundaries (zcta520) for year 2020 and later
            # Use 2010 ZCTA boundaries (zcta510) for earlier years
            if year >= 2020:
                return f"{self.BASE_URL}/TIGER{year}/ZCTA520/tl_{year}_us_zcta520.zip"
            else:
                return f"{self.BASE_URL}/TIGER{year}/ZCTA5/tl_{year}_us_zcta510.zip"
        elif geography == "place":
            state_fips = kwargs.get("state_fips")
            if not state_fips:
                raise ValueError("State FIPS code required for place geography")
            return f"{self.BASE_URL}/TIGER{year}/PLACE/tl_{year}_{state_fips}_place.zip"
        elif geography == "metropolitan statistical area/micropolitan statistical area":
            return f"{self.BASE_URL}/TIGER{year}/CBSA/tl_{year}_us_cbsa.zip"
        else:
            raise ValueError(f"Geography '{geography}' not yet supported")

    @staticmethod
    def download_with_wget_or_curl(url, zip_path):
        import shutil
        import subprocess

        # Try wget
        if shutil.which("wget"):
            print("Using wget to download...")
            subprocess.run(
                [
                    "wget",
                    "--quiet",
                    "--show-progress",
                    "--progress=bar:force:noscroll",
                    "-O",
                    zip_path,
                    url,
                ],
                check=True,
            )
        # Fallback to curl
        elif shutil.which("curl"):
            print("Using curl to download...")
            subprocess.run(["curl", "-L", "-o", zip_path, url], check=True)
        else:
            raise RuntimeError("Neither wget nor curl is available on this system.")

    def download_and_extract(self, url: str, filename: str) -> str:
        """Download and extract TIGER shapefile.

        Parameters
        ----------
        url : str
            Download URL
        filename : str
            Local filename for caching

        Returns
        -------
        str
            Path to extracted shapefile directory
        """
        # import urllib.request

        zip_path = os.path.join(self.cache_dir, filename)
        extract_dir = os.path.join(self.cache_dir, filename.replace(".zip", ""))

        # Check if already downloaded and extracted
        if os.path.exists(extract_dir):
            return extract_dir

        # Download file
        print(f"Downloading {filename}...")
        try:
            response = requests.get(url, stream=True, verify=certifi.where())
            response.raise_for_status()

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            print(f"Error downloading {filename} with requests: {e}")
            self.download_with_wget_or_curl(url, zip_path)

        # Extract shapefile
        print(f"Extracting {filename}...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Clean up zip file
        os.remove(zip_path)

        return extract_dir

    def get_shapefile_path(self, extract_dir: str) -> str:
        """Find the shapefile (.shp) in the extracted directory.

        Parameters
        ----------
        extract_dir : str
            Directory containing extracted files

        Returns
        -------
        str
            Path to .shp file
        """
        for file in os.listdir(extract_dir):
            if file.endswith(".shp"):
                return os.path.join(extract_dir, file)
        raise FileNotFoundError("No shapefile found in extracted directory")


def get_geography(
    geography: str,
    year: int = 2022,
    state: Optional[Union[str, int, List[Union[str, int]]]] = None,
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    keep_geo_vars: bool = False,
    cache_dir: Optional[str] = None,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Download and load geographic boundary data from TIGER/Line shapefiles.

    Parameters
    ----------
    geography : str
        Geography type (e.g., 'county', 'tract', 'block group')
    year : int, default 2022
        Census year for boundaries
    state : str, int, or list, optional
        State(s) to filter data for
    county : str, int, or list, optional
        County(ies) to filter data for (requires state)
    keep_geo_vars : bool, default False
        Whether to keep all geographic variables
    cache_dir : str, optional
        Directory for caching downloaded files
    **kwargs
        Additional filtering parameters

    Returns
    -------
    geopandas.GeoDataFrame
        Geographic boundary data

    Examples
    --------
    >>> # Get county boundaries for Texas
    >>> tx_counties = get_geography("county", state="TX", year=2022)
    >>>
    >>> # Get tract boundaries for Harris County, TX
    >>> harris_tracts = get_geography(
    ...     "tract",
    ...     state="TX",
    ...     county="201",
    ...     year=2022
    ... )
    """
    downloader = TigerDownloader(cache_dir)

    # Validate and convert state/county codes
    state_fips = None
    county_fips = None

    if state:
        state_fips_list = validate_state(state)
        # For now, handle single state for shapefile downloads
        state_fips = state_fips_list[0] if len(state_fips_list) == 1 else None
        if len(state_fips_list) > 1:
            print("Warning: Multiple states specified, will filter after download")

    if county and state_fips:
        county_fips_list = validate_county(county, state_fips)
        county_fips = county_fips_list[0] if len(county_fips_list) == 1 else None

    # Build download URL
    url = downloader._build_url(
        year=year, geography=geography, state_fips=state_fips, county_fips=county_fips
    )

    # Generate filename for caching
    filename = os.path.basename(url)

    # Download and extract
    extract_dir = downloader.download_and_extract(url, filename)
    shapefile_path = downloader.get_shapefile_path(extract_dir)

    # Load shapefile
    print(f"Loading {geography} boundaries...")
    gdf = gpd.read_file(shapefile_path)

    # Filter by state if multiple states or state filtering needed
    if state and "STATEFP" in gdf.columns:
        state_fips_list = validate_state(state)
        gdf = gdf[gdf["STATEFP"].isin(state_fips_list)]

    # Filter by county if specified
    if county and "COUNTYFP" in gdf.columns and state_fips:
        county_fips_list = validate_county(county, state_fips)
        gdf = gdf[gdf["COUNTYFP"].isin(county_fips_list)]

    # Standardize GEOID column
    if "GEOID" not in gdf.columns:
        if geography == "state" and "STATEFP" in gdf.columns:
            gdf["GEOID"] = gdf["STATEFP"]
        elif geography == "county" and "STATEFP" in gdf.columns and "COUNTYFP" in gdf.columns:
            gdf["GEOID"] = gdf["STATEFP"] + gdf["COUNTYFP"]
        elif (
            geography == "tract"
            and "STATEFP" in gdf.columns
            and "COUNTYFP" in gdf.columns
            and "TRACTCE" in gdf.columns
        ):
            gdf["GEOID"] = gdf["STATEFP"] + gdf["COUNTYFP"] + gdf["TRACTCE"]
        elif (
            geography == "block group"
            and "STATEFP" in gdf.columns
            and "COUNTYFP" in gdf.columns
            and "TRACTCE" in gdf.columns
            and "BLKGRPCE" in gdf.columns
        ):
            gdf["GEOID"] = gdf["STATEFP"] + gdf["COUNTYFP"] + gdf["TRACTCE"] + gdf["BLKGRPCE"]
        elif (
            geography == "metropolitan statistical area/micropolitan statistical area"
            and "CBSAFP" in gdf.columns
        ):
            gdf["GEOID"] = gdf["CBSAFP"]
        elif geography in ["zcta", "zip code tabulation area"] and "ZCTA5CE20" in gdf.columns:
            gdf["GEOID"] = gdf["ZCTA5CE20"]
        elif geography in ["zcta", "zip code tabulation area"] and "ZCTA5CE10" in gdf.columns:
            gdf["GEOID"] = gdf["ZCTA5CE10"]

    # Clean up columns if not keeping all geo vars
    if not keep_geo_vars:
        # Keep essential columns
        essential_cols = ["GEOID", "NAME", "geometry"]
        if geography == "state":
            essential_cols.extend(["STATEFP", "STUSPS"])
        elif geography == "county":
            essential_cols.extend(["STATEFP", "COUNTYFP", "NAMELSAD"])
        elif geography in ["tract", "block group"]:
            essential_cols.extend(["STATEFP", "COUNTYFP", "TRACTCE"])
            if geography == "block group":
                essential_cols.append("BLKGRPCE")
        elif geography == "metropolitan statistical area/micropolitan statistical area":
            essential_cols.extend(["CBSAFP", "NAMELSAD"])
        elif geography in ["zcta", "zip code tabulation area"]:
            # Keep both 2010 and 2020 ZCTA codes since they may vary by year
            essential_cols.extend(["ZCTA5CE20", "ZCTA5CE10"])

        # Keep only columns that exist
        cols_to_keep = [col for col in essential_cols if col in gdf.columns]
        gdf = gdf[cols_to_keep]

    # Ensure CRS is set (should be EPSG:4269 - NAD83)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4269")

    return gdf


def get_state_boundaries(year: int = 2022, **kwargs) -> gpd.GeoDataFrame:
    """Get US state boundaries."""
    return get_geography("state", year=year, **kwargs)


def get_county_boundaries(
    state: Optional[Union[str, int, List[Union[str, int]]]] = None,
    year: int = 2022,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Get US county boundaries, optionally filtered by state."""
    return get_geography("county", year=year, state=state, **kwargs)


def get_tract_boundaries(
    state: Union[str, int],
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    year: int = 2022,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Get census tract boundaries for a state, optionally filtered by county."""
    return get_geography("tract", year=year, state=state, county=county, **kwargs)


def get_block_group_boundaries(
    state: Union[str, int],
    county: Optional[Union[str, int, List[Union[str, int]]]] = None,
    year: int = 2022,
    **kwargs,
) -> gpd.GeoDataFrame:
    """Get block group boundaries for a state, optionally filtered by county."""
    return get_geography("block group", year=year, state=state, county=county, **kwargs)
