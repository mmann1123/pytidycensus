# Mapping Migration Flows

This guide demonstrates how to visualize county-to-county migration flows using `pytidycensus`. When you call `get_flows(geometry=True)`, pytidycensus automatically calculates accurate centroids and returns them ready for mapping.

## Basic Flow Mapping with Basemap

This example shows how to create an attractive migration flow map with a contextily basemap:

```python
import pytidycensus as tc
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import LineString
import contextily as ctx
import numpy as np

# Get flows with geometry
flows_geo = tc.get_flows(
    geography="county",
    state="CA",
    year=2018,
    geometry=True,
    output="wide"
)

# Create LineString geometries from centroids
lines = flows_geo.copy()
lines = lines.dropna(subset=['centroid1', 'centroid2'])
lines['geometry'] = lines.apply(lambda r: LineString([r['centroid1'], r['centroid2']]), axis=1)
lines = gpd.GeoDataFrame(lines, geometry='geometry', crs=flows_geo.crs)

# Project to Web Mercator for basemap compatibility
lines_web = lines.to_crs(epsg=3857)

# Scale line widths by flow volume using log transformation for better visual contrast
min_w, max_w = 0.5, 6.0
vals = np.log1p(lines_web['MOVEDIN'].astype(float).fillna(0))
max_val = vals.max() if vals.max() > 0 else 1.0
lines_web['lw'] = np.interp(vals, [0, max_val], [min_w, max_w])

# Sort so large flows draw on top of small flows
lines_web_sorted = lines_web.sort_values('MOVEDIN', ascending=True)

# Create the plot
fig, ax = plt.subplots(figsize=(12, 10))
lines_web_sorted.sample(1000).plot(
    ax=ax,
    linewidth=lines_web_sorted['lw'],
    column='MOVEDNET',            # Color by net migration
    cmap='RdYlBu',
    alpha=0.85,
    legend=True,
    zorder=1
)

# Plot origin/destination centroids
orig_pts = gpd.GeoDataFrame(
    geometry=lines[['centroid1']].rename(columns={'centroid1':'geometry'})['geometry'],
    crs=lines.crs
).set_geometry('geometry').to_crs(epsg=3857)

dest_pts = gpd.GeoDataFrame(
    geometry=lines[['centroid2']].rename(columns={'centroid2':'geometry'})['geometry'],
    crs=lines.crs
).set_geometry('geometry').to_crs(epsg=3857)

orig_pts.plot(ax=ax, markersize=18, color='black', alpha=0.9, zorder=3)
dest_pts.plot(ax=ax, markersize=14, color='white', edgecolor='black', alpha=0.9, zorder=4)

# Add basemap with fallbacks for reliability
try:
    ctx.add_basemap(ax, source=ctx.providers.Stamen.TonerLite)
except Exception:
    try:
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    except Exception:
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

ax.set_axis_off()
plt.title('County-to-county migration flows (linewidth ~ log(MOVEDIN), color ~ MOVEDNET)', fontsize=14)
plt.tight_layout()
plt.show()
```

## Simple Flow Map Without Basemap

For a cleaner look without external basemap dependencies:

```python
import pytidycensus as tc
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import LineString
import numpy as np

# Get flows with geometry
flows_geo = tc.get_flows(
    geography="county",
    state="NY",
    year=2018,
    geometry=True,
    output="wide"
)

# Create LineString geometries
lines = flows_geo.copy()
lines = lines.dropna(subset=['centroid1', 'centroid2'])
lines['geometry'] = lines.apply(lambda r: LineString([r['centroid1'], r['centroid2']]), axis=1)
lines = gpd.GeoDataFrame(lines, geometry='geometry', crs=flows_geo.crs)

# Filter for significant flows (>500 people)
significant_flows = lines[lines['MOVEDIN'] > 500].copy()

# Scale line widths
min_w, max_w = 0.5, 4.0
vals = np.log1p(significant_flows['MOVEDIN'].astype(float))
max_val = vals.max() if vals.max() > 0 else 1.0
significant_flows['lw'] = np.interp(vals, [0, max_val], [min_w, max_w])

# Plot
fig, ax = plt.subplots(figsize=(12, 10))
significant_flows.plot(
    ax=ax,
    linewidth=significant_flows['lw'],
    column='MOVEDNET',
    cmap='RdBu_r',
    alpha=0.7,
    legend=True
)

ax.set_axis_off()
plt.title('New York County Migration Flows (2018)', fontsize=14)
plt.tight_layout()
plt.show()
```

