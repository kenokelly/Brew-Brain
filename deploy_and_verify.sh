#!/bin/bash
set -e

# Configuration
HOST="kokelly@192.168.155.226"
REMOTE_DIR="brew-brain"
LOCAL_DIR="$(pwd)"

# Parse Arguments
FULL_REBUILD=false
RESTART_ONLY=false
if [[ "$1" == "--full" ]]; then
    FULL_REBUILD=true
elif [[ "$1" == "--restart-only" ]] || [[ "$1" == "-r" ]]; then
    RESTART_ONLY=true
fi

# 1. Sync & Remote Prep
echo "📡 Synchronizing configuration..."

# Function for parallel rsync
p_sync() {
    rsync -avz --delete --exclude 'node_modules' --exclude '.next' --exclude '__pycache__' --exclude '*.pyc' "$@" > /dev/null 2>&1
}

# Sync config and source files
p_sync ./.env ./docker-compose.yml ./telegraf.conf ./grafana ./app ./web $HOST:$REMOTE_DIR/ &
wait

# 2. Rebuild & Up
echo "🚀 Rebuilding and Finalizing Deployment..."
ssh $HOST "cd $REMOTE_DIR && docker compose up -d --build"

# 2b. Prune leftover build layers so the Pi's disk doesn't fill up over repeated deploys
echo "🧹 Pruning stale build cache & dangling images..."
ssh $HOST "docker builder prune -af && docker image prune -f" > /dev/null 2>&1

# 3. Verification (Fast check)
echo "🔍 Verifying Deployment..."
ssh $HOST "sleep 30" # Wait for containers to initialize on Raspberry Pi

echo "   [1/2] Checking API..."
if ssh $HOST "curl -s http://localhost:5000/api/health | grep -q 'healthy'"; then
    echo "✅ API Online"
else
    echo "❌ API Offline"
    exit 1
fi

echo "   [2/2] Checking Frontend..."
WEB_CODE=$(ssh $HOST "curl -s -o /dev/null -w '%{http_code}' http://localhost:3001")
if [ "$WEB_CODE" == "200" ]; then
    echo "✅ Frontend Online"
else
    echo "❌ Frontend Offline (HTTP $WEB_CODE)"
    exit 1
fi

# 4. Functional Smoke Tests (liveness above only proves the process is up,
#    not that the brewing math is correct — verify a couple of known values)
echo "🧪 Running functional smoke tests..."

echo "   [1/2] IBU calculator (50g @ 10% AA, 60min, 1.050 OG, 23L -> expect 55.2)..."
IBU_RESULT=$(ssh $HOST "curl -s -X POST http://localhost:5000/api/calculator/ibu -H 'Content-Type: application/json' -d '{\"alpha_acid\":10.0,\"weight_grams\":50,\"boil_time_mins\":60,\"boil_gravity\":1.050,\"batch_volume_liters\":23}'")
if echo "$IBU_RESULT" | grep -q '"ibu":55.2'; then
    echo "✅ IBU calculation correct"
else
    echo "❌ IBU calculation returned unexpected result: $IBU_RESULT"
    exit 1
fi

echo "   [2/2] Water profiles..."
WATER_RESULT=$(ssh $HOST "curl -s http://localhost:5000/api/water/profiles")
if echo "$WATER_RESULT" | grep -q '"status":"success"'; then
    echo "✅ Water chemistry module responding"
else
    echo "❌ Water profiles check failed: $WATER_RESULT"
    exit 1
fi

echo "🎉 OPTIMIZED DEPLOYMENT COMPLETE!"
echo "   Build strategy: Standalone Host-Build + Rsync Delta"
exit 0
