# Example Notebooks

This directory contains Jupyter notebook examples that demonstrate the key features of pytidycensus. These notebooks are Python ports of the original tidycensus R vignettes, adapted for the Python ecosystem.

## Available Examples

### [01_basic_usage.ipynb](01_basic_usage.ipynb)
**Basic usage of pytidycensus**

Learn the fundamentals of accessing Census data with pytidycensus:
- Setting up your Census API key
- Using `get_decennial()` and `get_acs()` functions
- Understanding data formats (tidy vs wide)
- Working with different geographic levels
- Searching for variables with `load_variables()`

### [02_spatial_data.ipynb](02_spatial_data.ipynb)
**Spatial data in pytidycensus**

Explore mapping and spatial analysis capabilities:
- Retrieving Census data with geometry
- Creating choropleth maps with matplotlib and geopandas
- Faceted mapping for multiple variables
- Working with coordinate reference systems
- Spatial data visualization best practices

### [03_margins_of_error.ipynb](03_margins_of_error.ipynb)
**Margins of error in the ACS**

Understanding uncertainty in American Community Survey data:
- Working with estimates and margins of error
- Visualizing uncertainty in data
- Aggregating estimates and calculating derived margins of error
- Using margin of error functions for proper statistical analysis

### [04_other_datasets.ipynb](04_other_datasets.ipynb)
**Other Census Bureau datasets**

Accessing additional Census datasets:
- Population Estimates Program data with `get_estimates()`
- Migration flows analysis
- Components of population change
- Housing estimates and characteristics

### [05_pums_data.ipynb](05_pums_data.ipynb)
**Working with Census microdata**

Advanced analysis with Public Use Microdata Sample (PUMS):
- Understanding microdata vs. aggregated data
- Working with Public Use Microdata Areas (PUMAs)
- Using survey weights for proper statistical inference
- Creating custom estimates from individual-level data

## Requirements

To run these notebooks, you'll need:

```bash
pip install pytidycensus matplotlib seaborn jupyter
```

For full functionality including spatial analysis:
```bash
pip install pytidycensus[all] matplotlib seaborn jupyter contextily
```

## Getting Started

1. **Get a Census API key** from https://api.census.gov/data/key_signup.html
2. **Set your API key** in your notebook:
   ```python
   import pytidycensus as tc
   tc.set_census_api_key("your_key_here")
   ```
3. **Start with basic usage** and work through the examples in order

## Running the Notebooks

### Local Jupyter
```bash
cd examples
jupyter notebook
```

### JupyterLab
```bash
cd examples  
jupyter lab
```

### Google Colab
Each notebook includes a "Open in Colab" badge for easy cloud execution.

## Data Notes

- **API Key Required**: All examples require a free Census API key
- **Data Currency**: Examples use recent data years (2020-2022) 
- **Geographic Scope**: Examples focus on US data at various geographic levels
- **Performance**: Some examples may take time to run due to data download

## Additional Resources

- **pytidycensus Documentation**: https://mmann1123.github.io/pytidycensus
- **Census API Documentation**: https://www.census.gov/data/developers/data-sets.html
- **GeoPandas Documentation**: https://geopandas.org/
- **Original R tidycensus**: https://walker-data.com/tidycensus/

## Contributing

Found an issue or want to improve an example? Please:

1. Open an issue at https://github.com/mmann1123/pytidycensus/issues
2. Submit a pull request with improvements
3. Share your own examples for inclusion

## Citation

If you use these examples in your work, please cite:

```
pytidycensus: Python interface to US Census Bureau APIs
https://github.com/mmann1123/pytidycensus
```