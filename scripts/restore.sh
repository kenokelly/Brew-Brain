#!/bin/bash
# ============================================
# Brew Brain Full System Restore Script
# ============================================
# Restores: InfluxDB, Grafana, Node-RED, Brew Brain config
# Usage: ./restore.sh <backup_archive.tar.gz>
#
# PREREQUISITES:
#   - Docker installed
#   - Node-RED installed
#   - Run from Brew-Brain project root

set -e

if [ -z "$1" ]; then
    echo "❌ Usage: ./restore.sh <backup_archive.tar.gz>"
    exit 1
fi

ARCHIVE="$1"
if [ ! -f "$ARCHIVE" ]; then
    echo "❌ Backup file not found: $ARCHIVE"
    exit 1
fi

echo "🍺 Brew Brain Full System Restore"
echo "=================================="
echo "Restoring from: $ARCHIVE"
echo ""
echo "⚠️  WARNING: This will overwrite existing data!"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Extract archive
BACKUP_DIR=$(basename "$ARCHIVE" .tar.gz)
echo "📦 Extracting archive..."
tar -xzf "$ARCHIVE"

# ============================================
# 1. Stop Running Services
# ============================================
echo "🛑 [1/6] Stopping services..."
docker compose down 2>/dev/null || true
sudo systemctl stop nodered 2>/dev/null || true

# ============================================
# 2. Restore Environment Config
# ============================================
echo "⚙️  [2/6] Restoring configuration..."
if [ -f "$BACKUP_DIR/config/.env" ]; then
    cp "$BACKUP_DIR/config/.env" .env
    echo "  ✅ Environment file restored"
fi

if [ -f "$BACKUP_DIR/config/docker-compose.yml" ]; then
    cp "$BACKUP_DIR/config/docker-compose.yml" docker-compose.yml
fi

if [ -f "$BACKUP_DIR/config/telegraf.conf" ]; then
    cp "$BACKUP_DIR/config/telegraf.conf" telegraf.conf
fi

# Restore brain_data
if [ -d "$BACKUP_DIR/config/brain_data" ]; then
    rm -rf brain_data
    cp -r "$BACKUP_DIR/config/brain_data" brain_data
    echo "  ✅ Brain data restored"
fi

# ============================================
# 3. Start Docker Stack (creates volumes)
# ============================================
echo "🐳 [3/6] Starting Docker stack..."
docker compose up -d --build
echo "  Waiting for containers to initialize (30s)..."
sleep 30

# ============================================
# 4. Restore InfluxDB Data
# ============================================
echo "📊 [4/6] Restoring InfluxDB..."
if [ -d "$BACKUP_DIR/influxdb" ]; then
    # Copy backup into container
    docker cp "$BACKUP_DIR/influxdb" influxdb:/tmp/restore_backup
    
    # Restore the backup
    docker exec influxdb influx restore /tmp/restore_backup \
        --token "$INFLUX_TOKEN" \
        --org homebrew \
        --full 2>/dev/null && \
        echo "  ✅ InfluxDB data restored" || \
        echo "  ⚠️  InfluxDB restore had warnings (check manually)"
    
    # Cleanup
    docker exec influxdb rm -rf /tmp/restore_backup
else
    echo "  ⚠️  No InfluxDB backup found"
fi

# ============================================
# 5. Restore Grafana Data
# ============================================
echo "📈 [5/6] Restoring Grafana..."
if [ -d "$BACKUP_DIR/grafana" ]; then
    # Stop grafana briefly
    docker stop grafana 2>/dev/null || true
    
    # Restore data
    rm -rf grafana_data
    cp -r "$BACKUP_DIR/grafana/grafana_data" grafana_data 2>/dev/null || \
        cp -r "$BACKUP_DIR/grafana" grafana_data
    
    # Restore provisioning if exists
    if [ -d "$BACKUP_DIR/grafana/provisioning" ]; then
        mkdir -p grafana/provisioning
        cp -r "$BACKUP_DIR/grafana/provisioning"/* grafana/provisioning/
    fi
    
    # Fix permissions
    sudo chown -R 472:472 grafana_data 2>/dev/null || true
    
    # Restart Grafana
    docker start grafana
    echo "  ✅ Grafana data restored"
else
    echo "  ⚠️  No Grafana backup found"
fi

# ============================================
# 6. Restore Node-RED
# ============================================
echo "🔴 [6/6] Restoring Node-RED..."
NODERED_DIR="$HOME/.node-red"

if [ -d "$BACKUP_DIR/nodered" ]; then
    # Ensure Node-RED directory exists
    mkdir -p "$NODERED_DIR"
    
    # Copy flow files
    cp "$BACKUP_DIR/nodered"/flows*.json "$NODERED_DIR/" 2>/dev/null && \
        echo "  ✅ Node-RED flows restored"
    
    # Copy settings and credentials
    [ -f "$BACKUP_DIR/nodered/settings.js" ] && cp "$BACKUP_DIR/nodered/settings.js" "$NODERED_DIR/"
    [ -f "$BACKUP_DIR/nodered/.config.runtime.json" ] && cp "$BACKUP_DIR/nodered/.config.runtime.json" "$NODERED_DIR/"
    [ -f "$BACKUP_DIR/nodered/flows_cred.json" ] && cp "$BACKUP_DIR/nodered/flows_cred.json" "$NODERED_DIR/"
    
    # Restore installed nodes from package.json
    if [ -f "$BACKUP_DIR/nodered/package.json" ]; then
        cp "$BACKUP_DIR/nodered/package.json" "$NODERED_DIR/"
        cd "$NODERED_DIR" && npm install --production 2>/dev/null
        cd -
        echo "  ✅ Node-RED packages restored"
    fi
    
    # Restart Node-RED
    sudo systemctl start nodered
else
    echo "  ⚠️  No Node-RED backup found"
fi

# ============================================
# 7. Restore Brew Brain Config via API
# ============================================
echo "🧠 Restoring Brew Brain config..."
if [ -f "$BACKUP_DIR/config/brew_brain_config.json" ]; then
    sleep 10  # Wait for API to be ready
    curl -s -X POST http://localhost:5000/api/restore \
        -F "file=@$BACKUP_DIR/config/brew_brain_config.json" \
        > /dev/null && \
        echo "  ✅ Brew Brain config restored via API" || \
        echo "  ⚠️  Could not restore via API (check manually)"
fi

# Cleanup
rm -rf "$BACKUP_DIR"

echo ""
echo "=================================="
echo "✅ Restore Complete!"
echo ""
echo "📋 Verify services:"
echo "   - Dashboard:  http://$(hostname -I | awk '{print $1}'):5000"
echo "   - Grafana:    http://$(hostname -I | awk '{print $1}'):3000"
echo "   - Node-RED:   http://$(hostname -I | awk '{print $1}'):1880"
echo "   - TiltPi UI:  http://$(hostname -I | awk '{print $1}'):1880/ui"
echo "=================================="
