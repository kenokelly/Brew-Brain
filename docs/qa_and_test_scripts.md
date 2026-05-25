# Brew-Brain QA & Test Scripts

## Overview
This document serves as the formal QA testing script for verifying the stability and functionality of Brew-Brain before any major deployment to the SRE/Raspberry Pi environment.

---

## 1. Regression Test Suite

### 1.1 UI Stability & Tab Navigation
- **Test Case**: Verify no client-side exceptions occur on page load.
- **Steps**:
  1. Load the Dashboard (`/`).
  2. Click the "Automation" tab in the sidebar.
  3. Click through the sub-tabs: Ingredient Scout, Sourcing, Yeast Scraper, Calculators.
- **Expected Result**: Pages load instantly. No "Application Error" or "Client-Side Exception" overlays appear.

### 1.2 Telemetry Ingestion (Status API)
- **Test Case**: Verify the backend is correctly exposing InfluxDB data to the frontend.
- **Steps**:
  1. Open a browser and navigate to `http://<device-ip>:5000/api/status`.
  2. Inspect the JSON payload.
- **Expected Result**: `sg`, `temp`, and `status` keys are present. The `test_mode` flag should be correct based on your `.env`.

---

## 2. Feature Verification Scripts

### 2.1 Refractometer Calculator
- **Test Case**: Verify the formula handles floats correctly without throwing type errors.
- **Steps**:
  1. Navigate to Automation -> Calculators.
  2. In the Refractometer section, enter `15.0` for Original Brix, `8.0` for Final Brix, and `1.04` for WCF.
  3. Click "Calculate".
- **Expected Result**: Corrected SG is successfully calculated. No crashes occur.

### 2.2 Ingredient Scout Scope
- **Test Case**: Verify the scout prevents generic items from dominating search results.
- **Steps**:
  1. Navigate to Automation -> Ingredient Scout.
  2. Search for "Citra".
- **Expected Result**: Results must specifically mention "hops", "pellets", or be sourced from "The Malt Miller" or "Get Er Brewed". General Amazon results for non-brewing items must be filtered out.

### 2.3 Keg Label Generation
- **Test Case**: Verify PDF/HTML label generation routes correctly.
- **Steps**:
  1. Navigate to Settings.
  2. Verify the Batch Name is filled out.
  3. Click "Download Keg Label".
- **Expected Result**: A new tab opens successfully rendering the label HTML without a 404 error.

---

## 3. Resilience & Degradation Testing

### 3.1 AI Bot Fallback
- **Test Case**: Ensure the application doesn't lock up if the AI container is missing or times out.
- **Steps**:
  1. Stop the Ollama container: `docker stop ollama`
  2. Navigate to AI Chat.
  3. Send a message: "Hello".
- **Expected Result**: After ~15 seconds, the bot replies with the graceful degradation template: *"The Brewmaster is currently offline. I can see your batch is at [X] SG, but I can't provide detailed advice right now."*

### 3.2 Missing External API Keys
- **Test Case**: Ensure the Sourcing tool doesn't crash if SerpAPI is missing.
- **Steps**:
  1. Remove the `SERPAPI_KEY` from settings/environment.
  2. Attempt a sourcing deficit search.
- **Expected Result**: A red error toast or text appears stating "Missing API Key", rather than spinning indefinitely or throwing a React exception.
