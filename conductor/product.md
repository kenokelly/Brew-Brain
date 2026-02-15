# Initial Concept
Brew Brain is an intelligent brewery monitor for Tilt Hydrometers that uses AI to provide fermentation predictions, calibration, and real-time monitoring.

# Product Definition - Brew Brain

## Vision
Brew Brain aims to transform the homebrewing experience by turning passive fermentation data into actionable intelligence. By providing a professional-grade, zero-configuration monitoring stack, it empowers brewers with high-accuracy predictions and automated safety watchdogs.

## Target Audience
- **Homebrewers with Tilt Hydrometers:** Individuals seeking deeper insights into their fermentation data without complex manual setup.
- **Data-Driven Brewers:** Enthusiasts interested in leveraging machine learning to optimize batch completion times and yeast performance.

## Core Goals
- **Predictive Accuracy:** Deliver highly accurate estimates for Final Gravity (FG) and completion dates using physics-informed machine learning.
- **Proactive Safety:** Protect every batch with automated alerts for stuck fermentations, temperature runaways, and hardware connectivity issues.
- **Effortless Visualization:** Provide a "batteries-included" Grafana dashboard experience that works out-of-the-box.
- **Operational Simplicity:** Streamline brewery management with features like smart calibration and one-click keg label generation.

## Key Features
- **ML Fermentation Engine:** Logistic regression models using automated yeast fingerprinting and physics-informed bias for high-accuracy predictions.
- **Automated Watchdog:** Real-time monitoring of Tilt signals and Raspberry Pi health.
- **Smart Calibration:** Easy-to-use manual offset entry to correct sensor drift based on refractometer readings.
- **Keg Label Generation:** One-click generation of printable 4x6" labels with QR codes for easy batch tracking.
- **Zero-Config Dashboard:** Pre-provisioned Grafana dashboards and a modern Next.js mobile-friendly web interface.
