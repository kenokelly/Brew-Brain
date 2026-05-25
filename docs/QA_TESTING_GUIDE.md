# Brew Brain Master QA & Testing Guide

This document contains end-to-end testing procedures for the major features developed across various phases. Use this guide to ensure new deployments haven't broken existing functionality.

---

## Phase 19: Kiosk & Tap Management Polish

**Objective:** Verify that the Kiosk mode displays correctly on the Pi and that pouring updates the math reliably.

### 1. Kiosk Display (Edge-to-Edge)
- **Action:** Open the `/kiosk` route on the Pi or a tablet.
- **Expected:** The left navigation sidebar should be completely hidden. The display should use 100% of the screen.
- **Action:** Tap the "Fullscreen" button (if not already full screen).
- **Expected:** The browser should enter native full-screen mode.

### 2. Pour Math & Visual Feedback
- **Action:** In Kiosk mode, press the "Pour" button on an active tap.
- **Expected:** 
  - The remaining volume (Litres) should decrease by the pour amount without crashing.
  - The percentage bar should visually shrink.
  - The color of the percentage bar should turn Orange/Red if it drops below the warning threshold.
  - *(Mobile only)* The device should trigger a haptic vibration.

### 3. Tap State Synchronization
- **Action:** Go to `/settings` and click "Manage Taps".
- **Expected:** The input form should explicitly display the "Remaining Volume" instead of just defaulting to 0L. If a tap had 10L left, the form must show 10L. 

---

## Sprint D: Board Operations & System Health

**Objective:** Verify the daily background reporting and live telemetry.

### 1. System Health Dashboard
- **Action:** Navigate to the main dashboard.
- **Expected:** The "System Health" widget should be visible.
- **Verify:** It should display real-time SD Card disk usage, RAM usage, and CPU temperature.

### 2. Scheduled Daily Reports
- **Action:** Wait for (or manually trigger) the daily report cron job (08:30 Weekdays / 11:00 Weekends).
- **Expected:** The Telegram bot should send a beautifully formatted "Daily Fermentation Report" summarizing gravity velocity and status for the active batch.

---

## Phase 17: SRE Maintenance & Observability

**Objective:** Ensure the automated background maintenance scripts are functioning.

### 1. Disk Health & Alerts
- **Action:** Ping the `GET /api/health/disk` endpoint.
- **Expected:** Returns JSON with total, used, free bytes, and percentage.
- **Action:** Fill the disk beyond 80% (or temporarily lower the threshold in code).
- **Expected:** A Telegram alert is fired immediately warning of low disk space.

### 2. Maintenance Cron Logs
- **Action:** SSH into the Pi and run `cat /data/maintenance.log`.
- **Expected:** You should see timestamps of `docker image prune` running successfully.

### 3. Tilt Silence (Idle Mode)
- **Action:** In Settings, ensure no Brewfather batch is set to "Active Fermentation".
- **Expected:** Disconnect the Tilt or change its temperature dramatically.
- **Verify:** No Telegram alerts should fire. The system must remain silent when no brew is active.

---

## Phase 16: Sourcing & SRE Logic

**Objective:** Verify the web scraper is efficiently pulling ingredient prices.

### 1. Vendor Price Comparison
- **Action:** Go to the **Sourcing** tab. Enter a recipe tag or ingredients like `Citra Hops`.
- **Expected:** The UI should fetch prices concurrently (using the ThreadPoolExecutor) from The Malt Miller and Get Er Brewed.
- **Verify:** Results should load significantly faster than in earlier versions. The JSON-LD parser should accurately grab the price and stock status without false positives.

### 2. Fuzzy Matching
- **Action:** Search for an oddly spelled ingredient (e.g., `Maris Otter Pale Ale Malt`).
- **Expected:** The `difflib` sequence matcher should still correctly identify and link it to standard `Maris Otter` products on the vendor sites.

---

## Phase 15 & 18: Edge AI & Troubleshooting

**Objective:** Verify the local Ollama LLM is responding and releasing memory.

### 1. Natural Language Brewmaster
- **Action:** Go to the `/chat` tab and ask a question like "Why is my beer cloudy?"
- **Expected:** A response streams back. 

### 2. RAM Optimization (Waste Management)
- **Action:** SSH into the Pi and run `docker stats`. Watch the `ollama` container while querying the chat.
- **Expected:** Memory usage spikes during the generation. Within a few seconds of completion, the memory should plummet back down (verifying `keep_alive: 0` is working).

### 3. Proactive Yeast Advice
- **Action:** On the dashboard, ensure a yeast strain (e.g., US-05) is active.
- **Expected:** The "Proactive Advice" widget should display specific tips regarding that exact yeast strain's preferred temperature range or attenuation behavior, pulled from the local SQLite database.
