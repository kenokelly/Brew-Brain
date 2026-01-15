# Requirements: G40 Brewing Mission Control (Web UI Integrated)

## 1. Project Overview

A Python-based automation suite for recipe discovery, hardware-specific scaling, and predictive fermentation monitoring, integrated into the existing Brew Brian Web UI and GitHub.

## 2. Hardware Specifications

- **Brewing System:** Grainfather G40 (40L capacity, 23L batch volume).
- **Fermentation:** 2 x 7 Gallon SS Brewtech Unitanks + 1/5hp Glycol Chiller.
- **Monitoring:** Tilt Hydrometer (via TiltPi on Pi 5), Anton Paar SmartRef, and EasyDens.
- **Water:** 100% Reverse Osmosis (RO) base.

## 3. Software Integration Requirements

- **Web UI:** Pull API keys (SerpApi, Brewfather, GitHub, Telegram) directly from existing UI settings.
- **Communications:** Use the existing Brew Brian Telegram Bot for all status and health alerts.
- **Deployment:** Must operate standalone on a Raspberry Pi 5 (optimized for low CPU/RAM).

## 4. Functional Requirements

- **Sourcing:** Non-intrusive SerpApi Shopping for The Malt Miller and Get Er Brewed.
- **Inventory:** Sync with Brewfather Inventory to check stock before suggesting purchases.
- **ML Prediction:** Implement a 4-Parameter Logistic (4PL) sigmoid model for FG and "Time to Terminal" forecasting.
- **Kinetics:** Use Arrhenius-type logic to adjust timelines based on Glycol Chiller performance.
- **Archiving:** Automatic Brew Day Log generation to GitHub in Markdown format.
