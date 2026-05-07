#!/bin/bash
# sd_health.sh — SD card I/O and wear monitoring for the Raspberry Pi
# Designed for cron: 0 4 * * 1 /home/pi/Brew-Brain/scripts/sd_health.sh
#
# Reads kernel I/O counters and disk health metrics.
# Logs output to /data/maintenance.log

set -euo pipefail

LOG_FILE="$(dirname "$0")/../data/maintenance.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "" >> "$LOG_FILE"
echo "=== SD Card Health — $TIMESTAMP ===" >> "$LOG_FILE"

# 1. Disk usage
echo "[disk usage]" >> "$LOG_FILE"
df -h / >> "$LOG_FILE" 2>&1

# 2. I/O stats from kernel (if available)
STAT_FILE="/sys/block/mmcblk0/stat"
if [ -f "$STAT_FILE" ]; then
    echo "[mmcblk0 stat]" >> "$LOG_FILE"
    cat "$STAT_FILE" >> "$LOG_FILE" 2>&1
else
    echo "[mmcblk0 stat] Not available" >> "$LOG_FILE"
fi

# 3. iostat snapshot (if installed)
if command -v iostat &> /dev/null; then
    echo "[iostat]" >> "$LOG_FILE"
    iostat -d mmcblk0 1 1 >> "$LOG_FILE" 2>&1
else
    echo "[iostat] Not installed — consider: sudo apt install sysstat" >> "$LOG_FILE"
fi

# 4. Docker disk usage
echo "[docker disk]" >> "$LOG_FILE"
docker system df >> "$LOG_FILE" 2>&1

echo "=== Done ===" >> "$LOG_FILE"
