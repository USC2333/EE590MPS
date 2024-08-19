import pandas as pd
from datetime import datetime

# Load the two files
gps_data = pd.read_csv('Processed_Pixal_GPS_data_20240816_210635.csv')
mps_data = pd.read_csv('MPS_data_20240819_112335.csv')

# Convert timestamps in both datasets to datetime objects for accurate merging
gps_data['timestamps'] = gps_data['timestamps'].apply(lambda x: [datetime.strptime(ts.strip(), "%m/%d/%Y %H:%M:%S") for ts in x.split(';')])
mps_data['Unnamed: 0'] = pd.to_datetime(mps_data['Unnamed: 0'], format="%m/%d/%Y %H:%M:%S")

# Round the MPS data timestamps to the nearest minute for matching
mps_data['timestamp_minute'] = mps_data['Unnamed: 0'].dt.floor('T')

# Function to round datetime objects to the nearest minute
def round_to_minute(dt):
    return dt.replace(second=0, microsecond=0)

# Function to find the average of temperature, pressure, and methane concentration for the GPS timestamps
def get_average_metrics(timestamps):
    rounded_timestamps = [round_to_minute(ts) for ts in timestamps]
    matching_records = mps_data[mps_data['timestamp_minute'].isin(rounded_timestamps)]
    
    if not matching_records.empty:
        avg_temperature = matching_records['temperature'].mean()
        avg_pressure = matching_records['pressure'].mean()
        avg_methane = matching_records['Methane_gas_concentration'].mean()
        return avg_temperature, avg_pressure, avg_methane
    else:
        return None, None, None

# Apply the function to each row in the GPS data
gps_data[['avg_temperature', 'avg_pressure', 'avg_methane']] = gps_data['timestamps'].apply(
    lambda x: pd.Series(get_average_metrics(x))
)

# Save the updated GPS data to a new file
output_file_path = 'Processed_GPS_with_Averages.csv'
gps_data.to_csv(output_file_path, index=False)
