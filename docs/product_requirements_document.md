# Brew-Brain Product Requirements Document (PRD)

## 1. Product Vision & Overview
Brew-Brain is an automated, AI-augmented smart dashboard and brewing assistant built for modern homebrewers. It acts as the central command center for the entire brewing lifecycle, integrating real-time telemetry from fermentation vessels with advanced planning, recipe management, and predictive intelligence.

The core objective of Brew-Brain is to eliminate the manual overhead of homebrewing logistics (inventory management, recipe calculations, pricing comparisons) while providing an intuitive, premium interface that tracks active fermentations in real-time.

## 2. Target Audience
- **Advanced Homebrewers**: Users who manage multiple fermenters, require precise temperature control, and rely on external software like Brewfather for recipe generation.
- **Data-Driven Brewers**: Users who appreciate visualizing specific gravity (SG) and temperature trends over time.
- **Cost-Conscious Brewers**: Users who want to optimize their ingredient purchases across multiple vendors automatically.

## 3. Core Features & Requirements

### 3.1 Real-Time Dashboard (Telemetry)
- **Requirement**: Display real-time data from Tilt Hydrometers and DS18B20 temperature probes.
- **Requirement**: Calculate real-time ABV based on the configured Original Gravity (OG) and current Specific Gravity (SG).
- **Requirement**: Display trend indicators (rising/falling) for temperature and SG.

### 3.2 Automation Hub
- **Requirement**: Provide a unified suite of tools for recipe planning and execution.
  - **Calculators**: Refractometer corrections, Carbonation levels, IBU scaling, and Priming Sugar calculations.
  - **Ingredient Scout**: A search engine limited to brewing vendors (The Malt Miller, Get Er Brewed) to find current prices for specific ingredients.
  - **Price Comparator**: Compare the total cost of a recipe's ingredient deficit across multiple supported vendors.
  - **Yeast Intelligence**: Extract yeast metadata (attenuation, flocculation, temp range) from an offline database or fallback to scraping manufacturer websites.

### 3.3 AI Brewmaster
- **Requirement**: A conversational AI interface powered by a locally hosted LLM (e.g., Llama 3 via Ollama).
- **Requirement**: The AI must be context-aware, meaning it has automatic access to the current batch's SG, temperature, and configured style.
- **Requirement**: Graceful fallback capabilities when the LLM is offline or unreachable.

### 3.4 Notifications & Alerts
- **Requirement**: Push notifications via Telegram.
- **Requirement**: Trigger alerts for anomaly detection (e.g., unexpected temperature spikes or stalled fermentation).
- **Requirement**: Respect configurable "Quiet Hours" to prevent alerts during the night.

### 3.5 Settings & Configuration
- **Requirement**: Provide a UI to configure API keys (Brewfather, SerpAPI, Telegram), batch parameters (Target FG, OG, Notes), and system preferences (Theme, Offset calibration).

## 4. Non-Functional Requirements
- **Performance**: The frontend must be statically generated where possible or fast-rendering client-side via Next.js. The API should respond in under 500ms for non-AI tasks.
- **Reliability**: The system must operate primarily on a local network (e.g., Raspberry Pi) and degrade gracefully if external internet connectivity is lost (e.g., caching local yeast data).
- **Aesthetics**: The UI must maintain a "premium" dark-mode glassmorphism aesthetic with smooth transitions, modern typography, and robust tooltips.

## 5. Success Metrics
- **Zero Client-Side Crashes**: 100% uptime for the UI components without React exceptions.
- **Accuracy**: Calculations (ABV, Refractometer) must perfectly match industry standard formulas.
- **Actionable AI**: The AI Brewmaster provides relevant troubleshooting rather than generic advice.
