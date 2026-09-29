# 🛠️ Brew-Brain Troubleshooting Knowledge Base

Common issues and proven fixes derived from historical deployment cycles.

---

## 1. Import Errors (`ModuleNotFoundError`)
- **Issue:** `No module named 'core.auth'` or similar.
- **Fix:** This is usually a `PYTHONPATH` or `working_dir` conflict in Docker. 
    - Ensure `docker-compose.yml` has `working_dir: /app` and `PYTHONPATH=/app`.
    - Ensure all imports in the code are root-relative (e.g., `from core.config` not `from app.core.config`).

## 2. Timezone Synchronization
- **Issue:** `Sync Loop Error: can't compare offset-naive and offset-aware datetimes`.
- **Fix:** Always use `datetime.now(timezone.utc)` for comparisons. InfluxDB data is always timezone-aware.

## 3. Database Connectivity
- **Issue:** InfluxDB or Grafana crash loops on startup.
- **Fix:** 
    - Check if `.env` exists on the host. 
    - Verify file permissions: `influxdb_data` and `grafana_data` must be writable by the Docker user (`472:472` for Grafana).

## 4. Frontend Blank Page
- **Issue:** Port 5000 loads but the page is empty.
- **Fix:** Likely a corrupted transfer of `app/static/index.html`. Re-sync the file and rebuild the container.

## 5. Pi Unreachable (no ping/SSH/web) but Still Running
- **Issue:** The Pi, dashboard and API all vanish from the network, but after a power cycle the app logs show it kept running the whole time.
- **Cause:** The Pi is on Wi-Fi (`wlan0`, SSID `Ballingarry-IOT`; `eth0` unused) and Wi-Fi power saving was on. The Pi's Broadcom radio is known to drop off the network with power save enabled and not recover.
- **Fix (applied 2026-09-29):**
    - `sudo iw dev wlan0 set power_save off` (immediate)
    - `sudo nmcli con modify preconfigured 802-11-wireless.powersave 2` (persists across reboots)
    - Verify: `iw dev wlan0 get power_save` → `off`
- **Diagnosing next time:** the system journal is now persistent (`/etc/systemd/journald.conf.d/brew-brain.conf`, capped at 100 MB), so `journalctl -b -1` shows the previous boot. Check `vcgencmd get_throttled` for power problems (`0x0` = none). A continuous `brain_data/brew_brain.log` across the outage means a network drop, not a crash or power loss.
- **Most robust fix:** use a wired Ethernet connection if the Pi is within reach of the router or a switch.
