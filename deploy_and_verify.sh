#!/bin/bash

# Configuration
HOST="kokelly@192.168.155.226"
REMOTE_DIR="brew-brain"
LOCAL_DIR="$(pwd)"

echo "🚀 Starting Deployment to $HOST..."

# 1. Clean Local Cache
echo "🧹 Cleaning local __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} +

# 2. Sync Files
echo "📡 Syncing files to remote..."
# Create remote dir just in case
ssh $HOST "mkdir -p $REMOTE_DIR"
# Copy app directory
scp -r $LOCAL_DIR/app $HOST:$REMOTE_DIR/
# Copy docker-compose
scp $LOCAL_DIR/docker-compose.yml $HOST:$REMOTE_DIR/
# Copy Grafana config
scp -r $LOCAL_DIR/grafana $HOST:$REMOTE_DIR/
# Copy Telegraf config
scp $LOCAL_DIR/telegraf.conf $HOST:$REMOTE_DIR/

# 3. Remote Build & Restart
echo "🏗️  Rebuilding and Restarting remote container..."
ssh $HOST "cd $REMOTE_DIR && docker compose down && docker compose up -d --build"

# 4. Verification
echo "🔍 Verifying Deployment..."
echo "   Waiting for service to start (15s)..."
ssh $HOST "sleep 15"

echo "   Checking API Health..."
RESPONSE=$(ssh $HOST "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/api/status")

if [ "$RESPONSE" == "200" ]; then
    echo "✅ API is ONLINE (HTTP 200)"
    
    echo "   Checking Logs for success..."
    LOGS=$(ssh $HOST "docker logs brew-brain 2>&1 | grep 'Serving on http://0.0.0.0:5000' | tail -n 1")
    if [ ! -z "$LOGS" ]; then
        echo "✅ Log Verification Passed: $LOGS"
        echo "🎉 DEPLOYMENT SUCCESSFUL!"
        exit 0
    else
        echo "⚠️  API is up but specific log line not found. Check manually."
        exit 0
    fi
else
    echo "❌ API Verification FAILED (HTTP $RESPONSE)"
    echo "   Dumping last 20 lines of logs:"
    ssh $HOST "docker logs brew-brain 2>&1 | tail -n 20"
    exit 1
fi
