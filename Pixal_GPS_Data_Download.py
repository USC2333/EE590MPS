import requests
import pandas as pd
import json
from datetime import datetime, timezone, timedelta

# Configuration
thingsboard_url = 'http://frontgate.tplinkdns.com:8080'
username = 'tenant@thingsboard.org'
password = 'ecet2023'
device_id = '80229380-4af4-11ef-92e8-77982ca011ca'

# Set the time range (GMT-0700)
def get_timestamp(date_str, hour=0, minute=0):
    gmt_minus_7 = timezone(timedelta(hours=-7))
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0, tzinfo=gmt_minus_7)
    return int(dt.timestamp() * 1000)

date = '2024-08-08'
start_ts = get_timestamp(date, 0, 0)
end_ts = get_timestamp(date, 23, 59)

def get_jwt_token():
    url = f'{thingsboard_url}/api/auth/login'
    response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps({'username': username, 'password': password}))
    response.raise_for_status()
    return response.json()['token']

def get_device_data(jwt_token):
    url = f'{thingsboard_url}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys=altitude,latitude,longitude&startTs={start_ts}&endTs={end_ts}&limit=10000&interval=5000'#&interval=5000&limit=1000&agg=AVG'
    headers = {'X-Authorization': f'Bearer {jwt_token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def save_to_csv(data):
    # Create a dictionary to store organized data
    organized_data = {}
    
    # Categorize data based on timestamp
    for key, values in data.items():
        for item in values:
            timestamp = item['ts']
            if timestamp not in organized_data:
                organized_data[timestamp] = {}
            organized_data[timestamp][key] = item['value']
    
    # Convert dictionary to DataFrame
    df = pd.DataFrame.from_dict(organized_data, orient='index')
    
    # Convert timestamp to human-readable format in GMT-7 (mm/dd/yyyy hh:mm:ss)
    gmt_minus_7 = timezone(timedelta(hours=-7))
    df.index = pd.to_datetime(df.index, unit='ms').tz_localize(timezone.utc).tz_convert(gmt_minus_7).strftime('%m/%d/%Y %H:%M:%S')
    
    # Sort by time from earliest to latest
    df = df.sort_index(ascending=True)
    
    # Generate a file name with the current timestamp
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"Pixal_GPS_data_{timestamp_str}.csv"
    
    # Save as CSV file
    df.to_csv(file_name)
    print(f'Data saved to {file_name}')

def main():
    jwt_token = get_jwt_token()
    data = get_device_data(jwt_token)
    save_to_csv(data)

if __name__ == '__main__':
    main()
