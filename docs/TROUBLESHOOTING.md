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