## Mapping with State Boundaries

Add geographic context by including state or county boundaries:

```python
import pytidycensus as tc
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import LineString
import numpy as np

# Get flows
flows_geo = tc.get_flows(
    geography="county",
    state="TX",
    year=2018,
    geometry=True,
    output="wide"
)

# Get Texas county boundaries for context
tx_counties = tc.get_geography("county", state="TX", year=2018)

# Create flow lines
lines = flows_geo.copy()
lines = lines.dropna(subset=['centroid1', 'centroid2'])
lines['geometry'] = lines.apply(lambda r: LineString([r['centroid1'], r['centroid2']]), axis=1)
lines = gpd.GeoDataFrame(lines, geometry='geometry', crs=flows_geo.crs)

# Filter significant flows
significant_flows = lines[lines['MOVEDIN'] > 1000].copy()

# Calculate line widths
min_w, max_w = 0.5, 5.0
vals = np.log1p(significant_flows['MOVEDIN'].astype(float))
max_val = vals.max() if vals.max() > 0 else 1.0
significant_flows['lw'] = np.interp(vals, [0, max_val], [min_w, max_w])

# Plot
fig, ax = plt.subplots(figsize=(14, 10))

# County boundaries as background
tx_counties.boundary.plot(ax=ax, linewidth=0.5, color='gray', alpha=0.3, zorder=1)

# Flow lines
significant_flows.plot(
    ax=ax,
    linewidth=significant_flows['lw'],
    column='MOVEDNET',
    cmap='coolwarm',
    alpha=0.8,
    legend=True,
    zorder=2
)

ax.set_axis_off()
plt.title('Texas County-to-County Migration Flows >1,000 people (2018)', fontsize=14)
plt.tight_layout()
plt.show()
```

## Multi-State Flow Analysis

Compare migration patterns across multiple states:

```python
import pytidycensus as tc
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import LineString
import numpy as np

# Get flows for multiple states
states = ['RI', 'MA']
all_flows = []

for state in states:
    flows = tc.get_flows(
        geography="county",
        state=state,
        year=2018,
        geometry=True,
        output="wide"
    )
    flows['state'] = state
    all_flows.append(flows)

# Combine all flows
combined_flows = gpd.pd.concat(all_flows, ignore_index=True)

# Create lines
lines = combined_flows.copy()
lines = lines.dropna(subset=['centroid1', 'centroid2'])
lines['geometry'] = lines.apply(lambda r: LineString([r['centroid1'], r['centroid2']]), axis=1)
lines = gpd.GeoDataFrame(lines, geometry='geometry', crs=combined_flows.crs)

# Filter for significant flows
significant_flows = lines[lines['MOVEDIN'] > 2000].copy()

# Create subplots for each state
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

for idx, state in enumerate(states):
    state_flows = significant_flows[significant_flows['state'] == state].copy()

    # Scale line widths
    vals = np.log1p(state_flows['MOVEDIN'].astype(float))
    max_val = vals.max() if vals.max() > 0 else 1.0
    state_flows['lw'] = np.interp(vals, [0, max_val], [0.5, 4.0])

    # Plot
    state_flows.plot(
        ax=axes[idx],
        linewidth=state_flows['lw'],
        column='MOVEDNET',
        cmap='RdBu_r',
        alpha=0.7
    )

    axes[idx].set_axis_off()
    axes[idx].set_title(f'{state} Migration Flows', fontsize=12)

plt.tight_layout()
plt.show()
```

