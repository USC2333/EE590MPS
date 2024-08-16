import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx

# Load the CSV file
file_path = 'Pixal_GPS_data_20240815_171306.csv'  # Replace with the path to your CSV file
gps_data = pd.read_csv(file_path)

# Create a GeoDataFrame using the latitude and longitude
gdf = gpd.GeoDataFrame(
    gps_data, geometry=gpd.points_from_xy(gps_data.longitude, gps_data.latitude))

# Convert to the Web Mercator projection
gdf = gdf.set_crs("EPSG:4326").to_crs("EPSG:3857")

# Plot the points on the map
fig, ax = plt.subplots(figsize=(10, 10))
gdf.plot(ax=ax, marker='o', color='red', markersize=5, linestyle='-', linewidth=2)

# Add OpenStreetMap basemap
ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

# Set plot title and labels
ax.set_title('GPS Path on Earth Map')
plt.xlabel('Longitude')
plt.ylabel('Latitude')

plt.show()

