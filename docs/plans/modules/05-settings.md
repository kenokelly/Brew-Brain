# PRD & Implementation Plan: System Settings (Module 5)

## 1. Executive Summary
The Settings module manages the environment state. This plan roots out "Stale Config" bugs by implementing a reactive configuration engine.

## 2. Technical Decisions
*   **Storage:** Move from a simple JSON file to a **Local-First Proxy** (in-memory cache synced to disk).
*   **Validation:** Use **Pydantic V2** for strict type enforcement on all settings (prevents strings being saved as numbers, which breaks the calculators).

## 3. Implementation Plan
1.  **Backend Fix:** Implement `SettingsManager` in `core/config.py` with thread-safe atomic writes.
2.  **UI Upgrade:** Segmented settings (Hardware, AI, API Keys).
    *   Add "Connectivity Test" buttons for Telegram/Brewfather keys.
    *   Add "Reset to Factory" safety switch.

## 4. Pros & Cons
*   **Pros:** Prevents system-wide crashes due to invalid user input.
*   **Cons:** Requires a backend restart/reload for certain hardware-level changes.

## 5. Stability Fixes
*   Fixes the issue where a missing API key causes a silent 500 error in the background services.
