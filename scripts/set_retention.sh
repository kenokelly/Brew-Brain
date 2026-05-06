#!/bin/bash
# Sets a 90-day retention policy on the fermentation bucket for InfluxDB 2.x

# Load env variables if present
if [ -f .env ]; then
  export $(cat .env | xargs)
fi

BUCKET_NAME=${INFLUX_BUCKET:-fermentation}
ORG_NAME=${INFLUX_ORG:-homebrew}
TOKEN=${INFLUX_TOKEN}
CONTAINER_NAME="influxdb"

if [ -z "$TOKEN" ]; then
    echo "Error: INFLUX_TOKEN is not set. Please set it or ensure .env is loaded."
    exit 1
fi

echo "Updating InfluxDB retention policy to 90 days for bucket '$BUCKET_NAME' in org '$ORG_NAME'..."

# Find Bucket ID
BUCKET_ID=$(docker exec $CONTAINER_NAME influx bucket list --name "$BUCKET_NAME" --org "$ORG_NAME" --token "$TOKEN" --hide-headers | awk '{print $1}')

if [ -z "$BUCKET_ID" ]; then
    echo "Error: Could not find bucket ID for '$BUCKET_NAME'."
    exit 1
fi

# Update Bucket
docker exec $CONTAINER_NAME influx bucket update --id "$BUCKET_ID" --retention 90d --token "$TOKEN"

if [ $? -eq 0 ]; then
    echo "Successfully updated retention policy to 90 days."
else
    echo "Failed to update retention policy."
    exit 1
fi
