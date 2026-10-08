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

## 6. Self-Recovery (installed on every deploy)
`ops/recovery/` makes the Pi recover by itself; `deploy_and_verify.sh` runs `sudo ops/recovery/install.sh` (idempotent; `--uninstall` removes it).
- **Network watchdog** (`brew-brain-recovery.timer`, every minute, starts 3 min after boot): if the gateway (or 1.1.1.1) is unreachable it escalates: 3 min → reconnect `wlan0`, 6 min → Wi-Fi radio off/on, 10 min → restart NetworkManager, 15 min → reboot. At most 3 reboots per 6 h, then it only nudges the Wi-Fi every 30 min, so a router/ISP outage can't cause a reboot loop.
- **App watchdog** (same timer): restarts `brew-brain` / `brew-brain-web` after 3 failed health checks in a row, at most 3 restarts per hour each. Skipped while the network is down.
- **Hardware watchdog**: `RuntimeWatchdogSec=15s` — if the system hangs, the SoC resets the Pi.
- **Kernel panic**: reboots after 10 s (`kernel.panic=10`, `panic_on_oops=1`).
- **Report**: once the network and API are healthy again, one Telegram message (also in the autopilot journal) lists what happened and what fixed it.
- **Logs**: `journalctl -t brew-brain-recovery`; state in `/var/lib/brew-brain-recovery/`. Previous boot: `journalctl -b -1`.
