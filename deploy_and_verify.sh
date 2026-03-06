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
    rsync -avz --delete "$@" > /dev/null 2>&1
}

# Sync config files (no longer syncing full app/web dirs since they are in containers)
p_sync ./docker-compose.yml ./telegraf.conf ./grafana $HOST:$REMOTE_DIR/ &
wait

# 2. Pull & Up
echo "🚀 Pulling latest images and Finalizing Deployment..."
ssh $HOST "cd $REMOTE_DIR && docker compose pull && docker compose up -d"

# 3. Verification (Fast check)
echo "🔍 Verifying Deployment..."
ssh $HOST "sleep 5" # Reliable stabilization

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

echo "🎉 OPTIMIZED DEPLOYMENT COMPLETE!"
echo "   Build strategy: Standalone Host-Build + Rsync Delta"
exit 0
