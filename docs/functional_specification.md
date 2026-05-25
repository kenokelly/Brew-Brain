# Brew-Brain Functional Specification

## 1. System Architecture
Brew-Brain follows a decoupled client-server architecture designed to run efficiently on low-resource hardware (e.g., Raspberry Pi) while providing a highly responsive user interface.

- **Frontend**: A Next.js (React) application serving as the UI layer. It leverages TailwindCSS for styling and React components for dynamic rendering.
- **Backend API**: A Python Flask application serving a RESTful JSON API under the `/api/` routing namespace. It uses blueprints to organize logic.
- **Time-Series Database**: InfluxDB handles all telemetry storage (Specific Gravity, Temperature, RSSI) queried via Flux.
- **Telemetry Ingestion**: Telegraf (or custom Python scripts) listen for Bluetooth Low Energy (BLE) broadcasts from the Tilt Hydrometer.

## 2. Hardware & Sensor Integration

### 2.1 Tilt Hydrometer
- The system reads BLE broadcasts containing SG and Temperature.
- **Calibration**: The backend applies an `offset` (configured via settings) to the raw SG reading.
- **State Management**: The API endpoint `/api/status` reads the latest data from `InfluxDB`, falling back to live memory state (`get_tilt_state()`) to ensure real-time accuracy.

### 2.2 DS18B20 Temperature Probe
- Used for measuring ambient or secondary temperatures.
- Data is read from the Linux filesystem at `/sys/class/thermal/thermal_zone0/temp` (or custom 1-wire paths).

## 3. Backend Services (`app/services/`)

### 3.1 AI Service (`ai.py`)
- Interfaces with a local `ollama` container to generate LLM responses.
- Payload generation injects context: current SG, batch name, and recent temperature.
- In the event of a timeout (15s) or missing container/model, the system gracefully degrades and returns a hardcoded "offline" template response.

### 3.2 Sourcing Service (`sourcing.py` & `scout.py`)
- Interfaces with the SerpAPI Google Shopping endpoints.
- Queries are strictly bounded by appending "homebrew" or targeting specific domains (`site:themaltmiller.co.uk`) to ensure only relevant brewing ingredients are returned.
- Computes aggregated pricing across multiple baskets for price comparison. Returns "Inconclusive" if a vendor lacks a specific ingredient.

### 3.3 Yeast Service (`yeast.py`)
- Provides offline yeast heuristics using a static dictionary mapping (`YEAST_DATABASE`).
- If an unknown strain is requested, the service performs a SerpAPI web search and naively scrapes the manufacturer's HTML using regex to extract attenuation, temperature ranges, and flocculation.

## 4. Automation & Calculators
- **Refractometer Correction**: Converts Brix to SG considering the Wort Correction Factor (WCF) and alcohol presence. Formula implemented in JavaScript on the frontend and validated.
- **ABV Calculation**: Derived dynamically based on OG and current SG using the standard equation: `(OG - SG) * 131.25`.

## 5. Deployment & Telemetry Infrastructure
- Handled via `docker-compose.yml`.
- Contains distinct containers:
  - `web` (Next.js)
  - `api` (Flask)
  - `influxdb` (Time-series DB)
  - `telegraf` (Agent)
  - `ollama` (LLM host)
  - `grafana` (Advanced legacy charting)
