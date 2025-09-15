Examples and Tutorials
======================

This section contains Jupyter notebook examples that demonstrate the key features of pytidycensus. These notebooks are Python ports of the original tidycensus R vignettes, adapted for the Python ecosystem.

Getting Started
---------------

All examples require a free Census API key. Get one at: https://api.census.gov/data/key_signup.html

To run these notebooks locally:

.. code-block:: bash

   pip install pytidycensus matplotlib seaborn jupyter
   jupyter notebook examples/

Basic Usage
-----------

.. toctree::
   :maxdepth: 1

   examples/01_basic_usage

Learn the fundamentals of accessing Census data with pytidycensus:

* Setting up your Census API key
* Using ``get_decennial()`` and ``get_acs()`` functions  
* Understanding data formats (tidy vs wide)
* Working with different geographic levels
* Searching for variables

Spatial Data and Mapping
-------------------------

.. toctree::
   :maxdepth: 1

   examples/02_spatial_data

Explore mapping and spatial analysis capabilities:

* Retrieving Census data with geometry
* Creating choropleth maps with matplotlib and geopandas
* Faceted mapping for multiple variables
* Working with coordinate reference systems
* Spatial data visualization best practices

Margins of Error
----------------

.. toctree::
   :maxdepth: 1

   examples/03_margins_of_error

Understanding uncertainty in American Community Survey data:

* Working with estimates and margins of error
* Visualizing uncertainty in data
* Aggregating estimates and calculating derived margins of error
* Using margin of error functions for proper statistical analysis

Other Census Datasets
----------------------

.. toctree::
   :maxdepth: 1

   examples/04_other_datasets

Accessing additional Census datasets:

* Population Estimates Program data with ``get_estimates()``
* Migration flows analysis
* Components of population change
* Housing estimates and characteristics

Census Microdata
-----------------

.. toctree::
   :maxdepth: 1

   examples/05_pums_data

Advanced analysis with Public Use Microdata Sample (PUMS):

* Understanding microdata vs. aggregated data
* Working with Public Use Microdata Areas (PUMAs)
* Using survey weights for proper statistical inference
* Creating custom estimates from individual-level data

Additional Resources
--------------------

* `pytidycensus GitHub Repository <https://github.com/mmann1123/pytidycensus>`_
* `Census API Documentation <https://www.census.gov/data/developers/data-sets.html>`_
* `GeoPandas Documentation <https://geopandas.org/>`_
* `Original R tidycensus <https://walker-data.com/tidycensus/>`_

Running Examples Online
------------------------

All examples include "Open in Colab" badges for easy execution in Google Colab without local installation.

Contributing Examples
----------------------

Have an interesting use case or analysis? We welcome contributions of additional examples:

1. Create a new Jupyter notebook following the existing format
2. Add descriptive markdown cells explaining the analysis
3. Include proper citations and data sources
4. Submit a pull request to the repository

For questions or suggestions about the examples, please open an issue on GitHub.

**Come study with us at The George Washington University**

.. image:: static/GWU_GE.png
   :alt: GWU Geography & Environment