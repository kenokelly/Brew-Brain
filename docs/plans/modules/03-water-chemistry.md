# PRD & Implementation Plan: Water Chemistry (Module 3)
**Base Truth:** `BrunWater-Ken.xlsm`

## 1. Executive Summary
This plan details the complete re-engineering of the Brew-Brain Water Chemistry module. We are abandoning generic ion profiles in favor of a full implementation of the logic found in the user's customized Bru'n Water model.

## 2. Technical Decisions
*   **Engine Logic:** Use the exact ionic contribution constants found in `BrunWater-Ken.xlsm` (e.g., Gypsum providing 232.8mg Ca per gram).
*   **Anion/Cation Balancing:** Implement the sequential addition logic (Magnesium first, then Anions) to prevent over-shooting targets.
*   **Acid Buffering:** Integrate the 88% Lactic and 75% Phosphoric acid titration math for sparge and mash acidification.

## 3. Implementation Plan
1.  **Backend Fix:** Rewrite `app/services/water_chemistry.py` to match the spreadsheet's precision.
2.  **Mash pH (Phase 9.9):** Create `app/services/mash_chemistry.py` to implement the spreadsheet's grain buffering models.
3.  **UI Upgrade:** Build a "Bru'n Water" style interactive lab in React.
    *   Add Ion Balance indicators (Anion vs Cation).
    *   Add color-coded "Safe Range" markers (e.g., Calcium should be 50-150ppm).

## 4. Pros & Cons
*   **Pros:** Scientific parity with the user's gold standard (Excel); roots out previous "simplified math" bugs.
*   **Cons:** Higher complexity; UI requires more input fields (Mash vs Sparge volumes).

## 5. Stability Fixes
*   Previous versions didn't account for the "shared ions" in Epsom salt properly; the new sequential engine fixes this dependency loop.
