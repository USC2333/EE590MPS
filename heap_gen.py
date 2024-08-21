import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ast
import re
import os
import folium
from tqdm import tqdm
from folium.plugins import HeatMap
from IPython.display import IFrame
import matplotlib.pyplot as plt
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import contextily as ctx
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import cv2

# Parameters
NUM_FRAME = 20
FPS = 2

def timestamps_average(time_list):
    # Calculate the total number of seconds from the first timestamp
    total_seconds = sum((t - time_list[0]).total_seconds() for t in time_list)
    
    # Find the average in seconds
    average_seconds = total_seconds / len(time_list)
    
    # Convert the average back to a timestamp
    average_time = time_list[0] + timedelta(seconds=round(average_seconds))
    
    return average_time

def convert_str_to_datetime_list(datetime_str):
    # Find all the datetime strings in the input string
    datetime_strings = re.findall(r'datetime\.datetime\((.*?)\)', datetime_str)
    
    # Convert the extracted strings to datetime objects
    datetime_list = [
        datetime(*map(int, dt_str.split(', ')))
        for dt_str in datetime_strings
    ]
    
    return datetime_list

def process_timestamp_string(datetime_str):
    datetime_list = convert_str_to_datetime_list(datetime_str)
    return timestamps_average(datetime_list)

data1 = pd.read_csv("data/Processed_GPS_with_Averages_1.csv")
data2 = pd.read_csv("data/Processed_GPS_with_Averages_2.csv")

data1['timestamps'] = data1['timestamps'].apply(process_timestamp_string)
data2['timestamps'] = data2['timestamps'].apply(process_timestamp_string)

def round_coordinates(lat, lon, precision):
    rounded_lat = round(lat, precision)
    rounded_lon = round(lon, precision)
    return rounded_lat, rounded_lon

# Check if two coordinates are within the same square area
def within_square(lat1, lon1, lat2, lon2, square_size):
    return abs(lat1 - lat2) <= square_size and abs(lon1 - lon2) <= square_size

def find_close_points(lat1, lon1, points_list, square_size):
    count = 0
    for lat2, lon2 in points_list:
        if within_square(lat1, lon1, lat2, lon2, square_size):
            count = count + 1
    return count

def calculate_average(numbers):
    if len(numbers) == 0:
        return 0  # Handle empty list case
    return sum(numbers) / len(numbers)

def data_match_averaging(data1, data2, precision = 0.001):
    data = data1.copy()
    points_list = data2[["latitude","longitude"]].to_numpy()
    avg_temperature2 = []
    avg_pressure2    = []
    avg_methane2     = []
    avg_time2        = []
    for index, row in data1.iterrows():
        matched_index_list  = []
        matched_timestamps  = []
        matched_temperature = []
        matched_pressure    = []
        matched_methane     = []
        lat1 = row['latitude']
        lon1 = row['longitude']
        for index2, row2 in data2.iterrows():
            lat2= row2['latitude']
            lon2 = row2['longitude']
            if within_square(lat1, lon1, lat2, lon2, precision):
                matched_index_list.append(index2)
                matched_timestamps.append(row2['timestamps'])
                matched_temperature.append(row2['avg_temperature'])
                matched_pressure.append(row2['avg_pressure'])
                matched_methane.append(row2['avg_methane'])
        avg_temperature2.append(round(np.mean(matched_temperature), 6))
        avg_pressure2.append(round(np.mean(matched_pressure), 6))
        avg_methane2.append(round(np.mean(matched_methane), 6))
        avg_time2.append(timestamps_average(matched_timestamps))
    data["avg_temperatue2"] = avg_temperature2
    data["avg_pressure2"] = avg_pressure2
    data["avg_methane2"] = avg_methane2
    data["timestamps2"] = avg_time2 
        
    return data

merged_data = data_match_averaging(data1, data2)
center_lat = (max(merged_data['latitude']) + min(merged_data['latitude']))/2
center_lon = (max(merged_data['longitude']) + min(merged_data['longitude']))/2

def linear_interpolation(time1, value1, time2, value2, given_time):
    # Convert time differences to seconds
    time1_seconds = time1.timestamp()
    time2_seconds = time2.timestamp()
    given_time_seconds = given_time.timestamp()
    # Calculate the slope (rate of change)
    slope = (value2 - value1) / (time2_seconds - time1_seconds)
    # Calculate the predicted value
    predicted_value = value1 + slope * (given_time_seconds - time1_seconds)
    return predicted_value

