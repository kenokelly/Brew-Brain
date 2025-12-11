# Brew-Brain Deployment Walkthrough

## Overview
Successfully deployed the **Brew-Brain** fermentation monitoring stack to the Raspberry Pi (`192.168.155.226`). The system is now fully operational, capturing data from the Tilt Hydrometer (via local simulation/forwarding), processing it with the Python backend, and visualizing it on the Grafana dashboard.

## Infrastructure Setup
The deployment consists of four Docker containers orchestrated via `docker-compose`:
1.  **`brew-brain`**: The customized Python flask app handling business logic, API endpoints, calibration, and ML predictions.
    *   **Port**: 5000 (Web Interface)
2.  **`influxdb`**: Time-series database for storing sensor readings.
    *   **Port**: 8086
3.  **`telegraf`**: Data collector receiving metrics and pushing to InfluxDB.
4.  **`grafana`**: Visualization platform.
    *   **Port**: 3000 (Dashboard)

## Key Challenges & Solutions

### 1. Service Crash Loop (InfluxDB & Grafana)
*   **Issue**: `influxdb` container kept restarting, causing `grafana` to fail dependent health checks.
*   **Cause**: Missing environment variables (`INFLUX_USER`, `INFLUX_PASS`) on the Raspberry Pi; the local `.env` was gitignored.
*   **Fix**: Created a `~/.env` file on the Pi with the required secrets and fixed file permissions for `grafana_data` and `influxdb_data` (was root-owned, needed `472:472`).

### 2. Missing Dashboards
*   **Issue**: Grafana loaded but showed "No dashboards found."
*   **Cause**:
    1.  Provisioning files (`fermentation.json`) were in the wrong directory (`datasources` instead of `dashboards`).
    2.  `dashboard.yml` pointed to a host path (`/var/lib/...`) instead of the container path (`/etc/grafana/...`).
*   **Fix**: Restructured the directories to standard Grafana provisioning layout and updated the path in `dashboard.yml`.

### 3. Data Synchronization Bug (Missing Gravity)
*   **Issue**: No gravity data was appearing on the dashboard, despite raw data being in InfluxDB.
*   **Logs**: `Sync Loop Error: can't compare offset-naive and offset-aware datetimes`.
*   **Cause**: The Python code was comparing `datetime.utcnow()` (naive) with InfluxDB timestamps (timezone-aware).
*   **Fix**: Patched `brew_brain.py` to use `datetime.now(timezone.utc)` everywhere.
*   **Important**: Had to **rebuild the Docker image** (`docker compose up --build`) on the Pi for the code changes to take effect, as the code is baked into the image, not just volume-mounted.

### 4. Blank Web Page
*   **Issue**: accessing `http://192.168.155.226:5000` showed a blank page.
*   **Cause**: `app/static/index.html` was truncated (file corruption during transfer), effectively an empty HTML shell.
*   **Fix**: Restored the full frontend code and synced it to the remote host.

## Verification
*   **Services**: All containers (`brew-brain`, `influxdb`, `telegraf`, `grafana`) are `Up`.
*   **Data Flow**: `brew-brain` logs show `Info - Wrote X points`, confirming it is reading from Influx, processing/calibrating, and writing back.
*   **Visualization**: Grafana displays the "Brew Brain Production" dashboard with Gravity (SG) and Temperature (converted to °C).
*   **Web UI**: The main app UI at port 5000 loads correctly, showing status cards and settings.

## Access Points
*   **Web App**: [http://192.168.155.226:5000](http://192.168.155.226:5000)
*   **Grafana**: [http://192.168.155.226:3000](http://192.168.155.226:3000) (User: `admin` / Password: `admin` - *change on first login*)
