# Tasks: Web UI Integration Roadmap

## Phase 1: Bridge & Integration 🔌

- [ ] 1.1 **Config Bridge:** Refactor modules to fetch API keys from Brew Brian settings.
- [ ] 1.2 **API Endpoints:** Register Scout and Health Check functions as internal UI routes.
- [ ] 1.3 **Bot Hook:** Integrate `modules/alerts.py` with the existing Telegram Bot.

## Phase 2: Scout & Sourcing Engine 🛒

- [ ] 2.1 **Non-Intrusive Scout:** Implement `modules/scout.py` using SerpApi logic.
- [ ] 2.2 **Inventory Sync:** Connect to Brewfather API to check stock levels (Task 3.4).
- [ ] 2.3 **Weekly Watch:** Schedule price watch alerts via Telegram for Citra/Simcoe/Malt.

## Phase 3: Hardware Scaling & Water 🧪

- [ ] 3.1 **G40 Calculator:** Implement Tinseth IBU and grain scaling.
- [ ] 3.2 **Water Module:** Add RO profiles for West Coast IPA and NEIPA.
- [ ] 3.3 **Costing:** Implement "Cost per Pint" logic.

## Phase 4: Machine Learning & Monitoring 📟

- [ ] 4.1 **Live Data Bridge:** Connect `modules/alerts.py` to the Pi 5 Tilt/SmartRef stream.
- [ ] 4.2 **4PL Model:** Implement the `kinetics.py` module for standalone ML prediction.
- [ ] 4.3 **Thermal Precision:** Monitor Glycol Chiller stability (Standard Deviation check).
- [ ] 4.4 **Local ML Optimization:** Optimize Scipy/NumPy for standalone Pi 5 performance.

## Phase 5: Automation & Archiving 🚀

- [ ] 5.1 **GitHub Logger:** Automate Markdown log generation to the repository.
- [ ] 5.2 **End-to-End Test:** Run a full "Scout-to-Log" workflow through the Web UI.
