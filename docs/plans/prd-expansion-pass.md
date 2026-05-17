# PRD: Brew-Brain Core Expansion (Phases 9.7, 9.8, 14.2)

## 1. Executive Summary
This document outlines the Product Requirements and Implementation Plan for three critical enhancements to the Brew-Brain ecosystem:
1.  **G40 Tinseth IBU & Grain Scaling Calculator** (Brewing Physics)
2.  **Advanced Water Chemistry Module** (Mineral Optimization)
3.  **Premium Dashboard UI Polish** (hardware-accelerated UX)

---

## 2. Phase 9.7: G40 Tinseth IBU & Grain Scaling

### Why this plan?
The Grainfather G40 has unique dead-space and boil-off characteristics. Standard formulas often over- or under-estimate IBUs and efficiency. We are implementing a hardware-specific calculator to ensure "Brew-Day vs. Reality" alignment.

### Key Decisions
*   **Formula:** Standardizing on the **Tinseth Formula** (industry standard for accuracy) but adding a "G40 Coefficient" to account for the specific pump/recirculation speed.
*   **Architecture:** Logic will live in `services/hop_math.py` to keep the API thin and reusable by both the Web UI and the AI Brewmaster.

### Implementation Plan
1.  Create `app/services/hop_math.py` with `calculate_tinseth_ibu`.
2.  Add `calculate_grain_scaling` to handle efficiency drops on high-gravity batches.
3.  Expose `POST /api/calculator/ibu`.

### Pros & Cons
*   **Pros:** Highly accurate IBU predictions; prevents over-bittering.
*   **Cons:** Requires user input for "Boil Gravity" which may be manually measured.

---

## 3. Phase 9.8: Water Chemistry Module

### Why this plan?
Water is 95% of beer. "West Coast IPA" vs "NEIPA" requires drastically different Mineral-to-Sulfate ratios. We are moving from "monitoring" to "active recipe assistance."

### Key Decisions
*   **Approach:** We will provide **Target Profiles** (West Coast, NEIPA, Stout) rather than a free-form ion calculator to simplify the UX and reduce "decision fatigue."
*   **Waste Management:** Data is stored in a tiny 2KB JSON file in `data/`, avoiding SQL/InfluxDB bloat.

### Implementation Plan
1.  Expand `app/services/water_chemistry.py` with standard profiles.
2.  Implement `calculate_salt_additions(current_profile, target_profile)`.

### Pros & Cons
*   **Pros:** Scientific precision for style accuracy.
*   **Cons:** Salt additions (Gypsum/Calcium Chloride) must still be weighed manually by the user.

---

## 4. Phase 14.2: Premium Dashboard UI Polish

### Why this plan?
As an "Intelligent Fermentation System," the UI must feel "alive." We are moving beyond static cards to high-performance, animated data visualizations.

### Key Decisions
*   **Engine:** Using **Framer Motion** for hardware-accelerated transitions. This ensures 60FPS on the Raspberry Pi's GPU rather than taxing the CPU.
*   **Waste Management:** Implementing "Windowed Rendering" for logs to prevent DOM bloat which crashes mobile browsers.

### Implementation Plan
1.  Refactor `app/page.tsx` to use `AnimatePresence`.
2.  Implement "Glassmorphism" styling for a premium modern aesthetic.
3.  Add "Live Pulse" indicators for active WebSocket streams.

### Pros & Cons
*   **Pros:** World-class UX; easier to read at a glance in the brewery.
*   **Cons:** Increased initial bundle size (~50KB increase).

---

## 5. Deployment & Lifecycle Status
*   **Phase 18 Status:** Fully implemented and verified locally. **Deployment to Production (Pi 5)** is scheduled to occur simultaneously with these 3 phases to minimize downtime.
*   **Lifecycle Management:** All PRDs and Plans are now stored in `docs/plans/` and committed to Git to ensure a "Decision Audit Trail."
