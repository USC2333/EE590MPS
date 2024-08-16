import requests, json, time
from pimux import scrip

headers = {"Content-Type": "application/json"}
url = f"http://frontgate.tplinkdns.com:8080/api/v1/Tg9FwQQOcqQypHrocgHF/telemetry"

while True:
    try:
        ts = time.time()
        
        # Attempt to retrieve and parse GPS data
        gps_output = scrip.compute("termux-location")
        gps_data = json.loads(gps_output["output"])
        
        # Ensure that 'latitude' and 'longitude' keys exist
        latitude = gps_data.get("latitude")
        longitude = gps_data.get("longitude")
        
        if latitude is not None and longitude is not None:
            data = json.dumps({"ts": ts, "latitude": latitude, "longitude": longitude})
            resp = requests.post(url, headers=headers, data=data)
        
    except Exception as e:
        # Catch all exceptions and allow the loop to continue running
        pass  # The pass statement will ignore the error and continue the loop

    # Optional: Add a delay to avoid high CPU usage
    time.sleep(2)