def map_data(data, num_frame = NUM_FRAME):
    start_time = min(data['timestamps'])
    end_time = max(data['timestamps2'])
    # Calculate the total duration between start_time and end_time
    total_duration = end_time - start_time
    # Calculate the duration of each interval
    interval_duration = total_duration / (num_frame - 1)
    # Generate the list of timestamps, rounding to the nearest second
    timestamps = [(start_time + i * interval_duration).replace(microsecond=0) for i in range(num_frame)]    
    print(f'total time: {total_duration.total_seconds()} seconds')

    for idx, given_time in enumerate(timestamps):
        mapped_data = pd.DataFrame(data[["latitude","longitude"]])
        mapped_data["timestamp"] = given_time
        temperature_list = []
        pressure_list    = []
        methane_list     = []
        for index, row in data.iterrows():
            temperature_list.append(round(linear_interpolation(row['timestamps'], row['avg_temperature'], 
                                                         row['timestamps2'], row['avg_temperatue2'], given_time),6))
            pressure_list.append(round(linear_interpolation(row['timestamps'], row['avg_pressure'], 
                                                         row['timestamps2'], row['avg_pressure2'], given_time),6))
            methane_list.append(round(linear_interpolation(row['timestamps'], row['avg_methane'], 
                                                         row['timestamps2'], row['avg_methane2'], given_time),6))
        mapped_data["temperature"] = temperature_list
        mapped_data["pressure"] = pressure_list
        mapped_data['methane'] = methane_list
        mapped_data.to_csv(f"mapped_data/frame{idx}.csv")
    
map_data(merged_data)

all_values = []
def normalize(value, min_val, max_val):
    return (value - min_val) / (max_val - min_val)
for idx in tqdm(range(0,NUM_FRAME)):
    data_t = pd.read_csv(f"mapped_data/frame{idx}.csv")
    all_values.extend(data_t.temperature)
min_val = 36
max_val = 46

normalized_data = [normalize(v, min_val, max_val) for v in all_values]

for idx in tqdm(range(0, NUM_FRAME)):
    subset_data = pd.read_csv(f"mapped_data/frame{idx}.csv")
    # Prepare the data for the heatmap
    base_map = folium.Map(location=[center_lat, center_lon], zoom_start=14.5)
    normalized_data = [[row['latitude'], row['longitude'], normalize(row['temperature'], min_val, max_val)]
                               for index, row in subset_data.iterrows()]

    gradient = {0.1: 'blue', 0.2: 'lime', 0.4: 'yellow', 0.65: 'orange', 0.9: 'red'}
    HeatMap(normalized_data, gredient = gradient, min_opacity=0.5).add_to(base_map)
    
    # Save the map to an HTML file and then take a screenshot
    map_file_path = f'./demo_image/temperature_heatmap_{idx}.html'
    base_map.save(map_file_path)

# Setup Chrome options
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Save Function
def save_screenshot(html_file_path, image_file_path):
    # Convert the file path to a URL
    url = f'file://{os.path.abspath(html_file_path)}'
    driver.get(url)
    time.sleep(2)  # Wait for the map to render
    driver.save_screenshot(image_file_path)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
for i in tqdm(range(NUM_FRAME)):
    html_file_path = f'demo_image/temperature_heatmap_{i}.html'
    image_file_path = f'demo_image/temperature_heatmap_{i}.png'
    save_screenshot(html_file_path, image_file_path)
#     print(f"Heatmap has been saved as {image_file_path}")
driver.quit()
print("ALL image saved")

image_files = [f'./demo_image/temperature_heatmap_{i}.png' for i in range(NUM_FRAME)]

# Determine the width and height from the first image
frame = cv2.imread(image_files[0])
height, width, layers = frame.shape

# Define the codec and create a VideoWriter object
video = cv2.VideoWriter('temperature_heatmap_video.avi', cv2.VideoWriter_fourcc(*'DIVX'), FPS, (width, height))

# Loop through the image files and write them to the video
#for image_file in image_files:
for idx, image_file in tqdm(enumerate(image_files), total=len(image_files)):
    cv_read = cv2.imread(image_file)
    time.sleep(1)
    video.write(cv_read)

print("Video has been created.")


