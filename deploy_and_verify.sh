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

echo "🚀 Starting Optimized Deployment to $HOST..."

# 1. Clean Local Cache
echo "🧹 Cleaning local __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 2. Host-Side Frontend Build (Background)
if [ "$RESTART_ONLY" = false ]; then
    echo "🏗️ Starting local Frontend build in background..."
    (
        cd web
        # Fast-Path: Only npm ci if package-lock changed
        if [ ! -d "node_modules" ] || [ package-lock.json -nt node_modules ]; then
            echo "📦 Package lock changed, installing..."
            npm ci > /dev/null 2>&1
        fi
        npm run build > /dev/null 2>&1
    ) &
    FE_BUILD_PID=$!
fi

# 3. Parallel Sync & Remote Prep
echo "📡 Starting Parallel Synchronization..."

# Function for parallel rsync
p_sync() {
    rsync -avz --delete "$@" > /dev/null 2>&1
}

# Sync Backend & Configs in parallel
p_sync ./app/requirements-core.txt ./app/requirements-app.txt $HOST:$REMOTE_DIR/app/ &
p_sync --exclude '__pycache__' --exclude '.venv' ./app $HOST:$REMOTE_DIR/ &
p_sync ./docker-compose.yml ./telegraf.conf ./grafana $HOST:$REMOTE_DIR/ &

# If not restart-only, start remote Backend build
if [ "$RESTART_ONLY" = false ]; then
    echo "🏗️ Starting remote Backend build (Async)..."
    # SRE Opt: Use --pull to ensure we have latest slim image without full rebuild
    ssh $HOST "cd $REMOTE_DIR && docker compose build --pull brew-brain" > /dev/null 2>&1 &
    BE_BUILD_PID=$!
fi

# Wait for local Frontend build
if [ ! -z "$FE_BUILD_PID" ]; then
    echo "⏳ Waiting for local Frontend build..."
    wait $FE_BUILD_PID
    echo "✅ Frontend build done."
    
    # Sync Web Artifacts (Grouped to avoid race conditions)
    echo "📦 Syncing web artifacts..."
    ssh $HOST "mkdir -p $REMOTE_DIR/web/.next"
    
    # Sync standalone content (contains server.js, node_modules)
    p_sync ./web/.next/standalone/ $HOST:$REMOTE_DIR/web/
    
    # Sync static and public (parallel is fine here as they go to subdirs)
    p_sync ./web/.next/static/ $HOST:$REMOTE_DIR/web/.next/static/ &
    p_sync ./web/public/ $HOST:$REMOTE_DIR/web/public/ &
    
    # Sync configs (Last, no delete to prevent wiping standalone)
    rsync -avz ./web/Dockerfile ./web/package.json $HOST:$REMOTE_DIR/web/
    
    wait # Wait for static/public
    echo "🏗️ Building remote Web container (Async)..."
    ssh $HOST "cd $REMOTE_DIR && docker compose build web" &
    WEB_BUILD_PID=$!
fi

# Final synchronization for all builds
echo "⏳ Waiting for all remote builds to finalize..."
[ ! -z "$BE_BUILD_PID" ] && wait $BE_BUILD_PID && echo "✅ Backend container ready."
[ ! -z "$WEB_BUILD_PID" ] && wait $WEB_BUILD_PID && echo "✅ Web container ready."

# 4. Final Up & Verification
echo "🚀 Finalizing Deployment..."
ssh $HOST "cd $REMOTE_DIR && docker compose up -d"

# 5. Verification (Fast check)
echo "🔍 Verifying Deployment..."
ssh $HOST "sleep 10" # Reliable stabilization

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
