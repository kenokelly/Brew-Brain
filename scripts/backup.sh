#!/bin/bash
# ============================================
# Brew Brain Full System Backup Script
# ============================================
# Backs up: InfluxDB, Grafana, Node-RED, Brew Brain config
# Usage: ./backup.sh [output_dir]
# 
# Run from Brew-Brain project root on the Raspberry Pi

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="${1:-brew_brain_backup_$TIMESTAMP}"

echo "🍺 Brew Brain Full System Backup"
echo "================================"
echo "Backup Directory: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"/{influxdb,grafana,nodered,config}

# ============================================
# 1. InfluxDB Data
# ============================================
echo "📊 [1/5] Backing up InfluxDB..."
if docker ps | grep -q influxdb; then
    # Create backup inside container
    docker exec influxdb influx backup /tmp/influx_backup \
        --token "$INFLUX_TOKEN" \
        --org homebrew 2>/dev/null || echo "  ⚠️  InfluxDB backup command returned warning (may still be successful)"
    
    # Copy from container to host
    docker cp influxdb:/tmp/influx_backup "$OUTPUT_DIR/influxdb/" 2>/dev/null && \
        echo "  ✅ InfluxDB data backed up" || \
        echo "  ⚠️  Could not copy InfluxDB backup"
    
    # Cleanup inside container
    docker exec influxdb rm -rf /tmp/influx_backup 2>/dev/null
else
    echo "  ⚠️  InfluxDB container not running - skipping"
fi

# ============================================
# 2. Grafana Data
# ============================================
echo "📈 [2/5] Backing up Grafana..."
if [ -d "grafana_data" ]; then
    cp -r grafana_data "$OUTPUT_DIR/grafana/" && \
        echo "  ✅ Grafana data backed up" || \
        echo "  ⚠️  Could not backup Grafana data"
else
    echo "  ⚠️  Grafana data directory not found"
fi

# Also backup provisioning if exists
if [ -d "grafana/provisioning" ]; then
    cp -r grafana/provisioning "$OUTPUT_DIR/grafana/provisioning"
fi

# ============================================
# 3. Node-RED / TiltPi Flows
# ============================================
echo "🔴 [3/5] Backing up Node-RED..."
NODERED_DIR="$HOME/.node-red"

if [ -d "$NODERED_DIR" ]; then
    # Copy flows
    cp "$NODERED_DIR"/flows*.json "$OUTPUT_DIR/nodered/" 2>/dev/null && \
        echo "  ✅ Node-RED flows backed up" || \
        echo "  ⚠️  No flow files found"
    
    # Copy settings and credentials (if exists)
    [ -f "$NODERED_DIR/settings.js" ] && cp "$NODERED_DIR/settings.js" "$OUTPUT_DIR/nodered/"
    [ -f "$NODERED_DIR/.config.runtime.json" ] && cp "$NODERED_DIR/.config.runtime.json" "$OUTPUT_DIR/nodered/"
    [ -f "$NODERED_DIR/flows_cred.json" ] && cp "$NODERED_DIR/flows_cred.json" "$OUTPUT_DIR/nodered/"
    
    # Copy package.json for installed nodes
    [ -f "$NODERED_DIR/package.json" ] && cp "$NODERED_DIR/package.json" "$OUTPUT_DIR/nodered/"
else
    echo "  ⚠️  Node-RED directory not found at $NODERED_DIR"
fi

# ============================================
# 4. Brew Brain Config
# ============================================
echo "🧠 [4/5] Backing up Brew Brain config..."

# Export via API if running
if curl -s http://localhost:5000/api/status > /dev/null 2>&1; then
    curl -s http://localhost:5000/api/backup > "$OUTPUT_DIR/config/brew_brain_config.json" && \
        echo "  ✅ Brew Brain config exported via API"
else
    echo "  ⚠️  Brew Brain not running - using local files"
fi

# Copy local data files
if [ -d "brain_data" ]; then
    cp -r brain_data "$OUTPUT_DIR/config/brain_data"
fi

# Copy environment and docker-compose
[ -f ".env" ] && cp .env "$OUTPUT_DIR/config/.env"
cp docker-compose.yml "$OUTPUT_DIR/config/"
cp telegraf.conf "$OUTPUT_DIR/config/" 2>/dev/null || true

# ============================================
# 5. Create Archive
# ============================================
echo "📦 [5/5] Creating archive..."
tar -czf "${OUTPUT_DIR}.tar.gz" "$OUTPUT_DIR" && \
    echo "  ✅ Archive created: ${OUTPUT_DIR}.tar.gz"

# Cleanup uncompressed folder
rm -rf "$OUTPUT_DIR"

# Final summary
SIZE=$(du -h "${OUTPUT_DIR}.tar.gz" | cut -f1)
echo ""
echo "================================"
echo "✅ Backup Complete!"
echo "   File: ${OUTPUT_DIR}.tar.gz"
echo "   Size: $SIZE"
echo ""
echo "📋 To restore on new Pi:"
echo "   1. Copy backup to new Pi"
echo "   2. Run: ./scripts/restore.sh ${OUTPUT_DIR}.tar.gz"
echo "================================"