## Understanding the Variables

The flow data includes several key variables:

- **MOVEDIN**: Number of people who moved into the destination
- **MOVEDOUT**: Number of people who moved out of the origin
- **MOVEDNET**: Net migration (MOVEDIN - MOVEDOUT)
- **FULL1_NAME**: Origin location name
- **FULL2_NAME**: Destination location name
- **centroid1**: Origin centroid (Point geometry)
- **centroid2**: Destination centroid (Point geometry)

## Customization Tips

### 1. Color Schemes
```python
# Positive flows (immigration)
cmap='Blues'

# Net migration (red = loss, blue = gain)
cmap='RdBu_r'

# Sequential yellow to red
cmap='YlOrRd'

# Diverging red-yellow-blue
cmap='RdYlBu'
```

### 2. Line Width Scaling
```python
# Linear scaling
widths = flows['MOVEDIN'] / flows['MOVEDIN'].max() * 5

# Log scaling (recommended for flows with wide range)
widths = np.log1p(flows['MOVEDIN'])
widths = (widths / widths.max() * 5).clip(lower=0.2)

# Square root scaling (middle ground)
widths = np.sqrt(flows['MOVEDIN'])
widths = (widths / widths.max() * 5).clip(lower=0.2)
```

### 3. Filtering Strategies
```python
# By volume
significant = flows[flows['MOVEDIN'] > 1000]

# By percentage (top 10%)
threshold = flows['MOVEDIN'].quantile(0.90)
top_flows = flows[flows['MOVEDIN'] > threshold]

# By net migration magnitude
abs_net = flows['MOVEDNET'].abs()
threshold = abs_net.quantile(0.85)
net_flows = flows[abs_net > threshold]
```

## Projection Notes

pytidycensus returns flows in **EPSG:4269 (NAD83)**, which works well for most mapping purposes. For specific use cases:

- **Web maps with basemaps**: Convert to EPSG:3857 (Web Mercator) using `.to_crs(epsg=3857)`
- **US national maps**: Convert to EPSG:2163 (US National Atlas Equal Area) using `.to_crs(epsg=2163)`
- **State-level maps**: Can use state-specific projections or stick with EPSG:4269

The centroid calculation is performed automatically by pytidycensus in an appropriate equal-area projection to ensure accuracy, then transformed back to EPSG:4269 for compatibility.

## Handling Large Datasets

When working with nationwide flows (millions of records):

```python
# Option 1: Get geometry=False first, then filter
flows = tc.get_flows(geography="county", year=2018, geometry=False)
significant = flows[flows['MOVEDIN'] > 5000].copy()
# Then add geometry only for filtered data if needed

# Option 2: Sample large datasets
lines_sample = lines.sample(n=5000, random_state=42)

# Option 3: Use spatial filters (bounding box)
minx, miny, maxx, maxy = -125, 32, -114, 42  # California bbox
lines_subset = lines.cx[minx:maxx, miny:maxy]
```

## Best Practices

1. **Filter before visualizing**: Large flow datasets can create cluttered maps. Filter for significant flows (e.g., >1000 people)
2. **Use log scaling**: Flow volumes often span orders of magnitude. Log scaling (`np.log1p()`) creates better visual contrast
3. **Sort by volume**: Draw small flows first, large flows last, so important flows appear on top
4. **Color meaningfully**: Use net migration (MOVEDNET) to show directionality
5. **Add context**: Include state/county boundaries or basemaps for geographic reference
6. **Mind the projections**: Use Web Mercator (EPSG:3857) when adding contextily basemaps

## Next Steps

- Explore demographic breakdowns with the `breakdown` parameter (available 2006-2015)
- See [examples/08_migration_flows_example.ipynb](08_migration_flows_example.ipynb) for more detailed examples
- Combine with other Census data using `get_acs()` or `get_decennial()`
- Create interactive maps with `folium` or `plotly`
