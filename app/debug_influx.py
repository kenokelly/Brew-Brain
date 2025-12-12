import os
import time
from influxdb_client import InfluxDBClient

url = os.environ.get("INFLUX_URL", "http://influxdb:8086")
token = os.environ.get("INFLUX_TOKEN", "my-super-secret-auth-token")
org = os.environ.get("INFLUX_ORG", "homebrew")
bucket = os.environ.get("INFLUX_BUCKET", "fermentation")

print(f"Connecting to {url}, Org: {org}, Bucket: {bucket}")

client = InfluxDBClient(url=url, token=token, org=org, debug=False)
query_api = client.query_api()

def list_fields(measurement):
    print(f"\n--- Fields for {measurement} ---")
    q = f'''
    import "influxdata/influxdb/schema"
    schema.measurementFieldKeys(bucket: "{bucket}", measurement: "{measurement}")
    '''
    try:
        tables = query_api.query(q)
        for table in tables:
            for record in table.records:
                print(f" - {record.get_value()}")
    except Exception as e:
        print(f"Error querying fields: {e}")

print("\n--- Measurements ---")
try:
    q_measurements = f'''
    import "influxdata/influxdb/schema"
    schema.measurements(bucket: "{bucket}")
    '''
    tables = query_api.query(q_measurements)
    measurements = []
    for table in tables:
        for record in table.records:
            val = record.get_value()
            print(f"Found: {val}")
            measurements.append(val)
    
    for m in measurements:
        list_fields(m)

except Exception as e:
    print(f"Error querying measurements: {e}")
