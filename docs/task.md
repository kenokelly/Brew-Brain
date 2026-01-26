# Brew Brain: AI/ML Implementation Tasks

## Phase 1: Anomaly Detection (Priority: HIGH) ✅ COMPLETE

### Week 1: Rule-Based Alerts

- [x] **Temperature Deviation Alert**
  - Trigger: temp outside yeast min/max ± 2°F for >30min
  - Location: `app/services/learning.py`
  - Test: Simulate temp spike, verify Telegram alert

- [x] **Stalled Fermentation Detection**
  - Trigger: SG change < 0.001 over 24 hours during active ferment
  - Query: Calculate SG slope from last 24h readings
  - Alert: "Fermentation may have stalled"

- [x] **Runaway Fermentation Detection**
  - Trigger: SG drop > 0.020 in 12 hours
  - Alert: "Rapid fermentation - check temperature"

- [x] **Tilt Signal Loss Alert**
  - Trigger: No reading for > 60 minutes
  - Existing: Partially in `status.py`, enhance

### Week 2: Statistical Anomaly Detection

- [x] **Z-Score Based Anomaly**
  - Calculate rolling mean/std for temp and SG rate
  - Flag readings > 2.5 std deviations
  - Add `anomaly_score` field to API response

- [x] **Dashboard Anomaly Widget**
  - Show anomaly count on dashboard
  - Color-coded severity (yellow/red)
  - Click to see details

---

## Phase 2: Data Pipeline (Priority: HIGH) ✅ COMPLETE

### Data Export

- [x] **Create Parquet Export Endpoint**
  - Endpoint: `GET /api/export/batch/<batch_id>`
  - Format: Parquet for efficient ML training
  - Fields: timestamp, temp, sg, batch_name, yeast, style

- [x] **Batch History Aggregator**
  - Query all completed batches from Brewfather
  - Pull corresponding Tilt data from InfluxDB
  - Store combined dataset for training

- [x] **Feature Engineering Module**
  - Calculate: SG velocity, temp variance, time-in-phase
  - Normalize features for ML input
  - Location: `app/ml/features.py` (Updated to `app/ml`)

---

## Phase 3: FG Prediction Model (Priority: MEDIUM) ✅ COMPLETE

### Model Development

- [x] **Training Data Preparation**
  - Collect: OG, yeast strain, temp profile, final FG
  - Minimum: 20 completed batches
  - Split: 80% train, 20% validation

- [x] **Gradient Boosting FG Predictor**
  - Features: OG, sg_velocity, temp_variance, avg_temp
  - Target: Final Gravity
  - Accuracy goal: ±0.003 SG

- [x] **Time-to-FG Predictor**
  - Features: Current SG, OG, velocity, temp
  - Target: Days remaining
  - Update prediction daily during ferment

- [x] **Model Serving Endpoint**
  - Endpoint: `POST /api/ml/train` and `GET /api/ml/predict`
  - Returns: predicted_fg, days_remaining, confidence
  - Real-time feature extraction for active batch

### UI Integration

- [x] **Prediction Display Card**
  - Show on Dashboard when fermenting
  - "Predicted FG: 1.012 (±0.003)"
  - "Est. completion: 3 days"

- [x] **Prediction Visuals**
  - Show live feature analysis (velocity, variance)
  - Method/Confidence reporting

---

## Phase 4: External Learning (Priority: LOW)

- [ ] **Recipe Scraper Service**
  - Source: Public BeerXML repositories
  - Extract: style, OG, FG, yeast, ferment schedule
  - Store: Local SQLite for fast queries

- [ ] **Style Embedding Model**
  - Train: Word2Vec on recipe descriptions
  - Output: Style → vector mapping
  - Use: Find similar styles for comparison

- [ ] **Peer Comparison Feature**
  - "Your IPA vs average IPA"
  - Show OG/FG/attenuation comparison
  - Suggest optimizations

---

## Infrastructure Tasks

### Async ML Worker (Optional)

- [ ] **Add Redis to Docker Compose**
  - Image: redis:alpine
  - Port: 6379 (internal only)
  - Memory limit: 128MB

- [ ] **Celery Worker Setup**
  - Tasks: train_model, batch_predict, export_data
  - Run in separate container
  - Share InfluxDB access

### Monitoring

- [ ] **ML Metrics Dashboard**
  - Grafana panel: prediction accuracy over time
  - Track: MAE, RMSE for FG predictions
  - Alert if accuracy degrades

---

## File Organization

```
app/
├── ml/
│   ├── __init__.py
│   ├── anomaly.py        # Anomaly detection
│   ├── prediction.py     # FG/time prediction
│   ├── features.py       # Feature engineering
│   └── models/           # Saved model files
│       ├── fg_predictor.joblib
│       └── time_predictor.joblib
├── services/
│   └── learning.py       # Existing, extend
└── api/
    └── ml_routes.py      # ML API endpoints
```

---

## Dependencies to Add

```txt
# requirements.txt additions
scikit-learn>=1.3.0
xgboost>=2.0.0
pyarrow>=14.0.0  # Parquet support
joblib>=1.3.0    # Model serialization
# Optional for async
celery>=5.3.0
redis>=5.0.0
```

---

## Next Steps

1. Review this task list
2. Answer questions in requirements.md
3. Prioritize which phase to start
4. Estimate historical batch count for training
