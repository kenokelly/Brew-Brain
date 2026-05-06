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

## Host Status

| Component | Status | Metrics / Info |
|-----------|--------|----------------|
| **Pi Connectivity** | 🟢 Online | Responsive on port 5000 (ICMP/Ping blocked) |
| **Pi Health** | 🟢 Healthy | Temp: 48.5°C |
| **Active Batch** | 🍺 "IPA no 1" | SG: 1.010 (Target: 1.001) at 16.1°C |
| **Last Checked** | 2026-03-19 | Verified via `/api/status` |

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

### Phase 10 — ML Refinement (Priority: MEDIUM) 🟡

- [ ] **10.1 Fix Normalization Disconnect** — Ensure `normalize_features` is consistently used in both `train_models` and `predict_fg`.
- [ ] **10.2 Sliding Window Velocity** — Update `calculate_sg_velocity` in `features.py` to use a 24h window instead of a simple linear average.
- [ ] **10.3 Feature Expansion (Yeast & Style)** — Encode and include `yeast_strain` and `style` features in FG and Time models.
- [ ] **10.4 Hyperparameter Tuning** — Implement Grid/Randomized search in `train_models` to optimize Gradient Boosting parameters.
- [ ] **10.5 Library Standardization** — Either switch to the `xgboost` library or update docstrings/logging to reflect the use of `sklearn.ensemble`.

---

### Phase 11 — Infrastructure & Async (Priority: HIGH) 🟡

- [ ] **11.1 Integrate Redis** — Add `redis:alpine` to `docker-compose.yml` with memory limits.
- [ ] **11.2 Implement Celery** — Replace manual threading in `services/worker.py` and `services/scheduler.py` with Celery workers.
- [ ] **11.3 Config Store Migration** — Evaluate moving from InfluxDB to a more standard config store (SQLite/JSON) for better reliability.
- [ ] **11.4 Persistent Logging** — Ensure `/data/app_debug.log` is properly rotated and accessible via the UI.

---

### Phase 12 — Backend Refactoring (Priority: MEDIUM) ✅

- [x] **12.1 Modularize API Routes** — Split `api/routes.py` (37KB) into `batches.py`, `ml.py`, and `settings.py`.
- [x] **12.2 Clean Up Services** — Refactor `services/sourcing.py` (40KB) and consolidate `water.py`/`water_chemistry.py`.
- [x] **12.3 API Validation** — Implement Pydantic models for all request bodies and response schemas.
- [x] **12.4 Dependency Cleanup** — Verify and remove unused dependencies from `requirements.txt`.

---

### Phase 13 — Testing & Quality (Priority: LOW) ⚪

- [ ] **13.1 Increase Coverage** — Add unit tests for `worker.py`, `scheduler.py`, and `alerting.py`.
- [ ] **13.2 Automate Verifications** — Convert `verify_*.py` scripts into proper `pytest` integration tests.
- [ ] **13.3 Linting & Type Checking** — Add `mypy` and `ruff` to the CI pipeline for stricter code quality.

---

### Phase 14 — Frontend Optimization (Priority: LOW) ⚪

- [ ] **14.1 Component Refactor** — Break down `AnomalyWidget.tsx` and `nav.tsx` into smaller, reusable components.
- [ ] **14.2 Socket.io Optimization** — Ensure WebSocket connections are properly managed and don't cause memory leaks.
- [ ] **14.3 Loading States** — Implement skeleton loaders for all data-heavy views (Charts, Anomaly Widget).

---

### Phase 15 — Edge AI (Experimental) ⚪

- [ ] **15.1 Ollama Deployment** — Add `ollama/ollama` to `docker-compose.yml` and pull a quantized 3B/8B model (e.g., Llama-3 or Phi-4).
- [ ] **15.2 Narrative Brew Logs** — Create `services/ai.py` to feed InfluxDB trends to the SLM and generate automated Markdown brew summaries.
- [ ] **15.3 Natural Language "Brewmaster"** — Implement a chat interface to query fermentation state (e.g., "How is my IPA doing?").
- [ ] **15.4 Smart Troubleshooting** — Use the SLM to analyze anomalies and provide actionable advice (e.g., "Increase temp to finish fermentation").

---

### Phase 16 — Sourcing & SRE Fixes (Priority: HIGH) ✅
- [x] **16.1 Fix Price Comparison Logic (SRE)** — Removed the 3-item limit. Implemented `ThreadPoolExecutor` for concurrent fetching, an in-memory TTL cache, and thread-safe domain rate-limiting.
- [x] **16.2 Improve Scraper Reliability** — Updated `search_vendor_direct` with robust JSON-LD parsing and introduced a 429/403 Circuit Breaker in `get_page_content`.
- [x] **16.3 Implement Brewfather Pagination** — Updated `fetch_brewfather_recipes` and `fetch_recipe_by_tag` in `alerts.py` to support `start_after` pagination.
- [x] **16.4 Broaden Ingredient Matching** — Enhanced `normalize_ingredient_name` and `INGREDIENT_ALIASES` with fuzzy matching (`difflib`).
- [x] **16.5 Restrict Vendor Allowlist** — Ensured `ALLOWED_DOMAINS` strictly limits scraping to only The Malt Miller and Get Er Brewed.
- [x] **16.6 Robust Sourcing Logic (SRE)** — Implemented JSON-LD (`application/ld+json`) parsing for accurate price/stock extraction.
- [x] **16.7 Fuzzy Ingredient Matching** — Introduced sequence matching (`difflib`) to analyze vendor product titles.

---

### Phase 17 — Maintenance & Observability (Priority: HIGH) ✅

> 32 GB SD card — disk is the tightest constraint on this Pi. Proactive monitoring prevents silent failures.

- [x] **17.1 Disk Usage Health Endpoint** — Add `GET /api/health/disk` returning total/used/free bytes and percentage for the SD card. Trigger a Telegram alert when usage exceeds 80%.
- [x] **17.2 Docker Image Pruning** — Add a cron script (`scripts/prune_docker.sh`) to run `docker image prune -f` and `docker builder prune -f` weekly. Log output to `/data/maintenance.log`.
- [x] **17.3 InfluxDB Retention Policy** — Configure a retention policy on the `fermentation` bucket (e.g. 90 days) to prevent unbounded growth. Archive older data to Parquet exports before drop.
- [x] **17.4 Log Rotation** — Implement `RotatingFileHandler` in Python logging config for `app_debug.log` (max 5 MB × 3 backups). Add `--log-opt max-size=10m` to Docker Compose log driver.
- [x] **17.5 Container Memory Limits** — Add `mem_limit` to `docker-compose.yml` for each container: InfluxDB (512 MB), Grafana (256 MB), Flask (384 MB), Telegraf (128 MB), Nginx (64 MB).
- [x] **17.6 SD Card Health Check** — Add SMART/wear-level monitoring via `scripts/sd_health.sh` using `iostat` or `/sys/block/mmcblk0/stat` to detect degrading I/O performance before failure.
- [x] **17.7 Scheduled Maintenance Summary** — Weekly Telegram message with disk %, container memory usage, InfluxDB bucket size, and uptime.
- [x] **17.8 Disable Tilt Notifications When Idle** — Add a "brew active" toggle (settings or auto-detect from Brewfather batch status). When no brew is active, suppress all Tilt-related Telegram alerts (temp deviation, stall warnings, signal loss) to avoid noise.

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
