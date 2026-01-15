#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Configuration
HOST="kokelly@192.168.155.226"
REMOTE_DIR="brew-brain"
LOCAL_DIR="$(pwd)"

# Parse Arguments
BUILD_MODE="incremental"  # Default: use Docker cache
if [[ "$1" == "--full" ]]; then
    BUILD_MODE="full"
    echo "🔄 Full Rebuild Mode: Clearing cache and rebuilding everything..."
elif [[ "$1" == "--restart-only" ]] || [[ "$1" == "-r" ]]; then
    BUILD_MODE="restart"
    echo "⚡ Restart Mode: Syncing code and restarting container only..."
elif [[ "$1" == "--patch" ]]; then
    BUILD_MODE="incremental"
    echo "🩹 Patch Mode (now default): Using Docker cache..."
fi

echo "🚀 Starting Deployment to $HOST..."

# 1. Clean Local Cache
echo "🧹 Cleaning local __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 2. Sync Files
echo "📡 Syncing files to remote..."
ssh $HOST "mkdir -p $REMOTE_DIR"
scp -r $LOCAL_DIR/app $HOST:$REMOTE_DIR/
scp $LOCAL_DIR/docker-compose.yml $HOST:$REMOTE_DIR/
scp -r $LOCAL_DIR/grafana $HOST:$REMOTE_DIR/
scp $LOCAL_DIR/telegraf.conf $HOST:$REMOTE_DIR/

# 3. Remote Build & Restart (based on mode)
case $BUILD_MODE in
    "restart")
        echo "🔄 Restarting container with new code..."
        ssh $HOST "cd $REMOTE_DIR && docker compose restart brew-brain"
        ;;
    "full")
        echo "🏗️  Full rebuild (clearing Docker cache)..."
        ssh $HOST "cd $REMOTE_DIR && docker compose down && docker system prune -af && docker compose build --no-cache && docker compose up -d"
        ;;
    *)
        echo "🏗️  Incremental build (using Docker layer cache)..."
        ssh $HOST "cd $REMOTE_DIR && docker compose down && docker compose build && docker compose up -d"
        ;;
esac

echo "✅ Build & Startup Command Successful"

# 4. Verification
echo "🔍 Verifying Deployment..."

# Shorter wait for restart mode
if [[ "$BUILD_MODE" == "restart" ]]; then
    echo "   Waiting for service to stabilize (10s)..."
    ssh $HOST "sleep 10"
else
    echo "   Waiting for service to stabilize (25s)..."
    ssh $HOST "sleep 25"
fi

# CHECK 1: Container Status (Must be RUNNING, not restarting)
echo "   [1/3] Checking Containers..."
CONTAINERS=$(ssh $HOST "docker ps --filter 'status=running' --format '{{.Names}}'")

if echo "$CONTAINERS" | grep -q "brew-brain" && echo "$CONTAINERS" | grep -q "influxdb"; then
    echo "✅ Containers Running (brew-brain, influxdb)"
else
    echo "❌ CRITICAL: Containers missing or not running!"
    echo "Current running containers:"
    echo "$CONTAINERS"
    echo "All containers:"
    ssh $HOST "docker ps -a"
    echo "--- LOGS (Tail 50) ---"
    ssh $HOST "docker logs brew-brain 2>&1 | tail -n 50"
    exit 1
fi

# CHECK 2: API Connectivity
echo "   [2/3] Checking API Connectivity..."
HTTP_CODE=$(ssh $HOST "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/api/status")

if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ API reachable (HTTP 200)"
else
    echo "❌ API Failure (HTTP $HTTP_CODE)"
    echo "--- LOGS (Tail 50) ---"
    ssh $HOST "docker logs brew-brain 2>&1 | tail -n 50"
    exit 1
fi

# CHECK 3: Data Integrity (Proving it works)
echo "   [3/3] Verifying Data Retrieval..."
DATA=$(ssh $HOST "curl -s http://localhost:5000/api/status")

# Check for known keys
if echo "$DATA" | grep -q "\"sg\"" && echo "$DATA" | grep -q "\"temp\""; then
    echo "✅ Data Retrieval Verified (Found Valid Sensor Data)"
    echo "   Retrieved Payload: $DATA"
else
    echo "❌ Data Verification Failed. Invalid JSON or Database Error."
    echo "   Response: $DATA"
    exit 1
fi

echo "🎉 DEPLOYMENT FULLY VERIFIED!"
echo ""
echo "📋 Deploy Modes:"
echo "   (default)       - Incremental build with Docker cache"
echo "   --restart-only  - Code sync + container restart (~30s)"
echo "   --full          - Full rebuild, no cache (~15min)"
exit 0
