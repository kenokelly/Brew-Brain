# PRD & Implementation Plan: G40 Calculators (Module 4)

## 1. Executive Summary
This plan addresses the unique hardware characteristics of the Grainfather G40 to ensure mathematical precision for recipe formulation and brew-day execution.

## 2. Technical Decisions
*   **Formula:** Standardize on **Tinseth** for IBUs and **Linear-Exponential Decay** for grain efficiency (matching the G40's high-gravity drop-off curve).
*   **Hardware Integration:** Hardcode the G40 "utilization boost" (1.1x) into the core library to ensure user-centric results.

## 3. Implementation Plan
1.  **Backend Fix:** Add a specific "G40 Profile" to all calculations.
2.  **UI Upgrade:** "Hardware Presets" dropdown.
    *   Animated "Efficiency Warning" gauge that moves in real-time as the user adds grain to the recipe.
3.  **Data:** Implement a "Recipe Refractometer" tool for Brix-to-SG conversion during the mash.

## 4. Pros & Cons
*   **Pros:** Exact parity with Grainfather app but running locally and integrated with live monitoring.
*   **Cons:** Formula is proprietary-ish (requires empirical tuning).

## 5. Stability Fixes
*   Previous versions had `min() arg is an empty sequence` in the math service; this plan implements a mandatory "Validation Decorator" for all numeric inputs.
