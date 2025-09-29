# Configuration file for the Sphinx documentation builder.

import os
import sys

import tomli

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------

project = "pytidycensus"
# copyright = "2024, pytidycensus contributors"
author = "Michael Mann & Kyle Walker"

# Get version from pyproject.toml
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "pyproject.toml"), "rb") as f:
        pyproject_data = tomli.load(f)
        release = pyproject_data["project"]["version"]
except (FileNotFoundError, KeyError, ImportError):
    # Fallback if file not found or missing key
    release = "0.1.6"
    print(f"Warning: Could not read version from pyproject.toml, using {release}")

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    # "myst_parser",
    "sphinx_autodoc_typehints",
    "nbsphinx",
    "myst_nb",
    "sphinx_google_analytics",
    "sphinx_sitemap",
]

# -- MyST-NB configuration --
# MyST-NB settings (for markdown files with code cells)
nb_execution_mode = "force"  # 'off', 'auto', 'force', 'cache', 'inline'  # Execute and cache markdown files with code cells
nb_execution_allow_errors = True  # Continue execution even if cells raise errors
nb_execution_timeout = 300
nb_execution_excludepatterns = ["*.ipynb", "*no-execute.md"]  # Skip all .ipynb files
jupyter_cache = "_build/.jupyter_cache"  # Cache location


# -- Templates and exclusions ------------------------------------------------

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]

# -- nbsphinx configuration --
nbsphinx_execute = "never"  # Don't execute notebooks during build
nbsphinx_allow_errors = True
nbsphinx_timeout = 300


# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = "pytidycensus Documentation"
html_short_title = "pytidycensus"

html_theme_options = {
    "logo_only": True,
    "display_version": True,
}

html_logo = "static/logo.png"

# -- Extension configuration -------------------------------------------------

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "show-inheritance": True,
}

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "geopandas": ("https://geopandas.org/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

# MyST settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
]

# Autosummary settings
autosummary_generate = True


# Google Analytics configuration
google_analytics_account = "G-5NFKHXMNYT"

# Sitemap configuration
html_baseurl = "https://mmann1123.github.io/pytidycensus/"
sitemap_url_scheme = "{link}"
sitemap_filename = "sitemap.xml"
sitemap_locales = ["en"]

# Optional: Exclude certain pages from sitemap
sitemap_excludes = [
    "search.html",
    "genindex.html",
    "py-modindex.html",
    "_sources/*",  # Exclude source files
]
