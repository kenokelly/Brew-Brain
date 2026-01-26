# Brew Brain: AI/ML Fermentation Intelligence

## Vision

Transform Brew Brain from a monitoring dashboard into an **Intelligent Fermentation System** that uses machine learning to predict fermentation outcomes, detect anomalies, and provide actionable insights.

---

## Core Requirements

### 1. Data Pipeline (Foundation)

| Requirement | Priority | Status |
|-------------|----------|--------|
| Real-time TiltPi data ingestion via Telegraf | P0 | ✅ Done |
| Historical data storage in InfluxDB | P0 | ✅ Done |
| API access to fermentation readings | P0 | ✅ Done |
| Brewfather batch metadata sync | P1 | ✅ Done |
| Data export for ML training (CSV/Parquet) | P1 | ✅ Done |

### 2. AI/ML Features

#### 2.1 Anomaly Detection (P0)

Detect unusual fermentation behavior in real-time:

- **Temperature spikes/drops** outside yeast tolerance
- **Stalled fermentation** (SG not changing for >24h)
- **Runaway fermentation** (SG dropping too fast)
- **Signal loss** (Tilt offline >1h)

**Implementation Options:**

| Approach | Complexity | Accuracy | Training Data |
|----------|------------|----------|---------------|
| Rule-based thresholds | Low | Medium | None |
| Statistical (Z-score) | Low | Medium | Minimal |
| Isolation Forest | Medium | High | 10+ batches |
| LSTM Autoencoder | High | Highest | 50+ batches |

**Recommendation:** Start with rule-based + Z-score, graduate to Isolation Forest.

---

#### 2.2 Fermentation Prediction (P1)

Predict fermentation outcomes using historical data:

| Prediction | Input Features | Target |
|------------|----------------|--------|
| Final Gravity (FG) | OG, yeast, temp profile, current SG slope | FG ± 0.002 |
| Time to FG | Current SG, temp, yeast strain | Days ± 1 |
| ABV Estimate | OG, predicted FG | ABV% |
| Optimal Ramp Day | Style, current SG, yeast | Day number |

**Model Options:**

- **XGBoost/LightGBM:** Fast, interpretable, works with 20+ batches
- **Prophet (Facebook):** Good for time-series, handles seasonality
- **LSTM/Transformer:** Best accuracy, needs 100+ batches

---

#### 2.3 Style-Aware Intelligence (P2)

Learn from external brewing knowledge:

- Scrape BeerXML recipes from public databases
- Build embeddings of style → fermentation profiles
- Compare user's batch to "peers" of same style
- Suggest temperature adjustments based on style norms

**Data Sources:**

- Brewfather public recipes (with permission)
- Brewersfriend recipe database
- BeerSmith cloud recipes
- Academic brewing datasets

---

### 3. Architecture Decision: Microservices vs Monolith

#### Current State: Monolith

```
┌─────────────────────────────────────────┐
│              Brew Brain (Flask)         │
│  ┌─────────────────────────────────┐    │
│  │ API Routes │ Services │ ML Logic│    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

#### Proposed: Lightweight Microservices

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Brew Brain  │  │   ML Worker  │  │  Data Sync   │
│   (Flask)    │◄─┤  (FastAPI)   │  │   (Celery)   │
│   Port 5000  │  │   Port 5001  │  │   Internal   │
└──────────────┘  └──────────────┘  └──────────────┘
       │                 │                 │
       └─────────────────┴─────────────────┘
                         │
                  ┌──────────────┐
                  │   InfluxDB   │
                  └──────────────┘
```

#### Recommendation

| Factor | Monolith | Microservices |
|--------|----------|---------------|
| Complexity | ✅ Low | ⚠️ Medium |
| Pi Resources | ✅ Minimal | ⚠️ Higher RAM |
| ML Isolation | ❌ Blocks main | ✅ Async |
| Deployment | ✅ Single image | ⚠️ Multi-container |
| Scaling | ❌ Limited | ✅ Independent |

**Decision:** Use **hybrid approach**:

- Keep Flask for API/UI
- Add **Celery + Redis** for async ML tasks
- ML runs in background, doesn't block API

---

### 4. Local Deployment Platforms (Railway Alternatives)

| Platform | Self-Hosted | Ease | Pi Support | Cost |
|----------|-------------|------|------------|------|
| **Coolify** | ✅ Yes | ⭐⭐⭐⭐ | ✅ ARM64 | Free |
| **CapRover** | ✅ Yes | ⭐⭐⭐ | ✅ ARM | Free |
| **k3s** | ✅ Yes | ⭐⭐ | ✅ Native | Free |
| **Docker Compose** | ✅ Yes | ⭐⭐⭐⭐⭐ | ✅ Native | Free |
| **Portainer** | ✅ Yes | ⭐⭐⭐⭐ | ✅ ARM64 | Free |

**Recommendation:** Stay with **Docker Compose** for simplicity. Add **Coolify** if multi-server deployment needed later.

---

## Implementation Roadmap

### Phase 1: Anomaly Detection (2 weeks) ✅ DONE

- [x] Add temperature deviation alerts (rule-based)
- [x] Add stalled fermentation detection (SG slope < 0.001/day)
- [x] Add Tilt signal loss alerts
- [x] Create anomaly dashboard widget

### Phase 2: Data Export & Training (1 week) ✅ DONE

- [x] Export historical batches to Parquet
- [x] Create training data pipeline
- [x] Label historical anomalies

### Phase 3: ML Prediction (3 weeks) ✅ DONE

- [x] Train FG prediction model (Gradient Boosting)
- [x] Train time-to-FG model
- [x] Add prediction endpoint to API
- [x] Display predictions in UI

### Phase 4: Style Intelligence (2 weeks)

- [ ] Scrape public recipe data
- [ ] Build style embedding model
- [ ] Implement "peer comparison" feature
- [ ] Add style-based recommendations

### Phase 5: Async ML Worker (Optional)

- [ ] Add Redis to stack
- [ ] Implement Celery worker
- [ ] Move heavy ML to background tasks

---

## Technical Stack Additions

| Component | Purpose | Resource Impact |
|-----------|---------|-----------------|
| **scikit-learn** | Anomaly detection | Low (~50MB) |
| **XGBoost** | Prediction models | Low (~100MB) |
| **Pandas** | Data processing | Already installed |
| **Redis** (optional) | Task queue | Low (~30MB) |
| **Celery** (optional) | Async workers | Low |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Anomaly detection accuracy | >90% |
| FG prediction accuracy | ±0.003 |
| Time-to-FG accuracy | ±2 days |
| False positive rate | <5% |
| API latency (with ML) | <500ms |

---

## Questions to Resolve

1. **Data Volume:** How many historical batches are available for training?
2. **Labeling:** Are there known "problem batches" to use as anomaly examples?
3. **Compute:** Should heavy ML training run on Pi or offload to Mac?
4. **Alerts:** How should anomaly alerts be delivered (Telegram, email, push)?
5. **Privacy:** Any concerns with scraping external recipe data?
