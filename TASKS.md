# Brew Brain — Master Plan

> Single source of truth for project status, requirements, and roadmap.
> Last updated: 2026-03-05

---

## Vision

Transform Brew Brain from a monitoring dashboard into an **Intelligent Fermentation System** — ML predictions, anomaly detection, cost-aware sourcing, and a premium web UI — running reliably on a Raspberry Pi 5.

---

## Architecture

```
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   Next.js Web    │   │   Brew Brain     │   │    Grafana       │
│   (Port 3001)    │──▶│   Flask API      │   │   (Port 3000)    │
│   React/Tailwind │   │   (Port 5000)    │   │   Dashboards     │
└──────────────────┘   └────────┬─────────┘   └────────┬─────────┘
                                │                       │
                       ┌────────┴───────────────────────┤
                       │         InfluxDB               │
                       │       (Port 8086)              │
                       └────────┬───────────────────────┘
                                │
                       ┌────────┴─────────┐
                       │     Telegraf     │
                       │  (Tilt ingest)   │
                       └──────────────────┘
```

**Stack:** Flask · Next.js (App Router) · InfluxDB v2 · Telegraf · Grafana · Docker Compose  
**Host:** Raspberry Pi 5 (`192.168.155.226`)

---

## Completed Work

### Phase 1 — Anomaly Detection ✅

- Rule-based alerts: temperature deviation, stalled/runaway fermentation, Tilt signal loss
- Z-score statistical anomaly detection
- Dashboard anomaly widget with severity colour coding

### Phase 2 — Data Pipeline ✅

- Parquet export endpoint (`GET /api/export/batch/<id>`)
- Batch history aggregator (Brewfather + InfluxDB)
- Feature engineering module (`app/ml/features.py`)

### Phase 3 — FG Prediction ✅

- Gradient Boosting FG predictor and time-to-FG predictor
- Physics-informed ML using yeast manufacturer specs
- Model serving endpoints (`POST /api/ml/train`, `GET /api/ml/predict`)
- Prediction display card and visuals in UI

---

## Open Work

### Phase 5 — Pi Stability (Priority: HIGH) 🔴

> Directly impacts reliability. Do this first.

- [ ] **5.1 Replace Playwright with Requests + BeautifulSoup**
  - Files: `app/services/sourcing.py`, `app/ml/scraper.py`
  - Why: Playwright launches headless Chromium (~500 MB RAM) causing OOM on the Pi
  - If JS rendering is strictly needed, use a separate lightweight service

- [ ] **5.2 Move Scraping to Background Jobs**
  - Files: `app/services/sourcing.py`, `app/api/routes.py`
  - Why: Synchronous scraping blocks Flask and freezes the dashboard
  - Use APScheduler; API returns a job ID, results pushed via SocketIO

- [ ] **5.3 Replace Pandas with Lightweight Alternatives**
  - Why: Pandas + NumPy consume significant RAM for small homebrew datasets
  - Use stdlib `statistics`, dicts, and list comprehensions instead

---

### Phase 6 — Security (Priority: HIGH) 🔴

> Required before exposing beyond home LAN.

- [ ] **6.1 Add Authentication**
  - Files: `app/main.py`, `app/api/routes.py`
  - Why: Zero auth — anyone on LAN has full control including config overwrite
  - Minimum: env var for API token, checked via decorator

- [ ] **6.2 Fix SSRF Risk in Sourcing**
  - Endpoint: `/api/sourcing/compare-by-tag/<tag>`
  - Validate and sanitise tag input; restrict outbound requests to known vendor domains

---

### Phase 7 — Code Quality (Priority: MEDIUM) 🟡

- [ ] **7.1 Fix Exception Handling**
  - Catch specific exceptions (`requests.Timeout`, `KeyError`, `InfluxDBError`)
  - Return meaningful error responses instead of generic 500s

- [ ] **7.2 Clean Up Lazy Imports**
  - Move heavy imports to top of file; use feature flags for optional deps

- [ ] **7.3 Improve Testing**
  - Switch to pytest with `unittest.mock.patch`
  - Add fixtures for InfluxDB mocking; cover core services

---

### Phase 8 — DevOps & Optimisation (Priority: MEDIUM) 🟡

- [ ] **8.1 GitHub Actions CI Pipeline**
  - Build `linux/arm64` Docker images on GitHub runners, push to GHCR
  - Pi just pulls pre-built images (avoids OOM during on-device builds)

- [ ] **8.2 Static Export for Frontend**
  - Add `output: 'export'` to Next.js config
  - Serve static files via Nginx or Flask (removes Node.js runtime from Pi)

- [ ] **8.3 Config Caching**
  - Cache config in memory or local JSON file
  - Refresh on explicit update only (currently queries InfluxDB on every read)

---

### Phase 9 — Web UI Integration (Priority: MEDIUM) 🟡

- [ ] **9.1 Config Bridge** — Refactor modules to fetch API keys from Brew Brain settings
- [ ] **9.2 API Endpoints** — Register Scout and Health Check as internal UI routes
- [ ] **9.3 Bot Hook** — Integrate `alerts.py` with the existing Telegram Bot
- [ ] **9.4 Non-Intrusive Scout** — Implement `scout.py` using SerpApi
- [ ] **9.5 Inventory Sync** — Connect to Brewfather API for stock levels
- [ ] **9.6 Weekly Price Watch** — Scheduled Telegram alerts for key ingredients
- [ ] **9.7 G40 Calculator** — Tinseth IBU and grain scaling
- [ ] **9.8 Water Module** — RO water profiles for West Coast IPA and NEIPA
- [ ] **9.9 Cost per Pint** — End-to-end costing logic
- [ ] **9.10 GitHub Logger** — Automate Markdown brew log generation

---

### Phase 4 — External Learning (Priority: LOW) 🟢

- [ ] **4.1 Recipe Scraper Service** — Public BeerXML repositories → local SQLite
- [ ] **4.2 Style Embedding Model** — Word2Vec on recipe descriptions
- [ ] **4.3 Peer Comparison** — "Your IPA vs average IPA" with OG/FG/attenuation

---

### Infrastructure (Optional / Future)

- [ ] Add Redis to Docker Compose (redis:alpine, 128 MB limit)
- [ ] Celery worker for async ML (train_model, batch_predict, export_data)
- [ ] ML Metrics Dashboard in Grafana (prediction accuracy over time)
- [ ] Alert if prediction accuracy degrades

---

## Success Metrics

| Metric                    | Target   |
|---------------------------|----------|
| Anomaly detection accuracy | > 90%    |
| FG prediction accuracy     | ± 0.003  |
| Time-to-FG accuracy        | ± 2 days |
| False positive rate         | < 5%     |
| API latency (with ML)      | < 500 ms |

---

## Reference Docs

| Document | Purpose |
|---|---|
| [README.md](file:///Users/kokelly/Brew-Brain/README.md) | Installation & usage |
| [user_guide.md](file:///Users/kokelly/Brew-Brain/docs/user_guide.md) | End-user guide (settings, Telegram, calibration) |
| [disaster_recovery.md](file:///Users/kokelly/Brew-Brain/docs/disaster_recovery.md) | Backup & restore procedures |
| [walkthrough.md](file:///Users/kokelly/Brew-Brain/docs/walkthrough.md) | Initial deployment walkthrough |
| [agent.md](file:///Users/kokelly/Brew-Brain/agent.md) | Agent conventions & Pi connection info |
