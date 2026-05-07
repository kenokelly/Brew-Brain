import os
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
if not INFLUX_TOKEN:
    raise ValueError("INFLUX_TOKEN environment variable is required")
INFLUX_ORG = os.getenv("INFLUX_ORG", "homebrew")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "fermentation")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=10000) # 10s timeout
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()
