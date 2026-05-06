# Product Definition - Brew Brain

## Vision
Brew Brain transforms the brewing experience by turning passive fermentation data into actionable intelligence. Beyond monitoring, it acts as a **Production Intelligence Layer** for the cellar, providing high-accuracy predictions and automated safety watchdogs.

## Target Audience
- **Fleet Operators:** Professional breweries monitoring multiple fermenters via a unified API.
- **Data-Driven Brewers:** Enthusiasts leveraging machine learning to optimize batch completion times and yeast performance.

## Core Goals
- **Predictive Accuracy:** Deliver highly accurate estimates for Final Gravity (FG) and completion dates using physics-informed machine learning and real-time accuracy tracking (MAE).
- **Proactive Safety:** Protect every batch with automated alerts for stuck fermentations, temperature runaways, and yeast anomalies.
- **Integration Readiness:** Provide a "Clean Handoff" API for seamless data ingestion from external brew-deck systems (e.g., PGBM).
- **Operational Simplicity:** Streamline cellar management with smart calibration and one-click label generation.

## Key Features
- **Async ML Engine:** Background model training and prediction powered by Celery and Redis.
- **MLOps Tracking:** Continuous logging of model performance metrics (MAE) to InfluxDB for Grafana-based auditing.
- **Automated Watchdog:** Real-time monitoring of sensor signals and Raspberry Pi system health.
- **Smart Calibration:** Zero-drift manual offset entry to synchronize Tilt readings with refractometers.
- **Keg Label Generation:** Automated generation of 4x6" labels with QR codes containing full batch metadata.
