# Brew Brain: Task List

## Phase 1: Anomaly Detection (Priority: HIGH) ✅ COMPLETE

### Week 1: Rule-Based Alerts
- [x] **Temperature Deviation Alert**
- [x] **Stalled Fermentation Detection**
- [x] **Runaway Fermentation Detection**
- [x] **Tilt Signal Loss Alert**

### Week 2: Statistical Anomaly Detection
- [x] **Z-Score Based Anomaly**
- [x] **Dashboard Anomaly Widget**

## Phase 2: Data Pipeline (Priority: HIGH) ✅ COMPLETE

- [x] **Create Parquet Export Endpoint**
- [x] **Batch History Aggregator**
- [x] **Feature Engineering Module**

## Phase 3: FG Prediction Model (Priority: MEDIUM) ✅ COMPLETE

- [x] **Training Data Preparation**
- [x] **Gradient Boosting FG Predictor**
- [x] **Time-to-FG Predictor**
- [x] **Model Serving Endpoint**
- [x] **Prediction Display Card**
- [x] **Prediction Visuals**

## Phase 4: External Learning (Priority: LOW)

- [ ] **Recipe Scraper Service** — Public BeerXML repositories
- [ ] **Style Embedding Model** — Word2Vec on recipe descriptions
- [ ] **Peer Comparison Feature** — "Your IPA vs average IPA"

---

## Phase 5: Pi Stability & Performance (Priority: HIGH)

*From code review — these directly impact reliability on the Pi.*

### 5.1 Replace Playwright with Requests + BeautifulSoup
- **Why:** Playwright launches headless Chromium — ~500MB+ RAM on a Pi causes OOM kills
- **Where:** `app/services/sourcing.py`, `app/ml/scraper.py`
- **Action:** Replace all Playwright browser calls with `requests` + `BeautifulSoup`
- **If JS rendering strictly needed:** Use a separate lightweight service, not inline browser launches

### 5.2 Move Scraping to Background Jobs
- **Why:** Synchronous scraping blocks Flask, freezing the dashboard
- **Where:** `app/services/sourcing.py`, `app/api/routes.py`
- **Action:** Use `APScheduler` — API returns a "Job Started" ID, results pushed via SocketIO

### 5.3 Replace Pandas with Lightweight Alternatives
- **Why:** Pandas + NumPy consume significant RAM for small homebrew datasets
- **Action:** Use standard Python dicts/lists/comprehensions. `statistics` stdlib for stats

---

## Phase 6: Security (Priority: HIGH)

### 6.1 Add Authentication
- **Why:** Zero auth — anyone on LAN has full control including config overwrite
- **Where:** `app/main.py`, `app/api/routes.py`
- **Action:** Add Flask HTTP Basic Auth or token auth. Minimum: env var for API token checked via decorator

### 6.2 Fix SSRF Risk in Sourcing
- **Why:** `/api/sourcing/compare-by-tag/<tag>` passes user input to external web requests
- **Action:** Validate/sanitise tag input. Restrict outbound requests to known vendor domains only

---

## Phase 7: Code Quality (Priority: MEDIUM)

### 7.1 Fix Exception Handling
- **Why:** Broad `except Exception` everywhere hides real errors
- **Action:** Catch specific exceptions (`requests.Timeout`, `KeyError`, `InfluxDBError`). Return meaningful error responses

### 7.2 Clean Up Lazy Imports
- **Why:** Heavy imports inside functions mask dependency issues and cause first-request lag
- **Action:** Move imports to top of file. Use proper feature flags for optional deps

### 7.3 Improve Testing
- **Action:** Switch to `pytest` with `unittest.mock.patch`. Add fixtures for InfluxDB mocking. Cover core services

---

## Phase 8: DevOps & Optimisation (Priority: MEDIUM)

### 8.1 GitHub Actions Build Pipeline
- **Why:** Building Docker images (especially Next.js) on the Pi is slow and may OOM
- **Action:** Build `linux/arm64` images on GitHub runners, push to GHCR. Pi just pulls pre-built images

### 8.2 Static Export for Frontend
- **Why:** Full Next.js SSR with Node.js runtime is heavy for a Pi
- **Action:** Add `output: 'export'` to Next.js config. Serve static files via Nginx or Flask

### 8.3 Config Caching
- **Why:** InfluxDB queried for every config read — unnecessary overhead
- **Action:** Cache config in memory or local JSON file. Refresh on explicit update only

---

## Infrastructure Tasks

### Async ML Worker (Optional)
- [ ] **Add Redis to Docker Compose** — redis:alpine, port 6379, 128MB limit
- [ ] **Celery Worker Setup** — Tasks: train_model, batch_predict, export_data

### Monitoring
- [ ] **ML Metrics Dashboard** — Grafana panel: prediction accuracy over time
- [ ] **Alert if accuracy degrades**

---

## File Organization
```
app/
├── ml/
│   ├── __init__.py
│   ├── anomaly.py
│   ├── prediction.py
│   ├── features.py
│   └── models/
│       ├── fg_predictor.joblib
│       └── time_predictor.joblib
├── services/
│   └── learning.py
└── api/
    └── ml_routes.py
```

---

## Dependencies to Add
```txt
scikit-learn>=1.3.0
xgboost>=2.0.0
pyarrow>=14.0.0
joblib>=1.3.0
# Optional for async
celery>=5.3.0
redis>=5.0.0
```

---

## Notes
- Phases 5-8 added from OpenClaw code review (2026-02-15)
- **Prioritise Phase 5 first** — directly impacts Pi stability
- Phase 6 should be done before exposing beyond home LAN
- Each task should be its own feature branch + PR per agent.md conventions
