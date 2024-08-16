import pandas as pd
import numpy as np
import csv
from datetime import datetime, timezone, timedelta
import os

# Define a function to round coordinates
def round_coordinates(lat, lon, precision):
    rounded_lat = round(lat, precision)
    rounded_lon = round(lon, precision)
    return rounded_lat, rounded_lon

# Check if two coordinates are within the same square area
def within_square(lat1, lon1, lat2, lon2, square_size):
    return abs(lat1 - lat2) <= square_size and abs(lon1 - lon2) <= square_size

def process_gps_data(input_file, precision, square_size):
    # Generate output file name
    file_name, file_extension = os.path.splitext(input_file)
    output_file = f"Processed_{os.path.basename(file_name)}{file_extension}"

    # Read the CSV file
    data = pd.read_csv(input_file)

    # Assume the data file has columns 'latitude', 'longitude', 'timestamp'
    latitudes = data['latitude'].values
    longitudes = data['longitude'].values
    timestamps = data.iloc[:, 0].values

    # Store results
    rounded_data = []

    for lat, lon, timestamp in zip(latitudes, longitudes, timestamps):
        rounded_lat, rounded_lon = round_coordinates(lat, lon, precision)
        merged = False
        for entry in rounded_data:
            if within_square(rounded_lat, rounded_lon, entry[0], entry[1], square_size):
                entry[2].append(timestamp)
                merged = True
                break
        if not merged:
            rounded_data.append([rounded_lat, rounded_lon, [timestamp]])

    # Write the processed data to a new CSV file
    with open(output_file, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['latitude', 'longitude', 'timestamps'])
        for entry in rounded_data:
            csvwriter.writerow([entry[0], entry[1], ";".join(entry[2])])

# Use this function to process the data
# precision is the number of decimal places, square_size is the size of the square, e.g., 0.0001 represents about 10 meters
process_gps_data('Pixal_GPS_data_20240816_113241.csv', precision=3, square_size=0.001)
