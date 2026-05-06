#!/bin/bash
# prune_docker.sh — Weekly Docker cleanup for the Raspberry Pi
# Designed for cron: 0 3 * * 0 /home/pi/Brew-Brain/scripts/prune_docker.sh
#
# Removes: dangling images, stopped containers, build cache
# Logs output to /data/maintenance.log (mounted volume)

set -euo pipefail

LOG_FILE="/home/pi/Brew-Brain/brain_data/maintenance.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "" >> "$LOG_FILE"
echo "=== Docker Prune — $TIMESTAMP ===" >> "$LOG_FILE"

# Prune dangling images
echo "[images]" >> "$LOG_FILE"
docker image prune -f >> "$LOG_FILE" 2>&1

# Prune build cache
echo "[builder]" >> "$LOG_FILE"
docker builder prune -f >> "$LOG_FILE" 2>&1

# Prune stopped containers (safety: only exited ones)
echo "[containers]" >> "$LOG_FILE"
docker container prune -f >> "$LOG_FILE" 2>&1

# Report disk after cleanup
echo "[disk]" >> "$LOG_FILE"
df -h / >> "$LOG_FILE" 2>&1

echo "=== Done ===" >> "$LOG_FILE"
