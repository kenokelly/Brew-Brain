# 🛠️ Brew-Brain SRE & Operations Guide

This document defines the operational procedures for maintaining the Brew-Brain production stack on Raspberry Pi 5.

---

## 1. Stack Architecture
Brew-Brain runs as a multi-container Docker stack joined by the `brewery-net` network.

- **Frontend:** Next.js (Port 3001)
- **API:** Flask (Port 5000)
- **Background Worker:** Celery (Internal)
- **Message Broker:** Redis (Port 6379)
- **Database:** InfluxDB v2 (Port 8086)
- **Visualization:** Grafana (Port 3000)
- **Ingestion:** Telegraf (Port 8094)

---

## 2. Disaster Recovery & Restoration

### Full System Restore (Target: < 10 mins)
If the Pi hardware fails, follow these steps:

1.  **Prepare Hardware:** Install fresh Raspberry Pi OS (Bookworm 64-bit).
2.  **Clone Repo:** `git clone https://github.com/kenokelly/brew-brain.git`
3.  **Restore Data:** 
    - Copy your `brain_data/`, `influxdb_data/`, and `grafana_data/` volumes from your backup source to `~/brew-brain/`.
4.  **Launch Stack:** `docker compose up -d --build`

### Volume Mapping Reference
| Volume | Purpose |
| :--- | :--- |
| `./brain_data` | ML models (.joblib), parquet exports, and application logs. |
| `./influxdb_data` | Persistent time-series sensor data. |
| `./grafana_data` | Dashboard configurations and user settings. |

---

## 3. Maintenance & Troubleshooting

### Clearing the Task Queue
If ML training tasks are hanging or the Celery worker is unresponsive:
```bash
# Flush Redis (Warning: This clears all pending tasks)
docker exec -it redis redis-cli flushall
# Restart the worker
docker compose restart celery-worker
```

### Checking ML Model Health
Verify that the model MAE (Mean Absolute Error) is being logged to InfluxDB:
```bash
docker exec -it influxdb influx query 'from(bucket:"fermentation") |> range(start:-24h) |> filter(fn:(r) => r._measurement == "ml_metrics")'
```

### Manual Image Rebuild
If code changes in `/app` are not reflecting:
```bash
docker compose up -d --build --force-recreate
```

---

## 4. Security (The CISO Gate)
- **API Token:** Ensure `BREW_BRAIN_API_TOKEN` is set in `.env`.
- **Bearer Auth:** All external integrations MUST use `Authorization: Bearer <token>`.
- **Grafana:** Default login is `admin/admin`. Change this immediately upon first boot.
