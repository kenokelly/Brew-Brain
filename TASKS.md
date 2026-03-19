# Brew Brain — Master Plan

> Single source of truth for project status, requirements, and roadmap.
> Last updated: 2026-03-19

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

### Phase 5 — Pi Stability (Priority: HIGH) 🟡

> Directly impacts reliability. Do this first.

- [x] **5.1 Replace Playwright with Requests + BeautifulSoup** ✅
  - Files: `app/services/sourcing.py`
  - Playwright fully removed; `get_page_content` uses `requests` + `BeautifulSoup`

- [x] **5.2 Move Scraping to Background Jobs** ✅
  - Files: `app/services/sourcing.py`, `app/api/routes.py`
  - `compare_recipe_prices_async` runs in background thread; API returns job ID

- [x] **5.3 Replace Pandas with Lightweight Alternatives** ✅
  - `alerts.py`: stdlib `csv` (parse_tilt_csv)
  - `batch_exporter.py`: `pyarrow.Table` / `pq.write_table`
  - `prediction.py`: `pyarrow.parquet` + list-of-dicts
  - Pandas removed from `requirements-core.txt` and `requirements.txt`

---

### Phase 6 — Security ✅

- [x] **6.1 Add Authentication** — API token via env var, checked via `@require_api_token` decorator
- [x] **6.2 Fix SSRF Risk in Sourcing** — Tag input sanitised, outbound requests restricted

---

### Phase 7 — Code Quality ✅

- [x] **7.1 Fix Exception Handling** — Specific exceptions, meaningful error responses
- [x] **7.2 Clean Up Lazy Imports** — Heavy imports moved to top of file
- [x] **7.3 Improve Testing** — Pytest with `unittest.mock.patch`, InfluxDB fixtures

---

### Phase 8 — DevOps & Optimisation ✅

- [x] **8.1 GitHub Actions CI Pipeline** — `linux/amd64` + `linux/arm64` images built on GitHub, pushed to GHCR
- [x] **8.2 Static Export for Frontend** — Next.js static export served via Nginx container
- [x] **8.3 Config Caching** — Config cached in memory, refreshed on explicit update only

---

### Phase 9 — Web UI Integration (Priority: MEDIUM) 🟡

- [x] **9.1 Config Bridge** — Refactor modules to fetch API keys from Brew Brain settings
- [x] **9.2 API Endpoints** — Register Scout and Health Check as internal UI routes
- [x] **9.3 Bot Hook** — Integrate `alerts.py` with the existing Telegram Bot
- [x] **9.4 Non-Intrusive Scout** — Implement `scout.py` using SerpApi
- [x] **9.5 Inventory Sync** — Connect to Brewfather API for stock levels
- [x] **9.6 Weekly Price Watch** — Scheduled Telegram alerts for key ingredients
- [x] **9.7 G40 Calculator** — Tinseth IBU and grain scaling
- [x] **9.8 Water Module** — RO water profiles for West Coast IPA and NEIPA
- [x] **9.9 Cost per Pint** — End-to-end costing logic
- [x] **9.10 GitHub Logger** — Automate Markdown brew log generation

---

### Phase 4 — External Learning ✅

- [x] **4.1 Recipe Scraper Service** — Public BeerXML repositories → local SQLite (dedup, seed sources, ingredient extraction, weekly cron)
- [x] **4.2 Style Embedding Model** — Ingredient-based TF-IDF on recipe grains/hops/yeast
- [x] **4.3 Peer Comparison** — "Your IPA vs average IPA" with OG/FG/ABV/IBU/attenuation percentiles

---

### Infrastructure (Optional / Future)

- [ ] Add Redis to Docker Compose (redis:alpine, 128 MB limit)
- [ ] Celery worker for async ML (train_model, batch_predict, export_data)
- [ ] ML Metrics Dashboard in Grafana (prediction accuracy over time)
- [ ] Alert if prediction accuracy degrades

---

## Success Metrics

| Metric                     | Target   |
|----------------------------|----------|
| Anomaly detection accuracy | > 90%    |
| FG prediction accuracy     | ± 0.003  |
| Time-to-FG accuracy        | ± 2 days |
| False positive rate        | < 5%     |
| API latency (with ML)      | < 500 ms |

---

## Reference Docs

| Document | Purpose |
|----------|---------|
| [README.md](file:///Users/kokelly/Brew-Brain/README.md) | Installation & usage |
| [user_guide.md](file:///Users/kokelly/Brew-Brain/docs/user_guide.md) | End-user guide (settings, Telegram, calibration) |
| [disaster_recovery.md](file:///Users/kokelly/Brew-Brain/docs/disaster_recovery.md) | Backup & restore procedures |
| [walkthrough.md](file:///Users/kokelly/Brew-Brain/docs/walkthrough.md) | Initial deployment walkthrough |
| [agent.md](file:///Users/kokelly/Brew-Brain/agent.md) | Agent conventions & Pi connection info |
