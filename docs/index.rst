pytidycensus Documentation
==========================

**pytidycensus** is a Python library that provides an integrated interface to several United States
Census Bureau APIs and geographic boundary files. It allows users to return Census and ACS data as
pandas DataFrames, and optionally returns GeoPandas GeoDataFrames with feature geometry for mapping
and spatial analysis.

This package is a Python port of the popular R package `tidycensus <https://walker-data.com/tidycensus/>`_
created by Kyle Walker.

Quick Start
-----------

Install pytidycensus:

.. code-block:: bash

   pip install pytidycensus

Get a Census API key at https://api.census.gov/data/key_signup.html and set it:

.. code-block:: python

   import pytidycensus as tc
   tc.set_census_api_key("your_key_here")

Retrieve some data:

.. code-block:: python

   # Get median household income by county in Texas
   tx_income = tc.get_acs(
       geography="county",
       variables="B19013_001",
       state="TX",
       year=2022
   )

   # Get the same data with geometry for mapping
   tx_income_geo = tc.get_acs(
       geography="county", 
       variables="B19013_001",
       state="TX",
       geometry=True
   )

Key Features
------------

- **Simple API**: Clean, consistent interface for all Census datasets
- **Pandas Integration**: Returns familiar pandas DataFrames
- **Spatial Support**: Optional GeoPandas integration for mapping
- **Multiple Datasets**: Support for ACS, Decennial Census, and Population Estimates
- **Geographic Flexibility**: From national to block group level data
- **Caching**: Built-in caching for variables and geography data

Supported Datasets
------------------

- **American Community Survey (ACS)**: 1-year and 5-year estimates
- **Decennial Census**: 1990, 2000, 2010, and 2020 data
- **Population Estimates Program**: Annual population estimates and components of change

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   getting_started
   pytidycensus_intro
   llm_assistant
   examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   api/modules

.. toctree::
   :maxdepth: 1
   :caption: Additional Information:

   changelog
   contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

**Come study with us at The George Washington University**

.. image:: static/GWU_GE.png
   :alt: GWU Geography & Environment